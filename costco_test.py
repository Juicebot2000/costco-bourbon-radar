import requests
import json
import re
from datetime import datetime

# ==============================================================
# COSTCO BOURBON RADAR V3
# ==============================================================
# Purpose:
#   Search Costco's GDX API and identify potential bourbon products.
#
# IMPORTANT:
#   This version is intentionally more diagnostic.
#   It shows candidate products instead of relying on overly
#   strict exact-name matching.
# ==============================================================


# --------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------

ENDPOINT = "https://gdx-api.costco.com/catalog/search/api/v1/search"

WAREHOUSE_ID = "471-wh"
ZIP_CODE = "95765"
STATE = "CA"

VISITOR_ID = "81593075349571012370904879373705132128"

CLIENT_IDENTIFIER = "168287ea-1201-45f6-9b45-5bbea49f8ee7"


# --------------------------------------------------------------
# SEARCH TERMS
# --------------------------------------------------------------

SEARCHES = [
    "Jack Daniel's",
    "Jack Daniel's Tennessee Whiskey",
    "Jack Daniel's Single Barrel",
    "Jack Daniel's 10",
    "Jack Daniel's 12",
    "Jack Daniel's 14",

    "Old Forester",
    "Old Forester Whiskey",
    "Old Forester 1924",

    "Weller",
    "Weller Bourbon",
    "Weller Full Proof",
    "Weller Antique 107",

    "Eagle Rare",
    "Eagle Rare Bourbon",

    "Blanton's",
    "Blanton's Bourbon",
    "Blanton's Gold",

    "E.H. Taylor",
    "E.H. Taylor Bourbon",
    "E.H. Taylor Barrel Proof",
]


# --------------------------------------------------------------
# COSTCO DELIVERY LOCATIONS
# --------------------------------------------------------------

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


# --------------------------------------------------------------
# HEADERS
# --------------------------------------------------------------

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

    "client-identifier": CLIENT_IDENTIFIER,
    "client_id": "USBC",
    "locale": "en-US",
    "searchResultProvider": "GRS",

    "sec-ch-ua": (
        '"Google Chrome";v="149", '
        '"Chromium";v="149", '
        '"Not)A;Brand";v="24"'
    ),
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}


# --------------------------------------------------------------
# NORMALIZE TEXT
# --------------------------------------------------------------

def normalize(text):
    """
    Normalize text so matching is easier.
    """

    if not text:
        return ""

    text = str(text).lower()

    # Normalize apostrophes
    text = text.replace("’", "'")

    # Remove punctuation
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# --------------------------------------------------------------
# BUILD SEARCH REQUEST
# --------------------------------------------------------------

def build_payload(search_term):

    return {
        "visitorId": VISITOR_ID,
        "query": search_term,
        "pageSize": 24,
        "offset": 0,
        "orderBy": None,
        "searchMode": "page",
        "personalizationEnabled": True,
        "warehouseId": WAREHOUSE_ID,
        "shipToPostal": ZIP_CODE,
        "shipToState": STATE,
        "deliveryLocations": DELIVERY_LOCATIONS,
        "filterBy": [
            "HIDE_OUT_OF_STOCK"
        ],
        "pageCategories": []
    }


# --------------------------------------------------------------
# EXTRACT PRICE
# --------------------------------------------------------------

def extract_price(rollup):

    if not isinstance(rollup, dict):
        return None

    # Warehouse-specific price is preferred
    warehouse_key = f"inventory({WAREHOUSE_ID}, price)"

    if warehouse_key in rollup:
        values = rollup.get(warehouse_key)

        if isinstance(values, list) and values:
            return values[0]

    # Fall back to normal price
    values = rollup.get("price")

    if isinstance(values, list) and values:
        return values[0]

    return None


# --------------------------------------------------------------
# EXTRACT WAREHOUSE AVAILABILITY
# --------------------------------------------------------------

def extract_availability(rollup):

    if not isinstance(rollup, dict):
        return None

    key = f"inventory({WAREHOUSE_ID}, attributes.availability)"

    value = rollup.get(key)

    if isinstance(value, list):
        return value

    return value


# --------------------------------------------------------------
# GET PRODUCT TEXT
# --------------------------------------------------------------

