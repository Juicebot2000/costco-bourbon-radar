import requests
import re
from datetime import datetime

# ================================================================
# COSTCO BOURBON RADAR - SEARCH ENGINE V4
# ================================================================

WAREHOUSE_ID = "471-wh"
ZIP_CODE = "95765"

# ----------------------------------------------------------------
# COSTCO API
# ----------------------------------------------------------------

SEARCH_URL = "https://gdx-api.costco.com/catalog/search/api/v1/search"

# These are the headers that have been working with the Costco API.
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

# ----------------------------------------------------------------
# TARGET BOURBON LIST
# ----------------------------------------------------------------
#
# The aliases are intentionally strict.
# Generic words such as "bourbon" and "whiskey" DO NOT count
# toward a target match.
#
# ----------------------------------------------------------------

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
        "jd 10",
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
        "jd 12",
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
        "jd 14",
    ],

    "Old Forester 1924": [
        "old forester 1924",
        "old forester 1924 bourbon",
        "old forester 1924 year",
        "of 1924",
    ],

    "Weller Full Proof": [
        "weller full proof",
        "weller fullproof",
        "weller fp",
    ],

    "Weller Antique 107": [
        "weller antique 107",
        "weller 107",
        "weller antique",
        "weller 107 proof",
    ],

    "Eagle Rare 10 Year": [
        "eagle rare",
        "eagle rare 10",
        "eagle rare 10 year",
        "eagle rare 10 year old",
        "eagle rare bourbon",
    ],

    "Blanton's": [
        "blanton's",
        "blantons",
        "blanton's bourbon",
        "blantons bourbon",
    ],

    "Blanton's Gold": [
        "blanton's gold",
        "blantons gold",
        "blanton gold",
        "blantons gold edition",
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

# ----------------------------------------------------------------
# SEARCH QUERIES
# ----------------------------------------------------------------
#
# We search several variations because Costco's search engine can
# behave differently depending on the exact query.
#
# ----------------------------------------------------------------

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
# HELPER FUNCTIONS
# ================================================================

def normalize_text(value):
    """
    Normalize text so matching is more reliable.

    Converts:
        Jack Daniel's
        Jack Daniels
        JACK DANIEL'S

    into a comparable lowercase representation.
    """

    if value is None:
        return ""

    value = str(value).lower()

    # Normalize apostrophes
    value = value.replace("’", "'")

    # Replace punctuation with spaces
    value = re.sub(r"[^a-z0-9]+", " ", value)

    # Collapse whitespace
    value = re.sub(r"\s+", " ", value).strip()

    return value


def get_brand(product):
    """
    Safely extract brand information.
    Costco sometimes returns a list and sometimes an empty value.
    """

    brand = product.get("brand", "")

    if isinstance(brand, list):
        return " ".join(str(x) for x in brand)

    return str(brand or "")


def get_title(product):
    """
    Try several possible Costco title fields.
    """

    possible_fields = [
        "title",
        "name",
        "productName",
        "displayName",
        "variantTitle",
        "variant_title",
    ]

    for field in possible_fields:
        value = product.get(field)

        if value:
            return str(value)

    return ""


def get_product_id(product):
    """
    Extract Costco product ID.
    """

    for field in [
        "productId",
        "productID",
        "product_id",
        "id",
    ]:
        value = product.get(field)

        if value:
            return str(value)

    return ""


def get_variant_id(product):
    """
    Extract Costco variant ID.
    """

    for field in [
        "variantId",
        "variantID",
        "variant_id",
    ]:
        value = product.get(field)

        if value:
            return str(value)

    return ""


def extract_inventory(product):
    """
    Attempt to extract warehouse inventory information from the
    different structures Costco may return.
    """

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


def build_product_url(product_id):
    """
    Build Costco product URL.
    """

    if not product_id:
        return ""

    # Only create a URL for numeric Costco product IDs.
    if not str(product_id).isdigit():
        return ""

    return (
        "https://www.costco.com/p/-/"
        f"{product_id}"
    )


# ================================================================
# TARGET MATCHING
# ================================================================

def target_match_score(target_name, title, brand):
    """
    Determine whether a Costco product is actually the target bottle.

    IMPORTANT:
    Generic words such as bourbon, whiskey, straight, Kentucky,
    bottle, etc. DO NOT produce a target match.

    The target's identifying expression must actually appear.
    """

    title_norm = normalize_text(title)
    brand_norm = normalize_text(brand)

    combined = f"{title_norm} {brand_norm}"

    aliases = TARGETS.get(target_name, [])

    best_score = 0
    best_alias = None

    for alias in aliases:

        alias_norm = normalize_text(alias)

        if not alias_norm:
            continue

        # --------------------------------------------------------
        # Exact phrase match
        # --------------------------------------------------------

        if alias_norm in combined:

            score = 100

            # Exact target phrase in the product title is strongest.
            if alias_norm in title_norm:
                score += 20

            if score > best_score:
                best_score = score
                best_alias = alias

    return best_score, best_alias


def is_obvious_non_bourbon(title, brand):
    """
    Reject obvious false positives.

    This is intentionally conservative. We don't reject a product
    merely because Costco's search engine returned something odd.
    """

    text = normalize_text(f"{title} {brand}")

    reject_terms = [
        "paper towel",
        "facial tissue",
        "energy drink",
        "sparkling water",
        "beef stick",
        "caviar",
        "honey",
        "chardonnay",
        "cabernet",
        "wine decanter",
        "atv",
        "electric youth",
        "restoril",
        "folbee",
        "paxil",
        "glyburide",
        "costco travel",
        "experience colorado",
        "experience tennessee",
        "colorado springs",
        "ihg hotels",
        "seabourn",
    ]

    for term in reject_terms:

        if term in text:
            return True

    return False


def classify_product(target_name, product):
    """
    Return:

        CONFIRMED
        REVIEW
        REJECTED
    """

    title = get_title(product)
    brand = get_brand(product)

    if not title:
        return "REJECTED", 0, None, "No product title"

    if is_obvious_non_bourbon(title, brand):
        return "REJECTED", 0, None, "Obvious non-bourbon product"

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
            "Target expression found"
        )

    # ------------------------------------------------------------
    # REVIEW
    # ------------------------------------------------------------

    if score >= 60:
        return (
            "REVIEW",
            score,
            alias,
            "Possible target match"
        )

    # ------------------------------------------------------------
    # REJECTED
    # ------------------------------------------------------------

    return (
        "REJECTED",
        score,
        alias,
        "Target expression not found"
    )


