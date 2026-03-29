"""
Test Suite for FastAPI RCE Microservice
========================================

Comprehensive tests using pytest and FastAPI TestClient.
Tests: authentication, candidate CRUD, code execution, and security.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from auth import get_password_hash
from models import User


# ============================================================
# Test Database Setup
# ============================================================

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user and return credentials."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123")
    )
    db_session.add(user)
    db_session.commit()
    return {"username": "testuser", "password": "testpass123"}


@pytest.fixture
def auth_token(client, test_user):
    """Get authentication token for test user."""
    response = client.post("/auth/login", json=test_user)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Return authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


# ============================================================
# Test: Authentication Endpoints
# ============================================================

class TestAuthentication:
    """Tests for auth endpoints."""

    def test_register_new_user(self, client):
        """Test successful user registration."""
        response = client.post("/auth/register", json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepass123"
        })
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with existing username fails."""
        response = client.post("/auth/register", json={
            "username": "testuser",
            "email": "another@example.com",
            "password": "securepass123"
        })
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email fails."""
        response = client.post("/auth/register", json={
            "username": "anotheruser",
            "email": "test@example.com",
            "password": "securepass123"
        })
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post("/auth/login", json=test_user)
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password fails."""
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user fails."""
        response = client.post("/auth/login", json={
            "username": "nobody",
            "password": "doesntmatter"
        })
        assert response.status_code == 401


# ============================================================
# Test: Unauthorized Access Rejections
# ============================================================

class TestUnauthorizedAccess:
    """Tests for endpoints requiring authentication."""

    def test_create_candidate_without_auth(self, client):
        """Test candidate creation requires auth."""
        response = client.post("/candidates/", json={
            "name": "John Doe",
            "email": "john@example.com"
        })
        assert response.status_code == 401

    def test_list_candidates_without_auth(self, client):
        """Test listing candidates requires auth."""
        response = client.get("/candidates/")
        assert response.status_code == 401

    def test_get_candidate_without_auth(self, client):
        """Test getting candidate requires auth."""
        response = client.get("/candidates/1")
        assert response.status_code == 401

    def test_execute_code_without_auth(self, client):
        """Test code execution requires auth."""
        response = client.post("/execute/", json={
            "code": "print('hello')",
            "language": "python",
            "timeout": 3
        })
        assert response.status_code == 401


# ============================================================
# Test: Candidate CRUD Operations
# ============================================================

class TestCandidateOperations:
    """Tests for candidate management."""

    def test_create_candidate_success(self, client, auth_headers):
        """Test successful candidate creation."""
        response = client.post("/candidates/", json={
            "name": "John Doe",
            "email": "john.doe@example.com"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["email"] == "john.doe@example.com"
        assert "id" in data
        assert "created_at" in data

    def test_create_duplicate_email_candidate(self, client, auth_headers):
        """Test creating candidate with duplicate email fails."""
        # Create first candidate
        client.post("/candidates/", json={
            "name": "First User",
            "email": "same@example.com"
        }, headers=auth_headers)

        # Try duplicate
        response = client.post("/candidates/", json={
            "name": "Second User",
            "email": "same@example.com"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_list_candidates_empty(self, client, auth_headers):
        """Test listing candidates when empty."""
        response = client.get("/candidates/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["candidates"] == []

    def test_list_candidates_with_data(self, client, auth_headers):
        """Test listing candidates returns all."""
        # Create multiple candidates
        for i in range(3):
            client.post("/candidates/", json={
                "name": f"Candidate {i}",
                "email": f"candidate{i}@example.com"
            }, headers=auth_headers)

        response = client.get("/candidates/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["candidates"]) == 3

    def test_get_candidate_by_id(self, client, auth_headers):
        """Test getting specific candidate."""
        # Create candidate
        create_response = client.post("/candidates/", json={
            "name": "Jane Doe",
            "email": "jane@example.com"
        }, headers=auth_headers)
        candidate_id = create_response.json()["id"]

        # Get candidate
        response = client.get(f"/candidates/{candidate_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Jane Doe"

    def test_get_nonexistent_candidate(self, client, auth_headers):
        """Test getting nonexistent candidate returns 404."""
        response = client.get("/candidates/999", headers=auth_headers)
        assert response.status_code == 404
        assert "Candidate not found" in response.json()["detail"]


# ============================================================
# Test: Code Execution Endpoint
# ============================================================

class TestCodeExecution:
    """Tests for code execution endpoint."""

    def test_execute_hello_world(self, client, auth_headers):
        """Test standard 'Hello World' execution."""
        response = client.post("/execute/", json={
            "code": "print('Hello World')",
            "language": "python",
            "timeout": 3
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Hello World" in data["stdout"]
        assert data["stderr"] == ""
        assert data["timed_out"] is False
        assert data["execution_time_ms"] is not None

    def test_execute_syntax_error(self, client, auth_headers):
        """Test code with syntax error returns proper error."""
        response = client.post("/execute/", json={
            "code": "print('missing quote",
            "language": "python",
            "timeout": 3
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert len(data["stderr"]) > 0
        assert "SyntaxError" in data["stderr"] or "EOL" in data["stderr"]

    def test_execute_infinite_loop_timeout(self, client, auth_headers):
        """Test malicious infinite loop triggers timeout."""
        response = client.post("/execute/", json={
            "code": "while True: pass",
            "language": "python",
            "timeout": 2
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["timed_out"] is True
        assert "timed out" in data["stderr"].lower()

    def test_execute_with_calculation(self, client, auth_headers):
        """Test code with computation returns correct result."""
        response = client.post("/execute/", json={
            "code": "x = 5 + 10\nprint(f'Result: {x}')",
            "language": "python",
            "timeout": 3
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Result: 15" in data["stdout"]

    def test_execute_import_math(self, client, auth_headers):
        """Test code with imports works correctly."""
        response = client.post("/execute/", json={
            "code": "import math\nprint(f'Pi: {math.pi:.2f}')",
            "language": "python",
            "timeout": 3
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Pi: 3.14" in data["stdout"]


# ============================================================
# Test: Health Check
# ============================================================

class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check_no_auth_required(self, client):
        """Test health check works without authentication."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])