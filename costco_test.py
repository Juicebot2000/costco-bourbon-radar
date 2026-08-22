import requests
import json

ITEM_NUMBER = "1605257"  # Jack Daniel's 10 Year

url = "https://www.costco.com/"

print("Costco Bourbon Radar")
print("====================")
print(f"Testing Costco item: {ITEM_NUMBER}")
print()
print("Next step: connect Costco's warehouse inventory endpoint.")
print("The item number has been identified; we are NOT assuming")
print("inventory is available until Costco confirms it.")
