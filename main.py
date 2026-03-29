"""
FastAPI Main Application
========================

REST API microservice for HR code testing platform.
Wraps rce_engine.py with JWT authentication and candidate management.
"""

import time
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import (
    Candidate,
    User,
    CandidateCreate,
    CandidateResponse,
    CandidateList,
    CodeSubmission,
    ExecutionResult,
    UserCreate,
    UserLogin,
    Token
)
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from rce_engine import SafeExecutor

# Initialize RCE executor
rce_executor = SafeExecutor()


# ============================================================
# Lifespan Events
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


# ============================================================
# FastAPI App Setup
# ============================================================

app = FastAPI(
    title="HR Code Testing Platform",
    description="REST API for managing candidates and executing code submissions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Authentication Endpoints
# ============================================================

@app.post("/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Returns JWT token on successful registration.
    """
    # Check if username exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate token
    access_token = create_access_token(data={"sub": new_user.username})
    return Token(access_token=access_token)


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.

    OAuth2 compatible - works with Swagger UI Authorize button.
    """
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token)


# ============================================================
# Candidate Endpoints
# ============================================================

@app.post("/candidates/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(
    candidate_data: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new candidate.

    Requires authentication.
    """
    # Check if email exists
    if db.query(Candidate).filter(Candidate.email == candidate_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    new_candidate = Candidate(
        name=candidate_data.name,
        email=candidate_data.email
    )
    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)

    return new_candidate


@app.get("/candidates/", response_model=CandidateList)
def list_candidates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all candidates.

    Requires authentication. Supports pagination.
    """
    total = db.query(Candidate).count()
    candidates = db.query(Candidate).offset(skip).limit(limit).all()

    return CandidateList(
        candidates=[CandidateResponse.model_validate(c) for c in candidates],
        total=total
    )


@app.get("/candidates/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific candidate by ID.

    Requires authentication.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    return candidate


# ============================================================
# Code Execution Endpoint
# ============================================================

@app.post("/execute/", response_model=ExecutionResult)
def execute_code(
    submission: CodeSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute submitted Python code in a sandboxed environment.

    Requires authentication.
    Returns execution results with stdout, stderr, and status.
    """
    start_time = time.time()

    result = rce_executor.execute(submission.code, timeout=submission.timeout)

    execution_time_ms = (time.time() - start_time) * 1000

    return ExecutionResult(
        success=result["success"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        timed_out=result["timed_out"],
        execution_time_ms=round(execution_time_ms, 3)
    )


# ============================================================
# Health Check
# ============================================================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "hr-code-testing"}


# ============================================================
# Application Entry Point
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)