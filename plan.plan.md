# Marketing Copilot MVP Implementation Plan

  

## Overview

  

Build a production-ready marketing copilot application demonstrating FastAPI, Next.js, PostgreSQL, RAG, and LLM integration. Follow the 6-week timeline from the specification with incremental feature delivery.

  

## Progress Summary

**Completed Steps: 9 out of 28 (32%)**

- ✅ Steps 1-9: Complete (Docker setup through Vector Store)
- ⚠️ Step 10: Partially complete (Ingestion Pipeline - core logic done, endpoint pending)
- ⏳ Steps 11-28: Pending

**Current Status:** Working on Step 10 - Ingestion Pipeline. Core ingestion logic is complete with comprehensive tests. Next step is to add the ingestion API endpoint.

  

## Implementation Guidelines

  

### Git Workflow

  

- **Branch naming**: `{type}/descriptive-name` where type is one of: `feature`, `fix`, `refactor`, `docs`

- **Incremental commits**: Each step should be a separate, testable commit (<200 lines of functional code excluding tests)

- **Review process**: Request review after completing each step before proceeding

  

### Python Standards

  

- **Naming**: snake_case for functions/vars, PascalCase for classes

- **Schemas**: Pydantic BaseModel for request/response; use `field_validator(mode='before')` for normalization

- **Datetimes**: Always return timezone-aware UTC datetimes using `datetime.now(UTC)`

- **Code organization**: Business logic separate from endpoints; heavy operations in separate modules

- **Functions**: Keep <50 lines; use list/dict comprehension over manual loops when simple

- **Type hints**: Annotate all public function signatures

- **Error handling**: Validate with Pydantic; return structured errors; avoid broad except clauses

- **Imports**: Defer heavy imports inside functions if rarely used

- **Avoid duplication**: Reuse logic wherever possible

  

### Testing Standards

  

- **Structure**: pytest tests under `tests/` mirroring source path

- **Fixtures**: Use conftest.py for shared setup; develop and reuse fixtures

- **Determinism**: No real time in tests; freeze time or pass as parameter

- **Cleanup**: Clear test setups after each test to avoid flakiness

- **Coverage**: Test both success and failure cases; reuse models/schemas in tests (no hardcoded schemas)

  

### Security

  

- Never log credentials or API keys

- Validate all externally supplied strings

- Use structured error responses (no raw exceptions)

  

### Documentation

  

- Document architectural decisions in `docs/ARCHITECTURE.md` or inline comments

- Use concise comments for non-obvious calculations

  

### Performance

  

- Use two queues for async operations: one for long-running tasks, one for quick wins

- Defer heavy imports inside functions if rarely used

  

## Incremental Implementation Steps

  

Each step should be:

  

- A separate branch following `{type}/descriptive-name` format

- Testable and functional (<200 lines of functional code excluding tests)

- Reviewed before proceeding to next step

  

### Step 1: Docker & Environment Setup ✅ COMPLETE

  

- Create docker-compose.yml with PostgreSQL and Redis

- Create .env.example with required variables

- Update .gitignore for sensitive files

  

### Step 2: Backend Foundation (FastAPI Skeleton) ✅ COMPLETE

  

- FastAPI app initialization (main.py)

- Configuration management (config.py with Pydantic Settings)

- Database connection setup (database.py with SQLAlchemy)

- Health check endpoint

  

### Step 3: Database Models & Migrations ✅ COMPLETE

  

- User model (id, email, name, role, password_hash, created_at)

- Alembic migration setup and initial migration

- Database session dependency

  

### Step 4: Authentication - Core Security ✅ COMPLETE

  

- Password hashing utilities (bcrypt)

- JWT token generation and validation

- Security dependencies module

  

### Step 5: Authentication - API Endpoints ✅ COMPLETE

  

- Signup endpoint (POST /api/auth/signup)

- Login endpoint (POST /api/auth/login)

- Get current user endpoint (GET /api/auth/me)

- Pydantic schemas for auth requests/responses

  

### Step 6: Project Model & CRUD ✅ COMPLETE

  

- Project model (id, owner_id, name, description, created_at)

- Project schemas (Pydantic)

- Create project endpoint (POST /api/projects)

- Get project endpoint (GET /api/projects/{id})

- List user projects endpoint (GET /api/projects)

  

### Step 7: Asset Model & File Upload ✅ COMPLETE

  

- Asset model (id, project_id, filename, content_type, ingested, metadata)

- File upload endpoint (POST /api/projects/{id}/assets)

- File validation and sanitization

- Storage abstraction (local storage for MVP)

  

### Step 8: Document Processing Foundation ✅ COMPLETE

  

- Document processor for text extraction (PDF, DOCX, TXT, MD)

