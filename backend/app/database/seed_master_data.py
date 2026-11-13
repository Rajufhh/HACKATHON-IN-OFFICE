"""
Database Seeder for Master Data:
Seeds default Integrity Rules, sample Assessment, and Reviewer.
"""
from datetime import datetime, timezone, timedelta
from app.database.connection import SessionLocal
from app.models import Learner, Assessment, Reviewer, IntegrityRule

def seed():
    db = SessionLocal()
    try:
        # 1. Default Integrity Rules
        default_rules = [
            {
                "rule_code": "INT-2026-000001",
                "rule_name": "Low Similarity — Citation Notice",
                "min_similarity": 0,
                "max_similarity": 19,
                "action": "INFORMATION",
                "description": "Standard baseline overlap (quotes, common bibliography). No misconduct implied."
            },
            {
                "rule_code": "INT-2026-000002",
                "rule_name": "Moderate Similarity — Routine Audit",
                "min_similarity": 20,
                "max_similarity": 39,
                "action": "INFORMATION",
                "description": "Moderate common phrase match or template code. Flagged for institutional records."
            },
            {
                "rule_code": "INT-2026-000003",
                "rule_name": "Significant Similarity — Academic Review Required",
                "min_similarity": 40,
                "max_similarity": 69,
                "action": "REVIEW",
                "description": "Substantial similarity detected. Reviewer assigned to verify sources and quotes."
            },
            {
                "rule_code": "INT-2026-000004",
                "rule_name": "High Similarity — Priority Due Process Review",
                "min_similarity": 70,
                "max_similarity": 100,
                "action": "PRIORITY_REVIEW",
                "description": "Critical overlap. Immediate reviewer assignment. Full due process preserved."
            },
        ]
        for r in default_rules:
            if not db.query(IntegrityRule).filter_by(rule_code=r["rule_code"]).first():
                db.add(IntegrityRule(**r))

        # 2. Sample Assessment
        if not db.query(Assessment).filter_by(assessment_code="ASM-2026-000001").first():
            db.add(Assessment(
                assessment_code="ASM-2026-000001",
                title="Python Programming Assignment",
                description="Object-Oriented Programming and Data Structure Design in Python",
                assessment_type="ASSIGNMENT",
                max_marks=100,
                due_date=datetime.now(timezone.utc) + timedelta(days=14),
                status="PUBLISHED"
            ))

        # 3. Sample Reviewer
        if not db.query(Reviewer).filter_by(reviewer_code="REV-2026-000001").first():
            db.add(Reviewer(
                reviewer_code="REV-2026-000001",
                full_name="Arun Kumar",
                email="arun@example.com",
                department="Computer Science",
                specialization="Python & Software Engineering",
                max_active_cases=10,
                status="ACTIVE"
            ))

        db.commit()
        print("Master data seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed()

