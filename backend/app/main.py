from fastapi import FastAPI

app = FastAPI(
    title="API de Korrijo",
    description="Backend del sistema de corrección automática de exámenes manuscritos",
    version="0.1.0-snapshot",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Korrijo API"}