- Text chunking utility (500 tokens with 50-token overlap)

- Error handling for unsupported formats

  

### Step 9: Embeddings & Vector Store Setup ✅ COMPLETE

  

- Embedding generation module (sentence-transformers or OpenAI)

- Vector store abstraction (FAISS + SQLite for MVP)

- Embedding storage and retrieval

  

### Step 10: Ingestion Pipeline ⚠️ PARTIALLY COMPLETE

  

- ✅ Core ingestion logic (backend/core/ingestion.py)
- ✅ Ingestion status tracking (ingesting field in Asset model)
- ✅ Comprehensive tests (tests/backend/core/test_ingestion.py)
- ❌ Ingestion endpoint (POST /api/projects/{project_id}/assets/{asset_id}/ingest) - **NEXT STEP**
- ❌ Background task orchestration (document → chunk → embed → store)

  

### Step 11: LLM Provider Abstraction

  

- ModelAdapter interface/abstract class

- OpenAI provider implementation

- Prompt template system

  

### Step 12: Content Generation - Core Logic

  

- Generation orchestration module

- Variant generation logic (short-form, long-form, CTA)

- Prompt construction with project context

  

### Step 13: Content Generation - API

  

- Generation endpoint (POST /api/generate)

- GenerationRecord model for tracking

- Response schemas with provenance metadata

  

### Step 14: Semantic Search

  

- Query embedding generation

- k-NN search implementation

- Result re-ranking and metadata filtering

  

### Step 15: RAG Pipeline

  

- RAG orchestration module (query → retrieve → prompt → LLM → response)

- Citation extraction and formatting

- Assistant endpoint (POST /api/assistant/query)

  

### Step 16: Frontend Foundation

  

- Next.js project setup with TypeScript

- Tailwind CSS configuration

- API client setup

- Type definitions matching backend schemas

  

### Step 17: Frontend Authentication

  

- Login page and form

- Signup page and form

- Token management (localStorage/cookies)

- Protected route wrapper

  

### Step 18: Frontend Project Management

  

- Project list page

- Create project form

- Project detail page

  

### Step 19: Frontend Asset Management

  

- Asset upload component (drag-and-drop)

- Asset list with ingestion status

- Ingestion trigger button

  

### Step 20: Frontend Content Generation

  

- Campaign creation form

- Generation interface

- Variant display component

- Content editor component

  

### Step 21: Frontend Assistant

  

- Chat interface component

- Message history display

- Streaming response handling

- Citation display component

  

### Step 22: Analytics Backend

  

- Metrics aggregation module

- Analytics endpoint (GET /api/projects/{id}/metrics)

- Usage statistics queries

  

### Step 23: Analytics Frontend

  

- Analytics dashboard page

- Metrics cards and charts

- CSV export functionality

  

### Step 24: Logging & Observability

  

- Structured logging setup (loguru with correlation IDs)

- Request/response logging middleware

- Health check endpoints enhancement

  

### Step 25: Testing - Backend Core

  

- Tests for authentication (success and failure cases)

- Tests for project CRUD

- Tests for file upload and validation

  

### Step 26: Testing - RAG & Generation

  

- Tests for document processing

- Tests for embedding generation

- Tests for content generation

- Tests for RAG pipeline

  

### Step 27: Security Hardening

  

- Rate limiting middleware (Redis-based)

- Input sanitization enhancements

- Security headers middleware

  

### Step 28: Deployment Configuration

  

- Production Dockerfiles

- docker-compose.prod.yml

- CI/CD pipeline (GitHub Actions)

- Deployment documentation

  

## Phase 1: Project Setup & Infrastructure (Week 0)

  

### 1.1 Docker & Development Environment

  

- **docker-compose.yml**: PostgreSQL and Redis services (already provided above)

- **.env.example**: Template for environment variables (DB credentials, LLM API keys, secrets)

- **.gitignore**: Ensure sensitive files and data directories are excluded

  

### 1.2 Backend Foundation (FastAPI)

  

- **backend/main.py**: FastAPI app initialization with CORS, middleware, logging

- **backend/config.py**: Pydantic settings for environment variables

- **backend/database.py**: SQLAlchemy engine, session management, connection pooling

