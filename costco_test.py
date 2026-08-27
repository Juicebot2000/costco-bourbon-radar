import requests
import re
import time
from datetime import datetime


# ================================================================
# COSTCO BOURBON RADAR - SEARCH ENGINE V5
# ================================================================
#
# IMPORTANT:
# This file intentionally contains NO Markdown backticks.
#
# V5 goals:
#   - Establish a Costco web session first
#   - Use browser-like headers
#   - Handle Costco 401 credential rotation cleanly
#   - Search all target bottles
#   - Strict target matching
#   - Reject false positives
#   - Deduplicate results
#   - Report warehouse inventory and price
#
# ================================================================


WAREHOUSE_ID = "471-wh"
ZIP_CODE = "95765"

SEARCH_URL = (
    "https://gdx-api.costco.com/catalog/search/api/v1/search"
)

COSTCO_HOME = "https://www.costco.com/"

# Costco has changed client identifiers over time.
#
# USBC was the identifier that worked in the earlier tests.
# The newer identifier below has been publicly observed in
# current Costco catalog clients.
#
# The script will try these in order.
CLIENT_IDENTIFIERS = [
    "USBC",
    "168287ea-1201-45f6-9b45-5bbea49f8ee7",
]


# ================================================================
# HEADERS
# ================================================================

BASE_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://www.costco.com",
    "referer": "https://www.costco.com/",
    "sec-ch-ua": (
        '"Chromium";v="149", '
        '"Google Chrome";v="149", '
        '"Not=A?Brand";v="99"'
    ),
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
}


