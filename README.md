# OpenClaw RCE Microservice

A production-ready FastAPI microservice for secure Python code execution, built with OpenClaw.

## Overview

This microservice provides a REST API for managing candidates and executing Python code submissions in a sandboxed environment. It's designed for HR code testing platforms where safe execution of untrusted code is critical.

## Features

- **JWT Authentication** — Secure user registration and login with OAuth2 password flow
- **Candidate Management** — Create, list, and retrieve candidate records
- **Sandboxed Code Execution** — Execute Python code safely with resource limits:
  - Timeout enforcement
  - Memory restrictions
  - File system isolation
  - Network access disabled
- **Swagger UI** — Interactive API documentation with built-in authorization
- **SQLite Database** — Lightweight persistence with SQLAlchemy ORM

## Tech Stack

- **Framework:** FastAPI
- **Database:** SQLite with SQLAlchemy ORM
- **Authentication:** JWT (python-jose) + bcrypt password hashing
- **Code Execution:** RestrictedPython subprocess with resource limits

## Project Structure

```
├── main.py           # FastAPI application and endpoints
├── auth.py           # JWT authentication utilities
├── database.py       # Database configuration and session management
├── models.py         # Pydantic models and SQLAlchemy tables
├── rce_engine.py     # Sandboxed Python code executor
├── requirements.txt  # Python dependencies
├── test_api.py       # API integration tests
├── test_rce.py       # RCE engine unit tests
└── .gitignore        # Git ignore rules
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register new user account |
| `POST` | `/auth/login` | Authenticate and get JWT token |
| `GET` | `/candidates/` | List all candidates (paginated) |
| `POST` | `/candidates/` | Create a new candidate |
| `GET` | `/candidates/{id}` | Get candidate by ID |
| `POST` | `/execute/` | Execute Python code submission |
| `GET` | `/health` | Health check endpoint |

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/techieworld2/OpenClaw-RCE-Microservice.git
cd OpenClaw-RCE-Microservice

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

The API will be available at `http://localhost:8000` with Swagger UI at `http://localhost:8000/docs`.

### Using the API

1. **Register** — Create an account via `/auth/register`
2. **Login** — Use Swagger UI's "Authorize" button or POST to `/auth/login`
3. **Authenticate** — Include `Authorization: Bearer <token>` in requests
4. **Execute Code** — POST Python code to `/execute/`

## Security

The RCE engine implements multiple security layers:

- **Subprocess isolation** — Code runs in separate process
- **Timeout limits** — Prevents infinite loops
- **Memory limits** — Prevents memory exhaustion attacks
- **No filesystem access** — Restricted filesystem operations
- **No network access** — Network calls blocked

---

*Built with [OpenClaw](https://github.com/openclaw/openclaw) — an AI-powered development assistant.*