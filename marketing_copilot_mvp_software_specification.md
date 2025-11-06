# Marketing Copilot — MVP Software Specification

## 1. Executive Summary
A Marketing Copilot is a web-based assistant that helps marketers craft, plan, and execute data-driven content and campaigns using GenAI. The MVP demonstrates core capabilities: contextual content generation, campaign brainstorming and templates, simple analytics dashboards, and an in-product assistant (contextual help) powered by an LLM with RAG (retrieval-augmented generation). The project showcases Full Stack engineering skills (Next.js/React frontend, Python backend with FastAPI), integration with Semantic Kernel-style orchestration, and cloud deployment (Azure or AWS).

### Primary objectives
- Deliver a functioning, secure, and demo-ready product that shows ability to design and implement GenAI features in a production-like stack.
- Validate user flows for content generation, campaign scaffold, and contextual assistance.
- Provide metrics and logging to evaluate model usefulness and product UX.


## 2. Scope (what's in MVP vs out)
**In MVP**
- User authentication (email + OAuth optional)
- Project and Campaign creation UI
- Content generation flows (brief -> multiple outputs; editing; regenerate)
- Contextual assistant: answer questions about user's project using RAG over user's uploaded assets and public templates
- RAG pipeline: document ingestion, embedding store, semantic search
- Backend APIs (FastAPI) and a minimal orchestration layer for invoking LLMs and embeddings
- Simple analytics dashboard (usage counts, top prompts, basic CTR-like metrics)
- Persistent storage for users, projects, assets; small ETL for uploaded docs
- CI/CD pipeline and deployment scripts for a demo deployment on Azure/AWS

**Out of MVP / next-phase**
- Multi-channel publishing (social APIs), advanced campaign automation, deep A/B testing UI, advanced billing/subscriptions, enterprise SSO, advanced fine-tuning of models, offline-first mobile app.


## 3. Users & Personas
- **Marketing Associate (Primary)** — creates briefs, asks assistant to draft posts, edits outputs.
- **Marketing Manager** — reviews campaigns, exports content, monitors analytics.
- **Developer / Demo Owner** — sets up the app, monitors logs, adjusts model/embeddings parameters.


## 4. High-level User Journeys
1. Sign up / Sign in
2. Create a Project -> Add Brand Assets (logo, tone guide, marketing copy, CSV of products)
3. Create Campaign -> Provide short brief (audience, objective, channels)
4. Generate content -> pick an output, edit, save to project
5. Ask contextual assistant "How should we position Product X for audience Y?" -> gets answer grounded on project's assets
6. View simple analytics for generated content (views, saves, feedback)


## 5. Features & User Stories (priority)

### 5.1 Authentication & Authorization
- As a user, I want to sign up/sign in so that my projects are private.
- Acceptance: Email sign-up works, session tokens valid for X hours, basic role check.

### 5.2 Project & Asset Management
- As a user, I can create projects and upload brand assets (text docs, images) so the assistant can ground responses.
- Acceptance: Stored assets accessible to RAG; accepted formats: .md, .txt, .pdf, .docx, .jpg, .png (for images we store as references).

### 5.3 Content Generation Flow
- As a user, I provide a brief and receive 3 candidate outputs (short form, long form, CTA variants).
- Acceptance: Backend returns 3 variations, with provenance metadata (tokens used, model id, embeddings used).

### 5.4 Contextual Assistant (RAG)
- As a user, I can ask questions about my project and get answers grounded in uploaded assets.
- Acceptance: Answers include citations to asset names and a confidence score; if no grounding available, assistant should say so.

### 5.5 Analytics & Telemetry
- As a user, I can view usage metrics: number of generations, most popular prompts, top performing templates.
- Acceptance: Dashboard lists metrics for the past 30 days and exports CSV.

### 5.6 Admin / Observability
- As a developer, I can view logs, model usage, and errors.
- Acceptance: Error logs stream to central logging (e.g., Azure Monitor / AWS CloudWatch). Basic health-check endpoints exist.


