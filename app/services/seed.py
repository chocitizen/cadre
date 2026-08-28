from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import Book, ContentState, DoctrineEntry, ExecutionState, Project, Specialist, Voyage, VoyageLesson
from app.services.gateway import default_execution_state

SEED_DOCTRINE = [
    ("majestic-standard", "Majestic is the standard", "Favor premium, authentic, refined, durable, intentional, high-quality outcomes over merely adequate alternatives.", "governing_standard"),
    ("sovereignty", "Sovereignty", "Retain control of governance, memory, identity, data, routing, architecture, and source-of-truth authority while using interchangeable external capabilities where useful.", "governing_standard"),
    ("kiss", "KISS", "Use the simplest reliable approach that meets the objective. Introduce complexity only when it creates justified long-term value.", "decision_filter"),
    ("presence", "Presence", "Maintain a visible and understandable current work state, including active work, completion, blockers, dependencies, and required human action.", "operating_standard"),
    ("flow", "Flow", "Continue execution through validated handoffs without unnecessary stops. Interrupt the human only for a concrete dependency.", "operating_standard"),
    ("synchronicity", "Synchronicity", "All specialists operate from the same canonical current context, decisions, constraints, source-of-truth references, and downstream dependencies.", "operating_standard"),
    ("alchemy", "Alchemy", "Transform ideas, knowledge, and existing resources into higher-value systems, capabilities, and outcomes through intelligent synthesis, engineering, and refinement.", "capability"),
    (
        "constitutional-execution",
        "CADRE Constitutional Execution Standard",
        "Every substantive artifact is produced by the strongest appropriate lead, support, and validation authorities; every handoff is self-contained and copy-ready; operational interaction removes filler; SIGNAL advances then delivers; DEPLOY remains NOT READY until production, owner authentication, protected-interface, critical-journey, URL, secure-credential-delivery, and rollback gates pass; founder and client workflows inherit the same behavior across voice, text, mobile, desktop, API, automation, and future interfaces.",
        "governing_standard",
    ),
]


def seed_doctrine(db: Session) -> None:
    for key, title, body, category in SEED_DOCTRINE:
        if db.scalar(select(DoctrineEntry).where(DoctrineEntry.key == key)) is None:
            db.add(DoctrineEntry(key=key, title=title, body=body, category=category, version="1.0", is_active=True))
    db.commit()


SPECIALISTS = [
    ("arc", "ARC", "AI integration and system architecture", ["architecture", "ai_routing"], ["integration", "architecture", "provider"], ["contract_validated", "failure_path_tested", "self_contained_handoff"]),
    ("invictus", "Invictus", "Security review and risk validation", ["security_review"], ["security", "privacy", "authorization"], ["finding_validated", "counterevidence_checked", "secrets_preserved"]),
    ("porter", "Porter", "Maintenance and system housekeeping", ["maintenance"], ["cleanup", "dependency", "drift"], ["tests_pass", "rollback_available", "dual_delivery_recorded"]),
    ("griot", "Griot", "Provenance, audit, and canonical record stewardship", ["audit", "provenance"], ["source", "history", "record"], ["source_cited", "receipt_recorded", "copy_ready_delivery"]),
    (
        "al",
        "Al",
        "LANSEIR sovereign engineering and repository operator",
        [
            "repository_administration",
            "codebase_maintenance",
            "ci_cd",
            "deployment_staging",
            "build_and_test",
            "dependency_management",
            "integration_routing",
            "operational_diagnostics",
            "rollback_preparation",
        ],
        ["engineering", "repository", "build", "test", "deploy", "automation", "integration", "recovery"],
        ["tests_pass", "secrets_preserved", "rollback_available", "material_evidence_recorded", "self_contained_handoff", "copy_ready_delivery"],
    ),
    ("liv", "Liv", "Personal and client operations", ["client_operations"], ["personal", "client", "journey"], ["privacy_preserved", "friction_minimized", "next_action_clear", "channel_parity"]),
    ("harv", "Harv", "Business operations and execution", ["business_operations"], ["business", "launch", "operations"], ["owner_identified", "result_measurable"]),
    ("concierge", "Concierge", "Procurement and integration coordination", ["procurement", "integration"], ["procure", "vendor", "connect"], ["authority_confirmed", "exit_path_documented"]),
]


def seed_product(db: Session) -> None:
    if db.scalar(select(Project).where(Project.slug == "lanseir-platform")) is None:
        db.add(
            Project(
                slug="lanseir-platform",
                name="LANSEIR Platform",
                description="Sovereign parent platform with CADRE as the internal execution system.",
                source_of_truth={
                    "registry": "source_of_truth_registry.json",
                    "doctrine": "00_governance/",
                    "locked_assets": [
                        "source_of_truth_registry.json",
                        "00_governance/lanseir_identity_charter.md",
                        "00_governance/promotion_rule.md",
                    ],
                },
            )
        )

    if db.get(ExecutionState, "canonical") is None:
        db.add(ExecutionState(key="canonical", payload=default_execution_state(), updated_by="system"))

    if db.scalar(select(Book).where(Book.slug == "vessel-mastering-the-ship-of-self")) is None:
        db.add(
            Book(
                slug="vessel-mastering-the-ship-of-self",
                title="VESSEL",
                subtitle="Mastering the Ship of Self",
                author="Cho Zen Dell",
                publisher="Sirrah Publishing",
                description="A grounded exploration of self-mastery through the enduring relationship between captain and vessel.",
                state=ContentState.draft,
            )
        )

    for key, name, responsibility, permissions, routing, validation in SPECIALISTS:
        specialist = db.scalar(select(Specialist).where(Specialist.key == key))
        if specialist is None:
            db.add(
                Specialist(
                    key=key,
                    name=name,
                    responsibility=responsibility,
                    permissions=permissions,
                    routing_criteria=routing,
                    validation_requirements=validation,
                )
            )
        else:
            specialist.name = name
            specialist.responsibility = responsibility
            specialist.permissions = permissions
            specialist.routing_criteria = routing
            specialist.validation_requirements = validation
            specialist.is_active = True

    voyage = db.scalar(select(Voyage).where(Voyage.slug == "first-crossing"))
    if voyage is None:
        voyage = Voyage(
            slug="first-crossing",
            title="The First Crossing",
            description="A three-part practice for seeing present reality, naming your heading, and choosing the next controlled action.",
            state=ContentState.available,
        )
        voyage.lessons = [
            VoyageLesson(position=1, title="Take Your Bearings", guidance="Pause before changing course. Describe present conditions without judgment or prediction.", prompt="What is true now, and what evidence supports it?"),
            VoyageLesson(position=2, title="Name the Heading", guidance="A heading is a direction, not a guarantee. Choose the outcome that best honors your authority and responsibility.", prompt="What direction matters most, and why does it deserve your effort?"),
            VoyageLesson(position=3, title="Set the Next Watch", guidance="Translate intention into a bounded action you can complete and verify.", prompt="What is the smallest meaningful action within your control, and how will you know it is complete?"),
        ]
        db.add(voyage)
    db.commit()
