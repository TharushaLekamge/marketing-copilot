from fastapi import FastAPI

import uvicorn

from backend.routers import auth

app = FastAPI()

# Include routers
app.include_router(auth.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "marketing_copilot_backend"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
