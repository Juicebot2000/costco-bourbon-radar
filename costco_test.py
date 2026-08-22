import requests
import json

# Costco item numbers we're testing
ITEMS = {
    "Jack Daniel's 10 Year - SKU 1605257": "1605257",
    "Jack Daniel's 10 Year - SKU 1740448": "1740448",
}

# Sacramento Costco
WAREHOUSE = "464"

print("=" * 60)
print("COSTCO BOURBON RADAR - LIVE TEST")
print("=" * 60)
print(f"Warehouse: Costco #{WAREHOUSE}")
print()

# Costco's public search endpoint
url = "https://gdx-api.costco.com/"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

for name, item_number in ITEMS.items():

    print(f"Testing: {name}")
    print(f"Item number: {item_number}")

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        print(f"HTTP status: {response.status_code}")
        print(f"Response length: {len(response.text)}")

        if response.text:
            print("Response preview:")
            print(response.text[:500])

    except Exception as e:
        print(f"ERROR: {e}")

    print("-" * 60)

print()
print("LIVE COSTCO CONNECTION TEST COMPLETE")
