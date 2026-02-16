# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/core/event_log.py
"""SQLite-backed EventLog with simple hash-chain integrity.

Minimal deterministic append/query API for PMM.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, List, Optional


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class EventLog:
    """Persistent append-only log of events with hash chaining."""

    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA busy_timeout = 1500")
        self._lock = threading.RLock()
        self._listeners: List = []
        self._fts_enabled = False
        self._init_db()

    def _init_db(self) -> None:
        try:
            with self._conn:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        content TEXT NOT NULL,
                        meta TEXT NOT NULL,
                        prev_hash TEXT,
                        hash TEXT
                    );
                    """
                )
                # Index to support efficient tail queries (ORDER BY id DESC LIMIT ?).
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_id_desc ON events(id DESC);"
                )
                # Index to support efficient kind-based scans.
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_kind ON events(kind);")
                # Composite and time indexes for deterministic filtered scans.
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_kind_id_desc ON events(kind, id DESC);"
                )
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);"
                )
                # Unique index on hash to support idempotent append with INSERT OR IGNORE.
                self._conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_hash ON events(hash);"
                )
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS event_chunks (
                        event_id INTEGER NOT NULL,
                        chunk_idx INTEGER NOT NULL,
                        chunk_text TEXT NOT NULL,
                        PRIMARY KEY (event_id, chunk_idx)
                    );
                    """
                )
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_event_chunks_event ON event_chunks(event_id);"
                )
                self._init_fts()
                self._backfill_fts()
                # Keep startup responsive on large ledgers; backfill incrementally.
                try:
                    self._backfill_chunks(batch_size=300, max_batches=1)
                except sqlite3.OperationalError:
                    # Fail-open when another process holds a write lock.
                    pass
        except sqlite3.OperationalError as exc:
            # Fail-open on lock contention from another active process.
            if "locked" in str(exc).lower():
                return
            raise

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "ts": row["ts"],
            "kind": row["kind"],
            "content": row["content"],
            "meta": json.loads(row["meta"] or "{}"),
            "prev_hash": row["prev_hash"],
            "hash": row["hash"],
        }

    def _init_fts(self) -> None:
        """Initialize FTS5 table when available; fail open when unavailable."""
        try:
            self._conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
                USING fts5(
                    content,
                    meta_text,
                    kind UNINDEXED,
                    tokenize='unicode61'
                );
                """
            )
            self._conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS events_chunks_fts
                USING fts5(
                    event_id UNINDEXED,
                    chunk_idx UNINDEXED,
                    chunk_text,
                    tokenize='unicode61'
                );
                """
            )
            self._fts_enabled = True
        except sqlite3.OperationalError:
            self._fts_enabled = False

    def _backfill_fts(self, batch_size: int = 1000) -> None:
        """Backfill missing rows into FTS index (append-only safe)."""
        if not self._fts_enabled:
            return
        while True:
            cur = self._conn.execute(
                """
                SELECT e.id, e.kind, e.content, e.meta
                FROM events e
                LEFT JOIN events_fts f ON f.rowid = e.id
                WHERE f.rowid IS NULL
                ORDER BY e.id ASC
                LIMIT ?
                """,
                (int(batch_size),),
            )
            rows = cur.fetchall()
            if not rows:
                break
            for row in rows:
                self._conn.execute(
                    """
                    INSERT INTO events_fts(rowid, content, meta_text, kind)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        int(row["id"]),
                        str(row["content"] or ""),
                        str(row["meta"] or ""),
                        str(row["kind"] or ""),
                    ),
                )

    @staticmethod
    def _split_content_chunks(
        content: str, *, chunk_size: int = 320, overlap: int = 64
    ) -> List[str]:
        text = str(content or "")
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        step = max(1, chunk_size - overlap)
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= len(text):
                break
            start += step
        return chunks

    @staticmethod
    def _snippet_around_query(text: str, query: str, max_chars: int) -> str:
        src = str(text or "")
        q = str(query or "").strip()
        if not src:
            return ""
        if not q:
            return src[:max_chars]
        low = src.lower()
        qlow = q.lower()
        at = low.find(qlow)
        if at < 0:
            return src[:max_chars]
        left = max(0, at - (max_chars // 3))
        right = min(len(src), left + max_chars)
        return src[left:right]

    def _backfill_chunks(self, batch_size: int = 500, max_batches: int = 1) -> None:
        batches = 0
        while True:
            if batches >= max(1, int(max_batches)):
                break
            cur = self._conn.execute(
                """
                SELECT e.id, e.content
                FROM events e
                LEFT JOIN event_chunks c ON c.event_id = e.id
                WHERE c.event_id IS NULL
                ORDER BY e.id ASC
                LIMIT ?
                """,
                (int(batch_size),),
            )
            rows = cur.fetchall()
            if not rows:
                break
            for row in rows:
                try:
                    self._index_chunks_for_event(
                        int(row["id"]), str(row["content"] or ""), replace=False
                    )
                except sqlite3.OperationalError:
                    # Another process may own a lock; defer to a future startup.
                    return
            batches += 1

    def _index_event_for_search(
        self, event_id: int, kind: str, content: str, meta: Dict[str, Any]
    ) -> None:
        if not self._fts_enabled:
            return
        meta_text = _canonical_json(meta or {})
        self._conn.execute(
            """
            INSERT OR REPLACE INTO events_fts(rowid, content, meta_text, kind)
            VALUES (?, ?, ?, ?)
            """,
            (int(event_id), str(content or ""), meta_text, str(kind or "")),
        )
        self._index_chunks_for_event(int(event_id), str(content or ""), replace=True)

    def _index_chunks_for_event(self, event_id: int, content: str, replace: bool) -> None:
        chunks = self._split_content_chunks(content)
        if replace:
            self._conn.execute(
                "DELETE FROM event_chunks WHERE event_id = ?",
                (int(event_id),),
            )
            if self._fts_enabled:
                self._conn.execute(
                    "DELETE FROM events_chunks_fts WHERE event_id = ?",
                    (str(int(event_id)),),
                )
        for idx, chunk_text in enumerate(chunks):
            self._conn.execute(
                """
                INSERT OR REPLACE INTO event_chunks(event_id, chunk_idx, chunk_text)
                VALUES (?, ?, ?)
                """,
                (int(event_id), int(idx), str(chunk_text)),
            )
            if self._fts_enabled:
                self._conn.execute(
                    """
                    INSERT INTO events_chunks_fts(event_id, chunk_idx, chunk_text)
                    VALUES (?, ?, ?)
                    """,
                    (str(int(event_id)), str(int(idx)), str(chunk_text)),
                )

    def register_listener(self, callback) -> None:
        """Register a callback(event_dict) when an event is appended."""
        with self._lock:
            self._listeners.append(callback)

    def _emit(self, ev: Dict[str, Any]) -> None:
        for cb in list(self._listeners):
            try:
                cb(ev)
            except Exception:
                # Listeners should not break the log
                pass

    def _last_hash(self) -> Optional[str]:
        with self._lock:
            cur = self._conn.execute("SELECT hash FROM events ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            return row[0] if row and row[0] else None

    def append(
        self, *, kind: str, content: str, meta: Optional[Dict[str, Any]] = None
    ) -> int:
        valid_kinds = {
            "user_message",
            "assistant_message",
            "reflection",
            "identity_adoption",
            "meta_summary",
            "metrics_turn",
            "metric_check",
            "commitment_open",
            "commitment_close",
            "claim",
            "autonomy_rule_table",
            "autonomy_tick",
            "autonomy_stimulus",
            "autonomy_kernel",
            "summary_update",
            "inter_ledger_ref",
            "config",
            "filler",
            "test_event",
            "metrics_update",
            "autonomy_metrics",
            "internal_goal_created",
            "retrieval_selection",
            "checkpoint_manifest",
            "embedding_add",
            "lifetime_memory",
            "web_search",
            "ledger_read",
            "ledger_search",
            # New kinds introduced by enhancement features
            "stability_metrics",
            "coherence_check",
            "outcome_observation",
            "policy_update",
            "meta_policy_update",
            # Concept Token Layer (CTL) event kinds
            "concept_define",
            "concept_alias",
            "concept_bind_event",
            "concept_relate",
            "concept_state_snapshot",
            "concept_bind_thread",
            # New kinds for Indexer/Archivist
            "claim_from_text",
            "concept_bind_async",
            # Ontological self-reflection event kinds
            "ontology_snapshot",
            "ontology_insight",
            "commitment_analysis",
        }
        binding_kinds = {
            "metric_check",
            "autonomy_kernel",
            "internal_goal_created",
            "config",
        }
        if kind in binding_kinds:
            assert kind in binding_kinds, f"Unsupported kind: {kind}"
        if kind not in valid_kinds:
            raise ValueError(f"Invalid event kind: {kind}")
        if not isinstance(content, str):
            raise TypeError("EventLog.append requires string content")
        meta = meta or {}
        ts = _iso_now()
        prev_hash = self._last_hash()
        # Hash payload intentionally excludes timestamp to keep digest
        # stable across independent runs producing identical semantic content.
        payload = {
            "kind": kind,
            "content": content,
            "meta": meta,
            "prev_hash": prev_hash,
        }
        digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

        # Enforce immutable runtime policy for sensitive kinds
        sensitive = {
            "config",
            "checkpoint_manifest",
            "embedding_add",
            "retrieval_selection",
        }
        if kind in sensitive:
            src = (meta or {}).get("source") or "unknown"
            # Load last policy config
            try:
                policy = None
                # Search from end for last policy
                for e in self.read_all()[::-1]:
                    if e.get("kind") != "config":
                        continue
                    try:
                        data = json.loads(e.get("content") or "{}")
                    except Exception:
                        continue
                    if isinstance(data, dict) and data.get("type") == "policy":
                        policy = data
                        break
                if policy and isinstance(policy.get("forbid_sources"), dict):
                    forbidden = policy["forbid_sources"].get(src)
                    if isinstance(forbidden, list) and kind in forbidden:
                        # Append violation and halt write
                        v_content = f"policy_violation:{src}:{kind}"
                        v_meta = {
                            "source": "runtime",
                            "actor": src,
                            "attempt_kind": kind,
                        }
                        # Write violation directly
                        with self._lock, self._conn:
                            v_payload = {
                                "kind": "violation",
                                "content": v_content,
                                "meta": v_meta,
                                "prev_hash": prev_hash,
                            }
                            v_digest = sha256(
                                _canonical_json(v_payload).encode("utf-8")
                            ).hexdigest()
                            curv = self._conn.execute(
                                "INSERT INTO events (ts, kind, content, meta, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?)",
                                (
                                    ts,
                                    "violation",
                                    v_content,
                                    _canonical_json(v_meta),
                                    prev_hash,
                                    v_digest,
                                ),
                            )
                            v_id = int(curv.lastrowid)
                            self._emit(
                                {
                                    "id": v_id,
                                    "ts": ts,
                                    "kind": "violation",
                                    "content": v_content,
                                    "meta": v_meta,
                                    "prev_hash": prev_hash,
                                    "hash": v_digest,
                                }
                            )
                        raise PermissionError(f"Policy forbids {src} writing {kind}")
            except PermissionError:
                raise
            except Exception:
                # Fail-open if policy unreadable
                pass

        with self._lock, self._conn:
            # Idempotent append using UNIQUE(hash) and INSERT OR IGNORE:
            # - On first insert, a new row is created.
            # - On conflict, no new row is created; we look up the existing row
            #   and emit it to listeners, returning its id.
            cur = self._conn.execute(
                "INSERT OR IGNORE INTO events (ts, kind, content, meta, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?)",
                (ts, kind, content, _canonical_json(meta), prev_hash, digest),
            )
            if cur.rowcount == 0:
                # Row with identical hash already exists; fetch canonical row.
                cur_row = self._conn.execute(
                    "SELECT id, ts, kind, content, meta, prev_hash, hash FROM events WHERE hash = ?",
                    (digest,),
                )
                row = cur_row.fetchone()
                if row is None:
                    raise RuntimeError("Invariant violation: hash conflict without row")
                ev_id = int(row["id"])
                ts_db = row["ts"]
                kind_db = row["kind"]
                content_db = row["content"]
                meta_db = json.loads(row["meta"] or "{}")
                prev_hash_db = row["prev_hash"]
                hash_db = row["hash"]
            else:
                ev_id = int(cur.lastrowid)
                ts_db = ts
                kind_db = kind
                content_db = content
                meta_db = meta
                prev_hash_db = prev_hash
                hash_db = digest

        ev = {
            "id": ev_id,
            "ts": ts_db,
            "kind": kind_db,
            "content": content_db,
            "meta": meta_db,
            "prev_hash": prev_hash_db,
            "hash": hash_db,
        }
        with self._lock, self._conn:
            self._index_event_for_search(ev_id, kind_db, content_db, meta_db)
        self._emit(ev)
        return ev_id

    def read_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM events ORDER BY id ASC")
            out: List[Dict[str, Any]] = []
            for row in cur.fetchall():
                out.append(
                    {
                        "id": row["id"],
                        "ts": row["ts"],
                        "kind": row["kind"],
                        "content": row["content"],
                        "meta": json.loads(row["meta"] or "{}"),
                        "prev_hash": row["prev_hash"],
                        "hash": row["hash"],
                    }
                )
        return out

    def read_tail(self, limit: int) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            rows.reverse()
            out: List[Dict[str, Any]] = []
            for row in rows:
                out.append(
                    {
                        "id": row["id"],
                        "ts": row["ts"],
                        "kind": row["kind"],
                        "content": row["content"],
                        "meta": json.loads(row["meta"] or "{}"),
                        "prev_hash": row["prev_hash"],
                        "hash": row["hash"],
                    }
                )
        return out

    def read_since(self, event_id: int, limit: int) -> List[Dict[str, Any]]:
        """Return events with id > event_id ordered ASC, capped by limit."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM events WHERE id > ? ORDER BY id ASC LIMIT ?",
                (int(event_id), int(limit)),
            )
            rows = cur.fetchall()
            out: List[Dict[str, Any]] = []
            for row in rows:
                out.append(
                    {
                        "id": row["id"],
                        "ts": row["ts"],
                        "kind": row["kind"],
                        "content": row["content"],
                        "meta": json.loads(row["meta"] or "{}"),
                        "prev_hash": row["prev_hash"],
                        "hash": row["hash"],
                    }
                )
        return out

    def read_range(
        self, start_id: int, end_id: int, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Return events between ids inclusive, ordered ASC."""
        params: List[Any] = [int(start_id), int(end_id)]
        sql = "SELECT * FROM events WHERE id >= ? AND id <= ? ORDER BY id ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        with self._lock:
            cur = self._conn.execute(sql, tuple(params))
            rows = cur.fetchall()
            out: List[Dict[str, Any]] = []
            for row in rows:
                out.append(
                    {
                        "id": row["id"],
                        "ts": row["ts"],
                        "kind": row["kind"],
                        "content": row["content"],
                        "meta": json.loads(row["meta"] or "{}"),
                        "prev_hash": row["prev_hash"],
                        "hash": row["hash"],
                    }
                )
        return out

    def read_by_kind(
        self, kind: str, limit: Optional[int] = None, reverse: bool = False
    ) -> List[Dict[str, Any]]:
        """Return events filtered by kind, ordered by id."""
        sql = "SELECT * FROM events WHERE kind = ? ORDER BY id ASC"
        params: List[Any] = [kind]
        if reverse:
            sql = "SELECT * FROM events WHERE kind = ? ORDER BY id DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        with self._lock:
            cur = self._conn.execute(sql, tuple(params))
            rows = cur.fetchall()
            out: List[Dict[str, Any]] = []
            for row in rows:
                out.append(
                    {
                        "id": row["id"],
                        "ts": row["ts"],
                        "kind": row["kind"],
                        "content": row["content"],
                        "meta": json.loads(row["meta"] or "{}"),
                        "prev_hash": row["prev_hash"],
                        "hash": row["hash"],
                    }
                )
        return out

    def last_of_kind(self, kind: str) -> Optional[Dict[str, Any]]:
        """Return the most recent event of a given kind."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM events WHERE kind = ? ORDER BY id DESC LIMIT 1",
                (kind,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "ts": row["ts"],
                "kind": row["kind"],
                "content": row["content"],
                "meta": json.loads(row["meta"] or "{}"),
                "prev_hash": row["prev_hash"],
                "hash": row["hash"],
            }

    def read_up_to(self, event_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM events WHERE id <= ? ORDER BY id ASC",
                (event_id,),
            )
            rows = cur.fetchall()
            out: List[Dict[str, Any]] = []
            for row in rows:
                out.append(
                    {
                        "id": row["id"],
                        "ts": row["ts"],
                        "kind": row["kind"],
                        "content": row["content"],
                        "meta": json.loads(row["meta"] or "{}"),
                        "prev_hash": row["prev_hash"],
                        "hash": row["hash"],
                    }
                )
        return out

    # Convenience API for validators/replay
    def get(self, event_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "ts": row["ts"],
                "kind": row["kind"],
                "content": row["content"],
                "meta": json.loads(row["meta"] or "{}"),
                "prev_hash": row["prev_hash"],
                "hash": row["hash"],
            }

    def exists(self, event_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute("SELECT 1 FROM events WHERE id = ?", (event_id,))
            return cur.fetchone() is not None

    def hash_sequence(self) -> List[str]:
        with self._lock:
            cur = self._conn.execute("SELECT hash FROM events ORDER BY id ASC")
            return [r[0] for r in cur.fetchall()]

    def count(self) -> int:
        """Return total event count using MAX(id) (append-only, no deletes)."""
        with self._lock:
            cur = self._conn.execute("SELECT MAX(id) FROM events")
            row = cur.fetchone()
            max_id = row[0] if row and row[0] is not None else 0
            return int(max_id)

    def find_entries(
        self,
        *,
        query: Optional[str] = None,
        kind: Optional[str] = None,
        start_id: Optional[int] = None,
        end_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Find ledger entries using deterministic SQL filters and optional FTS."""
        q = (query or "").strip()
        kind_val = (kind or "").strip()
        lim = max(1, min(int(limit), 50))

        where_clauses: List[str] = []
        params: List[Any] = []
        if kind_val:
            where_clauses.append("e.kind = ?")
            params.append(kind_val)
        if start_id is not None:
            where_clauses.append("e.id >= ?")
            params.append(int(start_id))
        if end_id is not None:
            where_clauses.append("e.id <= ?")
            params.append(int(end_id))
        where_sql = ""
        if where_clauses:
            where_sql = " AND " + " AND ".join(where_clauses)

        with self._lock:
            if q and self._fts_enabled:
                sql = (
                    "SELECT e.* "
                    "FROM events_fts f JOIN events e ON e.id = f.rowid "
                    "WHERE f MATCH ?"
                    f"{where_sql} "
                    "ORDER BY e.id DESC LIMIT ?"
                )
                try:
                    cur = self._conn.execute(sql, [q, *params, lim])
                    return [self._row_to_event(row) for row in cur.fetchall()]
                except sqlite3.Error:
                    # Fall back to LIKE path when query is not FTS-compatible.
                    pass

            if q:
                like = f"%{q}%"
                sql = (
                    "SELECT e.* FROM events e "
                    "WHERE (e.content LIKE ? OR e.meta LIKE ?)"
                    f"{where_sql} "
                    "ORDER BY e.id DESC LIMIT ?"
                )
                cur = self._conn.execute(sql, [like, like, *params, lim])
                return [self._row_to_event(row) for row in cur.fetchall()]

            sql = (
                "SELECT e.* FROM events e WHERE 1=1"
                f"{where_sql} "
                "ORDER BY e.id DESC LIMIT ?"
            )
            cur = self._conn.execute(sql, [*params, lim])
            return [self._row_to_event(row) for row in cur.fetchall()]

    def find_matching_chunks(
        self,
        *,
        query: str,
        kind: Optional[str] = None,
        start_id: Optional[int] = None,
        end_id: Optional[int] = None,
        limit: int = 20,
        snippet_chars: int = 180,
    ) -> List[Dict[str, Any]]:
        """Return chunk-level keyword matches with parent event IDs."""
        q = (query or "").strip()
        if not q:
            return []
        lim = max(1, min(int(limit), 100))
        snip = max(40, int(snippet_chars))
        kind_val = (kind or "").strip()

        where_clauses: List[str] = []
        params: List[Any] = []
        if kind_val:
            where_clauses.append("e.kind = ?")
            params.append(kind_val)
        if start_id is not None:
            where_clauses.append("e.id >= ?")
            params.append(int(start_id))
        if end_id is not None:
            where_clauses.append("e.id <= ?")
            params.append(int(end_id))
        where_sql = ""
        if where_clauses:
            where_sql = " AND " + " AND ".join(where_clauses)

        with self._lock:
            rows: List[sqlite3.Row] = []
            if self._fts_enabled:
                sql = (
                    "SELECT c.event_id, c.chunk_idx, c.chunk_text, e.kind "
                    "FROM events_chunks_fts c "
                    "JOIN events e ON e.id = CAST(c.event_id AS INTEGER) "
                    "WHERE events_chunks_fts MATCH ?"
                    f"{where_sql} "
                    "ORDER BY e.id DESC, CAST(c.chunk_idx AS INTEGER) ASC LIMIT ?"
                )
                try:
                    cur = self._conn.execute(sql, [q, *params, lim])
                    rows = cur.fetchall()
                except sqlite3.Error:
                    rows = []

            if not rows:
                # Fallback path: use full-event search and derive matching chunks
                # at query time (works even before chunk backfill completes).
                fallback_rows = self.find_entries(
                    query=q,
                    kind=kind_val or None,
                    start_id=start_id,
                    end_id=end_id,
                    limit=max(lim * 3, lim),
                )
                out: List[Dict[str, Any]] = []
                for row in fallback_rows:
                    event_id = int(row["id"])
                    chunks = self._split_content_chunks(str(row.get("content") or ""))
                    for idx, chunk_text in enumerate(chunks):
                        if q.lower() in chunk_text.lower():
                            out.append(
                                {
                                    "event_id": event_id,
                                    "kind": str(row.get("kind") or ""),
                                    "chunk_idx": idx,
                                    "snippet": self._snippet_around_query(
                                        chunk_text, q, snip
                                    ),
                                }
                            )
                            if len(out) >= lim:
                                return out
                return out

            out2: List[Dict[str, Any]] = []
            for row in rows:
                chunk_text = str(row["chunk_text"] or "")
                out2.append(
                    {
                        "event_id": int(row["event_id"]),
                        "kind": str(row["kind"] or ""),
                        "chunk_idx": int(row["chunk_idx"]),
                        "snippet": self._snippet_around_query(chunk_text, q, snip),
                    }
                )
            return out2

    def has_exec_bind(self, cid: str) -> bool:
        cid = (cid or "").strip()
        if not cid:
            return False
        events = self.read_all()
        for event in events:
            if event.get("kind") != "config":
                continue
            content_raw = event.get("content") or ""
            try:
                data = json.loads(content_raw)
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            if data.get("type") == "exec_bind" and data.get("cid") == cid:
                return True
        return False