## 6. Non-functional Requirements
- **Performance**: 95% of content generation requests complete in under 6s (depends on model); search queries < 250ms for small embedding DB.
- **Scalability**: MVP supports up to 1,000 monthly active users; design should be horizontally scalable.
- **Security**: Data encrypted at rest; HTTPS everywhere; sanitized user uploads; role-based access control.
- **Privacy**: Option to exclude assets from RAG; retention policy of 90 days for demo data.
- **Reliability**: 99% uptime for demo environment; retry logic for model API calls.


## 7. Technical Architecture

### 7.1 Overview
- **Frontend**: Next.js + React (TypeScript). Pages: Auth, Dashboard, Project, Campaign, Composer, Assistant chat, Analytics.
- **Backend API**: Python (FastAPI) with Pydantic models. Routes for auth, user/project CRUD, content generation, embeddings, search, metrics.
- **Vector DB / Embeddings**: Use a managed vector store (Azure Cognitive Search/RedisVectorDB/Pinecone/Weaviate). For MVP, we can start with open-source Milvus or a small SQLite + Faiss local option.
- **LLM Provider**: Use a hosted API (OpenAI / Azure OpenAI / Anthropic / Mistral). Abstracted through a ModelAdapter to allow swaps.
- **Orchestration**: Lightweight orchestration in backend to run RAG (embed -> semantic search -> construct prompt -> call LLM).
- **Storage**: Blob storage for assets (S3 or Azure Blob), relational DB for metadata (Postgres), Redis for caching and rate-limiting.
- **CI/CD**: GitHub Actions -> deploy to Azure App Service / AWS Elastic Beanstalk or containers on ECS/EKS/Azure Container Instances.


### 7.2 Component Diagram (text)
- User (browser) -> Next.js frontend -> Backend (FastAPI)
- FastAPI -> Postgres (metadata)
- FastAPI -> Blob Storage (assets)
- FastAPI -> Vector DB (embeddings)
- FastAPI -> LLM Provider (model calls)
- Telemetry -> Cloud logging + Prometheus/Grafana or cloud-native


## 8. Data Models (sample)

### User
```json
{
  "id": "uuid",
  "email": "string",
  "name": "string",
  "role": "user|admin",
  "created_at": "datetime"
}
```

### Project
```json
{
  "id":"uuid",
  "owner_id":"uuid",
  "name":"string",
  "description":"string",
  "assets":["asset_id"]
}
```

### Asset
```json
{
  "id":"uuid",
  "project_id":"uuid",
  "filename":"string",
  "content_type":"text|pdf|image",
  "ingested": true/false,
  "metadata": {}
}
```

### GenerationRecord
```json
{
  "id":"uuid",
  "project_id":"uuid",
  "user_id":"uuid",
  "prompt":"string",
  "response":"string",
  "model":"string",
  "tokens": { "prompt": 120, "completion": 320 },
  "created_at":"datetime"
}
```


## 9. API Specification (selected endpoints)

### Auth
- `POST /api/auth/signup` — body: {email, password, name}
- `POST /api/auth/login` — body: {email, password}
- `GET /api/auth/me` — returns user profile

### Projects & Assets
- `POST /api/projects` — create project
- `GET /api/projects/{id}`
- `POST /api/projects/{id}/assets` — upload asset (multipart/form-data)
- `POST /api/assets/{id}/ingest` — trigger ingestion & embedding

### Generation & Assistant
- `POST /api/generate` — body: {project_id, brief, tone, length, variants}
  - returns: array of variants + provenance
- `POST /api/assistant/query` — body: {project_id, question}
  - runs RAG: top-k retrieval then LLM answer

### Analytics
- `GET /api/projects/{id}/metrics` — returns usage metrics


## 10. RAG / Semantic Search Pipeline
1. Ingest document: extract text (pdf/docx/html), normalize, chunk (e.g., 500 tokens with 50-token overlap).
2. Create embeddings using provider.
3. Store embeddings in vector DB with metadata (project_id, chunk_id, source filename, offset).
4. Query flow: embed user query -> k-NN search -> re-rank by metadata & lexical similarity (if needed) -> build prompt with top-N chunks (include citations) -> call LLM.
5. Cache frequent queries and short-term result TTL.


## 11. Model & Prompting Design
- Keep a prompt template for assistant with system instructions: brand tone, goal, allowed sources.
- Limit retrieval context size (e.g., 3-5 chunks) to keep prompt concise.
- Return answer + source snippets and source IDs.
- Store prompt & used context for offline analysis.


