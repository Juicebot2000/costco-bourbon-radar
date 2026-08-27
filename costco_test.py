import requests
import json
import re
from datetime import datetime

# ============================================================
# COSTCO BOURBON RADAR - SEARCH ENGINE V2
# ============================================================

ENDPOINT = "https://gdx-api.costco.com/catalog/search/api/v1/search"

WAREHOUSE = "471-wh"
ZIP_CODE = "95765"

VISITOR_ID = "81593075349571012370904879373705132128"

SEARCHES = [
    "Jack Daniel's Tennessee Whiskey",
    "Jack Daniel's Single Barrel",
    "Jack Daniel's 10",
    "Jack Daniel's 12",
    "Jack Daniel's 14",
    "Old Forester Whiskey",
    "Old Forester 1924",
    "Weller Bourbon",
    "Weller Full Proof",
    "Weller Antique 107",
    "Eagle Rare Bourbon",
    "Blanton's Bourbon",
    "Blanton's Gold",
    "E.H. Taylor Bourbon",
    "E.H. Taylor Barrel Proof",
]

DELIVERY_LOCATIONS = [
    "653-bd",
    "893-bd",
    "471-wh",
    "1251-3pl",
    "1321-wm",
    "1479-3pl",
    "283-wm",
    "561-wm",
    "725-wm",
    "731-wm",
    "758-wm",
    "759-wm",
    "847_0-cor",
    "847_0-cwt",
    "847_0-edi",
    "847_0-ehs",
    "847_0-membership",
    "847_0-mpt",
    "847_0-spc",
    "847_0-wm",
    "847_1-cwt",
    "847_1-edi",
    "847_aa_00-spc",
    "847_aa_u610-edi",
    "847_bosch_1472-edi",
    "847_d-fis",
    "847_ge_sac-edi",
    "847_lg_n1f-edi",
    "847_lux_us51-edi",
    "847_NA-cor",
    "847_NA-pharmacy",
    "847_NA-wm",
    "847_ss_u357-edi",
    "847_wp_r460-edi",
    "951-wm",
    "952-wm",
    "9847-wcs",
]

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
}


def search_costco(search_term):
    """
    Send a request that reproduces the successful Chrome request.
    """

    payload = {
        "visitorId": VISITOR_ID,
        "query": search_term,
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
        "pageCategories": [],
    }

    response = requests.post(
        ENDPOINT,
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    return response


def is_bourbon_product(product):
    """
    Determine whether the returned Costco product actually looks
    like a whiskey/bourbon product.

    This prevents false positives from unrelated products.
    """

    title = product.get("title", "")
    brand = " ".join(product.get("brands", []))

    categories = product.get("categories", [])
    category_text = " ".join(categories)

    attributes = product.get("attributes", {})

    searchable_text = " ".join([
        title,
        brand,
        category_text,
        json.dumps(attributes),
    ]).lower()

    whiskey_terms = [
        "bourbon",
        "whiskey",
        "whisky",
        "tennessee whiskey",
        "straight bourbon",
        "straight whiskey",
    ]

    return any(term in searchable_text for term in whiskey_terms)


def get_warehouse_data(result):
    """
    Extract inventory and price information specifically for
    the requested Costco warehouse.
    """

    rollup = result.get("variantRollupValues", {})

    availability_key = (
        f"inventory({WAREHOUSE}, attributes.availability)"
    )

    price_key = f"inventory({WAREHOUSE}, price)"

    availability = rollup.get(availability_key)
    price = rollup.get(price_key)

    return availability, price


def matches_target(product, search_term):
    """
    Determine whether a genuine whiskey product appears relevant
    to the search term.
    """

    title = product.get("title", "").lower()
    brand = " ".join(product.get("brands", [])).lower()

    combined = f"{title} {brand}"

    # Remove punctuation for easier matching.
    normalized = re.sub(r"[^a-z0-9 ]", " ", combined)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    search_normalized = re.sub(
        r"[^a-z0-9 ]",
        " ",
        search_term.lower()
    )

    search_normalized = re.sub(
        r"\s+",
        " ",
        search_normalized
    ).strip()

    # Brand-specific matching.
    if "jack daniel" in search_term.lower():
        return "jack daniel" in normalized

    if "old forester" in search_term.lower():
        return "old forester" in normalized

    if "weller" in search_term.lower():
        return "weller" in normalized

    if "eagle rare" in search_term.lower():
        return "eagle rare" in normalized

    if "blanton" in search_term.lower():
        return "blanton" in normalized

    if "e.h. taylor" in search_term.lower():
        return (
            "e h taylor" in normalized
            or "eh taylor" in normalized
            or "taylor" in normalized
        )

    return search_normalized in normalized


def print_product(result):
    """
    Print useful information about a matching product.
    """

    product = result.get("product", {})

    title = product.get("title", "Unknown")
    product_id = result.get("id", "Unknown")

    brands = product.get("brands", [])
    variants = product.get("variants", [])

    availability, warehouse_price = get_warehouse_data(result)

    print("PRODUCT")
    print("-" * 70)
    print(f"Title: {title}")
    print(f"Brand: {brands}")
    print(f"Product ID: {product_id}")

    if variants:
        for variant in variants:
            print(f"Variant ID: {variant.get('id')}")
            print(f"Variant title: {variant.get('title')}")

    print(f"Warehouse: {WAREHOUSE}")
    print(f"Warehouse availability: {availability}")
    print(f"Warehouse price: {warehouse_price}")

    print(f"Costco URL: {result.get('uri', '')}")
    print()


def main():

    print("=" * 70)
    print("COSTCO BOURBON RADAR - SEARCH ENGINE V2")
    print("=" * 70)
    print(f"Warehouse: {WAREHOUSE}")
    print(f"ZIP: {ZIP_CODE}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    total_matches = 0

    for search_term in SEARCHES:

        print()
        print("=" * 70)
        print(f"SEARCH: {search_term}")
        print("=" * 70)

        try:

            response = search_costco(search_term)

            print(f"HTTP: {response.status_code}")

            if response.status_code != 200:
                print("ERROR RESPONSE:")
                print(response.text[:2000])
                continue

            try:
                data = response.json()
            except Exception:
                print("ERROR: Costco response was not valid JSON.")
                print(response.text[:2000])
                continue

            results = (
                data
                .get("searchResult", {})
                .get("results", [])
            )

            print(f"Results returned: {len(results)}")

            matches = []

            for result in results:

                product = result.get("product", {})

                # First make sure it is actually a whiskey/bourbon.
                if not is_bourbon_product(product):
                    continue

                # Then verify it actually matches our target.
                if not matches_target(product, search_term):
                    continue

                matches.append(result)

            if not matches:

                print("No matching bourbon products found.")

            else:

                print(f"VALID BOURBON MATCHES: {len(matches)}")

                for result in matches:
                    total_matches += 1
                    print_product(result)

        except requests.exceptions.Timeout:
            print("ERROR: Costco request timed out.")

        except requests.exceptions.RequestException as e:
            print(f"REQUEST ERROR: {e}")

        except Exception as e:
            print(f"UNEXPECTED ERROR: {repr(e)}")

    print()
    print("=" * 70)
    print("COSTCO BOURBON RADAR COMPLETE")
    print("=" * 70)
    print(f"Total valid bourbon matches: {total_matches}")
    print("=" * 70)


if __name__ == "__main__":
    main()
