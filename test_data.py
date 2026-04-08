import arangoasync
import arangoasync.auth
import asyncio
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

    fixed_indicators = [
        {
            "type": "ip",
            "value": "88.55.35.35"
        },
        {
            "type": "domain",
            "value": "do-not-delete-or-e2e-tests-will.fail"
        },
        {
            "type": "url",
            "value": "http://do-not-delete-or-e2e-tests-will.fail/terms"
        },
        {
            "type": "url",
            "value": "http://do-not-delete-or-e2e-tests-will.fail/privacy"
        },
        {
            "type": "url",
            "value": "http://do-not-delete-or-e2e-tests-will.fail/api"
        },
        {
            "type": "hash",
            "value": "71c81c1a9e3ff6a053896e12e8a04de20edc5fc5b5cc4702d7f09951823ffd60"
        },
        {
            "type": "hash",
            "value": "71c81c1a9e3ff6a053896e12e8a04de20edc5fc5b5cc4702d7f09951823ffd61"
        },
        {
            "type": "hash",
            "value": "71c81c1a9e3ff6a053896e12e8a04de20edc5fc5b5cc4702d7f09951823ffd62"
        },
        {
            "type": "hash",
            "value": "71c81c1a9e3ff6a053896e12e8a04de20edc5fc5b5cc4702d7f09951823ffd63"
        },
        {
            "type": "hash",
            "value": "71c81c1a9e3ff6a053896e12e8a04de20edc5fc5b5cc4702d7f09951823ffd64"
        },
        {
            "type": "hash",
            "value": "71c81c1a9e3ff6a053896e12e8a04de20edc5fc5b5cc4702d7f09951823ffd65"
        },
    ]

    generated_indicators = [*fixed_indicators]
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
            "value": f"71c81c1a9e3ff6a053896e12e8a04de20edc5fc5b5cc4702d7f09951823ff{i+100}"
        })

    await db.aql.execute("""
FOR i IN @indicators
    UPSERT { type: i.type, value: i.value }
    INSERT i
    UPDATE {}
    INTO indicators
""",
        bind_vars={"indicators": generated_indicators},
        batch_size=100,count=False
    )
    

    await db.aql.execute("""
FOR ip IN indicators
    FILTER ip.type == "ip"

    LET domain = FIRST(
        FOR d IN indicators
            FILTER d.type == "domain"
            SORT RAND()
            LIMIT 1
            RETURN d
    )

    INSERT {
        _from: ip._id,
        _to: domain._id,
        type: "resolves"
    }
    INTO relations
    OPTIONS { ignoreErrors: true }
""")

    await db.aql.execute("""
FOR d IN indicators
    FILTER d.type == "domain"

    LET url = FIRST(
        FOR u IN indicators
            FILTER u.type == "url"
            SORT RAND()
            LIMIT 1
            RETURN u
    )

    INSERT {
        _from: d._id,
        _to: url._id,
        type: "hosted_on"
    }
    INTO relations
    OPTIONS { ignoreErrors: true }
""")

    await db.aql.execute("""
FOR u IN indicators
    FILTER u.type == "url"

    LET h = FIRST(
        FOR x IN indicators
            FILTER x.type == "hash"
            SORT RAND()
            LIMIT 1
            RETURN x
    )

    INSERT {
        _from: u._id,
        _to: h._id,
        type: "downloaded_from"
    }
    INTO relations
    OPTIONS { ignoreErrors: true }
""")


    await db.aql.execute("""
FOR ip IN indicators
    FILTER ip.type == "ip"
    LET domain = FIRST(
        FOR d IN indicators
            FILTER d.type == "domain"
            SORT RAND()
            LIMIT 1
            RETURN d
    )
    INSERT {
        _from: ip._id,
        _to: domain._id,
        type: "resolves"
    } INTO relations OPTIONS { ignoreErrors: true }
""",
        batch_size=100,
        count=False
    )

    try:
        yield
    finally:
        await client.close()


async def main():
    async with test_data():
        pass


if __name__ == "__main__":
    asyncio.run(main())