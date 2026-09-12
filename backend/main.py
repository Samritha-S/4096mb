from fastapi import FastAPI

from backend.routers.ask import router as ask_router

app = FastAPI(title="HackbattleVIT Backend")
app.include_router(ask_router)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
