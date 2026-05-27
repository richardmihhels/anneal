from fastapi import FastAPI

from core.routers.ingest import router as ingest_router

app = FastAPI(title="Anneal API")
app.include_router(ingest_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
