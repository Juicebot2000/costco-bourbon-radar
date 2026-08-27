```python
import requests
import re
import json
import uuid
from datetime import datetime

# ================================================================
# COSTCO BOURBON RADAR - SEARCH ENGINE V5
# ================================================================
#
# V5 goals:
#
# 1. Reproduce Costco's browser-style search request as closely
#    as possible.
#
# 2. Keep the bourbon matching STRICT.
#
# 3. Never treat generic words such as "12", "gold", "bourbon",
#    or "whiskey" as proof that a product is a target bottle.
#
# 4. Save the raw Costco response when useful for debugging.
#
# ================================================================


# ================================================================
# CONFIGURATION
# ================================================================

WAREHOUSE_ID = "471-wh"
ZIP_CODE = "95765"

SEARCH_URL = (
    "https://gdx-api.costco.com/catalog/search/api/v1/search"
)

# Set to True while debugging Costco API changes.
SAVE_RAW_RESPONSES = True

RAW_RESPONSE_FILE = "costco_raw_response.json"

# ================================================================
# SESSION
# ================================================================

session = requests.Session()

# Browser-like headers.
#
# IMPORTANT:
# These are intentionally kept separate from the payload so that
# the request can be adjusted without changing the search logic.
#
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "client_id": "USBC",
    "content-type": "application/json",
    "origin": "https://www.costco.com",
    "referer": "https://www.costco.com/",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
}


# ================================================================
# TARGET BOURBON LIST
# ================================================================

TARGETS = {

    "Jack Daniel's 10 Year": [
        "jack daniel's 10",
        "jack daniels 10",
        "jack daniel 10",
        "jack daniel's 10 year",
        "jack daniels 10 year",
        "jack daniel 10 year",
        "jack daniel's 10 year old",
        "jack daniels 10 year old",
        "jack daniel 10 year old",
    ],

    "Jack Daniel's 12 Year": [
        "jack daniel's 12",
        "jack daniels 12",
        "jack daniel 12",
        "jack daniel's 12 year",
        "jack daniels 12 year",
        "jack daniel 12 year",
        "jack daniel's 12 year old",
        "jack daniels 12 year old",
        "jack daniel 12 year old",
    ],

    "Jack Daniel's 14 Year": [
        "jack daniel's 14",
        "jack daniels 14",
        "jack daniel 14",
        "jack daniel's 14 year",
        "jack daniels 14 year",
        "jack daniel 14 year",
        "jack daniel's 14 year old",
        "jack daniels 14 year old",
        "jack daniel 14 year old",
    ],

    "Old Forester 1924": [
        "old forester 1924",
        "old forester 1924 bourbon",
        "old forester 1924 year",
    ],

    "Weller Full Proof": [
        "weller full proof",
        "weller fullproof",
        "weller full-proof",
    ],

    "Weller Antique 107": [
        "weller antique 107",
        "weller 107",
        "weller antique 107 proof",
    ],

    "Eagle Rare 10 Year": [
        "eagle rare 10",
        "eagle rare 10 year",
        "eagle rare 10 year old",
        "eagle rare bourbon",
        "eagle rare bourbon whiskey",
    ],

    "Blanton's": [
        "blanton's bourbon",
        "blantons bourbon",
        "blanton's single barrel",
        "blantons single barrel",
    ],

    "Blanton's Gold": [
        "blanton's gold",
        "blantons gold",
        "blanton gold",
        "blantons gold edition",
        "blanton's gold edition",
    ],

    "E.H. Taylor Barrel Proof": [
        "e.h. taylor barrel proof",
        "eh taylor barrel proof",
        "e h taylor barrel proof",
        "e.h. taylor bp",
        "eh taylor bp",
        "e h taylor bp",
    ],
}


# ================================================================
# SEARCH QUERIES
# ================================================================

SEARCH_QUERIES = [

    # Jack Daniel's
    "Jack Daniel's",
    "Jack Daniel's Tennessee Whiskey",
    "Jack Daniel's Single Barrel",
    "Jack Daniel's 10",
    "Jack Daniel's 12",
    "Jack Daniel's 14",

    # Old Forester
    "Old Forester",
    "Old Forester Whiskey",
    "Old Forester 1924",

    # Weller
    "Weller",
    "Weller Bourbon",
    "Weller Full Proof",
    "Weller Antique 107",

    # Eagle Rare
    "Eagle Rare",
    "Eagle Rare Bourbon",

    # Blanton's
    "Blanton's",
    "Blanton's Bourbon",
    "Blanton's Gold",

    # E.H. Taylor
    "E.H. Taylor",
    "E.H. Taylor Bourbon",
    "E.H. Taylor Barrel Proof",
]


# ================================================================
# TEXT HELPERS
# ================================================================

def normalize_text(value):
    """
    Convert text to a consistent lowercase representation.
    """

    if value is None:
        return ""

    value = str(value).lower()

    value = value.replace("’", "'")
    value = value.replace("–", "-")
    value = value.replace("—", "-")

    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def get_brand(product):
    """
    Costco may return brand as:
        ["Kirkland Signature"]
    or:
        "Kirkland Signature"
    """

    brand = product.get("brand", "")

    if isinstance(brand, list):
        return " ".join(str(x) for x in brand)

    return str(brand or "")


def get_title(product):

    fields = [
        "title",
        "name",
        "productName",
        "displayName",
        "variantTitle",
        "variant_title",
    ]

    for field in fields:

        value = product.get(field)

        if value:
            return str(value)

    return ""


def get_product_id(product):

    fields = [
        "productId",
        "productID",
        "product_id",
        "id",
    ]

    for field in fields:

        value = product.get(field)

        if value:
            return str(value)

    return ""


def get_variant_id(product):

    fields = [
        "variantId",
        "variantID",
        "variant_id",
    ]

    for field in fields:

        value = product.get(field)

        if value:
            return str(value)

    return ""


# ================================================================
# INVENTORY / PRICE
# ================================================================

def extract_inventory(product):

    inventory = None
    price = None

    # ------------------------------------------------------------
    # Direct fields
    # ------------------------------------------------------------

    for field in [
        "warehouseAvailability",
        "warehouse_availability",
        "availability",
        "inventoryStatus",
    ]:

        if product.get(field) is not None:

            inventory = product.get(field)
            break

    for field in [
        "warehousePrice",
        "warehouse_price",
        "price",
    ]:

        if product.get(field) is not None:

            price = product.get(field)
            break

    # ------------------------------------------------------------
    # localInventories
    # ------------------------------------------------------------

    local = product.get("localInventories")

    if isinstance(local, list):

        for item in local:

            if not isinstance(item, dict):
                continue

            warehouse = str(
                item.get("warehouseId")
                or item.get("warehouse")
                or ""
            )

            if warehouse.lower() == WAREHOUSE_ID.lower():

                inventory = (
                    item.get("availability")
                    or item.get("inventory")
                    or item.get("status")
                    or inventory
                )

                price = (
                    item.get("price")
                    or price
                )

    # ------------------------------------------------------------
    # variantRollupValues
    # ------------------------------------------------------------

    variants = product.get("variantRollupValues")

    if isinstance(variants, list):

        for variant in variants:

            if not isinstance(variant, dict):
                continue

            warehouse = str(
                variant.get("warehouseId")
                or variant.get("warehouse")
                or ""
            )

            if warehouse.lower() == WAREHOUSE_ID.lower():

                inventory = (
                    variant.get("inventory")
                    or variant.get("availability")
                    or inventory
                )

                price = (
                    variant.get("price")
                    or price
                )

    return inventory, price


# ================================================================
# URL
# ================================================================

def build_product_url(product_id):

    if not product_id:
        return ""

    if not str(product_id).isdigit():
        return ""

    return (
        "https://www.costco.com/p/-/"
        f"{product_id}"
    )


# ================================================================
# COSTCO RESPONSE EXTRACTION
# ================================================================

def extract_products(data):

    if not isinstance(data, dict):
        return []

    # Direct structures
    for key in [
        "products",
        "results",
        "items",
    ]:

        products = data.get(key)

        if isinstance(products, list):
            return products

    # searchResults
    search_results = data.get("searchResults")

    if isinstance(search_results, dict):

        for key in [
            "products",
            "items",
            "results",
        ]:

            products = search_results.get(key)

            if isinstance(products, list):
                return products

    # searchResult
    search_result = data.get("searchResult")

    if isinstance(search_result, dict):

        for key in [
            "products",
            "items",
            "results",
        ]:

            products = search_result.get(key)

            if isinstance(products, list):
                return products

    # searchResultProvider / GRS style response
    provider = data.get("searchResultProvider")

    if provider:

        for key in [
            "products",
            "items",
            "results",
        ]:

            products = data.get(key)

            if isinstance(products, list):
                return products

    return []


# ================================================================
# STRICT NON-BOURBON FILTER
# ================================================================

def is_obvious_non_bourbon(title, brand):

    text = normalize_text(
        f"{title} {brand}"
    )

    reject_terms = [

        # Household
        "paper towel",
        "facial tissue",
        "toilet paper",

        # Drinks that are not bourbon
        "energy drink",
        "sparkling water",
        "waterloo",
        "chardonnay",
        "cabernet",
        "wine",
        "beer",

        # Food
        "beef stick",
        "caviar",
        "honey",
        "cheese",

        # Travel
        "costco travel",
        "experience colorado",
        "experience tennessee",
        "colorado springs",
        "ihg hotels",
        "seabourn",

        # Medication
        "restoril",
        "folbee",
        "paxil",
        "glyburide",

        # Vehicles
        "atv",
        "electric youth",

        # Barware
        "wine decanter",
        "decanter",

    ]

    for term in reject_terms:

        if term in text:
            return True

    return False


# ================================================================
# TARGET MATCHING
# ================================================================

def target_match_score(
    target_name,
    title,
    brand
):

    title_norm = normalize_text(title)
    brand_norm = normalize_text(brand)

    # ------------------------------------------------------------
    # IMPORTANT:
    #
    # Target identity must appear in the PRODUCT itself.
    #
    # We intentionally do NOT use the Costco search query here.
    #
    # ------------------------------------------------------------

    aliases = TARGETS.get(
        target_name,
        []
    )

    best_score = 0
    best_alias = None

    for alias in aliases:

        alias_norm = normalize_text(alias)

        if not alias_norm:
            continue

        # Exact phrase in title
        if alias_norm in title_norm:

            score = 100

            # Brand also confirms identity
            if target_name.startswith(
                "Jack Daniel"
            ) and "jack daniel" in title_norm:

                score += 10

            if target_name.startswith(
                "Old Forester"
            ) and "old forester" in title_norm:

                score += 10

            if target_name.startswith(
                "Weller"
            ) and "weller" in title_norm:

                score += 10

            if target_name.startswith(
                "Eagle Rare"
            ) and "eagle rare" in title_norm:

                score += 10

            if target_name.startswith(
                "Blanton"
            ) and "blanton" in title_norm:

                score += 10

            if target_name.startswith(
                "E.H. Taylor"
            ) and (
                "taylor" in title_norm
                or "eh taylor" in title_norm
            ):

                score += 10

            if score > best_score:

                best_score = score
                best_alias = alias

        # Exact phrase in brand
        elif alias_norm in brand_norm:

            score = 90

            if score > best_score:

                best_score = score
                best_alias = alias

    return best_score, best_alias


# ================================================================
# PRODUCT CLASSIFICATION
# ================================================================

def classify_product(
    target_name,
    product
):

    title = get_title(product)
    brand = get_brand(product)

    if not title:

        return (
            "REJECTED",
            0,
            None,
            "No product title"
        )

    if is_obvious_non_bourbon(
        title,
        brand
    ):

        return (
            "REJECTED",
            0,
            None,
            "Obvious non-bourbon product"
        )

    score, alias = target_match_score(
        target_name,
        title,
        brand
    )

    # ------------------------------------------------------------
    # CONFIRMED
    # ------------------------------------------------------------

    if score >= 100:

        return (
            "CONFIRMED",
            score,
            alias,
            "Exact target expression found in product"
        )

    # ------------------------------------------------------------
    # REVIEW
    # ------------------------------------------------------------

    if score >= 90:

        return (
            "REVIEW",
            score,
            alias,
            "Possible target identity found"
        )

    # ------------------------------------------------------------
    # REJECTED
    # ------------------------------------------------------------

    return (
        "REJECTED",
        score,
        alias,
        "Target expression not present in product"
    )


# ================================================================
# COSTCO API REQUEST
# ================================================================

def search_costco(query):

    # ------------------------------------------------------------
    # New visitor ID for this session.
    #
    # This avoids using the same artificial visitor ID every run.
    # ------------------------------------------------------------

    visitor_id = str(
        uuid.uuid4()
    )

    payload = {

        "visitorId": visitor_id,

        "query": query,

        "pageSize": 24,

        "offset": 0,

        "warehouseId": WAREHOUSE_ID,

        "shipToPostal": ZIP_CODE,

        "shipToState": "CA",

    }

    try:

        response = session.post(

            SEARCH_URL,

            headers=HEADERS,

            json=payload,

            timeout=30,

        )

        return response

    except requests.RequestException as e:

        print()
        print("REQUEST ERROR")
        print("-" * 70)
        print(str(e))

        return None


# ================================================================
# SAVE RAW RESPONSE
# ================================================================

def save_raw_response(
    query,
    response,
    data
):

    if not SAVE_RAW_RESPONSES:
        return

    try:

        record = {

            "timestamp": datetime.now().isoformat(),

            "query": query,

            "http_status": response.status_code,

            "response": data,

        }

        with open(
            RAW_RESPONSE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                record,
                f,
                indent=2,
                ensure_ascii=False
            )

    except Exception as e:

        print(
            f"Could not save raw response: {e}"
        )


# ================================================================
# PRINT PRODUCT
# ================================================================

def print_product(
    target_name,
    product,
    status,
    score,
    alias,
    reason
):

    title = get_title(product)

    brand = get_brand(product)

    product_id = get_product_id(
        product
    )

    variant_id = get_variant_id(
        product
    )

    inventory, price = extract_inventory(
        product
    )

    url = build_product_url(
        product_id
    )

    print()
    print(status)
    print("-" * 70)

    print(
        f"Target: {target_name}"
    )

    print(
        f"Match score: {score}"
    )

    if alias:

        print(
            f"Matched expression: {alias}"
        )

    print(
        f"Reason: {reason}"
    )

    print()

    print(
        f"Title: {title}"
    )

    print(
        f"Brand: {brand}"
    )

    print(
        f"Product ID: {product_id}"
    )

    print(
        f"Variant ID: {variant_id}"
    )

    print(
        f"Warehouse: {WAREHOUSE_ID}"
    )

    print(
        f"Warehouse availability: {inventory}"
    )

    print(
        f"Warehouse price: {price}"
    )

    if url:

        print(
            f"URL: {url}"
        )


# ================================================================
# API ERROR DIAGNOSTICS
# ================================================================

def print_api_error(response):

    print()
    print("COSTCO API REQUEST FAILED")
    print("-" * 70)

    print(
        f"HTTP status: {response.status_code}"
    )

    print()

    try:

        error_data = response.json()

        print(
            json.dumps(
                error_data,
                indent=2
            )
        )

    except Exception:

        print(
            response.text[:3000]
        )

    print()

    if response.status_code == 401:

        print(
            "DIAGNOSIS:"
        )

        print(
            "Costco's API gateway rejected the request "
            "before returning search results."
        )

        print(
            "This is an authentication/request-header issue, "
            "not a bourbon matching issue."
        )

        print()

        print(
            "The next step is to reproduce the exact browser "
            "request that currently returns HTTP 200."
        )


# ================================================================
# MAIN
# ================================================================

def main():

    start_time = datetime.now()

    print("=" * 70)

    print(
        "COSTCO BOURBON RADAR - SEARCH ENGINE V5"
    )

    print("=" * 70)

    print(
        f"Warehouse: {WAREHOUSE_ID}"
    )

    print(
        f"ZIP: {ZIP_CODE}"
    )

    print(
        "Started:",
        start_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("=" * 70)

    # ------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------

    confirmed_products = {}

    review_products = {}

    total_results = 0

    rejected_count = 0

    successful_requests = 0

    failed_requests = 0

    # ------------------------------------------------------------
    # Search
    # ------------------------------------------------------------

    for query in SEARCH_QUERIES:

        print()
        print("=" * 70)

        print(
            f"SEARCH: {query}"
        )

        print("=" * 70)

        response = search_costco(
            query
        )

        if response is None:

            failed_requests += 1

            continue

        print(
            f"HTTP: {response.status_code}"
        )

        # --------------------------------------------------------
        # API error
        # --------------------------------------------------------

        if response.status_code != 200:

            failed_requests += 1

            print_api_error(
                response
            )

            continue

        successful_requests += 1

        # --------------------------------------------------------
        # Parse JSON
        # --------------------------------------------------------

        try:

            data = response.json()

        except Exception:

            print(
                "Unable to decode Costco JSON response."
            )

            failed_requests += 1

            continue

        # Save latest successful response.
        save_raw_response(
            query,
            response,
            data
        )

        # --------------------------------------------------------
        # Extract products
        # --------------------------------------------------------

        products = extract_products(
            data
        )

        print(
            f"Results returned: {len(products)}"
        )

        total_results += len(
            products
        )

        if not products:

            print(
                "No products extracted from response."
            )

            continue

        query_confirmed = 0

        query_review = 0

        # --------------------------------------------------------
        # Evaluate every product against every target
        # --------------------------------------------------------

        for product in products:

            if not isinstance(
                product,
                dict
            ):

                continue

            for target_name in TARGETS:

                (
                    status,
                    score,
                    alias,
                    reason
                ) = classify_product(
                    target_name,
                    product
                )

                product_id = get_product_id(
                    product
                )

                variant_id = get_variant_id(
                    product
                )

                unique_id = (
                    f"{target_name}|"
                    f"{product_id}|"
                    f"{variant_id}"
                )

                # ------------------------------------------------
                # CONFIRMED
                # ------------------------------------------------

                if status == "CONFIRMED":

                    query_confirmed += 1

                    if (
                        unique_id
                        not in confirmed_products
                    ):

                        confirmed_products[
                            unique_id
                        ] = {

                            "target":
                                target_name,

                            "product":
                                product,

                            "score":
                                score,

                            "alias":
                                alias,

                            "reason":
                                reason,

                        }

                        print_product(
                            target_name,
                            product,
                            "🎯 CONFIRMED TARGET",
                            score,
                            alias,
                            reason,
                        )

                # ------------------------------------------------
                # REVIEW
                # ------------------------------------------------

                elif status == "REVIEW":

                    query_review += 1

                    if (
                        unique_id
                        not in review_products
                    ):

                        review_products[
                            unique_id
                        ] = {

                            "target":
                                target_name,

                            "product":
                                product,

                            "score":
                                score,

                            "alias":
                                alias,

                            "reason":
                                reason,

                        }

        # --------------------------------------------------------
        # Query summary
        # --------------------------------------------------------

        if query_confirmed:

            print()
            print(
                f"Confirmed matches: "
                f"{query_confirmed}"
            )

        elif query_review:

            print()
            print(
                f"Potential review matches: "
                f"{query_review}"
            )

        else:

            print(
                "No target bourbon matches found."
            )

    # ============================================================
    # FINAL REPORT
    # ============================================================

    print()
    print("=" * 70)

    print(
        "COSTCO BOURBON RADAR COMPLETE"
    )

    print("=" * 70)

    print(
        f"Successful API requests: "
        f"{successful_requests}"
    )

    print(
        f"Failed API requests: "
        f"{failed_requests}"
    )

    print(
        f"Total Costco search results examined: "
        f"{total_results}"
    )

    print(
        f"Confirmed target matches: "
        f"{len(confirmed_products)}"
    )

    print(
        f"Potential review matches: "
        f"{len(review_products)}"
    )

    print(
        f"Rejected/irrelevant results: "
        f"{rejected_count}"
    )

    # ============================================================
    # CONFIRMED
    # ============================================================

    print()
    print("=" * 70)

    print(
        "CONFIRMED TARGET BOURBONS"
    )

    print("=" * 70)

    if not confirmed_products:

        print(
            "NONE FOUND."
        )

    else:

        for item in (
            confirmed_products.values()
        ):

            print_product(

                item["target"],

                item["product"],

                "🎯 CONFIRMED TARGET",

                item["score"],

                item["alias"],

                item["reason"],

            )

    # ============================================================
    # REVIEW
    # ============================================================

    print()
    print("=" * 70)

    print(
        "POTENTIAL MATCHES REQUIRING REVIEW"
    )

    print("=" * 70)

    if not review_products:

        print(
            "NONE."
        )

    else:

        for item in (
            review_products.values()
        ):

            print_product(

                item["target"],

                item["product"],

                "⚠️ REVIEW",

                item["score"],

                item["alias"],

                item["reason"],

            )

    # ============================================================
    # FINISH
    # ============================================================

    elapsed = (
        datetime.now()
        - start_time
    )

    print()
    print("=" * 70)

    print(
        "Finished:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print(
        f"Runtime: {elapsed}"
    )

    print("=" * 70)


# ================================================================
# RUN
# ================================================================

if __name__ == "__main__":

    main()
```