def get_product_text(result):

    product = result.get("product", {})

    title = product.get("title", "")
    brand = product.get("brands", [])
    categories = product.get("categories", [])

    if not isinstance(brand, list):
        brand = [str(brand)]

    if not isinstance(categories, list):
        categories = [str(categories)]

    text_parts = [
        title,
        " ".join(brand),
        " ".join(categories),
    ]

    # Also inspect variants
    variants = product.get("variants", [])

    if isinstance(variants, list):

        for variant in variants:

            if not isinstance(variant, dict):
                continue

            text_parts.append(
                variant.get("title", "")
            )

            attributes = variant.get(
                "attributes",
                {}
            )

            if isinstance(attributes, dict):

                for value in attributes.values():

                    if not isinstance(value, dict):
                        continue

                    text_parts.extend(
                        value.get("text", [])
                    )

    return normalize(" ".join(
        str(x) for x in text_parts if x
    ))


# --------------------------------------------------------------
# BOURBON KEYWORDS
# --------------------------------------------------------------

BOURBON_WORDS = [
    "bourbon",
    "whiskey",
    "whisky",
    "tennessee whiskey",
]


# --------------------------------------------------------------
# TARGET MATCHING
# --------------------------------------------------------------

def calculate_match_score(search_term, result):

    product = result.get("product", {})

    title = normalize(
        product.get("title", "")
    )

    brands = product.get("brands", [])

    if not isinstance(brands, list):
        brands = [brands]

    brand_text = normalize(
        " ".join(str(x) for x in brands)
    )

    categories = product.get("categories", [])

    if not isinstance(categories, list):
        categories = [categories]

    category_text = normalize(
        " ".join(str(x) for x in categories)
    )

    all_text = get_product_text(result)

    score = 0

    # ----------------------------------------------------------
    # BRAND MATCHING
    # ----------------------------------------------------------

    if "jack daniel" in all_text:
        score += 50

    if "old forester" in all_text:
        score += 50

    if "weller" in all_text:
        score += 50

    if "eagle rare" in all_text:
        score += 50

    if "blanton" in all_text:
        score += 50

    if "eh taylor" in all_text:
        score += 50

    if "e h taylor" in all_text:
        score += 50

    # ----------------------------------------------------------
    # BOURBON / WHISKEY
    # ----------------------------------------------------------

    if "bourbon" in all_text:
        score += 20

    if "whiskey" in all_text:
        score += 10

    # ----------------------------------------------------------
    # SPECIFIC AGE / EXPRESSION
    # ----------------------------------------------------------

    search_normalized = normalize(search_term)

    if "10" in search_normalized and "10" in title:
        score += 30

    if "12" in search_normalized and "12" in title:
        score += 30

    if "14" in search_normalized and "14" in title:
        score += 30

    if "1924" in search_normalized and "1924" in title:
        score += 40

    if "full proof" in search_normalized and "full proof" in all_text:
        score += 40

    if "107" in search_normalized and "107" in all_text:
        score += 40

    if "gold" in search_normalized and "gold" in all_text:
        score += 40

    if "barrel proof" in search_normalized and "barrel proof" in all_text:
        score += 40

    # ----------------------------------------------------------
    # WAREHOUSE INVENTORY
    # ----------------------------------------------------------

    rollup = result.get(
        "variantRollupValues",
        {}
    )

    availability = extract_availability(
        rollup
    )

    if availability:

        if isinstance(availability, list):

            if "IN_STOCK" in availability:
                score += 25

        elif availability == "IN_STOCK":
            score += 25

    return score


# --------------------------------------------------------------
# DISPLAY RESULT
# --------------------------------------------------------------

def display_result(search_term, result, score):

    product = result.get(
        "product",
        {}
    )

    title = product.get(
        "title",
        "UNKNOWN"
    )

    brands = product.get(
        "brands",
        []
    )

    product_id = result.get(
        "id",
        ""
    )

    variants = product.get(
        "variants",
        []
    )

    variant_id = ""

    if isinstance(variants, list) and variants:

        variant_id = variants[0].get(
            "id",
            ""
        )

    rollup = result.get(
        "variantRollupValues",
        {}
    )

    availability = extract_availability(
        rollup
    )

    price = extract_price(
        rollup
    )

    url = product.get(
        "uri",
        ""
    )

    print()
    print("POTENTIAL BOURBON")
    print("-" * 70)

    print(f"Match score: {score}")

    print(f"Title: {title}")

    print(f"Brand: {brands}")

    print(f"Product ID: {product_id}")

    print(f"Variant ID: {variant_id}")

    print(f"Warehouse: {WAREHOUSE_ID}")

    print(
        f"Warehouse availability: "
        f"{availability}"
    )

    print(
        f"Warehouse price: "
        f"{price}"
    )

    print(f"URL: {url}")


