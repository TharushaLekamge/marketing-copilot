# Marketing Copilot

A web-based assistant that helps marketers craft, plan, and execute data-driven content and campaigns using GenAI. The MVP demonstrates core capabilities: contextual content generation, campaign brainstorming, analytics dashboards, and an in-product assistant powered by LLM with RAG (retrieval-augmented generation).

## Project Overview

Marketing Copilot is a full-stack application built with:
- **Backend**: FastAPI (Python) with PostgreSQL and Redis
- **Frontend**: Next.js (React/TypeScript)
- **Database**: PostgreSQL for metadata, Redis for caching
- **Authentication**: JWT-based authentication with bcrypt password hashing

## Implemented Endpoints

### Authentication

- **POST** `/api/auth/signup` - Create a new user account
  - Request: `{ "email": "user@example.com", "password": "password123", "name": "User Name" }`
  - Response: `201 Created` with user information
  - Validates email format, password length (min 8 chars), and checks for duplicate emails

- **POST** `/api/auth/login` - Authenticate user and get access token
  - Request: `{ "email": "user@example.com", "password": "password123" }`
  - Response: `200 OK` with JWT access token and user information
  - Returns `401 Unauthorized` for invalid credentials

### Health Check

- **GET** `/health` - Application health check
  - Response: `200 OK` with service status

### API Documentation

- **GET** `/docs` - Interactive API documentation (Swagger UI)
- **GET** `/redoc` - Alternative API documentation (ReDoc)

## Development Environment Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ (or Docker)
- Redis 7+ (or Docker)
- Docker and Docker Compose (optional, for containerized setup)

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   ```

3. **Activate virtual environment**:
   ```bash
   # Windows
   .venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Create environment file**:
   ```bash
   # Create backend/.env file with:
   DATABASE_URL=postgresql://marketing_copilot:marketing_copilot_dev@localhost:5432/marketing_copilot_db
   SECRET_KEY=your-secret-key-here
   APP_ENV=development
   APP_NAME=Marketing Copilot
   ```

6. **Start PostgreSQL and Redis** (using Docker Compose):
   ```bash
   # From project root
   docker-compose up -d postgres redis
   ```

7. **Run database migrations**:
   ```bash
   # From project root
   alembic -c backend/alembic.ini upgrade head
   ```

8. **Start the backend server**:
   ```bash
   # From project root
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Or run directly:
   ```bash
   cd backend
   python main.py
   ```

   Backend will be available at: http://localhost:8000
   API docs at: http://localhost:8000/docs

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

   Frontend will be available at: http://localhost:3000

### Running Tests

1. **Install test dependencies**:
   ```bash
   cd backend
   pip install -r requirements-test.txt
   ```

2. **Run tests**:
   ```bash
   # From project root
   pytest tests/backend/ -v
   ```

3. **Run linting**:
   ```bash
   # From project root
   ruff check backend/ tests/backend/
   ruff format --check backend/ tests/backend/
   ```

### Docker Setup (Optional)

1. **Start all services**:
   ```bash
   docker-compose up -d
   ```

2. **Access services**:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

3. **View logs**:
   ```bash
   docker-compose logs -f
   ```

4. **Stop services**:
   ```bash
   docker-compose down
   ```

## Project Structure

```
marketing-copilot/
├── backend/              # FastAPI backend
│   ├── alembic/         # Database migrations
│   ├── core/            # Core utilities (security, etc.)
│   ├── models/          # SQLAlchemy models
│   ├── routers/         # API routes
│   ├── schemas/         # Pydantic schemas
│   └── main.py          # Application entry point
├── frontend/            # Next.js frontend
├── tests/               # Test suite
│   └── backend/        # Backend tests
└── docker-compose.yml   # Docker services configuration
```

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, Pydantic, bcrypt, python-jose
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Testing**: pytest, TestClient
- **Linting**: Ruff

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes following the project guidelines
3. Write tests for new features
4. Run tests and linting: `pytest` and `ruff check`
5. Commit your changes: `git commit -m "feat: add your feature"`
6. Push to the branch: `git push origin feature/your-feature-name`
7. Create a Pull Request

## License

This project is part of a portfolio demonstration.
