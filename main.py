import fastapi
import httpx
import pytest

APP = fastapi.FastAPI()
BASE_URL = "/api/v1/search"

@APP.get(BASE_URL)
async def search(query: str) -> dict:
    return {"query": query}


@pytest.fixture
async def async_client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=APP),
        base_url="http://127.0.0.1:8000"
    ) as client:
        yield client

@pytest.mark.anyio
async def test_search_should_accept_valid_url(async_client):
    response = await async_client.get(
        BASE_URL + "?query=https://parus.tk"
    )
    assert 404 == response.status_code

@pytest.mark.anyio
async def test_search_should_accept_valid_hash(async_client):
    response = await async_client.get(
        BASE_URL + "?query=71c81c1a9e3ff6a053896e12e8a04de20edc5fc5b5cc4702d7f09951823ffd63"
    )
    assert 404 == response.status_code

@pytest.mark.anyio
async def test_search_should_accept_valid_domain(async_client):
    response = await async_client.get(
        BASE_URL + "?query=parus.de"
    )
    assert 404 == response.status_code

@pytest.mark.anyio
async def test_search_should_accept_mixed_case_query(async_client):
    response = await async_client.get(
        BASE_URL + "?query=CraZy.cOm"
    )
    assert 404 == response.status_code

@pytest.mark.anyio
async def test_search_should_find_result(async_client):
    response = await async_client.get(
        BASE_URL + "?query=parus.ti"
    )
    assert 200 == response.status_code

@pytest.mark.anyio
async def test_search_should_return_not_found(async_client):
    response = await async_client.get(
        BASE_URL + "?query=b00b5.free"
    )
    assert 404 == response.status_code

@pytest.mark.anyio
async def test_search_should_return_list(async_client):
    response = await async_client.get(
        BASE_URL + "?query=parus.ti"
    )
    assert type(response.json()) == list

@pytest.mark.anyio
async def test_search_route_should_exist(async_client):
    response = await async_client.get(
        BASE_URL + ""
    )
    assert 404 != response.status_code

@pytest.mark.anyio
async def test_search_should_reject_long_query(async_client):
    response = await async_client.get(
        BASE_URL + "?query=parus.ti" * 100
    )
    assert 422 == response.status_code

@pytest.mark.anyio
async def test_search_should_reject_invalid_ip(async_client):
    response = await async_client.get(
        BASE_URL + "?query=127.0.O.1"
    )
    assert 422 == response.status_code

@pytest.mark.anyio
async def test_search_should_reject_invalid_domain(async_client):
    response = await async_client.get(
        BASE_URL + "?query=parus..ru"
    )
    assert 422 == response.status_code

@pytest.mark.anyio
async def test_search_should_reject_invalid_hash(async_client):
    response = await async_client.get(
        BASE_URL + "?query=7Ic81c1a9e3ff6a053896e12e8a04de20edc5fc5b5cc4702d7f09951823ffd63")
    assert 422 == response.status_code

@pytest.mark.anyio
async def test_search_should_reject_invalid_url(async_client):
    response = await async_client.get(
        BASE_URL + "?query=ftq://parus.ti"
    )
    assert 422 == response.status_code

@pytest.mark.anyio
async def test_search_should_return_graph(async_client):
    response = await async_client.get(
        BASE_URL + "?query=parus.ti"
    )
    assert response.json() is not None

@pytest.mark.anyio
async def test_search_should_reject_query_with_whitespace(async_client):
    response = await async_client.get(
        BASE_URL + "?query=8.8.8. 8"
    )
    assert 422 == response.status_code

@pytest.mark.anyio
async def test_search_should_reject_null_query(async_client):
    response = await async_client.get(
        BASE_URL + "?query=",
        params="null"
    )
    assert 422 == response.status_code

@pytest.mark.anyio
async def test_search_should_reject_empty_query(async_client):
    response = await async_client.get(
        BASE_URL + ""
    )
    assert 422 == response.status_code