# ================================================================
# COSTCO SEARCH
# ================================================================

def search_costco(query):

    payload = {
        "visitorId": "bourbon-radar-v4",
        "query": query,
        "pageSize": 24,
        "offset": 0,
        "warehouseId": WAREHOUSE_ID,
        "shipToPostal": ZIP_CODE,
        "shipToState": "CA",
    }

    try:

        response = requests.post(
            SEARCH_URL,
            headers=HEADERS,
            json=payload,
            timeout=30,
        )

        return response

    except Exception as e:

        print(f"REQUEST ERROR: {e}")

        return None


# ================================================================
# EXTRACT PRODUCTS
# ================================================================

def extract_products(data):

    if not isinstance(data, dict):
        return []

    # Costco has used several structures.
    possible_paths = [
        data.get("products"),
        data.get("results"),
        data.get("items"),
    ]

    for products in possible_paths:

        if isinstance(products, list):
            return products

    # Search result structures
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

    # Search result provider structure
    provider = data.get("searchResult")

    if isinstance(provider, dict):

        for key in [
            "products",
            "items",
            "results",
        ]:

            products = provider.get(key)

            if isinstance(products, list):
                return products

    return []


# ================================================================
# PRINT PRODUCT
# ================================================================

def print_product(target_name, product, status, score, alias, reason):

    title = get_title(product)
    brand = get_brand(product)

    product_id = get_product_id(product)
    variant_id = get_variant_id(product)

    inventory, price = extract_inventory(product)

    url = build_product_url(product_id)

    print()
    print(status)
    print("-" * 70)

    print(f"Target: {target_name}")
    print(f"Match score: {score}")

    if alias:
        print(f"Matched expression: {alias}")

    print(f"Reason: {reason}")
    print()

    print(f"Title: {title}")
    print(f"Brand: {brand}")
    print(f"Product ID: {product_id}")
    print(f"Variant ID: {variant_id}")

    print(f"Warehouse: {WAREHOUSE_ID}")
    print(f"Warehouse availability: {inventory}")
    print(f"Warehouse price: {price}")

    if url:
        print(f"URL: {url}")


