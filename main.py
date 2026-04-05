import fastapi

app = fastapi.FastAPI()

@app.get("/api/v1/search")
async def search(query: str) -> dict:
    return {"query": query}
