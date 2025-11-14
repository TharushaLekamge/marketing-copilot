# Marketing Copilot

A web-based assistant that helps marketers craft, plan, and execute data-driven content and campaigns using GenAI. The MVP demonstrates core capabilities: contextual content generation, campaign brainstorming, analytics dashboards, and an in-product assistant powered by LLM with RAG (retrieval-augmented generation).

## Project Overview

Marketing Copilot is a full-stack application built with:
- **Backend**: FastAPI (Python) with PostgreSQL and Redis
- **Frontend**: Next.js (React/TypeScript)
- **Database**: PostgreSQL for metadata, Redis for caching
- **Authentication**: JWT-based authentication with bcrypt password hashing

## API Documentation

After deploying the application, you can access the interactive API documentation at `/docs` (Swagger UI) or `/redoc` (ReDoc). The API documentation provides:

- Complete endpoint reference with request/response schemas
- Interactive testing interface to try out endpoints
- Authentication details and examples
- All available endpoints for authentication, projects, assets, content generation, and the RAG assistant

You can also access the API docs directly from the web UI by clicking the "API Docs" link in the header of any page.

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

#### Ingest an Asset

1. On the project detail page, find the asset in the table
2. Click the **"Ingest"** button to start processing the asset
3. The button will be disabled while ingestion is in progress
4. Once ingestion completes, the asset status will update to "Ingested"
5. Ingested assets can be used for content generation and RAG queries

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