- **backend/models/**: SQLAlchemy models (User, Project, Asset, GenerationRecord)

- **backend/schemas/**: Pydantic schemas for request/response validation

- **backend/alembic.ini** & **migrations/**: Database migration setup

  

### 1.3 Frontend Foundation (Next.js)

  

- **frontend/package.json**: Next.js 14+, React, TypeScript, Tailwind CSS

- **frontend/tsconfig.json**: TypeScript configuration

- **frontend/tailwind.config.js**: Styling setup

- **frontend/app/**: Next.js App Router structure (layout, auth, dashboard pages)

- **frontend/lib/api.ts**: API client with axios/fetch for backend communication

- **frontend/lib/types.ts**: TypeScript interfaces matching backend schemas

  

### 1.4 CI/CD Setup

  

- **.github/workflows/ci.yml**: GitHub Actions for linting, testing, Docker builds

- **Dockerfile.backend**: Multi-stage build for FastAPI service

- **Dockerfile.frontend**: Build for Next.js static export or container

  

## Phase 2: Authentication & Core Data Models (Week 1)

  

### 2.1 Database Schema

  

- **backend/models/user.py**: User model (id, email, name, role, password_hash, created_at)

- **backend/models/project.py**: Project model (id, owner_id, name, description, created_at)

- **backend/models/asset.py**: Asset model (id, project_id, filename, content_type, ingested, metadata)

- **backend/models/generation_record.py**: GenerationRecord model (id, project_id, user_id, prompt, response, model, tokens, created_at)

- **backend/alembic/versions/001_initial_schema.py**: Initial migration

  

### 2.2 Authentication System

  

- **backend/routers/auth.py**: Signup, login, me endpoints

- **backend/core/security.py**: Password hashing (bcrypt), JWT token generation/validation

- **backend/core/dependencies.py**: get_current_user dependency for protected routes

- **frontend/app/auth/login/page.tsx**: Login page with form

- **frontend/app/auth/signup/page.tsx**: Signup page

- **frontend/lib/auth.ts**: Token storage, API client with auth headers

  

### 2.3 File Upload & Storage

  

- **backend/routers/assets.py**: POST /api/projects/{id}/assets endpoint

- **backend/core/storage.py**: File upload handler (local storage or S3/Azure Blob abstraction)

- **backend/core/file_processing.py**: File type validation, sanitization

- **frontend/components/AssetUpload.tsx**: Drag-and-drop file upload component

  

## Phase 3: RAG Pipeline & Embeddings (Week 2)

  

### 3.1 Document Processing

  

- **backend/core/document_processor.py**: Extract text from PDF, DOCX, TXT, MD files

- **backend/core/chunking.py**: Text chunking (500 tokens with 50-token overlap)

- **backend/core/embeddings.py**: Embedding generation using sentence-transformers or OpenAI

  

### 3.2 Vector Store Setup

  

- **Option A (MVP)**: SQLite + FAISS for local development

  - **backend/core/vector_store.py**: FAISS index management, metadata storage in SQLite

- **Option B (Production)**: Milvus or managed service (Pinecone/Azure Cognitive Search)

  - Update docker-compose.yml with Milvus service if chosen

  

### 3.3 Ingestion Pipeline

  

- **backend/routers/assets.py**: POST /api/assets/{id}/ingest endpoint

- **backend/core/ingestion.py**: Orchestrate document processing → chunking → embedding → vector store

- **backend/tasks/ingestion.py**: Background task for async ingestion (Celery or asyncio)

  

### 3.4 Ingestion UI

  

- **frontend/app/projects/[id]/assets/page.tsx**: Asset list with ingest status

- **frontend/components/IngestButton.tsx**: Trigger ingestion with progress indicator

  

## Phase 4: Content Generation & LLM Integration (Week 3)

  

### 4.1 LLM Provider Abstraction

  

- **backend/core/llm_provider.py**: Abstract ModelAdapter interface

- **backend/core/providers/openai_provider.py**: OpenAI implementation

- **backend/core/providers/azure_openai_provider.py**: Azure OpenAI implementation (optional)

- **backend/config.py**: Model selection (GPT-4, GPT-3.5-turbo, Claude, etc.)

  

### 4.2 Content Generation API

  

- **backend/routers/generation.py**: POST /api/generate endpoint

- **backend/core/prompt_templates.py**: System prompts for content generation

- **backend/core/generation.py**: Orchestrate brief → prompt construction → LLM call → 3 variants

- **backend/core/variant_generator.py**: Generate short-form, long-form, CTA variants

  

### 4.3 Generation UI

  

- **frontend/app/projects/[id]/campaigns/new/page.tsx**: Campaign creation form

- **frontend/app/projects/[id]/campaigns/[campaignId]/generate/page.tsx**: Generation interface

- **frontend/components/ContentVariants.tsx**: Display 3 variants with edit/save actions

- **frontend/components/ContentEditor.tsx**: Rich text editor for editing generated content

  

## Phase 5: Contextual Assistant (RAG) (Week 4)

  

### 5.1 Semantic Search

  

- **backend/core/semantic_search.py**: Query embedding → k-NN search → re-ranking

- **backend/core/retrieval.py**: Retrieve top-N chunks with metadata and citations

  

### 5.2 RAG Orchestration

  

- **backend/routers/assistant.py**: POST /api/assistant/query endpoint

- **backend/core/rag_pipeline.py**: Query → retrieve → construct prompt with context → LLM → response with citations

- **backend/core/prompt_templates.py**: Assistant system prompt with RAG context

  

### 5.3 Assistant UI

  

- **frontend/app/projects/[id]/assistant/page.tsx**: Chat interface

- **frontend/components/AssistantChat.tsx**: Message list, input, streaming response

- **frontend/components/Citation.tsx**: Display source citations in responses

  

## Phase 6: Analytics & Observability (Week 5)

  

### 6.1 Metrics Collection

  

- **backend/routers/analytics.py**: GET /api/projects/{id}/metrics endpoint

- **backend/core/metrics.py**: Aggregate usage counts, top prompts, generation stats

- **backend/models/metrics.py**: Metrics aggregation queries (SQLAlchemy)

  

### 6.2 Analytics Dashboard

  

- **frontend/app/analytics/page.tsx**: Dashboard with charts (recharts or Chart.js)

- **frontend/components/MetricsCard.tsx**: Display individual metrics

- **frontend/components/ExportButton.tsx**: CSV export functionality

  

### 6.3 Logging & Health Checks

  

- **backend/core/logging.py**: Structured logging with correlation IDs (loguru)

- **backend/routers/health.py**: GET /health, GET /health/db endpoints

- **backend/middleware/logging.py**: Request/response logging middleware

  

## Phase 7: Polish & Deployment (Week 6)

  

### 7.1 Testing

  

- **backend/tests/**: Unit tests for core modules (pytest)

- **backend/tests/integration/**: API endpoint tests

- **frontend/tests/**: Component tests (Jest + React Testing Library)

  

### 7.2 Security Hardening

  

- **backend/core/security.py**: Input sanitization, rate limiting (Redis)

- **backend/middleware/rate_limit.py**: Rate limiting middleware

- **backend/core/file_processing.py**: Virus scanning integration (optional ClamAV)

  

### 7.3 Deployment Configuration

  

- **docker-compose.prod.yml**: Production Docker Compose with environment-specific configs

- **backend/Dockerfile**: Production-optimized FastAPI container

- **frontend/Dockerfile**: Next.js production build

- **.github/workflows/deploy.yml**: Deployment pipeline (Azure/AWS)

  

### 7.4 Documentation

  

- **README.md**: Setup instructions, architecture overview, API documentation

- **docs/API.md**: OpenAPI/Swagger documentation (auto-generated from FastAPI)

- **docs/DEPLOYMENT.md**: Deployment guide for Azure/AWS

  

## Key Files to Create

  

### Backend Structure

  

```

backend/

├── main.py

├── config.py

├── database.py

├── models/

│   ├── __init__.py

│   ├── user.py

│   ├── project.py

│   ├── asset.py

│   └── generation_record.py

├── schemas/

│   ├── __init__.py

│   ├── auth.py

│   ├── project.py

│   └── generation.py

├── routers/

│   ├── __init__.py

│   ├── auth.py

│   ├── projects.py

│   ├── assets.py

│   ├── generation.py

│   ├── assistant.py

│   └── analytics.py

├── core/

│   ├── security.py

│   ├── dependencies.py

│   ├── storage.py

│   ├── document_processor.py

│   ├── chunking.py

│   ├── embeddings.py

│   ├── vector_store.py

│   ├── ingestion.py

│   ├── llm_provider.py

│   ├── generation.py

│   ├── semantic_search.py

│   ├── rag_pipeline.py

│   └── prompt_templates.py

└── alembic/

    └── versions/

```

  

### Frontend Structure

  

```

frontend/

├── app/

│   ├── layout.tsx

│   ├── page.tsx (dashboard)

│   ├── auth/

│   │   ├── login/

│   │   └── signup/

│   ├── projects/

│   │   ├── [id]/

│   │   │   ├── assets/

│   │   │   ├── campaigns/

│   │   │   └── assistant/

│   └── analytics/

├── components/

│   ├── AssetUpload.tsx

│   ├── ContentVariants.tsx

│   ├── AssistantChat.tsx

│   └── MetricsCard.tsx

└── lib/

    ├── api.ts

    ├── auth.ts

    └── types.ts

```

  

## Implementation Order

  

1. Docker setup (PostgreSQL + Redis)

2. Backend skeleton (FastAPI app, database connection, models)

3. Authentication (signup, login, JWT)

4. Project & Asset CRUD

5. Document ingestion pipeline

6. Vector store integration

7. LLM provider abstraction

8. Content generation API

9. RAG pipeline

10. Frontend pages and components

11. Analytics dashboard

12. Testing and deployment