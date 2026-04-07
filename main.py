import fastapi
import httpx
import pytest

APP = fastapi.FastAPI()

@APP.get("/api/v1/search")
async def search(query: str) -> dict:
    return {"query": query}


@pytest.fixture
async def async_client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=APP),
        base_url="http://127.0.0.1:8000"
    ) as client:
        yield client
