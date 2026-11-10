import copy
import json
from pathlib import Path
import tempfile
import unittest

from outbound_demo.pipeline import NoSendLedger, apply_reviews, contact_key, draft_hash, prepare, route

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class PipelineBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((EXAMPLES / "fixture.json").read_text())
        self.drafts, self.trace = prepare(self.fixture)
        self.decisions = json.loads((EXAMPLES / "review-decisions.json").read_text())
        self.reviewed = apply_reviews(self.drafts, self.decisions)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "ledger.json"

    def test_prepare_keeps_suppressed_and_ungrounded_records_out_of_review(self):
        self.assertEqual([d["id"] for d in self.drafts], ["alpha", "bravo"])
        self.assertEqual([t["status"] for t in self.trace],
                         ["pending-review", "pending-review", "needs-detail", "suppressed", "suppressed", "duplicate"])

    def test_hiring_recommendation_requires_source_evidence(self):
        campaign, reason = route({"campaign": "hiring"}, {"hiring_signal": False})
        self.assertEqual(campaign, "operations")
        self.assertIn("no hiring signal", reason)

    def test_unknown_campaign_falls_back_to_an_allowed_one(self):
        self.assertEqual(route({"campaign": "invented"}, {"hiring_signal": True})[0], "hiring")

    def test_pending_drafts_cannot_be_uploaded(self):
        self.assertEqual(NoSendLedger(self.path).stage(self.drafts, self.fixture["leads"]), [])

    def test_rejected_drafts_cannot_be_uploaded(self):
        decisions = copy.deepcopy(self.decisions)
        decisions[0]["decision"] = "rejected"
        self.assertEqual(NoSendLedger(self.path).stage(apply_reviews(self.drafts, decisions), self.fixture["leads"]), [])

    def test_stale_review_is_rejected(self):
        self.drafts[0]["body"] += " Changed after the review."
        with self.assertRaisesRegex(ValueError, "stale"):
            apply_reviews(self.drafts, self.decisions)

    def test_reviewer_is_required(self):
        self.decisions[0]["reviewer"] = ""
        with self.assertRaises(ValueError):
            apply_reviews(self.drafts, self.decisions)

    def test_edit_after_approval_requires_new_review(self):
        self.reviewed[0]["subject"] = "Changed subject"
        with self.assertRaisesRegex(ValueError, "edited"):
            NoSendLedger(self.path).stage(self.reviewed, self.fixture["leads"])

    def test_latest_suppression_is_checked_after_review(self):
        self.fixture["leads"][0]["do_not_contact"] = True
        self.assertEqual(NoSendLedger(self.path).stage(self.reviewed, self.fixture["leads"]), [])

    def test_reply_on_duplicate_record_wins(self):
        self.fixture["leads"][-1]["replied"] = True
        self.assertEqual(NoSendLedger(self.path).stage(self.reviewed, self.fixture["leads"]), [])

    def test_case_insensitive_contact_identity_prevents_repeat_upload(self):
        ledger = NoSendLedger(self.path)
        self.assertEqual(len(ledger.stage(self.reviewed, self.fixture["leads"])), 1)
        self.assertEqual(NoSendLedger(self.path).stage(self.reviewed, self.fixture["leads"]), [])
        self.assertFalse(ledger.rows[0]["email_sent"])

    def test_missing_verification_blocks_upload(self):
        for lead in self.fixture["leads"]:
            if lead["id"] == "alpha":
                lead["verification_status"] = "unknown"
        self.assertEqual(NoSendLedger(self.path).stage(self.reviewed, self.fixture["leads"]), [])

    def test_real_contact_domains_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "reserved"):
            contact_key({"email": "person@a-real-company.com"})

    def test_fixture_reply_is_written_back_to_ledger(self):
        ledger = NoSendLedger(self.path)
        ledger.stage(self.reviewed, self.fixture["leads"])
        ledger.sync([{"contact_key": "alex@alpha.example", "kind": "reply"}])
        self.assertEqual(ledger.rows[0]["status"], "suppressed-after-reply")

    def test_hash_binds_destination_and_content(self):
        draft = copy.deepcopy(self.drafts[0])
        original = draft_hash(draft)
        draft["contact_key"] = "another@example.com"
        self.assertNotEqual(draft_hash(draft), original)
