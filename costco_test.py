import requests
import json

URL = "https://gdx-api.costco.com/catalog/search/api/v1/search"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://www.costco.com",
    "Referer": "https://www.costco.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
    "client-identifier": "168287ea-1201-45f6-9b45-5bbea49f8ee7",
    "client_id": "USBC",
    "locale": "en-US",
    "searchResultProvider": "GRS",
}

SEARCHES = [
    "1605257",
    "1740448",
    "Jack Daniel",
    "Weller",
    "Blanton",
    "Eagle Rare",
    "Old Forester",
    "E.H. Taylor",
]

for query in SEARCHES:

    payload = {
        "visitorId": "81593075349571012370904879373705132128",
        "query": query,
        "pageSize": 100,
        "offset": 0,
        "orderBy": None,
        "searchMode": "page",
        "personalizationEnabled": False,
        "warehouseId": "471-wh",
        "shipToPostal": "95765",
        "shipToState": "CA",
        "deliveryLocations": [
            "471-wh"
        ],
        "filterBy": [],
        "pageCategories": []
    }

    print("\n" + "=" * 70)
    print("SEARCH:", query)

    try:
        r = requests.post(
            URL,
            headers=HEADERS,
            json=payload,
            timeout=30
        )

        print("HTTP:", r.status_code)

        if r.status_code != 200:
            print(r.text[:1000])
            continue

        data = r.json()

        results = data.get("searchResult", {}).get("results", [])

        print("RESULT COUNT:", len(results))

        for result in results:

            product = result.get("product", {})
            rollup = result.get("variantRollupValues", {})

            print("\nPRODUCT")
            print("-" * 70)

            print("Title:", product.get("title"))
            print("Brand:", product.get("brands"))
            print("Product ID:", result.get("id"))

            variants = product.get("variants", [])

            for v in variants:
                print("Variant ID:", v.get("id"))
                print("Variant title:", v.get("title"))

            print("Price:", rollup.get("price"))

            print(
                "Warehouse availability:",
                rollup.get(
                    "inventory(471-wh, attributes.availability)"
                )
            )

            print(
                "Warehouse price:",
                rollup.get(
                    "inventory(471-wh, price)"
                )
            )

            print("URL:", product.get("uri"))

    except Exception as e:
        print("ERROR:", repr(e))

print("\n" + "=" * 70)
print("COSTCO PRODUCT DISCOVERY TEST COMPLETE")
print("=" * 70)
