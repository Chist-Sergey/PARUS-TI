import pytest
import httpx
import re
import fastapi
import contextlib
import arangoasync
import arangoasync.exceptions
import arangoasync.auth
import asgi_lifespan


DATABASE_CONNECTIONS = {}
@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    client = arangoasync.ArangoClient(
        hosts=["http://127.0.0.1:8529"]
    )

    system_db = await client.db(
        "_system",
        auth=arangoasync.auth.Auth(
            username="root",
            password="root"
        )
    )
    if not await system_db.has_database("parus"):
        await system_db.create_database("parus")

    db = await client.db(
        "parus",
        auth=arangoasync.auth.Auth(
            username="root", password="root"
        )
    )

    try:
        await db.create_collection("indicators", col_type="document")
    except arangoasync.exceptions.CollectionCreateError:
        pass

    try:
        await db.create_collection("relations", col_type="edge")
    except arangoasync.exceptions.CollectionCreateError:
        pass

    try:
        await db.collection("indicators").add_index(
            type="persistent",
            fields=["type", "value"],
            options={"unique": True}
        )
    except arangoasync.exceptions.IndexCreateError:
        pass

    await db.aql.execute("""
LET indicators = [
{ type: "ip", value: "192.168.1.1" },
{ type: "domain", value: "example.com" },
{ type: "url", value: "https://example.com/page" },
{ type: "hash", value: "a1b2c3d4e5f6" }
]

LET docs = (
FOR i IN indicators
    UPSERT { type: i.type, value: i.value }
    INSERT i
    UPDATE {} IN indicators
    RETURN NEW
)

LET edges = [
{ from: docs[0]._id, to: docs[1]._id, type: "resolves" },
{ from: docs[1]._id, to: docs[2]._id, type: "hosted_on" },
{ from: docs[2]._id, to: docs[3]._id, type: "downloaded_from" }
]

FOR e IN edges
UPSERT { _from: e.from, _to: e.to, type: e.type }
    INSERT {
    _from: e.from,
    _to: e.to,
    type: e.type
    }
    UPDATE {} IN relations
""")

    DATABASE_CONNECTIONS["parus"] = db

    yield

    DATABASE_CONNECTIONS.clear()


APP = fastapi.FastAPI(lifespan=lifespan)
BASE_URL = "/api/v1/search"
@APP.get(BASE_URL)
async def search(query: str) -> list:
    indicator_type: str
    query_length_current = len(query)
    query_length_max = 255

    if not query:
        raise fastapi.HTTPException(422, "Пустой запрос")

    # защита от RegEx DoS
    elif query_length_current > query_length_max:
        raise fastapi.HTTPException(status_code=422, detail=f" Запрос слишком длинный. Максимальная длина составляет {query_length_max} символов, но вы указали {query_length_current} символов.")

    # валидация запроса для:
    # IP v6
    elif re.match(r"^[A-Fa-f0-9]{1,4}(:[A-Fa-f0-9]{1,4}){7}$", query):
        indicator_type = "IP"

    # сбрасываем нагрузку с RegEx
    # для остальных запросов регистр не важен
    query = query.lower()

    # Hash RSA256
    if re.match(r"^[a-f0-9]{64}$", query):
        indicator_type = "Hash"

    # URL
    elif re.match(r"^(ftp|http|https)://[a-z0-9.-]+\.[a-z]{2,6}$", query):
        indicator_type = "URL"

    # IP v4
    elif re.match(r"^([0-9]{1,3}\.){3}[0-9]{1,3}$", query):
        indicator_type = "IP"

    # Domain
    elif re.match(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)*\.[a-z]{2,}$", query):
        indicator_type = "Domain"

    else:
        raise fastapi.HTTPException(status_code=422, detail="Неверный формат запроса. Допустимые форматы: Hash (RSA256), IP, Domain, URL.")

    aql_query = """
LET start_vertex = FIRST(
    FOR doc IN indicators
        FILTER doc.value == @indicator_value
        AND doc.type == @indicator_type
        LIMIT 1
        RETURN doc
)

FILTER start_vertex != NULL

FOR v, e, p IN 1..2 ANY start_vertex._id GRAPH 'intelligence'
    OPTIONS {
        bfs: true,
        uniqueVertices: 'global',
        uniqueEdges: 'path'
    }
    RETURN {
        start: start_vertex,
        vertex: v,
        edge: e,
        path: p
    }
"""

    cursor = await DATABASE_CONNECTIONS["parus"].aql.execute(
        aql_query,
        bind_vars={
            "indicator_value": query,
            "indicator_type": indicator_type.lower()
        },
        batch_size=100,
        count=False
    )

    if not cursor.has_more:
        raise fastapi.HTTPException(status_code=404, detail=f"Не найдено результатов для такого {indicator_type}")

    return [doc async for doc in cursor]


@pytest.fixture
async def async_client():
    async with asgi_lifespan.LifespanManager(APP) as manager:
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
async def test_search_should_accept_valid_ip(async_client):
    response = await async_client.get(
        BASE_URL + "?query=192.168.9.1"
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
async def test_search_should_return_dict(async_client):
    response = await async_client.get(
        BASE_URL + "?query=b00b5.free"
    )
    assert dict == type(response.json())

@pytest.mark.anyio
async def test_search_should_return_list(async_client):
    response = await async_client.get(
        BASE_URL + "?query=192.168.1.1"
    )
    assert list == type(response.json())

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
