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
            title_elem = item.find("ns:Title", namespaces)
            item_id_elem = item.find("ns:ItemID", namespaces)
            price_elem = item.find(".//ns:CurrentPrice", namespaces)
            quantity_elem = item.find(".//ns:Quantity", namespaces)

            title = title_elem.text if title_elem is not None else "N/A"
            item_id = item_id_elem.text if item_id_elem is not None else "N/A"
            price = price_elem.text if price_elem is not None else "N/A"
            quantity = quantity_elem.text if quantity_elem is not None else "N/A"

            item_data = {
                "ItemID": item_id,
                "Title": title,
                "Price": price,
                "Quantity": quantity,
                "Variations": []
            }

            # Parse variations
            variations_block = item.find("ns:Variations", namespaces)
            if variations_block is not None:
                variations = variations_block.findall("ns:Variation", namespaces)
                for variation in variations:
                    variation_price_elem = variation.find("ns:StartPrice", namespaces)
                    variation_quantity_elem = variation.find("ns:Quantity", namespaces)
                    variation_title_elem = variation.find("ns:VariationTitle", namespaces)

                    variation_data = {
                        "Price": variation_price_elem.text if variation_price_elem is not None else "N/A",
                        "Quantity": variation_quantity_elem.text if variation_quantity_elem is not None else "N/A",
                        "Title": variation_title_elem.text if variation_title_elem is not None else "N/A",
                        "Specifics": []
                    }

                    # Parse specifics
                    specifics = variation.findall(".//ns:NameValueList", namespaces)
                    for specific in specifics:
                        name_elem = specific.find("ns:Name", namespaces)
                        value_elem = specific.find("ns:Value", namespaces)

                        name = name_elem.text if name_elem is not None else "N/A"
                        value = value_elem.text if value_elem is not None else "N/A"

                        variation_data["Specifics"].append({name: value})

                    item_data["Variations"].append(variation_data)  # Append variation

            items.append(item_data)

        return jsonify(items)
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    return render_template("listings.html")


if __name__ == "__main__":
    app.run(debug=True)