# ================================================================
# MAIN
# ================================================================

def main():

    start_time = datetime.now()

    print("=" * 70)
    print("COSTCO BOURBON RADAR - SEARCH ENGINE V4")
    print("=" * 70)

    print(f"Warehouse: {WAREHOUSE_ID}")
    print(f"ZIP: {ZIP_CODE}")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    print("=" * 70)

    # ------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------

    confirmed_products = {}
    review_products = {}

    rejected_count = 0
    total_results = 0

    # ------------------------------------------------------------
    # Run every Costco search
    # ------------------------------------------------------------

    for query in SEARCH_QUERIES:

        print()
        print("=" * 70)
        print(f"SEARCH: {query}")
        print("=" * 70)

        response = search_costco(query)

        if response is None:
            print("HTTP: REQUEST FAILED")
            continue

        print(f"HTTP: {response.status_code}")

        if response.status_code != 200:

            print("Costco API request failed.")

            try:
                print(response.text[:1000])
            except Exception:
                pass

            continue

        try:
            data = response.json()

        except Exception:

            print("Unable to decode Costco JSON response.")
            continue

        products = extract_products(data)

        print(f"Results returned: {len(products)}")

        total_results += len(products)

        if not products:

            print("No results.")
            continue

        # --------------------------------------------------------
        # Match against every bourbon target
        # --------------------------------------------------------

        query_confirmed = 0
        query_review = 0

        for product in products:

            if not isinstance(product, dict):
                continue

            for target_name in TARGETS:

                status, score, alias, reason = classify_product(
                    target_name,
                    product
                )

                product_id = get_product_id(product)
                variant_id = get_variant_id(product)

                unique_id = (
                    f"{target_name}|"
                    f"{product_id}|"
                    f"{variant_id}"
                )

                if status == "CONFIRMED":

                    query_confirmed += 1

                    if unique_id not in confirmed_products:

                        confirmed_products[unique_id] = {
                            "target": target_name,
                            "product": product,
                            "score": score,
                            "alias": alias,
                            "reason": reason,
                        }

                        print_product(
                            target_name,
                            product,
                            status,
                            score,
                            alias,
                            reason,
                        )

                elif status == "REVIEW":

                    query_review += 1

                    if unique_id not in review_products:

                        review_products[unique_id] = {
                            "target": target_name,
                            "product": product,
                            "score": score,
                            "alias": alias,
                            "reason": reason,
                        }

                else:

                    rejected_count += 1

        if query_confirmed == 0 and query_review == 0:

            print("No target bourbon matches found.")

        elif query_confirmed == 0:

            print(
                f"Potential review matches found: {query_review}"
            )

        else:

            print(
                f"Confirmed matches found: {query_confirmed}"
            )

    # ============================================================
    # FINAL REPORT
    # ============================================================

    print()
    print("=" * 70)
    print("COSTCO BOURBON RADAR COMPLETE")
    print("=" * 70)

    print(f"Total Costco search results examined: {total_results}")
    print(f"Confirmed target matches: {len(confirmed_products)}")
    print(f"Potential review matches: {len(review_products)}")
    print(f"Rejected/irrelevant results: {rejected_count}")

    # ------------------------------------------------------------
    # CONFIRMED MATCHES
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("CONFIRMED TARGET BOURBONS")
    print("=" * 70)

    if not confirmed_products:

        print("NONE FOUND.")

    else:

        for item in confirmed_products.values():

            print_product(
                item["target"],
                item["product"],
                "🎯 CONFIRMED TARGET",
                item["score"],
                item["alias"],
                item["reason"],
            )

    # ------------------------------------------------------------
    # REVIEW MATCHES
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("POTENTIAL MATCHES REQUIRING REVIEW")
    print("=" * 70)

    if not review_products:

        print("NONE.")

    else:

        for item in review_products.values():

            print_product(
                item["target"],
                item["product"],
                "⚠️ REVIEW",
                item["score"],
                item["alias"],
                item["reason"],
            )

    # ------------------------------------------------------------
    # FINISH
    # ------------------------------------------------------------

    elapsed = datetime.now() - start_time

    print()
    print("=" * 70)
    print(
        "Finished:",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    print(f"Runtime: {elapsed}")
    print("=" * 70)


if __name__ == "__main__":
    main()