# --------------------------------------------------------------
# SEARCH COSTCO
# --------------------------------------------------------------

def search_costco(search_term):

    payload = build_payload(
        search_term
    )

    try:

        response = requests.post(
            ENDPOINT,
            headers=HEADERS,
            json=payload,
            timeout=30
        )

    except requests.exceptions.RequestException as e:

        print(
            f"REQUEST ERROR: {e}"
        )

        return None

    print(
        f"HTTP: {response.status_code}"
    )

    if response.status_code != 200:

        print(
            "ERROR RESPONSE:"
        )

        print(
            response.text[:2000]
        )

        return None

    try:

        data = response.json()

    except json.JSONDecodeError:

        print(
            "ERROR: Costco response "
            "was not valid JSON."
        )

        return None

    results = (
        data
        .get("searchResult", {})
        .get("results", [])
    )

    print(
        f"Results returned: "
        f"{len(results)}"
    )

    return results


# --------------------------------------------------------------
# MAIN
# --------------------------------------------------------------

def main():

    print("=" * 70)
    print(
        "COSTCO BOURBON RADAR - SEARCH ENGINE V3"
    )
    print("=" * 70)

    print(
        f"Warehouse: {WAREHOUSE_ID}"
    )

    print(
        f"ZIP: {ZIP_CODE}"
    )

    print(
        f"Started: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print("=" * 70)

    total_candidates = 0

    for search_term in SEARCHES:

        print()
        print("=" * 70)

        print(
            f"SEARCH: {search_term}"
        )

        print("=" * 70)

        results = search_costco(
            search_term
        )

        if results is None:
            continue

        if not results:

            print(
                "No results."
            )

            continue

        scored_results = []

        for result in results:

            score = calculate_match_score(
                search_term,
                result
            )

            scored_results.append(
                (score, result)
            )

        # Highest scoring first
        scored_results.sort(
            key=lambda x: x[0],
            reverse=True
        )

        # ------------------------------------------------------
        # IMPORTANT:
        # Show the top candidates even if their score is low.
        # This lets us see what Costco is actually returning.
        # ------------------------------------------------------

        shown = 0

        for score, result in scored_results:

            # Only show meaningful candidates
            if score >= 40:

                display_result(
                    search_term,
                    result,
                    score
                )

                shown += 1
                total_candidates += 1

                if shown >= 5:
                    break

        # ------------------------------------------------------
        # DIAGNOSTIC MODE
        # ------------------------------------------------------

        if shown == 0:

            print()
            print(
                "No high-confidence bourbon "
                "matches."
            )

            print()
            print(
                "TOP COSTCO SEARCH RESULTS:"
            )

            print("-" * 70)

            for score, result in scored_results[:5]:

                product = result.get(
                    "product",
                    {}
                )

                title = product.get(
                    "title",
                    "UNKNOWN"
                )

                brands = product.get(
                    "brands",
                    []
                )

                product_id = result.get(
                    "id",
                    ""
                )

                rollup = result.get(
                    "variantRollupValues",
                    {}
                )

                availability = (
                    extract_availability(
                        rollup
                    )
                )

                price = extract_price(
                    rollup
                )

                print(
                    f"[Score {score}] "
                    f"{title}"
                )

                print(
                    f"    Brand: {brands}"
                )

                print(
                    f"    Product ID: "
                    f"{product_id}"
                )

                print(
                    f"    Availability: "
                    f"{availability}"
                )

                print(
                    f"    Price: "
                    f"{price}"
                )

                print()

    print("=" * 70)

    print(
        "COSTCO BOURBON RADAR COMPLETE"
    )

    print("=" * 70)

    print(
        f"Total candidate matches: "
        f"{total_candidates}"
    )

    print("=" * 70)


# --------------------------------------------------------------
# RUN
# --------------------------------------------------------------

if __name__ == "__main__":
    main()
