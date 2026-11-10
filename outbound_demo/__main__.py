import argparse
import json
from pathlib import Path

from .pipeline import NoSendLedger, apply_reviews, prepare


def main():
    parser = argparse.ArgumentParser(description="Run an outbound workflow on synthetic, local-only fixtures")
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    examples = Path(__file__).resolve().parents[1] / "examples"
    fixture = json.loads((examples / "fixture.json").read_text())
    decisions = json.loads((examples / "review-decisions.json").read_text())
    drafts, trace = prepare(fixture)
    reviewed = apply_reviews(drafts, decisions)
    ledger = NoSendLedger(args.output / "upload-ledger.json")
    staged = ledger.stage(reviewed, fixture["leads"])
    ledger.sync(json.loads((examples / "events.json").read_text()))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "drafts.json").write_text(json.dumps(reviewed, indent=2) + "\n")
    summary = {"mode": "synthetic fixtures; local simulation", "input_rows": len(fixture["leads"]),
               "drafts": len(drafts), "new_simulated_uploads": len(staged), "emails_sent": 0, "trace": trace}
    (args.output / "run.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
