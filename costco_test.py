import requests
import json
import re

URL = "https://gdx-api.costco.com/catalog/search/api/v1/search"

SEARCHES = [
    "Jack Daniel's",
    "Old Forester",
    "Weller",
    "Eagle Rare",
    "Blanton's",
    "EH Taylor",
]

WAREHOUSE = "471-wh"
ZIP_CODE = "95765"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
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
    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

DELIVERY_LOCATIONS = [
    "653-bd", "893-bd", "471-wh",
    "1251-3pl", "1321-wm", "1479-3pl",
    "283-wm", "561-wm", "725-wm",
    "731-wm", "758-wm", "759-wm",
    "847_0-cor", "847_0-cwt", "847_0-edi",
    "847_0-ehs", "847_0-membership", "847_0-mpt",
    "847_0-spc", "847_0-wm", "847_1-cwt",
    "847_1-edi", "847_aa_00-spc",
    "847_aa_u610-edi", "847_bosch_1472-edi",
    "847_d-fis", "847_ge_sac-edi",
    "847_lg_n1f-edi", "847_lux_us51-edi",
    "847_NA-cor", "847_NA-pharmacy",
    "847_NA-wm", "847_ss_u357-edi",
    "847_wp_r460-edi",
    "951-wm", "952-wm", "9847-wcs"
]


def search_costco(query):

    payload = {
        "visitorId": "81593075349571012370904879373705132128",
        "query": query,
        "pageSize": 24,
        "offset": 0,
        "orderBy": None,
        "searchMode": "page",
        "personalizationEnabled": True,
        "warehouseId": WAREHOUSE,
        "shipToPostal": ZIP_CODE,
        "shipToState": "CA",
        "deliveryLocations": DELIVERY_LOCATIONS,
        "filterBy": ["HIDE_OUT_OF_STOCK"],
        "pageCategories": []
    }

    r = requests.post(
        URL,
        headers=HEADERS,
        json=payload,
        timeout=30
    )

    print(f"\n{'=' * 70}")
    print(f"SEARCH: {query}")
    print(f"HTTP: {r.status_code}")

    if r.status_code != 200:
        print(r.text[:1000])
        return

    data = r.json()

    results = data.get("searchResult", {}).get("results", [])

    print(f"Results returned: {len(results)}")

    found = 0

    for result in results:

        product = result.get("product", {})

        title = product.get("title", "")
        brands = product.get("brands", [])

        variants = product.get("variants", [])

        rollup = result.get("variantRollupValues", {})

        # Combine searchable text
        text = (
            title + " " +
            " ".join(brands)
        ).lower()

        bourbon_terms = [
            "jack daniel",
            "old forester",
            "weller",
            "eagle rare",
            "blanton",
            "taylor",
        ]

        if not any(term in text for term in bourbon_terms):
            continue

        found += 1

        print("\nBOURBON MATCH")
        print("-" * 70)

        print("Title:", title)
        print("Brand:", ", ".join(brands))

        print("Product ID:", result.get("id"))

        if variants:
            print("Variant ID:", variants[0].get("id"))

        print("Price:", rollup.get("price"))

        warehouse_availability = rollup.get(
            f"inventory({WAREHOUSE}, attributes.availability)"
        )

        warehouse_price = rollup.get(
            f"inventory({WAREHOUSE}, price)"
        )

        print("Warehouse:", WAREHOUSE)
        print("Warehouse availability:", warehouse_availability)
        print("Warehouse price:", warehouse_price)

        print("URL:", product.get("uri"))

    if found == 0:
        print("\nNo bourbon matches found in returned results.")


print("=" * 70)
print("COSTCO BOURBON RADAR - BOURBON SEARCH ENGINE")
print("=" * 70)
print("Warehouse:", WAREHOUSE)
print("ZIP:", ZIP_CODE)

for search in SEARCHES:
    search_costco(search)

print("\n" + "=" * 70)
print("BOURBON SEARCH COMPLETE")
print("=" * 70)
