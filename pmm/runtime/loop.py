# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/runtime/loop.py
"""Minimal runtime loop orchestrator for PMM v2."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from pmm.core.event_log import EventLog
from pmm.core.mirror import Mirror
from pmm.core.meme_graph import MemeGraph
from pmm.core.commitment_manager import CommitmentManager
from pmm.core.schemas import Claim
from pmm.core.validators import validate_claim
from pmm.core.semantic_extractor import (
    extract_commitments,
    extract_claims,
    extract_closures,
    extract_reflect,
)
from pmm.core.concept_graph import ConceptGraph
from pmm.core.concept_ops_compiler import compile_assistant_message_concepts
from pmm.commitments.binding import extract_exec_binds
from pmm.runtime.autonomy_kernel import AutonomyKernel, KernelDecision
from pmm.runtime.prompts import compose_system_prompt
from pmm.core.identity_manager import maybe_append_identity_adoptions
from pmm.runtime.reflection import TurnDelta, build_reflection_text
from pmm.retrieval.pipeline import run_retrieval_pipeline, RetrievalConfig
from pmm.runtime.context_renderer import render_context
from pmm.retrieval.vector import (
    selection_digest,
    ensure_embedding_for_event,
)
from pmm.runtime.bindings import ExecBindRouter
from pmm.runtime.autonomy_supervisor import AutonomySupervisor
from pmm.runtime.ontology_autonomy import OntologyAutonomy
from pmm.core.autonomy_tracker import AutonomyTracker
from pmm.core.commitment_analyzer import CommitmentAnalyzer
from pmm.learning.outcome_tracker import build_outcome_observation_content
from pmm.runtime.indexer import Indexer
from pmm.runtime.ctl_injector import CTLLookupInjector
import asyncio
import threading
import time


DEBUG = False  # Set to True for debugging


class RuntimeLoop:
    def __init__(
        self,
        *,
        eventlog: EventLog,
        adapter,
        replay: bool = False,
        autonomy: bool = True,
        thresholds: Optional[Dict[str, int]] = None,
    ) -> None:
        self.eventlog = eventlog
        self.mirror = Mirror(eventlog)
        self.memegraph = MemeGraph(eventlog)
        # wire event listeners
        self.eventlog.register_listener(self.mirror.sync)
        self.eventlog.register_listener(self.memegraph.add_event)
        # ConceptGraph projection for CTL (rebuildable and listener-backed)
        self.concept_graph = ConceptGraph(eventlog)
        # Seed from existing events (if any), then listen for updates
        self.concept_graph.rebuild()
        self.eventlog.register_listener(self.concept_graph.sync)
        self.commitments = CommitmentManager(eventlog)
        self.adapter = adapter
        self.replay = replay
        self.autonomy = AutonomyKernel(eventlog, thresholds=thresholds)
        self.tracker = AutonomyTracker(eventlog)
        # Ontology autonomy
        self._commitment_analyzer = CommitmentAnalyzer(eventlog)
        self._ontology_autonomy = OntologyAutonomy(
            eventlog, self._commitment_analyzer, snapshot_interval=50
        )
        self.indexer = Indexer(eventlog)
        self.ctl_injector = CTLLookupInjector(self.concept_graph)
        self.exec_router: ExecBindRouter | None = None
        if self.replay:
            self.mirror.rebuild()
            self.autonomy = AutonomyKernel(eventlog)
        if not self.replay:
            self.exec_router = ExecBindRouter(eventlog)
            if not any(
                e["kind"] == "autonomy_rule_table" for e in self.eventlog.read_all()
            ):
                self.autonomy.ensure_rule_table_event()

            if autonomy:
                # Start autonomy supervisor
                epoch = "2025-11-01T00:00:00Z"  # Hardcoded for now
                interval_s = 10  # Hardcoded for testing
                self.supervisor = AutonomySupervisor(eventlog, epoch, interval_s)
                # LISTENER FIRST — catch every stimulus
                self.eventlog.register_listener(self._on_autonomy_stimulus)
                # THEN start the supervisor
                self._supervisor_thread = threading.Thread(
                    target=self._run_supervisor_async, daemon=True
                )
                self._supervisor_thread.start()

    def _run_supervisor_async(self) -> None:
        """Run the supervisor in an asyncio event loop."""
        asyncio.run(self.supervisor.run_forever())

    def _on_autonomy_stimulus(self, event: Dict[str, Any]) -> None:
        if DEBUG:
            print(f"[STIMULUS RECEIVED] id={event['id']} | kind={event['kind']}")
        if event.get("kind") == "autonomy_stimulus":
            try:
                payload = json.loads(event["content"])
                slot = payload.get("slot")
                slot_id = payload.get("slot_id")
                if slot is not None and slot_id:
                    if DEBUG:
                        print(f" → CALLING run_tick(slot={slot}, id={slot_id})")

                    def _delayed_tick() -> None:
                        time.sleep(0.2)
                        self.run_tick(slot=slot, slot_id=slot_id)

                    threading.Thread(target=_delayed_tick, daemon=True).start()
            except json.JSONDecodeError:
                if DEBUG:
                    print(" → [ERROR] Failed to parse autonomy_stimulus content")

    def _extract_commitments(self, text: str) -> List[str]:
        lines = (text or "").splitlines()
        return extract_commitments(lines)

    def _extract_closures(self, text: str) -> List[str]:
        lines = (text or "").splitlines()
        candidates = extract_closures(lines)
        return [c for c in candidates if self._valid_cid(c)]

    @staticmethod
    def _valid_cid(cid: str) -> bool:
        """Return True for any non-empty CID (legacy-compatible).

        Rationale: commitments may use short test CIDs (e.g., "abcd"),
        internal CIDs (mc_000123), or 8-hex derived IDs. To preserve
        backward compatibility and avoid rejecting valid closures, accept
        any non-empty, stripped string here. Deterministic validation of
        structure can be added later without breaking tests.
        """
        return bool((cid or "").strip())

    def _extract_reflect(self, text: str) -> Dict[str, Any] | None:
        lines = (text or "").splitlines()
        return extract_reflect(lines)

    def _extract_web_request(self, text: str) -> Dict[str, Any] | None:
        lines = (text or "").splitlines()
        for ln in lines:
            stripped = (ln or "").strip()
            if not stripped.startswith("WEB:"):
                continue
            payload = stripped.split("WEB:", 1)[1].strip()
            if not payload:
                continue
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {"query": payload}
        return None

    def _extract_ledger_get_request(self, text: str) -> Dict[str, Any] | None:
        body = text or ""
        lines = body.splitlines()
        for ln in lines:
            stripped = (ln or "").strip()
            if not stripped.startswith("LEDGER_GET:"):
                continue
            payload = stripped.split("LEDGER_GET:", 1)[1].strip()
            if not payload:
                continue
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                try:
                    return {"id": int(payload)}
                except ValueError:
                    return {"id": payload}
        # Fallback: XML-style tool call emitted by some adapters, e.g.
        # <invoke name="LEDGER_GET"><parameter name="id">1</parameter></invoke>
        if "LEDGER_GET" in body:
            match = re.search(
                r'<invoke\s+name="LEDGER_GET".*?<parameter\s+name="id">\s*([^<]+?)\s*</parameter>',
                body,
                flags=re.DOTALL,
            )
            if match:
                raw_id = match.group(1).strip()
                try:
                    return {"id": int(raw_id)}
                except ValueError:
                    return {"id": raw_id}
        return None

    def _extract_ledger_find_request(self, text: str) -> Dict[str, Any] | None:
        body = text or ""
        lines = body.splitlines()
        for ln in lines:
            stripped = (ln or "").strip()
            if not stripped.startswith("LEDGER_FIND:"):
                continue
            payload = stripped.split("LEDGER_FIND:", 1)[1].strip()
            if not payload:
                continue
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {"query": payload}

        if "LEDGER_FIND" in body:
            req: Dict[str, Any] = {}
            for key in ("query", "kind", "from_id", "to_id", "limit"):
                match = re.search(
                    rf'<invoke\s+name="LEDGER_FIND".*?<parameter\s+name="{key}">\s*([^<]+?)\s*</parameter>',
                    body,
                    flags=re.DOTALL,
                )
                if not match:
                    continue
                raw_val = match.group(1).strip()
                if key in ("from_id", "to_id", "limit"):
                    try:
                        req[key] = int(raw_val)
                    except ValueError:
                        req[key] = raw_val
                else:
                    req[key] = raw_val
            if req:
                return req
        return None

    def _extract_claims(self, text: str) -> List[Claim]:
        lines = (text or "").splitlines()
        try:
            parsed = extract_claims(lines)
        except ValueError:
            # Keep runtime robust: skip malformed claim lines
            parsed = []
        return [Claim(type=ctype, data=data) for ctype, data in parsed]

    def _get_temporal_context(self) -> Optional[str]:
        """Get temporal context to inject into system prompts."""
        try:
            events = self.eventlog.read_all()
            if len(events) < 10:  # Not enough events for meaningful temporal analysis
                return None

            last_event_id = int(events[-1]["id"])
            start_id = max(1, last_event_id - 30)  # Look at last 30 events

            # Get recent temporal patterns
            result = self.autonomy.temporal_analyzer.analyze_window(
                start_id, last_event_id
            )

            # Build context string from significant patterns
            context_parts = []

            for pattern in result.patterns:
                if pattern.confidence > 0.7:  # Only include high-confidence patterns
                    if pattern.pattern_type == "low_identity_stability":
                        context_parts.append(
                            f"Recent identity coherence analysis shows stability degradation (confidence: {pattern.confidence:.2f})"
                        )
                    elif pattern.pattern_type == "commitment_burst":
                        context_parts.append(
                            f"Recent commitment clustering detected (confidence: {pattern.confidence:.2f})"
                        )
                    elif (
                        pattern.pattern_type == "learning_loops"
                        and pattern.confidence < 0.3
                    ):
                        context_parts.append(
                            f"Learning stagnation detected (loop confidence: {pattern.confidence:.2f})"
                        )
                    elif pattern.pattern_type == "engagement_periods":
                        context_parts.append(
                            f"High engagement periods detected (confidence: {pattern.confidence:.2f})"
                        )

            # Check for anomalies
            anomalies = self.autonomy.temporal_analyzer.detect_anomalies(
                sensitivity=0.6
            )
            if anomalies:
                context_parts.append(
                    f"Recent temporal anomalies: {'; '.join(anomalies[:2])}"
                )

            if context_parts:
                return "## Recent Temporal Patterns\n" + "\n".join(
                    f"• {part}" for part in context_parts
                )

        except Exception:
            # If temporal analysis fails, don't inject context
            pass

        return None

    def _parse_ref_lines(self, content: str) -> None:
        refs: List[str] = []
        parsed: Dict[str, Any] | None = None
        try:
            parsed = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            parsed = None

        if isinstance(parsed, dict) and isinstance(parsed.get("refs"), list):
            refs = [str(r) for r in parsed["refs"]]
        else:
            refs = [
                line[5:].strip()
                for line in content.splitlines()
                if line.startswith("REF: ")
            ]

        for ref in refs:
            if "#" not in ref:
                continue
            path, event_id_str = ref.split("#", 1)
            try:
                event_id = int(event_id_str)
            except ValueError:
                continue
            target_log = EventLog(path)
            target_event = target_log.get(event_id)
            if target_event:
                self.eventlog.append(
                    kind="inter_ledger_ref",
                    content=f"REF: {path}#{event_id}",
                    meta={"target_hash": target_event["hash"], "verified": True},
                )
            else:
                self.eventlog.append(
                    kind="inter_ledger_ref",
                    content=f"REF: {path}#{event_id}",
                    meta={"verified": False, "error": "not found"},
                )

    def run_turn(self, user_input: str) -> List[Dict[str, Any]]:
        if self.replay:
            # Replay mode: do not mutate ledger; simply return existing events.
            return self.eventlog.read_all()

        from pmm.runtime.reflection_synthesizer import synthesize_reflection
        from pmm.runtime.identity_summary import maybe_append_summary
        from pmm.runtime.lifetime_memory import maybe_append_lifetime_memory

        # 1. Log user message
        user_event_id = self.eventlog.append(
            kind="user_message", content=user_input, meta={"role": "user"}
        )
        # If vector retrieval is enabled, append embedding_add for the user message (idempotent)
        retrieval_cfg = self.mirror.current_retrieval_config or {}
        if retrieval_cfg and retrieval_cfg.get("strategy") == "vector":
            model = str(retrieval_cfg.get("model", "hash64"))
            dims = int(retrieval_cfg.get("dims", 64))
            ensure_embedding_for_event(
                events=[],
                eventlog=self.eventlog,
                event_id=user_event_id,
                text=user_input,
                model=model,
                dims=dims,
            )

        # 2. Build prompts
        history = self.eventlog.read_tail(limit=10)
        total_events = self.eventlog.count()
        meditation_active = total_events > 20 and total_events % 37 == 0
        open_comms = self.mirror.get_open_commitment_events()

        # Configure and run Retrieval Pipeline
        pipeline_config = RetrievalConfig()

        # CTL Lookup Injection: Identify concepts in query and force their inclusion
        injected_tokens = self.ctl_injector.extract_tokens(user_input)
        pipeline_config.sticky_concepts.extend(injected_tokens)

        if retrieval_cfg:
            try:
                limit_val = int(retrieval_cfg.get("limit", 20))
                if limit_val > 0:
                    pipeline_config.limit_total_events = limit_val
            except (ValueError, TypeError):
                pass

            if retrieval_cfg.get("strategy") == "vector":
                pipeline_config.enable_vector_search = True
            elif retrieval_cfg.get("strategy") == "fixed":
                # "fixed" implies relying on limit, usually no vector?
                # But fixed means "fixed window".
                # The new pipeline is always graph/concept aware.
                # If we want to support pure fixed window, we would need to bypass.
                # But the proposal says "Consolidate CTL... Legacy cleanup".
                # So we can interpret "fixed" as just limiting size but still using concepts.
                # Or we can disable vector search for fixed.
                pipeline_config.enable_vector_search = False

        user_event = self.eventlog.get(user_event_id)

        retrieval_result = run_retrieval_pipeline(
            query_text=user_input,
            eventlog=self.eventlog,
            concept_graph=self.concept_graph,
            meme_graph=self.memegraph,
            config=pipeline_config,
            user_event=user_event,
        )

        ctx_block = render_context(
            result=retrieval_result,
            eventlog=self.eventlog,
            concept_graph=self.concept_graph,
            meme_graph=self.memegraph,
            mirror=self.mirror,
        )

        selection_ids = retrieval_result.event_ids
        # We don't calculate vector scores in pipeline result yet, so pass empty/dummy
        selection_scores = [0.0] * len(selection_ids)

        # Check if graph context is actually present
        context_has_graph = "## Graph" in ctx_block
        base_prompt = compose_system_prompt(
            history,
            open_comms,
            context_has_graph=context_has_graph,
            history_len=total_events,
        )

        # Add temporal context if enough events exist
        temporal_context = self._get_temporal_context()
        if temporal_context:
            base_prompt = f"{temporal_context}\n\n{base_prompt}"

        system_prompt = f"{ctx_block}\n\n{base_prompt}" if ctx_block else base_prompt

        # 3. Invoke model
        t0 = time.perf_counter()
        effective_user_prompt = user_input
        assistant_reply = self.adapter.generate_reply(
            system_prompt=system_prompt, user_prompt=effective_user_prompt
        )
        t1 = time.perf_counter()

        # 3a. Optional web search tool call (single pass).
        web_request = self._extract_web_request(assistant_reply)
        if web_request:
            from pmm.runtime.web_search import run_web_search

            query = str(web_request.get("query") or "").strip()
            provider = web_request.get("provider")
            limit = web_request.get("limit", 5)
            tool_payload = run_web_search(query, provider=provider, limit=limit)
            self.eventlog.append(
                kind="web_search",
                content=json.dumps(tool_payload, sort_keys=True, separators=(",", ":")),
                meta={"source": "assistant", "trigger": "marker"},
            )
            effective_user_prompt = (
                f"{user_input}\n\n[WEB_SEARCH_RESULTS]\n"
                f"{json.dumps(tool_payload, sort_keys=True, separators=(',', ':'))}"
            )
            assistant_reply = self.adapter.generate_reply(
                system_prompt=system_prompt, user_prompt=effective_user_prompt
            )
            t1 = time.perf_counter()

        # 3b. Optional ledger event lookup (single pass).
        ledger_request = self._extract_ledger_get_request(assistant_reply)
        if ledger_request:
            from pmm.runtime.ledger_reader import run_ledger_get

            event_id = ledger_request.get("id")
            include_meta = bool(ledger_request.get("include_meta", True))
            max_content_chars = ledger_request.get("max_content_chars", 4000)
            tool_payload = run_ledger_get(
                self.eventlog,
                event_id=event_id,
                include_meta=include_meta,
                max_content_chars=max_content_chars,
            )
            self.eventlog.append(
                kind="ledger_read",
                content=json.dumps(tool_payload, sort_keys=True, separators=(",", ":")),
                meta={"source": "assistant", "trigger": "marker", "request": ledger_request},
            )
            effective_user_prompt = (
                f"{effective_user_prompt}\n\n[LEDGER_GET_RESULTS]\n"
                f"{json.dumps(tool_payload, sort_keys=True, separators=(',', ':'))}"
            )
            assistant_reply = self.adapter.generate_reply(
                system_prompt=system_prompt, user_prompt=effective_user_prompt
            )
            t1 = time.perf_counter()

        # 3c. Optional ledger search lookup (single pass).
        ledger_find_request = self._extract_ledger_find_request(assistant_reply)
        if ledger_find_request:
            from pmm.runtime.ledger_reader import run_ledger_find

            tool_payload = run_ledger_find(
                self.eventlog,
                query=ledger_find_request.get("query"),
                kind=ledger_find_request.get("kind"),
                from_id=ledger_find_request.get("from_id"),
                to_id=ledger_find_request.get("to_id"),
                limit=ledger_find_request.get("limit", 20),
                include_meta=bool(ledger_find_request.get("include_meta", True)),
                max_content_chars=ledger_find_request.get("max_content_chars", 2000),
            )
            self.eventlog.append(
                kind="ledger_search",
                content=json.dumps(tool_payload, sort_keys=True, separators=(",", ":")),
                meta={
                    "source": "assistant",
                    "trigger": "marker",
                    "request": ledger_find_request,
                },
            )
            effective_user_prompt = (
                f"{effective_user_prompt}\n\n[LEDGER_FIND_RESULTS]\n"
                f"{json.dumps(tool_payload, sort_keys=True, separators=(',', ':'))}"
            )
            assistant_reply = self.adapter.generate_reply(
                system_prompt=system_prompt, user_prompt=effective_user_prompt
            )
            t1 = time.perf_counter()

        # 3d. Try to parse optional structured JSON header (intent/outcome/etc. + concepts).
        #     Expected pattern in test mode: first line is a JSON object, followed
        #     by normal free-text. We leave assistant_reply unchanged and only
        #     record a normalized payload + concepts for CTL indexing.
        structured_payload: Optional[str] = None
        active_concepts: List[str] = []
        try:
            reply_str = assistant_reply or ""
            # Prefer a JSON header on the first line if present; fall back to
            # parsing the whole reply when there is a single-line payload.
            if "\n" in reply_str:
                # split once into leading line + remainder
                parts = reply_str.split("\n", 1)
                header_line = parts[0]
            else:
                header_line = reply_str
            parsed = json.loads(header_line)
            if isinstance(parsed, dict):
                # Structured control payload
                if all(
                    k in parsed for k in ("intent", "outcome", "next", "self_model")
                ) and all(
                    isinstance(parsed[k], str)
                    for k in ("intent", "outcome", "next", "self_model")
                ):
                    structured_payload = json.dumps(
                        parsed, sort_keys=True, separators=(",", ":")
                    )
                # Optional Active Concepts for CTL indexing
                concepts_val = parsed.get("concepts")
                if isinstance(concepts_val, list):
                    active_concepts = [
                        str(c).strip()
                        for c in concepts_val
                        if isinstance(c, str) and str(c).strip()
                    ]
        except (TypeError, json.JSONDecodeError):
            structured_payload = None
            active_concepts = []

        # Deterministic ontological concept seeding fallback during meditations
        if meditation_active and not active_concepts:
            active_concepts.extend(
                ["ontology.structure", "identity.evolution", "awareness.loop"]
            )

        # Universal continuity fallback: ensure every turn has at least one concept binding
        # This prevents orphaned events and strengthens narrative continuity in ConceptGraph
        if not active_concepts:
            active_concepts = ["identity.continuity"]

        # 4. Log assistant message (content preserved; optional structured/concept meta)
        ai_meta: Dict[str, Any] = {"role": "assistant"}
        if structured_payload is not None:
            ai_meta["assistant_structured"] = True
            ai_meta["assistant_schema"] = "assistant.v1"
            ai_meta["assistant_payload"] = structured_payload
        # Include deterministic generation metadata from adapters if present
        gen_meta = getattr(self.adapter, "generation_meta", None)
        if isinstance(gen_meta, dict):
            for k, v in gen_meta.items():
                ai_meta[k] = v
        ai_event_id = self.eventlog.append(
            kind="assistant_message",
            content=assistant_reply,
            meta=ai_meta,
        )

        # 4a. Active Indexing: bind this turn's events to any model-emitted concepts.
        if active_concepts:
            turn_event_ids = [user_event_id, ai_event_id]
            for token in active_concepts:
                # Idempotent binding via ConceptGraph projection.
                existing = set(self.concept_graph.events_for_concept(token))
                for eid in turn_event_ids:
                    if eid in existing:
                        continue
                    bind_content = json.dumps(
                        {
                            "event_id": eid,
                            "tokens": [token],
                            "relation": "relevant_to",
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    self.eventlog.append(
                        kind="concept_bind_event",
                        content=bind_content,
                        meta={"source": "active_indexing"},
                    )
        # Compile any structured CTL concept_ops from this assistant message.
        # This is deterministic and no-op when concept_ops is absent.
        assistant_event = self.eventlog.get(ai_event_id)
        if assistant_event is not None:
            compile_assistant_message_concepts(
                self.eventlog,
                self.concept_graph,
                assistant_event,
            )
        # If vector retrieval, append embedding for assistant message (idempotent)
        if retrieval_cfg and retrieval_cfg.get("strategy") == "vector":
            model = str(retrieval_cfg.get("model", "hash64"))
            dims = int(retrieval_cfg.get("dims", 64))
            ensure_embedding_for_event(
                events=[],
                eventlog=self.eventlog,
                event_id=ai_event_id,
                text=assistant_reply,
                model=model,
                dims=dims,
            )

        # 4a. Parse REF: lines and append inter_ledger_ref events
        self._parse_ref_lines(assistant_reply)

        # 4b. If vector retrieval was used, append retrieval_selection event
        if selection_ids is not None and selection_scores is not None:
            # Build provenance digest for auditability
            model = str((retrieval_cfg or {}).get("model", "hash64"))
            dims = int((retrieval_cfg or {}).get("dims", 64))
            dig = selection_digest(
                selected=selection_ids,
                scores=selection_scores,
                model=model,
                dims=dims,
                query_text=user_input,
            )
            sel_content = json.dumps(
                {
                    "turn_id": ai_event_id,
                    "selected": selection_ids,
                    "scores": selection_scores,
                    "strategy": "vector",
                    "model": model,
                    "dims": dims,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            self.eventlog.append(
                kind="retrieval_selection", content=sel_content, meta={"digest": dig}
            )

        # 4c. Per-turn diagnostics (deterministic formatting)
        prov = "dummy"
        cls = type(self.adapter).__name__.lower()
        if "openai" in cls:
            prov = "openai"
        elif "ollama" in cls:
            prov = "ollama"
        model_name = getattr(self.adapter, "model", "") or ""
        in_tokens = len((system_prompt or "").split()) + len(
            (effective_user_prompt or "").split()
        )
        out_tokens = len((assistant_reply or "").split())
        # Use adapter-provided deterministic latency if present (e.g., DummyAdapter)
        lat_ms = getattr(self.adapter, "deterministic_latency_ms", None)
        if lat_ms is None:
            lat_ms = int((t1 - t0) * 1000)
        diag = (
            f"provider:{prov},model:{model_name},"
            f"in_tokens:{in_tokens},out_tokens:{out_tokens},lat_ms:{lat_ms}"
        )
        self.eventlog.append(kind="metrics_turn", content=diag, meta={})

        # 4d. Synthesize deterministic reflection and maybe append summary
        synthesize_reflection(self.eventlog, mirror=self.mirror)
        maybe_append_summary(self.eventlog)
        maybe_append_lifetime_memory(self.eventlog, self.concept_graph, self.memegraph)

        delta = TurnDelta()

        # 5. Commitments (open)
        for c in self._extract_commitments(assistant_reply):
            cid = self.commitments.open_commitment(c, source="assistant")
            if cid:
                delta.opened.append(cid)
                extract_exec_binds(self.eventlog, c, cid)

                # Bind concepts to this thread/CID for thread-first retrieval.
                if active_concepts:
                    existing = set(
                        self.concept_graph.resolve_cids_for_concepts(active_concepts)
                    )
                    for token in active_concepts:
                        if cid in existing:
                            continue
                        bind_content = json.dumps(
                            {
                                "cid": cid,
                                "tokens": [token],
                                "relation": "relevant_to",
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        self.eventlog.append(
                            kind="concept_bind_thread",
                            content=bind_content,
                            meta={"source": "loop"},
                        )

        if self.exec_router is not None:
            self.exec_router.tick()

        # 6. Claims
        for claim in self._extract_claims(assistant_reply):
            ok, _msg = validate_claim(claim, self.eventlog, self.mirror)
            if ok:
                # Persist valid claims to ledger for future retrieval
                claim_content = (
                    f"CLAIM:{claim.type}="
                    f"{json.dumps(claim.data, sort_keys=True, separators=(',', ':'))}"
                )
                claim_event_id = self.eventlog.append(
                    kind="claim",
                    content=claim_content,
                    meta={"claim_type": claim.type, "validated": True},
                )
                # Auto-bind all validated claims into CTL for long-term recall
                target_token = claim.type
                already_bound = claim_event_id in self.concept_graph.events_for_concept(
                    target_token
                )
                if not already_bound:
                    bind_content = json.dumps(
                        {
                            "event_id": claim_event_id,
                            "tokens": [target_token],
                            "relation": "describes",
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    self.eventlog.append(
                        kind="concept_bind_event",
                        content=bind_content,
                        meta={"source": "auto_binder"},
                    )
            else:
                delta.failed_claims.append(claim)

        # 6a. Identity adoption – derive from validated identity_* CLAIMs.
        # This is ledger-only, deterministic, and idempotent.
        maybe_append_identity_adoptions(self.eventlog)

        # 7. Closures
        to_close = self._extract_closures(assistant_reply)
        actually_closed = self.commitments.apply_closures(to_close, source="assistant")
        delta.closed.extend(actually_closed)

        # 8. REFLECT block
        delta.reflect_block = self._extract_reflect(assistant_reply)

        # 9. Reflection append only if delta non-empty
        if not delta.is_empty():
            reflection_text = build_reflection_text(delta)
            if reflection_text:
                self.eventlog.append(
                    kind="reflection",
                    content=reflection_text,
                    meta={"about_event": ai_event_id},
                )
                self._parse_ref_lines(reflection_text)

        # 10. Ontology autonomy: maybe emit snapshot and check for insights
        if self._ontology_autonomy.maybe_emit_snapshot():
            insights = self._ontology_autonomy.detect_insights()
            if insights:
                self._ontology_autonomy.emit_insights(insights)

        return self.eventlog.read_tail(limit=200)

    def run_interactive(self) -> None:  # pragma: no cover - simple IO wrapper
        try:
            while True:
                inp = input("You> ")
                if inp is None:
                    break
                # Graceful exits
                if inp.strip().lower() in {"exit", ".exit", "quit"}:
                    break
                events = self.run_turn(inp)
                # Print last assistant/reflection contents
                if self.replay:
                    # In replay, nothing new; just show last assistant/reflection in log
                    for e in events[::-1]:
                        if e["kind"] in ("assistant_message", "reflection"):
                            role = (
                                "Assistant"
                                if e["kind"] == "assistant_message"
                                else "Reflection"
                            )
                            print(f"{role}> {e['content']}")
                            break
                else:
                    # fresh turn appended; print the last assistant
                    last_ai = [e for e in events if e["kind"] == "assistant_message"][
                        -1
                    ]
                    # Hide COMMIT lines from user display (still logged in ledger)
                    lines = [
                        ln
                        for ln in (last_ai["content"] or "").splitlines()
                        if not extract_commitments([ln.upper()])
                        and not (ln or "").strip().startswith("WEB:")
                        and not (ln or "").strip().startswith("LEDGER_GET:")
                        and not (ln or "").strip().startswith("LEDGER_FIND:")
                    ]
                    assistant_output = "\n".join(lines)
                    print(f"Assistant> {assistant_output}")
        except (EOFError, KeyboardInterrupt):
            return

    def run_tick(self, *, slot: int, slot_id: str) -> KernelDecision:
        if DEBUG:
            print(f"[AUTONOMY TICK] slot={slot} | id={slot_id}")
        # Snapshot ledger before decision for outcome analysis
        events_before = self.eventlog.read_tail(limit=200)
        last_id_before = events_before[-1]["id"] if events_before else 0

        decision = self.autonomy.decide_next_action()
        if DEBUG:
            print(f" → DECISION: {decision.decision} | {decision.reasoning}")

        # Log the tick FIRST
        payload = json.dumps(decision.as_dict(), sort_keys=True, separators=(",", ":"))
        self.eventlog.append(
            kind="autonomy_tick",
            content=payload,
            meta={"source": "autonomy_kernel", "slot": slot, "slot_id": slot_id},
        )

        # THEN execute
        if decision.decision == "reflect":
            from pmm.runtime.reflection_synthesizer import synthesize_reflection

            # Pass the staleness threshold so the synthesizer can compute stale flags
            meta_extra = {
                "source": "autonomy_kernel",
                "slot_id": slot_id,
                "staleness_threshold": str(
                    self.autonomy.thresholds["commitment_staleness"]
                ),
                "auto_close_threshold": str(
                    self.autonomy.thresholds["commitment_auto_close"]
                ),
            }
            reflection_id = synthesize_reflection(
                self.eventlog,
                meta_extra=meta_extra,
                staleness_threshold=int(meta_extra["staleness_threshold"]),
                auto_close_threshold=int(meta_extra["auto_close_threshold"]),
                autonomy=self.autonomy,
            )
            if reflection_id:
                target_event = self.eventlog.get(reflection_id)
                self._parse_ref_lines(target_event["content"])
        elif decision.decision == "summarize":
            from pmm.runtime.identity_summary import maybe_append_summary

            maybe_append_summary(self.eventlog)
        elif decision.decision == "index":
            self.indexer.run_indexing_cycle()
        elif decision.decision == "temporal_reflection":
            # Handle temporal reflection triggered by identity stability issues
            from pmm.runtime.reflection_synthesizer import synthesize_reflection

            meta_extra = {
                "source": "autonomy_kernel",
                "slot_id": slot_id,
                "trigger": "temporal_pattern",
                "reason": decision.reasoning,
                "staleness_threshold": str(
                    self.autonomy.thresholds["commitment_staleness"]
                ),
                "auto_close_threshold": str(
                    self.autonomy.thresholds["commitment_auto_close"]
                ),
            }
            reflection_id = synthesize_reflection(
                self.eventlog,
                meta_extra=meta_extra,
                staleness_threshold=int(meta_extra["staleness_threshold"]),
                auto_close_threshold=int(meta_extra["auto_close_threshold"]),
                autonomy=self.autonomy,
            )
            if reflection_id:
                target_event = self.eventlog.get(reflection_id)
                self._parse_ref_lines(target_event["content"])
        elif decision.decision == "temporal_analysis":
            # Handle deep temporal analysis when anomalies detected
            from pmm.temporal_analysis import TemporalAnalyzer

            # Log the temporal analysis trigger
            self.eventlog.append(
                kind="temporal_analysis_triggered",
                content=f"Temporal analysis triggered: {decision.reasoning}",
                meta={
                    "source": "autonomy_kernel",
                    "trigger": "temporal_pattern",
                    "reason": decision.reasoning,
                    "evidence": decision.evidence,
                },
            )

        if self.exec_router is not None:
            self.exec_router.tick()

        # After executing the decision, emit per-tick outcome observation and
        # invoke adaptive metrics/learning in the autonomy kernel.
        events_after = self.eventlog.read_tail(limit=200)
        self._emit_tick_outcome_and_adapt(
            decision=decision,
            last_id_before=last_id_before,
            events_after=events_after,
            slot=slot,
            slot_id=slot_id,
        )

        return decision

    def _emit_tick_outcome_and_adapt(
        self,
        *,
        decision: KernelDecision,
        last_id_before: int,
        events_after: List[Dict[str, Any]],
        slot: int,
        slot_id: str,
    ) -> None:
        """Emit outcome_observation for this autonomy tick and adapt."""
        # Events that occurred as a result of this tick (including autonomy_tick)
        events_since = [e for e in events_after if int(e.get("id", 0)) > last_id_before]

        # Determine observed_result based on whether the intended action actually
        # produced its corresponding ledger events.
        observed_result = "success"
        if decision.decision == "reflect":
            has_reflection = any(
                e.get("kind") == "reflection"
                and (e.get("meta") or {}).get("source") == "autonomy_kernel"
                for e in events_since
            )
            observed_result = "success" if has_reflection else "no_delta"
        elif decision.decision == "summarize":
            has_summary = any(e.get("kind") == "summary_update" for e in events_since)
            observed_result = "success" if has_summary else "no_delta"
        elif decision.decision == "index":
            has_index = any(
                e.get("kind") in ("claim_from_text", "concept_bind_async")
                for e in events_since
            )
            observed_result = "success" if has_index else "no_delta"

        # Encode action_kind as autonomy_<decision> for learning metrics.
        action_kind = f"autonomy_{decision.decision}"
        commitment_id = ""
        action_payload = f"decision={decision.decision}"
        evidence_event_ids = [int(e.get("id", 0)) for e in events_since][-10:]

        content_dict = build_outcome_observation_content(
            commitment_id=commitment_id,
            action_kind=action_kind,
            action_payload=action_payload,
            observed_result=observed_result,
            evidence_event_ids=evidence_event_ids,
        )
        self.eventlog.append(
            kind="outcome_observation",
            content=json.dumps(content_dict, sort_keys=True, separators=(",", ":")),
            meta={"source": "autonomy_kernel", "slot": slot, "slot_id": slot_id},
        )

        # Invoke adaptive telemetry/learning for this tick. These helpers are
        # deterministic and idempotent over the ledger.
        self.autonomy._maybe_emit_stability_metrics()
        self.autonomy._maybe_emit_coherence_check()
        self.autonomy._maybe_emit_meta_policy_update()
        self.autonomy._maybe_emit_policy_update()
        # Maintain CTL bindings as part of autonomy maintenance, keeping CTL
        # fully automatic and PMM-internal while reusing the shared
        # ConceptGraph projection instead of rebuilding from scratch.
        self.autonomy._maybe_maintain_concepts(events_after, self.concept_graph)
