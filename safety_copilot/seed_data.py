from .models import SafetyKnowledge, Helpline


def seed_database():

    # Prevent duplicate insert
    if SafetyKnowledge.objects.exists():
        return

    # SAFETY KNOWLEDGE
    SafetyKnowledge.objects.create(
        incident_type="theft",
        immediate_steps="Block bank cards, change passwords, report to police immediately",
        evidence_to_collect="CCTV footage, transaction logs, witness info, phone IMEI",
        safety_measures="Avoid isolated areas, enable phone tracking, keep emergency contacts ready"
    )

    SafetyKnowledge.objects.create(
        incident_type="cyber",
        immediate_steps="Block bank account, report to cyber portal, change passwords",
        evidence_to_collect="Screenshots, transaction IDs, email logs, phone numbers used",
        safety_measures="Never share OTP, verify links before clicking, enable 2FA"
    )

    SafetyKnowledge.objects.create(
        incident_type="harassment",
        immediate_steps="Inform trusted contacts, report to police, block offender",
        evidence_to_collect="Chat logs, call records, screenshots, location history",
        safety_measures="Avoid travelling alone at night, share live location"
    )

    SafetyKnowledge.objects.create(
        incident_type="assault",
        immediate_steps="Move to safe place, seek medical help, report to police",
        evidence_to_collect="Medical report, photos of injuries, witness statements",
        safety_measures="Avoid conflict zones, stay in well-lit public areas"
    )

    # HELPLINES
    Helpline.objects.create(
        name="National Emergency",
        number="112",
        category="All"
    )

    Helpline.objects.create(
        name="Women Helpline",
        number="1091",
        category="Women"
    )

    Helpline.objects.create(
        name="Cyber Crime Helpline",
        number="1930",
        category="Cyber"
    )

    print("✅ Safety Copilot Seed Data Inserted")
