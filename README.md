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

- **GET** `/api/auth/me` - Get current authenticated user information
  - Response: `200 OK` with current user information
  - Returns `403 Forbidden` if user is not authenticated
  - Requires authentication

### Projects

All project endpoints require authentication via Bearer token in the Authorization header.

- **POST** `/api/projects` - Create a new project
  - Request: `{ "name": "Project Name", "description": "Project description" }`
  - Response: `201 Created` with project information
  - Requires authentication

- **GET** `/api/projects` - List all projects for the current user
  - Response: `200 OK` with list of projects
  - Returns only projects owned by the authenticated user
  - Requires authentication

- **GET** `/api/projects/{project_id}` - Get a specific project
  - Response: `200 OK` with project information
  - Returns `404 Not Found` if project doesn't exist or user doesn't have access
  - Returns `403 Forbidden` if user doesn't own the project
  - Returns `400 Bad Request` if project_id format is invalid
  - Requires authentication

- **GET** `/api/projects/{project_id}/generation-records` - List all generation records for a project
  - Response: `200 OK` with list of generation records (ordered by created_at desc)
  - Returns `404 Not Found` if project doesn't exist
  - Returns `403 Forbidden` if user doesn't own the project
  - Returns `400 Bad Request` if project_id format is invalid
  - Requires authentication
  - Each generation record includes:
    - `generation_id`: UUID of the generation record
    - `short_form`, `long_form`, `cta`: Content variants
    - `metadata`: Model information, project_id, tokens_used
    - `variants`: Array with variant statistics (character_count, word_count)

- **PATCH** `/api/projects/{project_id}` - Update a project
  - Request: `{ "name": "Updated Name", "description": "Updated description" }` (all fields optional)
  - Response: `200 OK` with updated project information
  - Returns `404 Not Found` if project doesn't exist
  - Returns `403 Forbidden` if user doesn't own the project
  - Requires authentication

- **DELETE** `/api/projects/{project_id}` - Delete a project
  - Response: `204 No Content` on success
  - Returns `404 Not Found` if project doesn't exist
  - Returns `403 Forbidden` if user doesn't own the project
  - Requires authentication

### Assets

All asset endpoints require authentication via Bearer token in the Authorization header. Assets represent files (documents, images, etc.) that belong to projects.

- **POST** `/api/projects/{project_id}/assets` - Upload a new asset (file upload)
  - Request: Multipart form data with `file` field
  - Response: `201 Created` with asset metadata (id, filename, content_type, ingested, metadata, timestamps)
  - Returns `404 Not Found` if project doesn't exist or user doesn't own it
  - Returns `422 Unprocessable Entity` if filename is missing or empty, file type not allowed, or file size exceeds 100MB
  - Defaults to `application/octet-stream` if content_type is not provided
  - Requires authentication
  - Files are stored in local storage (configurable via `STORAGE_PATH` environment variable)

- **GET** `/api/projects/{project_id}/assets` - List all assets for a project
  - Response: `200 OK` with list of assets
  - Returns `404 Not Found` if project doesn't exist or user doesn't own it
  - Requires authentication

- **GET** `/api/projects/{project_id}/assets/{asset_id}` - Get a specific asset
  - Response: `200 OK` with asset information
  - Returns `404 Not Found` if asset or project doesn't exist or user doesn't own the project
  - Requires authentication

- **PATCH** `/api/projects/{project_id}/assets/{asset_id}` - Update an asset
  - Request: `{ "filename": "new-name.pdf", "content_type": "application/pdf", "ingested": true, "metadata": { "key": "value" } }` (all fields optional)
  - Response: `200 OK` with updated asset information
  - Returns `404 Not Found` if asset or project doesn't exist or user doesn't own the project
  - Requires authentication

- **DELETE** `/api/projects/{project_id}/assets/{asset_id}` - Delete an asset
  - Response: `204 No Content` on success
  - Returns `404 Not Found` if asset or project doesn't exist or user doesn't own the project
  - Requires authentication
  - Deletes both the database record and the file from storage

- **GET** `/api/projects/{project_id}/assets/{asset_id}/download` - Download an asset file
  - Response: `200 OK` with file content as download
  - Returns `404 Not Found` if asset, project, or file doesn't exist or user doesn't own the project
  - Requires authentication

