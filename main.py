import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from routers.vlr_router import router as vlr_router
from routers.v2_router import router as v2_router
from utils.http_client import close_http_client
from utils.constants import API_TITLE, API_DESCRIPTION, API_PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.environ.get("API_KEY", "")
OPEN_PATHS = {"/", "/version", "/openapi.json", "/health"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting vlrggapi")
    yield
    logger.info("Shutting down — closing HTTP client")
    await close_http_client()


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    docs_url="/",
    redoc_url=None,
    lifespan=lifespan,
)


@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if API_KEY and request.url.path not in OPEN_PATHS:
        provided = request.headers.get("x-api-key", "")
        if provided != API_KEY:
            return JSONResponse({"detail": "Invalid or missing API key"}, status_code=403)
    return await call_next(request)


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(vlr_router)
app.include_router(v2_router)


@app.get("/version", tags=["Meta"])
def version():
    return {"version": "2.0.0", "default_api": "v2"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=API_PORT)
