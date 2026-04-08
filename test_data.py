import arangoasync
import arangoasync.exceptions
import arangoasync.auth
import asyncio
import random
import contextlib


@contextlib.asynccontextmanager
async def test_data():
    client = arangoasync.ArangoClient(
        hosts=[
            "http://127.0.0.1:8529"
        ]
    )

    # system_db = await client.db(
    #     "_system",
    #     auth=arangoasync.auth.Auth(
    #         username="root",
    #         password="root"
    #     )
    # )
    # if not await system_db.has_database("parus"):
    #     await system_db.create_database("parus")

    db = await client.db(
        "parus",
        auth=arangoasync.auth.Auth(
            username="root", password="root"
        )
    )

    # try:
    #     await db.create_collection("indicators", col_type="document")
    # except arangoasync.exceptions.CollectionCreateError:
    #     pass

    # try:
    #     await db.create_collection("relations", col_type="edge")
    # except arangoasync.exceptions.CollectionCreateError:
    #     pass

    # try:
    #     await db.collection("indicators").add_index(
    #         type="persistent",
    #         fields=["type", "value"],
    #         options={"unique": True}
    #     )
    # except arangoasync.exceptions.IndexCreateError:
    #     pass

    generated_indicators = []
    for i in range(1, 255):
        generated_indicators.append({
            "type": "ip",
            "value": f"192.168.1.{i}"
        })
        generated_indicators.append({
            "type": "domain",
            "value": f"example{i}.com"
        })
        generated_indicators.append({
            "type": "url",
            "value": f"https://example{i}.com/page"
        })
        generated_indicators.append({
            "type": "hash",
            "value": f"a1b2c3d4e5f6{i}"
        })

    insert_result = None
    try:
        insert_result = await db.aql.execute(
            """
            LET indicators = @generated_indicators

            LET inserted = (
                FOR i IN indicators
                    INSERT {
                        type: i.type,
                        value: i.value
                    }
                    INTO indicators
                    RETURN NEW
            )

            RETURN inserted
            """,
            bind_vars={"generated_indicators": generated_indicators},
            batch_size=100,
            count=False
        )
    except arangoasync.exceptions.ArangoError:
        try:
            yield
        finally:
            await client.close()
        return


    inserted_docs = [doc async for doc in insert_result]

    ips = [doc for doc in inserted_docs if doc["type"] == "ip"]
    domains = [doc for doc in inserted_docs if doc["type"] == "domain"]
    urls = [doc for doc in inserted_docs if doc["type"] == "url"]
    hashes = [doc for doc in inserted_docs if doc["type"] == "hash"]

    generated_edges = []

    for ip in ips:
        target_domain = random.choice(domains)
        generated_edges.append({
            "_from": ip["_id"],
            "_to": target_domain["_id"],
            "type": "resolves"
        })

    for domain in domains:
        target_url = random.choice(urls)
        generated_edges.append({
            "_from": domain["_id"],
            "_to": target_url["_id"],
            "type": "hosted_on"
        })

    for url in urls:
        target_hash = random.choice(hashes)
        generated_edges.append({
            "_from": url["_id"],
            "_to": target_hash["_id"],
            "type": "downloaded_from"
        })

    try:
        await db.aql.execute(
            """
            LET edges = @generated_edges

            FOR e IN edges
                UPSERT {
                    _from: e._from,
                    _to: e._to,
                    type: e.type
                }
                INSERT {
                    _from: e._from,
                    _to: e._to,
                    type: e.type
                }
                UPDATE {}
                INTO relations
            """,
            bind_vars={"generated_edges": generated_edges},
            batch_size=100,
            count=False
        )
    except arangoasync.exceptions.ArangoError:
        pass


    try:
        yield
    finally:
        await client.close()


async def main():
    print("Наполнение базы данных...")
    async with test_data():
        print("База данных заполнена!")


if __name__ == "__main__":
    asyncio.run(main())