- **POST** `/api/projects/{project_id}/assets/{asset_id}/ingest` - Start ingestion of an asset
  - Response: `202 Accepted` with `{ "message": "Ingestion started", "asset_id": "...", "ingesting": true }`
  - Returns `404 Not Found` if asset or project doesn't exist or user doesn't own the project
  - Returns `409 Conflict` if asset is already being ingested
  - Requires authentication
  - Ingestion runs asynchronously in the background and includes:
    1. Extracting text from the file (PDF, DOCX, TXT, MD)
    2. Chunking the text into smaller pieces
    3. Generating embeddings for each chunk
    4. Storing vectors in the vector store
  - The `ingesting` field on the asset tracks ingestion status
  - Check asset status via GET endpoint to see when ingestion completes

### Content Generation

All content generation endpoints require authentication via Bearer token in the Authorization header.

- **POST** `/api/generate` - Generate content variants for a marketing campaign (asynchronous)
  - Request: `{ "project_id": "uuid", "brief": "Campaign brief", "brand_tone": "Professional and friendly", "audience": "Young professionals", "objective": "Increase brand awareness", "channels": ["social", "email"] }`
    - `project_id` (required): UUID of the project
    - `brief` (required): Campaign brief or description (min 1 character)
    - `brand_tone` (optional): Brand tone and style guidelines
    - `audience` (optional): Target audience description
    - `objective` (optional): Campaign objective
    - `channels` (optional): List of target channels (e.g., social, email)
  - Response: `202 Accepted` with generation acceptance confirmation:
    ```json
    {
      "message": "Generation started",
      "generation_id": "uuid",
      "status": "pending"
    }
    ```
  - Returns `404 Not Found` if project doesn't exist
  - Returns `403 Forbidden` if user doesn't own the project
  - Requires authentication
  - **Note**: This endpoint accepts the generation request and processes it asynchronously in the background. Use the `generation_id` to poll the GET endpoint below to check status and retrieve results.
  - Uses project assets (if ingested) for context during generation
  - Creates a generation record in the database with `pending` status
  - Generation status transitions: `pending` → `processing` → `completed` or `failed`

- **GET** `/api/generate/{generation_id}` - Get a single generation record by ID
  - Response: `200 OK` with generation record (content varies by status):
    
    **When status is `pending` or `processing`:**
    ```json
    {
      "generation_id": "uuid",
      "short_form": "",
      "long_form": "",
      "cta": "",
      "metadata": {
        "model": "gpt-4o",
        "model_info": {"base_url": ""},
        "project_id": "uuid",
        "tokens_used": null,
        "generation_time": null
      },
      "variants": [...]
    }
    ```
    
    **When status is `completed`:**
    ```json
    {
      "generation_id": "uuid",
      "short_form": "Short-form content variant (max 280 chars)",
      "long_form": "Long-form content variant (150-300 words)",
      "cta": "CTA-focused content variant",
      "metadata": {
        "model": "gpt-4o",
        "model_info": {"base_url": ""},
        "project_id": "uuid",
        "tokens_used": 300,
        "generation_time": null
      },
      "variants": [
        {
          "variant_type": "short_form",
          "content": "...",
          "character_count": 150,
          "word_count": 25
        },
        ...
      ]
    }
    ```
  - Returns `404 Not Found` if generation record or project doesn't exist
  - Returns `403 Forbidden` if user doesn't own the project
  - Returns `422 Unprocessable Entity` if generation_id format is invalid
  - Returns `500 Internal Server Error` if generation status is `failed` (includes error message)
  - Requires authentication
  - **Usage**: Poll this endpoint after creating a generation request to check status and retrieve results when `status` is `completed`

