"""End-to-end orchestration of the feedback sync.

Steps (each logged):
  1. Read all source rows dynamically.
  2. Identify relevant rows (course matches the configured program filter).
  3. Extract the raw feedback column.
  4. Rewrite feedback professionally.
  5. Build destination rows in the destination's own column order.
  6. Drop duplicates (against local state AND existing destination rows).
  7. Safely append new rows to ONLY the "AI for Women" tab.
  8. Persist state and report a summary.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass

from .config import Config
from .rewriter import Rewriter, is_usable
from .sheets import SheetsClient, normalize_header, resolve_header
from .state import SyncState

logger = logging.getLogger("feedback_sync.workflow")

# Semantic fields used to build a stable dedupe key (present in both sheets).
_KEY_FIELDS = {
    "email": ["email"],
    "course": ["which course", "course name", "course"],
    "topic": ["topic of the session", "name/topic of the session", "topic"],
    "date": ["timestamp", "date"],
}


def _normalize_text(value: object) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _key_from_parts(parts: list[str]) -> str:
    joined = "||".join(_normalize_text(p) for p in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


@dataclass
class SyncResult:
    source_rows: int = 0
    relevant_rows: int = 0
    skipped_no_feedback: int = 0
    duplicates: int = 0
    rewritten: int = 0
    appended: int = 0
    errors: int = 0
    dry_run: bool = False

    def summary(self) -> str:
        return (
            f"source_rows={self.source_rows} relevant={self.relevant_rows} "
            f"skipped_no_feedback={self.skipped_no_feedback} "
            f"duplicates={self.duplicates} rewritten={self.rewritten} "
            f"appended={self.appended} errors={self.errors} "
            f"dry_run={self.dry_run}"
        )


class FeedbackSyncWorkflow:
    def __init__(self, cfg: Config, client: SheetsClient, rewriter: Rewriter):
        self.cfg = cfg
        self.client = client
        self.rewriter = rewriter
        self.state = SyncState(cfg.state_file)

    # --- helpers ------------------------------------------------------------

    def _is_relevant(self, record: dict, program_col: str | None) -> bool:
        if not self.cfg.program_filters:
            return True  # no filter configured => keep all rows
        if not program_col:
            return False
        course = _normalize_text(record.get(program_col, ""))
        return any(_normalize_text(f) in course for f in self.cfg.program_filters)

    def _record_key(self, record: dict, source_headers: list[str]) -> str:
        parts = []
        for candidates in _KEY_FIELDS.values():
            col = resolve_header(source_headers, candidates)
            parts.append(record.get(col, "") if col else "")
        return _key_from_parts(parts)

    def _dest_row_key(self, record: dict, dest_headers: list[str]) -> str:
        parts = []
        for candidates in _KEY_FIELDS.values():
            col = resolve_header(dest_headers, candidates)
            parts.append(record.get(col, "") if col else "")
        return _key_from_parts(parts)

    def _build_dest_row(
        self,
        src: dict,
        improved: str,
        dest_headers: list[str],
        source_headers: list[str],
        serial: int,
    ) -> list:
        """Build one destination row, in destination header order."""
        row = []
        for header in dest_headers:
            nh = normalize_header(header)
            if nh in {"feedback"}:
                row.append(improved)
            elif "source" in nh:
                row.append(self.cfg.source_label)
            elif nh in {"s no", "sno", "sl no", "serial", "sr no"} or nh.startswith(
                "s no"
            ):
                row.append(serial)
            else:
                candidates = self.cfg.field_map.get(header)
                if candidates is None:
                    # Try matching by the destination header name itself.
                    candidates = [header]
                src_col = resolve_header(source_headers, candidates)
                row.append(src.get(src_col, "") if src_col else "")
        return row

    @staticmethod
    def _next_serial(existing_rows: list[dict], dest_headers: list[str]) -> int:
        col = resolve_header(dest_headers, ["s no", "s. no", "sl no", "serial"])
        if not col:
            return len(existing_rows) + 1
        max_n = 0
        for r in existing_rows:
            try:
                max_n = max(max_n, int(str(r.get(col, "")).strip() or 0))
            except ValueError:
                continue
        return max_n + 1

    # --- main ---------------------------------------------------------------

    def run(self) -> SyncResult:
        result = SyncResult(dry_run=self.cfg.dry_run)

        records = self.client.read_source_records()
        result.source_rows = len(records)
        if not records:
            logger.warning("Source returned no rows; nothing to do.")
            return result

        source_headers = list(records[0].keys())
        program_col = (
            resolve_header(source_headers, [self.cfg.program_column])
            if self.cfg.program_column
            else None
        )
        if self.cfg.program_column and not program_col:
            logger.warning(
                "Program column %r not found in source headers %s.",
                self.cfg.program_column,
                source_headers,
            )

        feedback_col = self._resolve_feedback_column(source_headers)
        logger.info("Using feedback column: %r", feedback_col)

        # Destination header + existing rows for dedupe and column order.
        ws = self.client.open_destination()
        dest_headers = self.client.read_header(ws)
        existing_rows = self.client.read_existing_rows(ws)
        existing_keys = {
            self._dest_row_key(r, dest_headers) for r in existing_rows
        }
        logger.info(
            "Destination has %d existing rows (%d unique keys).",
            len(existing_rows),
            len(existing_keys),
        )

        serial = self._next_serial(existing_rows, dest_headers)
        new_rows: list[list] = []
        new_keys: set[str] = set()

        for record in records:
            if not self._is_relevant(record, program_col):
                continue
            result.relevant_rows += 1

            key = self._record_key(record, source_headers)
            if key in self.state or key in existing_keys or key in new_keys:
                result.duplicates += 1
                continue

            raw = str(record.get(feedback_col, "")) if feedback_col else ""
            if not is_usable(raw, self.cfg.min_feedback_chars):
                result.skipped_no_feedback += 1
                continue

            try:
                context = {
                    "Course": record.get(
                        resolve_header(source_headers, ["which course", "course"]) or "",
                        "",
                    ),
                    "Expert": record.get(
                        resolve_header(source_headers, ["faculty", "expert"]) or "", ""
                    ),
                    "Topic": record.get(
                        resolve_header(source_headers, ["topic"]) or "", ""
                    ),
                }
                improved = self.rewriter.rewrite(raw, context)
                result.rewritten += 1
            except Exception:  # noqa: BLE001 - log and skip a single bad row
                logger.exception("Failed to rewrite feedback; skipping row. key=%s", key)
                result.errors += 1
                continue

            row = self._build_dest_row(
                record, improved, dest_headers, source_headers, serial
            )
            new_rows.append(row)
            new_keys.add(key)
            serial += 1
            logger.debug("Prepared row: raw=%r -> improved=%r", raw, improved)

        logger.info("Prepared %d new row(s) for append.", len(new_rows))

        if self.cfg.dry_run:
            logger.info("DRY_RUN=true; not writing to destination.")
            for r in new_rows:
                logger.info("[dry-run] would append: %s", r)
        elif new_rows:
            result.appended = self.client.append_rows(ws, new_rows)
            self.state.update(new_keys)
            self.state.save()
        else:
            logger.info("No new rows to append.")

        logger.info("Run complete: %s", result.summary())
        return result

    def _resolve_feedback_column(self, source_headers: list[str]) -> str | None:
        if self.cfg.feedback_column:
            col = resolve_header(source_headers, [self.cfg.feedback_column])
            if col:
                return col
            logger.warning(
                "Configured FEEDBACK_COLUMN %r not found; auto-detecting.",
                self.cfg.feedback_column,
            )
        # Auto-detect: prefer a free-text feedback column over multi-selects.
        for candidates in (
            ["please let us know more"],
            ["feedback added"],
            ["what went wrong"],
            ["feedback"],
            ["if you had a good experience"],
        ):
            col = resolve_header(source_headers, candidates)
            if col:
                return col
        return None