# ================================================================
# TARGET BOURBONS
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
    ],

    "Weller Full Proof": [
        "weller full proof",
        "weller fullproof",
    ],

    "Weller Antique 107": [
        "weller antique 107",
        "weller 107",
        "weller antique 107 proof",
    ],

    "Eagle Rare 10 Year": [
        "eagle rare",
        "eagle rare 10",
        "eagle rare 10 year",
        "eagle rare 10 year old",
    ],

    "Blanton's": [
        "blanton's",
        "blantons",
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


# ================================================================
# SEARCH QUERIES
# ================================================================

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
# SESSION
# ================================================================

session = requests.Session()

session.headers.update(BASE_HEADERS)


# ================================================================
# NORMALIZATION
# ================================================================

def normalize_text(value):

    if value is None:
        return ""

    value = str(value).lower()

    value = value.replace("’", "'")

    value = re.sub(r"[^a-z0-9]+", " ", value)

    value = re.sub(r"\s+", " ", value).strip()

    return value


# ================================================================
# BRAND
# ================================================================

def get_brand(product):

    brand = product.get("brand", "")

    if isinstance(brand, list):
        return " ".join(str(x) for x in brand)

    return str(brand or "")


# ================================================================
# TITLE
# ================================================================

def get_title(product):

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


# ================================================================
# PRODUCT ID
# ================================================================

def get_product_id(product):

    for field in [
        "productId",
        "productID",
        "product_id",
        "itemNumber",
        "item_number",
        "id",
    ]:

        value = product.get(field)

        if value:
            return str(value)

    return ""


# ================================================================
# VARIANT ID
# ================================================================

def get_variant_id(product):

    for field in [
        "variantId",
        "variantID",
        "variant_id",
    ]:

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

    # ------------------------------------------------------------
    # Direct fields
    # ------------------------------------------------------------

    for field in [
        "warehouseAvailability",
        "warehouse_availability",
        "availability",
        "inventoryStatus",
        "inventory_status",
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
                or item.get("warehouseCode")
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
                or variant.get("warehouseCode")
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
# COSTCO URL
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
# NON-BOURBON FILTER
# ================================================================

def is_obvious_non_bourbon(title, brand):

    text = normalize_text(
        f"{title} {brand}"
    )

    reject_terms = [

        "paper towel",
        "paper towels",
        "facial tissue",
        "energy drink",
        "sparkling water",
        "beef stick",
        "caviar",
        "honey caviar",
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

        "gift card",
        "egift card",
        "restaurant",
        "hotel",
    ]

    for term in reject_terms:

        if term in text:
            return True

    return False


# ================================================================
# STRICT TARGET MATCHING
# ================================================================

def target_match_score(target_name, title, brand):

    title_norm = normalize_text(title)
    brand_norm = normalize_text(brand)

    combined = (
        f"{title_norm} {brand_norm}"
    ).strip()

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

        # --------------------------------------------------------
        # Alias must appear as a phrase.
        # --------------------------------------------------------

        if alias_norm in combined:

            score = 100

            # Product title is stronger than brand field.
            if alias_norm in title_norm:
                score += 20

            if score > best_score:

                best_score = score
                best_alias = alias

    return best_score, best_alias


# ================================================================
# CLASSIFY
# ================================================================

def classify_product(target_name, product):

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

    if score >= 100:

        return (
            "CONFIRMED",
            score,
            alias,
            "Exact target expression found"
        )

    if score >= 60:

        return (
            "REVIEW",
            score,
            alias,
            "Possible target match"
        )

    return (
        "REJECTED",
        score,
        alias,
        "Target expression not found"
    )


# ================================================================
# OPEN COSTCO FIRST
# ================================================================

def establish_costco_session():

    print()
    print("=" * 70)
    print("ESTABLISHING COSTCO WEB SESSION")
    print("=" * 70)

    try:

        response = session.get(
            COSTCO_HOME,
            timeout=30,
        )

        print(
            f"Costco homepage HTTP: "
            f"{response.status_code}"
        )

        print(
            f"Session cookies: "
            f"{len(session.cookies)}"
        )

        return response.status_code == 200

    except Exception as e:

        print(
            f"Costco homepage request failed: {e}"
        )

        return False


# ================================================================
# SEARCH COSTCO
# ================================================================

def search_costco(query, client_identifier):

    payload = {

        "visitorId": (
            "bourbon-radar-v5-"
            + str(int(time.time()))
        ),

        "query": query,

        "pageSize": 24,

        "offset": 0,

        "warehouseId": WAREHOUSE_ID,

        "shipToPostal": ZIP_CODE,

        "shipToState": "CA",
    }

    headers = dict(BASE_HEADERS)

    headers["client_id"] = client_identifier

    try:

        response = session.post(

            SEARCH_URL,

            headers=headers,

            json=payload,

            timeout=30,
        )

        return response

    except Exception as e:

        print(
            f"REQUEST ERROR: {e}"
        )

        return None


# ================================================================
# EXTRACT PRODUCTS
# ================================================================

def extract_products(data):

    if not isinstance(data, dict):
        return []

    # ------------------------------------------------------------
    # Direct structures
    # ------------------------------------------------------------

    for key in [
        "products",
        "results",
        "items",
    ]:

        products = data.get(key)

        if isinstance(products, list):
            return products

    # ------------------------------------------------------------
    # searchResults
    # ------------------------------------------------------------

    search_results = data.get(
        "searchResults"
    )

    if isinstance(search_results, dict):

        for key in [
            "products",
            "items",
            "results",
        ]:

            products = search_results.get(key)

            if isinstance(products, list):
                return products

    # ------------------------------------------------------------
    # searchResult
    # ------------------------------------------------------------

    search_result = data.get(
        "searchResult"
    )

    if isinstance(search_result, dict):

        for key in [
            "products",
            "items",
            "results",
        ]:

            products = search_result.get(key)

            if isinstance(products, list):
                return products

    # ------------------------------------------------------------
    # provider response
    # ------------------------------------------------------------

    provider = data.get(
        "searchResultProvider"
    )

    if isinstance(provider, dict):

        for key in [
            "products",
            "items",
            "results",
        ]:

            products = provider.get(key)

            if isinstance(products, list):
                return products

    # ------------------------------------------------------------
    # Recursive fallback
    #
    # Costco occasionally changes nesting.
    # ------------------------------------------------------------

    def find_product_list(obj):

        if isinstance(obj, dict):

            for key, value in obj.items():

                if key.lower() in [
                    "products",
                    "items",
                    "results",
                ]:

                    if isinstance(value, list):

                        if all(
                            isinstance(x, dict)
                            for x in value
                        ):

                            return value

                found = find_product_list(value)

                if found:
                    return found

        elif isinstance(obj, list):

            for item in obj:

                found = find_product_list(item)

                if found:
                    return found

        return []

    return find_product_list(data)


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

    product_id = get_product_id(product)
    variant_id = get_variant_id(product)

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
        f"Warehouse availability: "
        f"{inventory}"
    )

    print(
        f"Warehouse price: {price}"
    )

    if url:

        print(
            f"URL: {url}"
        )


# ================================================================
# DIAGNOSTIC 401
# ================================================================

def print_401_diagnostic(response):

    print()
    print("!" * 70)
    print("COSTCO API RETURNED HTTP 401")
    print("!" * 70)

    print()
    print(
        "Costco's API gateway rejected the request "
        "before product search."
    )

    print()
    print(
        "This usually means the Costco storefront "
        "client identifier/request headers have changed."
    )

    print()
    print("Response:")

    try:

        data = response.json()

        print(
            data
        )

    except Exception:

        print(
            response.text[:2000]
        )

    print()
    print(
        "The script will NOT treat this as "
        "'zero bourbon inventory'."
    )

    print(
        "A 401 means the search could not be performed."
    )

    print("!" * 70)


# ================================================================
# MAIN
# ================================================================

def main():

    start_time = datetime.now()

    print("=" * 70)
    print(
        "COSTCO BOURBON RADAR - "
        "SEARCH ENGINE V5"
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
    # Establish browser-like Costco session
    # ------------------------------------------------------------

    establish_costco_session()

    # ------------------------------------------------------------
    # Results
    # ------------------------------------------------------------

    confirmed_products = {}
    review_products = {}

    total_results = 0

    rejected_count = 0

    successful_searches = 0

    failed_searches = 0

    credentials_working = None

    active_client_identifier = None

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

        response = None

        # --------------------------------------------------------
        # Try current client identifier first.
        # If Costco says 401, try the next one.
        # --------------------------------------------------------

        identifiers_to_try = []

        if active_client_identifier:

            identifiers_to_try.append(
                active_client_identifier
            )

        for identifier in CLIENT_IDENTIFIERS:

            if identifier not in identifiers_to_try:

                identifiers_to_try.append(
                    identifier
                )

        for client_identifier in identifiers_to_try:

            response = search_costco(
                query,
                client_identifier
            )

            if response is None:
                continue

            print(
                f"Client identifier: "
                f"{client_identifier}"
            )

            print(
                f"HTTP: "
                f"{response.status_code}"
            )

            if response.status_code == 200:

                active_client_identifier = (
                    client_identifier
                )

                credentials_working = True

                break

            if response.status_code == 401:

                continue

            break

        # --------------------------------------------------------
        # No response
        # --------------------------------------------------------

        if response is None:

            failed_searches += 1

            print(
                "REQUEST FAILED."
            )

            continue

        # --------------------------------------------------------
        # 401
        # --------------------------------------------------------

        if response.status_code == 401:

            failed_searches += 1

            credentials_working = False

            print_401_diagnostic(
                response
            )

            # Stop here rather than making 20 identical
            # unauthorized requests.

            print()
            print(
                "STOPPING SEARCH."
            )

            print(
                "There is no value in sending the "
                "remaining queries until the Costco "
                "credential/header issue is resolved."
            )

            break

        # --------------------------------------------------------
        # Other HTTP error
        # --------------------------------------------------------

        if response.status_code != 200:

            failed_searches += 1

            print(
                "Costco API request failed."
            )

            try:

                print(
                    response.text[:2000]
                )

            except Exception:

                pass

            continue

        # --------------------------------------------------------
        # Parse JSON
        # --------------------------------------------------------

        try:

            data = response.json()

        except Exception:

            failed_searches += 1

            print(
                "Unable to decode Costco JSON response."
            )

            continue

        # --------------------------------------------------------
        # Extract products
        # --------------------------------------------------------

        products = extract_products(
            data
        )

        print(
            f"Results returned: "
            f"{len(products)}"
        )

        total_results += len(products)

        successful_searches += 1

        if not products:

            print(
                "No Costco products returned."
            )

            continue

        # --------------------------------------------------------
        # Match products
        # --------------------------------------------------------

        query_confirmed = 0
        query_review = 0

        seen_this_query = set()

        for product in products:

            if not isinstance(product, dict):
                continue

            product_id = get_product_id(
                product
            )

            variant_id = get_variant_id(
                product
            )

            # ----------------------------------------------------
            # Prevent duplicate product processing
            # ----------------------------------------------------

            product_key = (
                f"{product_id}|"
                f"{variant_id}|"
                f"{get_title(product)}"
            )

            if product_key in seen_this_query:
                continue

            seen_this_query.add(
                product_key
            )

            # ----------------------------------------------------
            # Test against every target
            # ----------------------------------------------------

            for target_name in TARGETS:

                (
                    status,
                    score,
                    alias,
                    reason,
                ) = classify_product(
                    target_name,
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

            print(
                f"Confirmed matches: "
                f"{query_confirmed}"
            )

        elif query_review:

            print(
                f"Potential review matches: "
                f"{query_review}"
            )

        else:

            print(
                "No target bourbon matches found."
            )

        # --------------------------------------------------------
        # Small delay
        # --------------------------------------------------------

        time.sleep(0.25)

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

    print(
        f"Rejected/irrelevant results: "
        f"{rejected_count}"
    )

    # ------------------------------------------------------------
    # CONFIRMED
    # ------------------------------------------------------------

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
    # REVIEW
    # ------------------------------------------------------------

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
    # Credential status
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "API STATUS"
    )
    print("=" * 70)

    if credentials_working is True:

        print(
            "Costco API credentials: WORKING"
        )

        print(
            f"Active client identifier: "
            f"{active_client_identifier}"
        )

    elif credentials_working is False:

        print(
            "Costco API credentials: REJECTED"
        )

        print(
            "The search did not complete."
        )

    else:

        print(
            "Costco API credentials: "
            "NOT TESTED"
        )

    # ------------------------------------------------------------
    # Finish
    # ------------------------------------------------------------

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


if __name__ == "__main__":
    main()
