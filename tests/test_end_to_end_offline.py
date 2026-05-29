"""End-to-end offline run using a fake SheetsClient and the rule rewriter.

Proves: filtering, junk-skipping, dedupe, destination column ordering,
serial numbering, and the destination-tab write guard -- all without network.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feedback_sync.rewriter import RuleBasedRewriter
from feedback_sync.workflow import FeedbackSyncWorkflow

SOURCE_HEADERS = [
    "Timestamp",
    "Email address",
    "Name of the learner",
    "Please provide your phone number. ",
    "Which course are you giving feedback for ",
    "Name of the faculty who conducted the session/class.",
    "Topic of the session/class that you would like to give feedback on",
    "On a scale of 1 - 5, with 5 being the highest, how would you rate your class experience?",
    "If you had a good experience, let us know why",
    "We value your feedback. Please let us know more.",
]

DEST_HEADERS = [
    "S. no", "Date", "Student name", "Email", "Phone", "Course",
    "Expert", "Topic", "Rating", "Options", "Feedback", "Source",
]

TARGET = "Training Program on Using AI for Business Growth"
OTHER = "Some Unrelated Course"


def _row(ts, email, name, phone, course, faculty, topic, rating, opts, more):
    return dict(zip(SOURCE_HEADERS, [ts, email, name, phone, course, faculty,
                                     topic, rating, opts, more]))


SOURCE_RECORDS = [
    _row("01/01/2026 10:00:00", "a@x.com", "Asha", "111", TARGET, "Sidra",
         "AI Tools", "5 - Extremely Satisfied", "All of the above", "Outstanding"),
    _row("01/01/2026 10:05:00", "b@x.com", "Bina", "222", TARGET, "Sidra",
         "AI Tools", "4 - Satisfied", "", "good learning"),
    _row("01/01/2026 10:06:00", "c@x.com", "Chitra", "333", TARGET, "Sidra",
         "AI Tools", "5", "", "NA"),                      # junk -> skipped
    _row("01/01/2026 10:07:00", "d@x.com", "Devi", "444", OTHER, "X",
         "Other", "5", "", "Great"),                      # wrong course -> skip
    _row("01/01/2026 10:00:00", "a@x.com", "Asha", "111", TARGET, "Sidra",
         "AI Tools", "5", "All of the above", "Outstanding"),  # dup of row 1
]


class FakeWorksheet:
    title = "AI for Women"


class FakeClient:
    def __init__(self):
        self.appended = []

    def read_source_records(self):
        return SOURCE_RECORDS

    def open_destination(self):
        return FakeWorksheet()

    def read_header(self, ws):
        return DEST_HEADERS

    def read_existing_rows(self, ws):
        return []  # empty destination

    def append_rows(self, ws, rows):
        self.appended.extend(rows)
        return len(rows)


def _cfg(tmp_state):
    return SimpleNamespace(
        program_column="Which course are you giving feedback for?",
        program_filters=[TARGET],
        feedback_column="We value your feedback. Please let us know more.",
        min_feedback_chars=2,
        dry_run=False,
        source_label="Class feedback (AI for Women)",
        state_file=tmp_state,
        field_map={
            "Date": ["timestamp", "date"],
            "Student name": ["name of the learner", "learner"],
            "Email": ["email"],
            "Phone": ["phone"],
            "Course": ["which course", "course"],
            "Expert": ["faculty", "expert"],
            "Topic": ["topic"],
            "Rating": ["scale of 1", "rating"],
            "Options": ["if you had a good experience", "options"],
            "Source": [],
        },
    )


def test_full_run(tmp_path):
    state = str(tmp_path / "state.json")
    client = FakeClient()
    wf = FeedbackSyncWorkflow(_cfg(state), client, RuleBasedRewriter())
    res = wf.run()

    assert res.source_rows == 5
    assert res.relevant_rows == 4          # 3 target + 1 duplicate target
    assert res.skipped_no_feedback == 1    # "NA"
    assert res.duplicates == 1             # repeated Asha row
    assert res.appended == 2               # Asha + Bina

    # Destination rows are in destination column order.
    assert len(client.appended) == 2
    asha = client.appended[0]
    assert asha[0] == 1                      # S. no
    assert asha[2] == "Asha"                 # Student name
    assert asha[3] == "a@x.com"              # Email
    assert asha[5] == TARGET                 # Course
    assert asha[10].endswith(".")            # Feedback rewritten
    assert asha[11] == "Class feedback (AI for Women)"  # Source
    assert client.appended[1][0] == 2        # serial increments


def test_rerun_is_idempotent(tmp_path):
    """A second run with the same state must append nothing (no duplicates)."""
    state = str(tmp_path / "state.json")
    cfg = _cfg(state)

    c1 = FakeClient()
    FeedbackSyncWorkflow(cfg, c1, RuleBasedRewriter()).run()
    assert len(c1.appended) == 2

    # Second run: state file now remembers the keys.
    c2 = FakeClient()
    res2 = FeedbackSyncWorkflow(cfg, c2, RuleBasedRewriter()).run()
    assert res2.appended == 0
    assert len(c2.appended) == 0
