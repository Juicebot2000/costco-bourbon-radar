import json
from playwright.sync_api import sync_playwright

ITEM_NUMBER = "1605257"

print("=" * 70)
print("COSTCO BOURBON RADAR - API TRANSPORT TEST")
print("=" * 70)
print(f"Testing item: {ITEM_NUMBER}")
print()

with sync_playwright() as p:
    request = p.request.new_context(
        extra_http_headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/139.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )

    try:
        # Costco product GraphQL endpoint
        url = "https://ecom-api.costco.com/graphql"

        query = """
        query Product($itemNumbers: [String!]!) {
          products(itemNumbers: $itemNumbers) {
            itemNumber
            name
            price
          }
        }
        """

        payload = {
            "query": query,
            "variables": {
                "itemNumbers": [ITEM_NUMBER]
            }
        }

        print("Requesting Costco product data...")
        print("Endpoint:", url)
        print()

        response = request.post(
            url,
            data=json.dumps(payload),
            timeout=60000
        )

        print("HTTP status:", response.status)
        print("Response length:", len(response.text()))
        print()

        body = response.text()

        if body:
            try:
                data = json.loads(body)
                print("RESPONSE:")
                print(json.dumps(data, indent=2)[:15000])
            except Exception:
                print("RAW RESPONSE:")
                print(body[:15000])
        else:
            print("EMPTY RESPONSE")

    except Exception as e:
        print("ERROR:")
        print(repr(e))

    finally:
        request.dispose()

print()
print("=" * 70)
print("API TRANSPORT TEST COMPLETE")
print("=" * 70)
