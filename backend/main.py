from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import uvicorn

from backend.routers import assistant, assets, auth, generation, projects

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4000",
        "http://127.0.0.1:4000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(assets.router)
app.include_router(generation.router)
app.include_router(assistant.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "marketing_copilot_backend"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        loop="asyncio",  # Explicitly use asyncio instead of auto (which tries uvloop)
    )
