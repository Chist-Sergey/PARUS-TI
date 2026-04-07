import fastapi

APP = fastapi.FastAPI()

@APP.get("/api/v1/search")
async def search(query: str) -> dict:
    return {"query": query}
