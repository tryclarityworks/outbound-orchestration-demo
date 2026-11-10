"""Local orchestration around extracted rendering and evidence checks.

All enrichment and model recommendations are synthetic fixtures. No network or
sending adapter is imported by this package.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import CAMPAIGNS
from .render import _render, _variant
from .rules import scrub_fabrication


def contact_key(lead: dict) -> str:
    email = str(lead.get("email", "")).strip().casefold()
    if "@" not in email:
        raise ValueError("A synthetic contact needs an email address")
    domain = email.rsplit("@", 1)[1]
    if domain not in {"example.com", "example.org", "example.net"} and not domain.endswith((".example", ".test", ".invalid")):
        raise ValueError("The demo accepts only reserved example domains")
    return email


def suppressed(lead: dict) -> bool:
    return bool(lead.get("do_not_contact") or lead.get("replied") or lead.get("unsubscribed"))


def draft_hash(draft: dict) -> str:
    payload = {k: draft[k] for k in ("contact_key", "campaign", "subject", "body")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def route(recommendation: dict, research: dict) -> tuple[str, str]:
    candidate = recommendation.get("campaign")
    if candidate not in CAMPAIGNS:
        candidate = "hiring" if research.get("hiring_signal") else "operations"
        reason = "Unknown model recommendation; used an evidence-based fallback"
    else:
        reason = "Fixture model recommendation passed the allowed-campaign check"
    if CAMPAIGNS[candidate].requires_hiring_signal and not research.get("hiring_signal"):
        return "operations", "Overrode hiring campaign because the source has no hiring signal"
    return candidate, reason


def prepare(fixture: dict) -> tuple[list[dict], list[dict]]:
    drafts, trace, seen = [], [], set()
    for lead in fixture["leads"]:
        key = contact_key(lead)
        if key in seen:
            trace.append({"id": lead["id"], "status": "duplicate"})
            continue
        seen.add(key)
        if suppressed(lead):
            trace.append({"id": lead["id"], "status": "suppressed"})
            continue
        research = fixture["research"][lead["id"]]
        detail = scrub_fabrication(research.get("detail", ""), research.get("context", ""),
                                   ", ".join(research.get("roles_hiring", [])),
                                   "yes" if research.get("hiring_signal") else "no")
        campaign, reason = route(fixture["recommendations"][lead["id"]], research)
        rendered = _render(CAMPAIGNS[campaign], {
            "Personalization Line": detail, "Name": lead["name"],
        }, _variant(key))
        if not rendered:
            trace.append({"id": lead["id"], "status": "needs-detail"})
            continue
        subject, body = rendered
        draft = {"id": lead["id"], "contact_key": key, "campaign": campaign,
                 "subject": subject, "body": body, "review_status": "pending",
                 "route_reason": reason}
        draft["content_hash"] = draft_hash(draft)
        drafts.append(draft)
        trace.append({"id": lead["id"], "status": "pending-review", "campaign": campaign})
    return drafts, trace


def apply_reviews(drafts: list[dict], decisions: list[dict]) -> list[dict]:
    by_id = {d["id"]: d for d in decisions}
    reviewed = []
    for draft in drafts:
        item = dict(draft)
        decision = by_id.get(draft["id"])
        if decision:
            if decision.get("content_hash") != draft_hash(draft):
                raise ValueError("Review is stale: draft content changed")
            if not decision.get("reviewer", "").strip() or decision.get("decision") not in {"approved", "rejected"}:
                raise ValueError("Review needs a reviewer and an explicit decision")
            item.update(review_status=decision["decision"], reviewer=decision["reviewer"],
                        approved_hash=decision["content_hash"])
        reviewed.append(item)
    return reviewed


class NoSendLedger:
    """Simulate an upload locally. No email provider or network transport exists."""

    def __init__(self, path: Path):
        self.path = path
        self.rows = json.loads(path.read_text()) if path.exists() else []

    def stage(self, drafts: list[dict], current_leads: list[dict]) -> list[dict]:
        # A suppression flag on any duplicate record wins.
        current = {}
        for lead in current_leads:
            key = contact_key(lead)
            current[key] = {"suppressed": suppressed(lead) or current.get(key, {}).get("suppressed", False),
                            "verified": (lead.get("verification_status") == "deliverable"
                                         and current.get(key, {}).get("verified", True))}
        existing = {r["contact_key"] for r in self.rows}
        staged = []
        for draft in drafts:
            key = draft["contact_key"]
            state = current.get(key)
            if draft.get("review_status") != "approved" or not draft.get("reviewer"):
                continue
            if draft.get("approved_hash") != draft_hash(draft):
                raise ValueError("Approved draft was edited; obtain a new review")
            if not state or state["suppressed"] or not state["verified"] or key in existing:
                continue
            row = {"contact_key": key, "draft_id": draft["id"], "status": "simulated-upload",
                   "content_hash": draft_hash(draft), "email_sent": False}
            self.rows.append(row)
            staged.append(row)
            existing.add(key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.rows, indent=2) + "\n")
        return staged

    def sync(self, events: list[dict]) -> None:
        for event in events:
            if event.get("kind") not in {"reply", "unsubscribe"}:
                raise ValueError("Unknown fixture event")
            for row in self.rows:
                if row["contact_key"] == event["contact_key"]:
                    row["status"] = "suppressed-after-" + event["kind"]
        self.path.write_text(json.dumps(self.rows, indent=2) + "\n")
