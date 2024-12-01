from flask import Flask, jsonify, render_template, request
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import os

app = Flask(__name__)

# Global eBay API Variables
auth_token = os.getenv("AUTH_TOKEN")  # Load the auth token from .env
ebay_api_url = "https://api.ebay.com/ws/api.dll"
headers = {
    "X-EBAY-API-SITEID": "0",
    "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
    "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
    "X-EBAY-API-IAF-TOKEN": auth_token,
    "Content-Type": "text/xml",
}

@app.route("/api/ebay-listings")
def fetch_all_listings():
    page_number = int(request.args.get("page", 1))
    entries_per_page = int(request.args.get("entriesPerPage", 200))
    items = []

    if not auth_token:
        return jsonify({"error": "Missing eBay auth token"}), 400

    body = f"""<?xml version="1.0" encoding="utf-8"?>
    <GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <RequesterCredentials>
            <eBayAuthToken>{auth_token}</eBayAuthToken>
        </RequesterCredentials>
        <ActiveList>
            <Pagination>
                <EntriesPerPage>{entries_per_page}</EntriesPerPage>
                <PageNumber>{page_number}</PageNumber>
            </Pagination>
        </ActiveList>
    </GetMyeBaySellingRequest>"""

    try:
        response = requests.post(ebay_api_url, data=body, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return jsonify({"error": f"eBay API returned status {response.status_code}"}), response.status_code

        root = ET.fromstring(response.text)
        namespaces = {"ns": "urn:ebay:apis:eBLBaseComponents"}

        for item in root.findall(".//ns:Item", namespaces):
            item_id = item.find("ns:ItemID", namespaces)
            item_id = item_id.text if item_id is not None else "N/A"

            title = item.find("ns:Title", namespaces)
            title = title.text if title is not None else "N/A"

            price = item.find(".//ns:CurrentPrice", namespaces)
            price = price.text if price is not None else "N/A"

            quantity = item.find(".//ns:Quantity", namespaces)
            quantity = quantity.text if quantity is not None else "N/A"

            items.append({"ItemID": item_id, "Title": title, "Price": price, "Quantity": quantity})

        return jsonify(items)
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
