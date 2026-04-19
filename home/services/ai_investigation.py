"""
home/services/ai_investigation.py
Groq-powered investigation intelligence.
"""

import json
from groq import Groq
from django.conf import settings


def draft_investigation_report(crime_report) -> dict:
    """
    Given a CrimeReport object, Groq generates a complete first draft
    of the investigation report — IPC sections, scene narrative, next steps.
    Called when officer clicks "AI Draft" on the form.
    Returns a dict that pre-fills the form fields.
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    prompt = f"""
You are an expert Indian police officer with 20 years of investigation experience in Maharashtra.
Draft a structured investigation report based on this crime report.

Crime Type: {crime_report.crime_type}
Description: {crime_report.description}
Location: {crime_report.address}
Date Reported: {crime_report.reported_at.strftime('%d %B %Y')}
Status: {crime_report.resolution_status}

Return ONLY this exact JSON (no markdown, no explanation):
{{
  "incident_summary": "Factual 3-4 sentence account of the incident: who, what, where, when, how. Professional police language.",
  "ipc_sections": "Comma-separated relevant IPC sections with crime names e.g. '302 (Murder), 34 (Common Intention)'",
  "scene_description": "2-3 sentences describing what officers would typically find at this type of crime scene.",
  "action_taken": "Chronological list of 5-6 standard investigation steps for this crime type, each on a new line starting with a date placeholder [DATE].",
  "evidence_notes": "List of 3-4 typical evidence items that should be collected for this crime type.",
  "ai_risk_assessment": "2 sentences: likelihood of successful prosecution based on crime type + what critical evidence is typically missing in such cases.",
  "ai_next_steps": "3 concrete next investigation steps an officer should take, numbered.",
  "suggested_outcome": "chargesheet_filed or closure_report or further_investigation — pick most likely for this crime type"
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[AI Draft Error] {e}")
        return {}


def analyze_completed_report(report) -> dict:
    """
    After officer fills the form, Groq does a quality check:
    - Missing evidence flags
    - IPC section validation
    - Prosecution strength score (0-100)
    - SHO review notes
    Called on submit, result shown to officer before final submission.
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    witnesses = len(report.witness_statements or [])
    evidence  = len(report.evidence_items or [])

    prompt = f"""
You are a senior IPS officer reviewing an investigation report before court submission.

Case Type: {report.crime_report.crime_type}
IPC Sections Filed: {report.ipc_sections}
FIR Number: {report.fir_number or 'Not filed'}
Actions Taken: {report.action_taken[:300]}
Witnesses: {witnesses} recorded
Evidence Items: {evidence} logged
Arrests: {'Yes — ' + report.arrest_details[:100] if report.arrests_made else 'None'}
CCTV Reviewed: {report.cctv_reviewed}
Site Visited: {report.site_visited}
Forensics Sent: {report.forensic_sent}
Officer Conclusion: {report.officer_conclusion[:200] if report.officer_conclusion else 'Not written'}

Return ONLY this JSON:
{{
  "prosecution_strength": 0-100,
  "strength_label": "Weak / Moderate / Strong / Very Strong",
  "critical_gaps": ["gap1", "gap2"],
  "ipc_validation": "Valid / Missing sections: XYZ / Incorrect: explanation",
  "sho_flag": "yes or no — should SHO flag this for revision?",
  "sho_note": "One sentence for SHO: what to watch for in this report",
  "court_readiness": "Ready / Needs work: explain in one sentence",
  "commendation": "One sentence acknowledging strong aspects of the investigation"
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[AI Review Error] {e}")
        return {
            "prosecution_strength": 50,
            "strength_label": "Moderate",
            "critical_gaps": ["AI review unavailable"],
            "ipc_validation": "Manual review required",
            "sho_flag": "no",
            "sho_note": "AI review unavailable",
            "court_readiness": "Manual review required",
            "commendation": "",
        }


def generate_witness_prompt(crime_type: str, witness_number: int) -> str:
    """
    Returns a Groq-generated question guide for interviewing
    the Nth witness for a specific crime type.
    Called when officer clicks "+ Add Witness".
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    prompt = f"""
You are a senior detective training a junior officer.
Generate 5 specific interview questions for witness #{witness_number} 
in a {crime_type} case under Maharashtra Police jurisdiction.

Return ONLY a JSON array of 5 strings (the questions). No extra text.
["question1", "question2", "question3", "question4", "question5"]
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[Witness Prompt Error] {e}")
        return [
            "What did you see at the time of the incident?",
            "Can you describe the accused/suspect?",
            "What time did you witness this?",
            "Was anyone else present with you?",
            "Are you willing to testify in court?",
        ]
