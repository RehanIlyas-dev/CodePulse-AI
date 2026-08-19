from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router
from app.core import redis as redis_module
from database import engine, Base

@asynccontextmanager
# Lifespan context manager to handle startup and shutdown events
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Initialize the Redis client
    await redis_module.init_redis()
    try:
        await redis_module.redis_client.ping()
    except Exception as e:
        print(f"WARNING: Redis not reachable - {e}")
    yield
    # Close the Redis client on shutdown
    await redis_module.close_redis()

app = FastAPI(title="CodePulse AI ", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
async def root():
    return {"status": "online", "system": "CodePulse AI Backend Engine"}