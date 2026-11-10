from dataclasses import dataclass


@dataclass(frozen=True)
class Campaign:
    slug: str
    email: dict
    requires_hiring_signal: bool = False


CAMPAIGNS = {
    "operations": Campaign("operations", {
        "subjects": ["A workflow question", "A question for {{firstName}}"],
        "template": "Hi {{firstName}}, {{detail}} Would it be useful to compare how that handoff is tracked?",
    }),
    "hiring": Campaign("hiring", {
        "subjects": ["Your open coordinator role", "A workflow question"],
        "template": "Hi {{firstName}}, {{detail}} Would it be useful to map the repeated steps around that role?",
    }, requires_hiring_signal=True),
}
