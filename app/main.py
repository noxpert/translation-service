import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.init_db import init_db
from app.routers import lookup, phrases, translate, words

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Hungarian Language Service...")
    init_db()
    yield
    logger.info("Shutting down Hungarian Language Service.")


app = FastAPI(
    title="Hungarian Language Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(lookup.router)
app.include_router(translate.router)
app.include_router(words.router)
app.include_router(phrases.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "hungarian-language-service"}