## 12. Experimentation & Productization
- Add an `/experiments` module to support model A/B testing: variant toggles per project, collect interleaved metrics (engagement, user feedback), and compute lift.
- Provide a simple UI to enable/disable experimental models per project.


## 13. Security & Compliance
- OAuth 2.0 for third-party logins. JWT for sessions with short expiry and refresh tokens.
- Sanitize user file uploads. Virus scan optional (ClamAV) for public demos.
- Access controls: user can't access other users' projects.
- Audit logs for admin actions.


## 14. Deployment & Infra (MVP recommendation)
**Option A — Azure-first (recommended if aligning with Sitecore/Azure ecosystem)**
- Web App (Next.js) — Vercel or Azure Static Web Apps
- API — Azure App Service or Container App running FastAPI
- Blob Storage — Azure Blob Storage
- DB — Azure Database for PostgreSQL
- Vector search — Azure Cognitive Search (with vector similarity) or managed Pinecone
- Logging & Monitoring — Azure Application Insights

**Option B — AWS**
- Web App — Vercel/CloudFront + S3 (static) or Amplify
- API — AWS Fargate / ECS / Lambda (if Serverless)
- Blob Storage — S3
- DB — RDS Postgres
- Vector DB — Pinecone or Faiss on EC2, or OpenSearch k-NN
- Logging — CloudWatch

**CI/CD**: GitHub Actions building Docker images, unit tests, deploy to chosen environment.


## 15. Observability, Metrics & KPIs
- **Product KPIs**: number of generations per user, retention (7/30-day), average session length, save/export rate.
- **Model KPIs**: tokens consumed, median latency, error rate, user feedback score on responses.
- **Infra KPIs**: CPU/memory utilization, request latency percentiles, uptime.

Logging: structured logs (JSON), use correlation IDs for requests.


## 16. Acceptance Criteria for MVP
- End-to-end generation flow: brief -> generate 3 variants -> save to project.
- RAG assistant: ask question -> returns grounded answer with citation for at least 80% of queries that have relevant assets.
- Secure authentication and per-user data isolation.
- Basic analytics dashboard working and exportable to CSV.
- CI/CD deploys demo to cloud and health-check endpoints pass.


## 17. Timeline / Milestones (6-week aggressive plan)
- **Week 0 — Project setup**: repo, CI, dev infra, skeleton Next.js + FastAPI.
- **Week 1 — Auth + Projects + Storage**: Postgres schema, file uploads.
- **Week 2 — Ingestion & embeddings**: doc parsing, chunking, vector DB, basic ingest UI.
- **Week 3 — Generation API + Frontend composer**: integrate LLM provider, produce initial generation flows.
- **Week 4 — Assistant (RAG) UI**: chat UI with retrieval grounding, citations.
- **Week 5 — Analytics + Observability**: telemetry, dashboard, logging.
- **Week 6 — Polish & Deploy**: tests, security checks, demo deploy, README + runbook.


## 18. Risks & Mitigations
- **Model cost overruns**: Use token limits, sampling settings, and caching. Provide budget alerts.
- **Bad hallucinations**: Use retrieval grounding and conservative system prompts. Surface provenance. Include an explicit "I don't know" fallback.
- **Data leakage**: encrypt at rest and in transit; strict access control; option to opt-out from vector indexing.
- **Regulatory or IP concerns**: warn users about copyright when uploading third-party content.


## 19. Open Questions (to resolve before development)
- Which LLM provider and embedding provider will we use for the demo (cost/latency trade-offs)?
- Vector DB choice: managed (Pinecone/Azure Cognitive Search) vs self-hosted (Faiss/Milvus)?
- Will we permit public sign-up or restrict to invite-only for demo?
- Branding / Tone templates to ship with the demo.


## 20. Appendix — Example prompt template (simplified)
```
System: You are a helpful marketing copy assistant. Use the brand assets and tone provided. Cite sources when using uploaded documents.
User: <user brief>
Context: <top retrieved doc snippets with metadata>
Instruction: Produce 3 variants: short social post (<= 280 chars), long-form post (~150-300 words), CTA + subject line.
```


---
*End of specification.*

