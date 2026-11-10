"""Deterministic text and evidence checks adapted from Clarity Works tooling."""
import re

HIRING_TERMS = ("hiring", "hire ", "hired", "recruiting", "recruit ", "job opening", "open role", "staffing")

def scrub_dashes(text: str) -> str:
    """Normalize em/en dashes in a templated draft."""
    return re.sub(r"\s*[—–]\s*", ", ", text or "")

def scrub_fabrication(detail: str, context: str, roles_hiring: str, hiring_signal: str) -> str:
    """Reject (empty) a detail that claims a hiring signal not grounded in the lead's
    own scraped data (Roles Hiring / Hiring Signal / Company Context)."""
    if not detail:
        return detail
    low = detail.lower()
    if any(t in low for t in HIRING_TERMS):
        grounded = (bool((roles_hiring or "").strip())
                    or (hiring_signal or "").strip().lower() == "yes"
                    or any(t in (context or "").lower() for t in HIRING_TERMS))
        if not grounded:
            return ""
    return detail
