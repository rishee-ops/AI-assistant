"""Google Sheets access via gspread + a service account.

Includes:
* service-account authentication (file path OR inline JSON),
* network retry with exponential backoff on transient API errors,
* fuzzy header resolution (real headers have stray spaces / "?" / casing),
* a hard guard so writes can ONLY ever touch the configured destination tab.
"""

from __future__ import annotations

import json
import logging
import re

import gspread
from google.oauth2.service_account import Credentials
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("feedback_sync.sheets")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# gspread raises APIError on transient 429/5xx; retry those.
_RETRYABLE = (gspread.exceptions.APIError, ConnectionError, TimeoutError)


def _retry():
    return retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=16),
        retry=retry_if_exception_type(_RETRYABLE),
    )


def normalize_header(text: str) -> str:
    """Lower-case, collapse whitespace, drop punctuation for fuzzy matching."""
    text = (text or "").replace("\n", " ").strip().lower()
    text = re.sub(r"[^a-z0-9 ]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def resolve_header(headers: list[str], candidates: list[str]) -> str | None:
    """Find the real header best matching any candidate substring.

    Tries exact normalized equality first, then substring containment.
    Returns the original (un-normalized) header, or ``None``.
    """
    norm = {normalize_header(h): h for h in headers}
    cand_norm = [normalize_header(c) for c in candidates]

    for c in cand_norm:  # exact match wins
        if c in norm:
            return norm[c]
    for c in cand_norm:  # then substring
        for nh, original in norm.items():
            if c and c in nh:
                return original
    return None


class SheetsClient:
    def __init__(self, cfg):
        self._cfg = cfg
        self._gc = self._authorize(cfg)

    @staticmethod
    def _authorize(cfg) -> gspread.Client:
        if cfg.service_account_json.strip():
            info = json.loads(cfg.service_account_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
            logger.info("Authenticated with inline service-account JSON.")
        else:
            creds = Credentials.from_service_account_file(
                cfg.service_account_file, scopes=SCOPES
            )
            logger.info(
                "Authenticated with service-account file %s.",
                cfg.service_account_file,
            )
        return gspread.authorize(creds)

    # --- Source -------------------------------------------------------------

    @_retry()
    def read_source_records(self) -> list[dict]:
        """Return source rows as a list of dicts keyed by header.

        Reads dynamically: whatever rows/columns exist are returned.
        """
        ss = self._gc.open_by_key(self._cfg.source_spreadsheet_id)
        ws = self._select_source_worksheet(ss)
        logger.info(
            "Reading source tab %r (%d rows incl. header).",
            ws.title,
            ws.row_count,
        )
        # expected_headers="" avoids gspread's duplicate-header explosion;
        # get_all_records maps each row to the header row reliably.
        records = ws.get_all_records(head=1)
        logger.info("Read %d data rows from source.", len(records))
        return records

    def _select_source_worksheet(self, spreadsheet) -> gspread.Worksheet:
        cfg = self._cfg
        if cfg.source_worksheet_title:
            try:
                return spreadsheet.worksheet(cfg.source_worksheet_title)
            except gspread.exceptions.WorksheetNotFound:
                titles = [w.title for w in spreadsheet.worksheets()]
                raise gspread.exceptions.WorksheetNotFound(
                    f"Source tab {cfg.source_worksheet_title!r} not found. "
                    f"Available tabs: {titles}"
                )
        # Fall back to gid.
        gid = int(cfg.source_worksheet_gid)
        for ws in spreadsheet.worksheets():
            if ws.id == gid:
                return ws
        raise gspread.exceptions.WorksheetNotFound(
            f"No source worksheet with gid={gid}."
        )

    # --- Destination --------------------------------------------------------

    @_retry()
    def open_destination(self) -> gspread.Worksheet:
        """Open ONLY the configured destination tab. Hard guard included."""
        ss = self._gc.open_by_key(self._cfg.dest_spreadsheet_id)
        target = self._cfg.dest_worksheet_title
        try:
            ws = ss.worksheet(target)
        except gspread.exceptions.WorksheetNotFound:
            titles = [w.title for w in ss.worksheets()]
            raise gspread.exceptions.WorksheetNotFound(
                f"Destination tab {target!r} not found. Available tabs: {titles}"
            )
        # SAFETY: refuse to proceed if we somehow resolved a different tab.
        if ws.title != target:
            raise RuntimeError(
                f"Refusing to write: resolved tab {ws.title!r} != target {target!r}."
            )
        logger.info("Opened destination tab %r (write target).", ws.title)
        return ws

    @_retry()
    def read_header(self, ws: gspread.Worksheet) -> list[str]:
        header = ws.row_values(1)
        logger.info("Destination header: %s", header)
        return header

    @_retry()
    def read_existing_rows(self, ws: gspread.Worksheet) -> list[dict]:
        return ws.get_all_records(head=1)

    @_retry()
    def append_rows(self, ws: gspread.Worksheet, rows: list[list]) -> int:
        """Append rows below existing data without touching anything else."""
        if not rows:
            return 0
        # value_input_option=RAW so text is stored verbatim (no formula/number
        # coercion), and INSERT_ROWS so we never overwrite existing cells.
        ws.append_rows(
            rows,
            value_input_option="RAW",
            insert_data_option="INSERT_ROWS",
            table_range="A1",
        )
        logger.info("Appended %d row(s) to %r.", len(rows), ws.title)
        return len(rows)