- **PATCH** `/api/generate/{generation_id}` - Update generated content variants
  - Request: `{ "short_form": "Updated short form", "long_form": "Updated long form content", "cta": "Updated CTA" }`
    - All fields are optional - only provided fields will be updated
    - Fields not provided will preserve existing values
  - Response: `200 OK` with updated content:
    ```json
    {
      "message": "Content updated successfully",
      "updated": {
        "generation_id": "uuid",
        "short_form": "Updated short form",
        "long_form": "Updated long form content",
        "cta": "Updated CTA",
        "metadata": {
          "model": "gpt-3.5-turbo-instruct",
          "model_info": {"base_url": ""},
          "project_id": "uuid",
          "tokens_used": 300,
          "generation_time": null
        },
        "variants": [...]
      }
    }
    ```
  - Returns `404 Not Found` if generation record or project doesn't exist
  - Returns `403 Forbidden` if user doesn't own the project
  - Returns `422 Unprocessable Entity` if generation_id format is invalid
  - Requires authentication
  - Updates the generation record in the database
  - Preserves original metadata (model, tokens, etc.)

### Assistant (RAG)

All assistant endpoints require authentication via Bearer token in the Authorization header.

- **POST** `/api/assistant/query` - Query the assistant with RAG (Retrieval-Augmented Generation)
  - Request: `{ "project_id": "uuid", "question": "What are marketing strategies?", "top_k": 5, "include_citations": true }`
    - `project_id` (required): UUID of the project to search within
    - `question` (required): User's question (min 1 character)
    - `top_k` (optional): Number of relevant chunks to retrieve (default: 5, min: 1, max: 20)
    - `include_citations` (optional): Whether to include citations in response (default: true)
  - Response: `200 OK` with assistant answer and citations:
    ```json
    {
      "answer": "Based on the provided context, marketing strategies involve careful planning and execution...",
      "citations": [
        {
          "index": 1,
          "text": "This is a document about marketing strategies and campaign planning.",
          "asset_id": "uuid",
          "chunk_index": 0,
          "score": 0.85,
          "metadata": {
            "source": "marketing_guide.pdf"
          }
        }
      ],
      "metadata": {
        "model": "gpt-4o",
        "provider": "openai",
        "project_id": "uuid",
        "chunks_retrieved": 5,
        "has_context": true
      }
    }
    ```
  - Returns `404 Not Found` if project doesn't exist
  - Returns `403 Forbidden` if user doesn't own the project
  - Returns `500 Internal Server Error` if RAG pipeline fails
  - Requires authentication
  - **How it works**:
    1. Uses semantic search to retrieve relevant document chunks from the project's ingested assets
    2. Builds context from retrieved chunks with citation information
    3. Constructs a prompt with the context and user's question
    4. Generates an answer using an LLM (via Semantic Kernel)
    5. Returns the answer with citations from source documents
  - **Citations**: Each citation includes:
    - `index`: Citation number (1-based)
    - `text`: Excerpt from the source document
    - `asset_id`: ID of the source asset
    - `chunk_index`: Chunk index within the asset
    - `score`: Similarity score (0.0-1.0, higher is more relevant)
    - `metadata`: Additional metadata (e.g., source filename)
  - **Note**: Only ingested assets are searchable. Use the ingestion endpoint (`POST /api/projects/{project_id}/assets/{asset_id}/ingest`) to process assets before querying.

### Health Check

- **GET** `/health` - Application health check
  - Response: `200 OK` with service status

### API Documentation

- **GET** `/docs` - Interactive API documentation (Swagger UI)
- **GET** `/redoc` - Alternative API documentation (ReDoc)

## Using the Frontend

The Marketing Copilot frontend provides a web-based interface for managing projects and assets. Access the frontend at `http://localhost:3000` after starting the development server.

### Getting Started

1. **Start the Backend**: Ensure the backend is running on `http://localhost:8000`
2. **Start the Frontend**: Navigate to the frontend directory and run `npm run dev`
3. **Access the Application**: Open `http://localhost:3000` in your browser

### Authentication

#### Sign Up
1. Navigate to the signup page (`/signup`)
2. Enter your email, password (minimum 8 characters), and name
3. Click "Sign Up" to create your account
4. You'll be automatically logged in after successful signup

#### Login
1. Navigate to the login page (`/login`)
2. Enter your email and password
3. Click "Login" to authenticate
4. You'll be redirected to your projects dashboard

#### Logout
- Click the "Logout" button in the header to sign out
- You'll be redirected to the login page

### Managing Projects

#### View All Projects
- After logging in, you'll see the **Projects** page listing all your projects
- Each project card displays:
  - Project name and description
  - Creation and update dates
  - Actions: View, Edit, Delete

