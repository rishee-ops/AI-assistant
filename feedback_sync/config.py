"""Configuration loading and validation.

All runtime configuration comes from environment variables (optionally loaded
from a local ``.env`` file). Nothing secret is ever hard-coded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load .env once, if present. Real environment variables always win.
load_dotenv(override=False)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _get(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and (value is None or value.strip() == ""):
        raise ConfigError(f"Required environment variable {name!r} is not set.")
    return "" if value is None else value


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _get_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


# Default mapping from DESTINATION column headers -> candidate SOURCE header
# substrings (matched fuzzily). The destination row is always built in the
# destination's own column order, so its structure/formatting is preserved.
DEFAULT_FIELD_MAP: dict[str, list[str]] = {
    "Date": ["timestamp", "date"],
    "Student name": ["name of the learner", "learner's name", "student name", "learner"],
    "Email": ["email"],
    "Phone": ["phone"],
    "Course": ["which course", "course name", "course"],
    "Expert": ["name of the faculty", "name of the expert", "faculty", "expert"],
    "Topic": ["topic of the session", "name/topic of the session", "topic"],
    "Rating": ["scale of 1", "how would you rate", "rating"],
    "Options": ["if you had a good experience", "options"],
    # "Feedback" is filled with the REWRITTEN text, handled specially.
    "Source": [],  # constant label, handled specially.
}


@dataclass(frozen=True)
class Config:
    # Auth
    service_account_file: str
    service_account_json: str

    # Source
    source_spreadsheet_id: str
    source_worksheet_title: str
    source_worksheet_gid: str

    # Destination
    dest_spreadsheet_id: str
    dest_worksheet_title: str

    # Matching / extraction
    program_column: str
    program_filters: list[str]
    feedback_column: str
    row_id_column: str
    min_feedback_chars: int

    # Rewriting
    rewrite_engine: str
    anthropic_api_key: str
    rewrite_model: str
    rewrite_max_tokens: int

    # Behaviour
    state_file: str
    dry_run: bool
    source_label: str

    # Logging
    log_level: str
    log_file: str

    field_map: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_FIELD_MAP))

    def validate(self) -> None:
        if not self.service_account_file and not self.service_account_json:
            raise ConfigError(
                "Provide GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON."
            )
        if not self.source_worksheet_title and not self.source_worksheet_gid:
            raise ConfigError(
                "Provide SOURCE_WORKSHEET_TITLE or SOURCE_WORKSHEET_GID."
            )
        if not self.dest_worksheet_title:
            raise ConfigError("DEST_WORKSHEET_TITLE is required.")
        if self.rewrite_engine not in {"anthropic", "rule"}:
            raise ConfigError("REWRITE_ENGINE must be 'anthropic' or 'rule'.")
        if self.rewrite_engine == "anthropic" and not self.anthropic_api_key:
            raise ConfigError(
                "REWRITE_ENGINE=anthropic requires ANTHROPIC_API_KEY "
                "(or set REWRITE_ENGINE=rule for offline mode)."
            )


def load_config() -> Config:
    """Build a validated :class:`Config` from the environment."""
    cfg = Config(
        service_account_file=_get("GOOGLE_SERVICE_ACCOUNT_FILE"),
        service_account_json=_get("GOOGLE_SERVICE_ACCOUNT_JSON"),
        source_spreadsheet_id=_get("SOURCE_SPREADSHEET_ID", required=True),
        source_worksheet_title=_get("SOURCE_WORKSHEET_TITLE"),
        source_worksheet_gid=_get("SOURCE_WORKSHEET_GID"),
        dest_spreadsheet_id=_get("DEST_SPREADSHEET_ID", required=True),
        dest_worksheet_title=_get("DEST_WORKSHEET_TITLE", "AI for Women"),
        program_column=_get("PROGRAM_COLUMN"),
        program_filters=_get_list("PROGRAM_FILTER"),
        feedback_column=_get("FEEDBACK_COLUMN"),
        row_id_column=_get("ROW_ID_COLUMN"),
        min_feedback_chars=_get_int("MIN_FEEDBACK_CHARS", 2),
        rewrite_engine=_get("REWRITE_ENGINE", "anthropic").strip().lower(),
        anthropic_api_key=_get("ANTHROPIC_API_KEY"),
        rewrite_model=_get("REWRITE_MODEL", "claude-sonnet-4-6"),
        rewrite_max_tokens=_get_int("REWRITE_MAX_TOKENS", 400),
        state_file=_get("STATE_FILE", "./state/synced_keys.json"),
        dry_run=_get_bool("DRY_RUN", False),
        source_label=_get("SOURCE_LABEL", "Class feedback (AI for Women)"),
        log_level=_get("LOG_LEVEL", "INFO").upper(),
        log_file=_get("LOG_FILE", "./logs/feedback_sync.log"),
    )
    cfg.validate()
    return cfg
