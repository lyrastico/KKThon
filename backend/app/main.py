from fastapi import FastAPI
from app.api.router import api_router

app = FastAPI(title="Apocalipssi API")

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}