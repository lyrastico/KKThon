import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="1.0.0")
app.include_router(api_router)


def _cors_origins() -> list[str]:
    if not settings.cors_origins:
        return ["*"]
    raw = settings.cors_origins.strip()
    if raw.startswith("["):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return [o.strip() for o in raw.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