#### Create a New Project
1. Click the **"New Project"** button on the projects page
2. Enter a project name (required)
3. Optionally add a description
4. Click **"Create Project"** to save
5. You'll be redirected to the project detail page

#### View Project Details
1. Click on a project card or the **"View"** button
2. The project detail page shows:
   - Project name and description
   - Creation and update timestamps
   - All assets associated with the project
   - Edit and delete options

#### Edit a Project
1. From the project detail page, click **"Edit Project"**
2. Update the project name and/or description
3. Click **"Save Changes"** to update
4. Or click **"Cancel"** to discard changes

#### Delete a Project
1. From the projects list page, click **"Delete"** on a project card
2. Confirm the deletion in the dialog
3. The project and all its assets will be permanently deleted

### Managing Assets

#### Upload an Asset
1. Navigate to a project detail page
2. Click the **"Upload File"** button
3. Select a file from your computer
4. Supported file types include:
   - Documents: PDF, DOCX, TXT, MD
   - Images: JPG, PNG, GIF, etc.
   - Other common file types
5. The file will be uploaded and appear in the assets table
6. Maximum file size: 100MB

#### View Assets
- On the project detail page, all assets are displayed in a table showing:
  - File icon and name
  - Content type (MIME type)
  - Ingestion status (Ingested/Pending)
  - Upload date
  - Actions (Download, Delete)

#### Download an Asset
1. On the project detail page, find the asset in the table
2. Click the **"Download"** button
3. The file will be downloaded to your computer

#### Delete an Asset
1. On the project detail page, find the asset in the table
2. Click the **"Delete"** button
3. Confirm the deletion in the dialog
4. The asset and its file will be permanently deleted

### Asset Ingestion Status

- **Pending**: Asset has been uploaded but not yet ingested
- **Ingested**: Asset has been processed and is ready for use in content generation and RAG queries

> **Note**: The ingestion endpoint is available via the API (`POST /api/projects/{project_id}/assets/{asset_id}/ingest`). Frontend integration for triggering ingestion will be available in a future update.

### Navigation

- **Home**: Redirects to projects page if logged in, or login page if not
- **Projects**: View all your projects
- **Project Detail**: View and manage a specific project and its assets
- **Header**: Shows your email and logout button

### Error Handling

The frontend displays error messages for:
- Authentication failures
- Network errors
- Validation errors (e.g., missing required fields)
- File upload errors (e.g., file too large, invalid type)

Error messages appear as red alert boxes at the top of the relevant page.

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

1. **Create uploads directory** (required for file storage):
   ```bash
   # From project root
   mkdir -p uploads
   ```
   
   This directory will be mounted into the Docker container to persist uploaded files. The directory will be created automatically if it doesn't exist, but creating it beforehand ensures proper permissions.

2. **Start all services**:
   ```bash
   docker-compose up -d
   ```

3. **Access services**:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

4. **View logs**:
   ```bash
   docker-compose logs -f
   ```

5. **Stop services**:
   ```bash
   docker-compose down
   ```

## Project Structure

```
marketing-copilot/
├── backend/              # FastAPI backend
│   ├── alembic/         # Database migrations
│   ├── core/            # Core utilities
│   │   ├── generation.py      # Content generation orchestration
│   │   ├── rag_pipeline.py    # RAG pipeline orchestration
│   │   ├── semantic_search.py # Semantic search orchestration
│   │   ├── ingestion.py       # Document ingestion pipeline
│   │   ├── vector_store.py    # Vector store abstraction
│   │   ├── embeddings.py     # Embedding generation
│   │   └── sk_plugins/        # Semantic Kernel plugins
│   ├── models/          # SQLAlchemy models
│   ├── routers/         # API routes
│   │   ├── assistant.py # RAG assistant endpoint
│   │   ├── generation.py # Content generation endpoints
│   │   └── ...
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
- **AI/ML**: 
  - Semantic Kernel (LLM orchestration)
  - OpenAI API (GPT-4o)
  - Sentence Transformers (embeddings)
  - FAISS (vector search)
- **Vector Store**: FAISS + SQLite for document embeddings
- **RAG Pipeline**: Semantic search + LLM generation with citations
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
