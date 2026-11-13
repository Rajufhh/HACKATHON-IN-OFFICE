from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import Base, engine

# Register all database models
import app.models

# Import routes
from app.routes.learner_routes import router as learner_router
from app.routes.assessment_routes import router as assessment_router
from app.routes.reviewer_routes import router as reviewer_router
from app.routes.integrity_rule_routes import router as integrity_rule_router
from app.routes.submission_routes import router as submission_router
from app.routes.similarity_routes import router as similarity_router
from app.routes.case_routes import router as case_router
from app.routes.reviewer_conflict_routes import router as conflict_router
from app.routes.evidence_routes import router as evidence_router
from app.routes.decision_routes import router as decision_router
from app.routes.appeal_routes import router as appeal_router
from app.routes.analytics_routes import router as analytics_router
from app.routes.dataset_routes import router as dataset_router

app = FastAPI(
    title="Academic Integrity Management System",
    description="Academic Integrity and Similarity Case Management API",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Register API routers
app.include_router(learner_router)
app.include_router(assessment_router)
app.include_router(reviewer_router)
app.include_router(integrity_rule_router)
app.include_router(submission_router)
app.include_router(similarity_router)
app.include_router(case_router, prefix="/api/v1")
app.include_router(conflict_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(decision_router, prefix="/api/v1")
app.include_router(appeal_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(dataset_router, prefix="/api/v1")

@app.get("/")
def home():
    return {
        "message": "Academic Integrity Platform",
        "status": "Running"
    }

@app.get("/health")
def health():
    return {
        "status": "Healthy"
    }
