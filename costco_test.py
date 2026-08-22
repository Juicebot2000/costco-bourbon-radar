import json
from playwright.sync_api import sync_playwright

ITEM_NUMBER = "1605257"

print("=" * 70)
print("COSTCO BOURBON RADAR - PLAYWRIGHT TEST")
print("=" * 70)
print(f"Testing Costco item: {ITEM_NUMBER}")
print()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        )
    )

    page = context.new_page()

    try:
        print("Opening Costco...")
        response = page.goto(
            "https://www.costco.com/",
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("Costco page status:", response.status if response else "NO RESPONSE")
        print("Page title:", page.title())
        print()

        # Test Costco's product GraphQL service through the browser context.
        api_url = "https://ecom-api.costco.com/graphql"

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

        print("Testing Costco product API...")
        print("Endpoint:", api_url)
        print()

        api_response = page.request.post(
            api_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=60000
        )

        print("API HTTP status:", api_response.status)
        print("API response length:", len(api_response.text()))
        print()

        body = api_response.text()

        if body:
            try:
                data = json.loads(body)
                print("API RESPONSE:")
                print(json.dumps(data, indent=2)[:15000])
            except Exception:
                print("RAW RESPONSE:")
                print(body[:15000])
        else:
            print("EMPTY API RESPONSE")

    except Exception as e:
        print("ERROR:")
        print(repr(e))

    finally:
        browser.close()

print()
print("=" * 70)
print("PLAYWRIGHT TEST COMPLETE")
print("=" * 70)
