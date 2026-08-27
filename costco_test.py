import json
import re
import time
from datetime import datetime
from urllib.parse import quote

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# ================================================================
# COSTCO BOURBON RADAR - SEARCH ENGINE V6
# Browser Network Capture Edition
# ================================================================

WAREHOUSE_ID = "471-wh"
ZIP_CODE = "95765"

COSTCO_HOME = "https://www.costco.com/"
COSTCO_SEARCH = "https://www.costco.com/s?keyword={}"

# ----------------------------------------------------------------
# TARGET BOURBONS
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

SEARCH_QUERIES = [
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


# ================================================================
# TEXT HELPERS
# ================================================================

def normalize_text(value):
    if value is None:
        return ""

    value = str(value).lower()
    value = value.replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def get_brand(product):
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
# INVENTORY
# ================================================================

def extract_inventory(product):
    inventory = None
    price = None

    direct_inventory_fields = [
        "warehouseAvailability",
        "warehouse_availability",
        "availability",
        "inventoryStatus",
        "inventory",
    ]

    direct_price_fields = [
        "warehousePrice",
        "warehouse_price",
        "price",
    ]

    for field in direct_inventory_fields:
        if product.get(field) is not None:
            inventory = product.get(field)
            break

    for field in direct_price_fields:
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
                    or variant.get("status")
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
# FALSE POSITIVE FILTER
# ================================================================

def is_obvious_non_bourbon(title, brand):
    text = normalize_text(
        f"{title} {brand}"
    )

    reject_terms = [
        "paper towel",
        "facial tissue",
        "energy drink",
        "sparkling water",
        "beef stick",
        "caviar",
        "honey caviar",
        "wine decanter",
        "chardonnay",
        "cabernet",
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


# ================================================================
# TARGET MATCHING
# ================================================================

def target_match_score(target_name, title, brand):

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
        # Exact target phrase
        # --------------------------------------------------------

        if alias_norm in combined:

            score = 100

            # Product title match is stronger than brand-only match.
            if alias_norm in title_norm:
                score += 20

            if score > best_score:
                best_score = score
                best_alias = alias

    return best_score, best_alias


def classify_product(target_name, product):

    title = get_title(product)
    brand = get_brand(product)

    if not title:
        return "REJECTED", 0, None, "No product title"

    if is_obvious_non_bourbon(title, brand):
        return (
            "REJECTED",
            0,
            None,
            "Obvious non-bourbon product",
        )

    score, alias = target_match_score(
        target_name,
        title,
        brand,
    )

    if score >= 100:
        return (
            "CONFIRMED",
            score,
            alias,
            "Target expression found",
        )

    if score >= 60:
        return (
            "REVIEW",
            score,
            alias,
            "Possible target match",
        )

    return (
        "REJECTED",
        score,
        alias,
        "Target expression not found",
    )


# ================================================================
# JSON PRODUCT EXTRACTION
# ================================================================

def recursively_find_product_lists(obj, found=None):
    """
    Costco has changed its JSON structure several times.

    This recursively searches the response for lists that appear
    to contain product dictionaries.
    """

    if found is None:
        found = []

    if isinstance(obj, dict):

        # Common product-list keys.
        for key in [
            "products",
            "items",
            "results",
            "productResults",
            "searchResults",
            "searchResult",
        ]:

            value = obj.get(key)

            if isinstance(value, list):

                product_count = 0

                for item in value:

                    if isinstance(item, dict):

                        if any(
                            key_name in item
                            for key_name in [
                                "productId",
                                "productID",
                                "productName",
                                "title",
                                "name",
                                "variantId",
                            ]
                        ):
                            product_count += 1

                if product_count > 0:

                    for item in value:

                        if isinstance(item, dict):
                            found.append(item)

        for value in obj.values():
            recursively_find_product_lists(
                value,
                found,
            )

    elif isinstance(obj, list):

        for item in obj:
            recursively_find_product_lists(
                item,
                found,
            )

    return found


def extract_products(data):

    products = recursively_find_product_lists(data)

    # ------------------------------------------------------------
    # Deduplicate
    # ------------------------------------------------------------

    unique = {}

    for product in products:

        product_id = get_product_id(product)
        variant_id = get_variant_id(product)

        key = (
            product_id,
            variant_id,
            get_title(product),
        )

        if key not in unique:
            unique[key] = product

    return list(unique.values())


# ================================================================
# PRINT PRODUCT
# ================================================================

def print_product(
    target_name,
    product,
    status,
    score,
    alias,
    reason,
):

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
# BROWSER SEARCH
# ================================================================

def perform_browser_search(page, query):

    encoded_query = quote(query)

    search_url = COSTCO_SEARCH.format(
        encoded_query
    )

    captured_responses = []

    # ------------------------------------------------------------
    # Capture Costco search API responses.
    # ------------------------------------------------------------

    def handle_response(response):

        url = response.url.lower()

        # Look for Costco catalog/search traffic.
        if (
            "catalog/search" in url
            or "/search/api/" in url
            or "searchresult" in url
        ):

            try:

                content_type = (
                    response.headers.get(
                        "content-type",
                        ""
                    ).lower()
                )

                if "json" in content_type:

                    data = response.json()

                    captured_responses.append({
                        "url": response.url,
                        "status": response.status,
                        "data": data,
                    })

            except Exception:
                pass

    page.on(
        "response",
        handle_response,
    )

    try:

        # --------------------------------------------------------
        # Navigate to actual Costco search page.
        # --------------------------------------------------------

        page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        # Give Costco's JavaScript time to make API requests.
        page.wait_for_timeout(7000)

    except PlaywrightTimeoutError:

        print(
            "Browser navigation timed out."
        )

    except Exception as e:

        print(
            f"Browser navigation error: {e}"
        )

    finally:

        try:
            page.remove_listener(
                "response",
                handle_response,
            )
        except Exception:
            pass

    # ------------------------------------------------------------
    # Select the best captured response.
    # ------------------------------------------------------------

    if not captured_responses:
        return None

    successful = [
        item
        for item in captured_responses
        if item["status"] == 200
    ]

    if successful:

        # Prefer responses containing actual products.
        for item in successful:

            products = extract_products(
                item["data"]
            )

            if products:
                return item

        return successful[0]

    return captured_responses[0]


# ================================================================
# MAIN
# ================================================================

def main():

    start_time = datetime.now()

    print("=" * 70)
    print("COSTCO BOURBON RADAR - SEARCH ENGINE V6")
    print("BROWSER NETWORK CAPTURE")
    print("=" * 70)

    print(f"Warehouse: {WAREHOUSE_ID}")
    print(f"ZIP: {ZIP_CODE}")
    print(
        f"Started: "
        f"{start_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print("=" * 70)

    confirmed_products = {}
    review_products = {}

    total_results = 0
    successful_searches = 0
    failed_searches = 0

    # ============================================================
    # START PLAYWRIGHT
    # ============================================================

    with sync_playwright() as p:

        print()
        print("=" * 70)
        print("STARTING CHROMIUM")
        print("=" * 70)

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/Los_Angeles",
            viewport={
                "width": 1440,
                "height": 900,
            },
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        page = context.new_page()

        # --------------------------------------------------------
        # Costco homepage
        # --------------------------------------------------------

        print()
        print("=" * 70)
        print("ESTABLISHING COSTCO WEB SESSION")
        print("=" * 70)

        try:

            homepage_response = page.goto(
                COSTCO_HOME,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            if homepage_response:

                print(
                    "Costco homepage HTTP:",
                    homepage_response.status,
                )

            else:

                print(
                    "Costco homepage response unavailable."
                )

        except Exception as e:

            print(
                f"Costco homepage error: {e}"
            )

        # --------------------------------------------------------
        # Cookies
        # --------------------------------------------------------

        try:

            cookies = context.cookies()

            print(
                f"Browser cookies established: "
                f"{len(cookies)}"
            )

        except Exception:

            print(
                "Unable to read browser cookies."
            )

        # --------------------------------------------------------
        # Search every query
        # --------------------------------------------------------

        for query in SEARCH_QUERIES:

            print()
            print("=" * 70)
            print(f"SEARCH: {query}")
            print("=" * 70)

            result = perform_browser_search(
                page,
                query,
            )

            if result is None:

                print(
                    "NO COSTCO SEARCH API RESPONSE CAPTURED."
                )

                failed_searches += 1

                continue

            status_code = result["status"]

            print(
                f"Captured Costco search HTTP: "
                f"{status_code}"
            )

            if status_code != 200:

                print()
                print("!" * 70)
                print(
                    "COSTCO SEARCH REQUEST FAILED"
                )
                print("!" * 70)

                print(
                    "The browser captured a Costco search "
                    "request, but Costco did not return HTTP 200."
                )

                print()
                print(
                    "Request URL:"
                )

                print(
                    result["url"]
                )

                print()
                print(
                    "HTTP:",
                    status_code,
                )

                failed_searches += 1

                continue

            products = extract_products(
                result["data"]
            )

            print(
                f"Products extracted: "
                f"{len(products)}"
            )

            total_results += len(products)
            successful_searches += 1

            if not products:

                print(
                    "Search response contained no "
                    "recognizable Costco products."
                )

                continue

            # ----------------------------------------------------
            # Match products against all targets
            # ----------------------------------------------------

            query_confirmed = 0
            query_review = 0

            for product in products:

                if not isinstance(product, dict):
                    continue

                for target_name in TARGETS:

                    (
                        classification,
                        score,
                        alias,
                        reason,
                    ) = classify_product(
                        target_name,
                        product,
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
                        f"{variant_id}|"
                        f"{get_title(product)}"
                    )

                    # ------------------------------------------------
                    # CONFIRMED
                    # ------------------------------------------------

                    if classification == "CONFIRMED":

                        query_confirmed += 1

                        if (
                            unique_id
                            not in confirmed_products
                        ):

                            confirmed_products[
                                unique_id
                            ] = {
                                "target": target_name,
                                "product": product,
                                "score": score,
                                "alias": alias,
                                "reason": reason,
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

                    elif classification == "REVIEW":

                        query_review += 1

                        if (
                            unique_id
                            not in review_products
                        ):

                            review_products[
                                unique_id
                            ] = {
                                "target": target_name,
                                "product": product,
                                "score": score,
                                "alias": alias,
                                "reason": reason,
                            }

            if query_confirmed:

                print()
                print(
                    f"Confirmed target matches in "
                    f"this search: {query_confirmed}"
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

            # ----------------------------------------------------
            # Small delay between searches
            # ----------------------------------------------------

            time.sleep(1.5)

        # --------------------------------------------------------
        # Close browser
        # --------------------------------------------------------

        browser.close()

    # ============================================================
    # FINAL REPORT
    # ============================================================

    print()
    print("=" * 70)
    print("COSTCO BOURBON RADAR COMPLETE")
    print("=" * 70)

    print(
        f"Successful searches: "
        f"{successful_searches}"
    )

    print(
        f"Failed searches: "
        f"{failed_searches}"
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

    # ============================================================
    # CONFIRMED
    # ============================================================

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

    # ============================================================
    # REVIEW
    # ============================================================

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

    # ============================================================
    # API STATUS
    # ============================================================

    print()
    print("=" * 70)
    print("API / BROWSER STATUS")
    print("=" * 70)

    if successful_searches > 0:

        print(
            "Costco browser search: WORKING"
        )

        print(
            "The script successfully captured "
            "Costco's browser-generated search response."
        )

    elif failed_searches > 0:

        print(
            "Costco browser search: FAILED"
        )

        print(
            "No successful Costco search responses "
            "were captured."
        )

    else:

        print(
            "Costco browser search: UNKNOWN"
        )

    # ============================================================
    # FINISH
    # ============================================================

    elapsed = datetime.now() - start_time

    print()
    print("=" * 70)

    print(
        "Finished:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    )

    print(
        f"Runtime: {elapsed}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()
