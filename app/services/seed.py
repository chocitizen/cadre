from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import DoctrineEntry

SEED_DOCTRINE = [
    ("majestic-standard", "Majestic is the standard", "Favor premium, authentic, refined, durable, intentional, high-quality outcomes over merely adequate alternatives.", "governing_standard"),
    ("sovereignty", "Sovereignty", "Retain control of governance, memory, identity, data, routing, architecture, and source-of-truth authority while using interchangeable external capabilities where useful.", "governing_standard"),
    ("kiss", "KISS", "Use the simplest reliable approach that meets the objective. Introduce complexity only when it creates justified long-term value.", "decision_filter"),
    ("presence", "Presence", "Maintain a visible and understandable current work state, including active work, completion, blockers, dependencies, and required human action.", "operating_standard"),
    ("flow", "Flow", "Continue execution through validated handoffs without unnecessary stops. Interrupt the human only for a concrete dependency.", "operating_standard"),
    ("synchronicity", "Synchronicity", "All specialists operate from the same canonical current context, decisions, constraints, source-of-truth references, and downstream dependencies.", "operating_standard"),
    ("alchemy", "Alchemy", "Transform ideas, knowledge, and existing resources into higher-value systems, capabilities, and outcomes through intelligent synthesis, engineering, and refinement.", "capability"),
]


def seed_doctrine(db: Session) -> None:
    for key, title, body, category in SEED_DOCTRINE:
        if db.scalar(select(DoctrineEntry).where(DoctrineEntry.key == key)) is None:
            db.add(DoctrineEntry(key=key, title=title, body=body, category=category, version="1.0", is_active=True))
    db.commit()
