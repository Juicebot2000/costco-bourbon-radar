import requests

ITEM_NUMBER = "1605257"
WAREHOUSE = "464"

print("=" * 60)
print("COSTCO BOURBON RADAR - API TEST")
print("=" * 60)
print(f"Item: {ITEM_NUMBER}")
print(f"Warehouse: {WAREHOUSE}")
print()

# Current Costco API endpoint documented by the
# open-source Costco integration we're testing against.
url = "https://gdx-api.costco.com/"

params = {
    "itemNumber": ITEM_NUMBER,
    "warehouseNumber": WAREHOUSE,
}

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/139.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://www.costco.com",
    "Referer": "https://www.costco.com/",
}

try:
    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=30
    )

    print("URL requested:")
    print(response.url)
    print()
    print("HTTP status:", response.status_code)
    print("Response length:", len(response.text))
    print()

    if response.text:
        print("Response:")
        print(response.text[:5000])
    else:
        print("EMPTY RESPONSE")

except Exception as e:
    print("REQUEST ERROR:", repr(e))

print()
print("API TEST COMPLETE")
