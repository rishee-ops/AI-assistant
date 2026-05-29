"""Offline tests for the core logic (no network / no Google / no LLM).

Run with:  python -m pytest -q
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feedback_sync.rewriter import RuleBasedRewriter, is_usable
from feedback_sync.sheets import normalize_header, resolve_header


def test_is_usable_filters_junk():
    assert is_usable("Outstanding")
    assert is_usable("good learning")
    assert not is_usable("NA")
    assert not is_usable("n/a")
    assert not is_usable("-")
    assert not is_usable("")
    assert not is_usable("   ")


def test_rule_rewriter_cleans_text():
    r = RuleBasedRewriter()
    out = r.rewrite("very good class beautifully explained intangible assets")
    assert out.endswith(".")
    assert out[0].isupper()


def test_resolve_header_fuzzy():
    headers = [
        "Timestamp",
        "Email address",
        "Which course are you giving feedback for ",  # trailing space, no ?
        "We value your feedback. Please let us know more.",
    ]
    # Configured with a "?" -- must still match.
    assert (
        resolve_header(headers, ["Which course are you giving feedback for?"])
        == "Which course are you giving feedback for "
    )
    assert resolve_header(headers, ["email"]) == "Email address"
    assert resolve_header(headers, ["please let us know more"]) == (
        "We value your feedback. Please let us know more."
    )
    assert resolve_header(headers, ["nonexistent"]) is None


def test_normalize_header():
    assert normalize_header("S. no") == "s no"
    assert normalize_header("Which course?  ") == "which course"


def test_program_filter_matching():
    from types import SimpleNamespace

    from feedback_sync.workflow import FeedbackSyncWorkflow

    cfg = SimpleNamespace(
        program_filters=["Training Program on Using AI for Business Growth"],
        state_file="/tmp/_t_state.json",
    )
    # Bypass __init__ (which would build a SyncState); test the method directly.
    wf = FeedbackSyncWorkflow.__new__(FeedbackSyncWorkflow)
    wf.cfg = cfg
    col = "Course"
    assert wf._is_relevant(
        {"Course": "Training Program on Using AI for Business Growth"}, col
    )
    assert not wf._is_relevant({"Course": "Some other course"}, col)
