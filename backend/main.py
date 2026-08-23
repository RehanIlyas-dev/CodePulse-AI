from contextlib import asynccontextmanager
from fastapi import FastAPI
import sentry_sdk
import os
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from app.api.endpoints import router as api_router
from app.api.auth import router as auth_router
from app.core import redis as redis_module
from app.core.exceptions import register_exception_handlers
from database import engine, Base
import app.models.user  

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
 
# --> SENTRY INITIALIZATION
SENTRY_DSN = os.getenv("SENTRY_DSN")   
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            # Integrate with FastAPI and Starlette for error tracking
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        traces_sample_rate=1.0,  # Traces sample rate for performance monitoring
        profiles_sample_rate=1.0,
        environment=os.getenv("ENVIRONMENT", "development"),
    )

app = FastAPI(title="CodePulse AI ", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:5174,http://localhost:5173"
    ).split(",") if o.strip()],
    allow_credentials=True,  # required for the httpOnly refresh cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(auth_router, prefix="/api/v1")

register_exception_handlers(app)

@app.get("/")
async def root():
    return {"status": "online", "system": "CodePulse AI Backend Engine"}