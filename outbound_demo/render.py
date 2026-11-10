"""Template rendering extracted from the production drafting stage."""
import hashlib
from .models import Campaign
from .rules import scrub_dashes

def _variant(lead_id: str) -> str:
    return "A" if int(hashlib.md5(lead_id.encode()).hexdigest(), 16) % 2 == 0 else "B"

def _first_name(name: str) -> str:
    return (name.split() or [""])[0]

def _render(campaign: Campaign, lead: dict, variant: str) -> tuple[str, str] | None:
    email = campaign.email or {}
    template = (email.get("template") or "").strip()
    subjects = email.get("subjects") or []
    if not template or not subjects:
        return None
    detail = scrub_dashes((lead.get("Personalization Line") or "").strip())
    if not detail:
        return None  # no honest opener; leave queued (a research pass could resolve later)
    first = _first_name(lead.get("Name", ""))

    body = template.replace("{{firstName}}", first).replace("{{detail}}", detail)
    body = scrub_dashes(body).strip()

    idx = 0 if variant == "A" else min(1, len(subjects) - 1)
    subject = subjects[idx].replace("{{firstName}}", first)
    return subject, body
