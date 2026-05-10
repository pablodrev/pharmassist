"""FastAPI application entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from db import init_db
from api.routes import auth, reports, drugs, rag

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing database...")
    await init_db()
    print("Database initialized")
    yield
    # Shutdown (if needed)
    print("Shutting down...")


app = FastAPI(
    title="PharmAssist API",
    description="Pharmacovigilance Analysis Backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware — разрешённые origins читаются из переменной окружения.
# При использовании nginx-прокси в Docker CORS не нужен (один origin),
# но нужен для локальной разработки (Vite dev-сервер на отдельном порту).
_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(drugs.router)
app.include_router(rag.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
