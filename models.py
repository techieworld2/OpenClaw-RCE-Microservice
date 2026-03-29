"""
Models Module
=============

Pydantic schemas for API validation and SQLAlchemy models for database.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import Column, Integer, String, DateTime
from database import Base


# ============================================================
# SQLAlchemy Models (Database Tables)
# ============================================================

class Candidate(Base):
    """
    Candidate database model.

    Represents a job candidate who will take coding tests.
    """
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class User(Base):
    """
    User database model for authentication.

    Represents an HR admin or recruiter who can manage candidates.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# ============================================================
# Pydantic Schemas (API Validation)
# ============================================================

# ---------- User Schemas ----------

class UserCreate(BaseModel):
    """Schema for user registration."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded token data."""
    username: Optional[str] = None


# ---------- Candidate Schemas ----------

class CandidateCreate(BaseModel):
    """Schema for creating a new candidate."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com"
            }
        }
    )


class CandidateResponse(BaseModel):
    """Schema for candidate response."""
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateList(BaseModel):
    """Schema for list of candidates."""
    candidates: list[CandidateResponse]
    total: int


# ---------- Code Execution Schemas ----------

class CodeSubmission(BaseModel):
    """Schema for code execution request."""
    code: str = Field(..., min_length=1)
    language: str = Field(default="python", pattern="^python$")
    timeout: int = Field(default=3, ge=1, le=60)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "print('Hello World')",
                "language": "python",
                "timeout": 3
            }
        }
    )


class ExecutionResult(BaseModel):
    """Schema for code execution response."""
    success: bool
    stdout: str
    stderr: str
    timed_out: bool
    execution_time_ms: Optional[float] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "stdout": "Hello World\n",
                "stderr": "",
                "timed_out": False,
                "execution_time_ms": 15.3
            }
        }
    )