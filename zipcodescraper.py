import requests
from bs4 import BeautifulSoup
import json
import pymongo
from pymongo import MongoClient, errors
import os
import sys
import logging
import re

# ------------------ Setup Logging ------------------ #
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("zipcode_scraper.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# ------------------ Constants & Config ------------------ #
BASE_URL = "https://www.unitedstateszipcodes.org/pa/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
              "image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Referer": "https://www.google.com/"
}
OUTPUT_DIR = "output"  # Directory to save JSON files

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------ MongoDB Setup ------------------ #
def get_mongo_client(uri="mongodb://localhost:27017/"):
    try:
        client = MongoClient(uri)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        logging.info("Connected to MongoDB successfully.")
        return client
    except errors.ConnectionFailure as e:
        logging.error(f"Could not connect to MongoDB: {e}")
        sys.exit(1)

# ------------------ Helper Functions ------------------ #
def fetch_page(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        logging.info(f"Successfully fetched the page: {url}")
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching the page: {e}")
        sys.exit(1)

def parse_zipcodes(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract the state name
    state_header = soup.find("h1")
    if state_header:
        # Example: "Georgia ZIP Codes"
        state_text = state_header.get_text(strip=True)
        match = re.match(r"^(.*?)\s+ZIP Codes$", state_text, re.IGNORECASE)
        if match:
            state_name = match.group(1).strip()
            logging.info(f"Extracted state name: {state_name}")
        else:
            logging.error("Failed to parse state name from header.")
            sys.exit(1)
    else:
        logging.error("Failed to extract the state name from the page.")
        sys.exit(1)

    # Find all panels containing the zip code data
    panels = soup.find_all("div", {"class": "panel panel-default panel-prefixes"})
    if not panels:
        logging.error("Failed to find the zip code data panels on the page.")
        sys.exit(1)

    # Collect data from all panels
    zip_data = []
    for panel in panels:
        list_items = panel.find_all("div", {"class": "list-group-item"})
        if not list_items:
            logging.warning("No zip code entries found in a panel.")
            continue

        for item in list_items:
            row = {}
            for field, class_name in [
                ("Zip Code", "prefix-col1"),
                ("Type", "prefix-col2"),
                ("Common Cities", "prefix-col3"),
                ("County", "prefix-col4"),
                ("Area Codes", "prefix-col5")
            ]:
                element = item.find("div", {"class": class_name})
                if element:
                    row[field] = element.get_text(strip=True)
                else:
                    row[field] = "N/A"
                    logging.warning(f"Missing '{field}' in a zip code entry.")
            zip_data.append(row)

    logging.info(f"Extracted {len(zip_data)} zip code records.")
    return state_name, zip_data

def transform_zip_data(state_name, zip_data):
    """
    Transform the scraped zip data into the desired MongoDB document format.
    """
    transformed_data = []
    for entry in zip_data:
        try:
            postcode = int(entry["Zip Code"])
        except ValueError:
            logging.warning(f"Invalid Zip Code format: {entry['Zip Code']}. Skipping entry.")
            continue  # Skip entries with invalid zip codes

        # Extract all three-digit area codes using regex
        area_codes_raw = entry["Area Codes"]
        if area_codes_raw != "N/A":
            # Find all three-digit numbers
            area_codes = re.findall(r'\b\d{3}\b', area_codes_raw)
            # Convert to integers and remove duplicates
            area_codes = sorted(list(set(int(code) for code in area_codes if 200 <= int(code) <= 999)))
            areacode = ", ".join(map(str, area_codes)) if area_codes else "N/A"
        else:
            areacode = "N/A"

        transformed_entry = {
            "postcode": postcode,
            "scrapedsuccessfully": False,
            "processing": False,
            "totalrecordsfound": 0,
            "totaluniquerecordsfound": 0,
            "didresultsloadcompletely": False,
            "state": state_name,
            "recordsfoundwithemail": 0,
            "commoncities": entry["Common Cities"],
            "county": entry["County"],
            "areacode": areacode
        }
        transformed_data.append(transformed_entry)
    logging.info(f"Transformed data into {len(transformed_data)} MongoDB documents.")
    return transformed_data

def save_to_json(state_name, transformed_data):
    output_file = os.path.join(OUTPUT_DIR, f"{state_name}_zipcodes.json")
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(transformed_data, file, ensure_ascii=False, indent=4)
        logging.info(f"Data has been saved to '{output_file}'")
    except IOError as e:
        logging.error(f"Failed to write data to JSON file: {e}")
        sys.exit(1)

def remove_duplicates(collection):
    """
    Remove duplicate documents based on the 'postcode' field.
    Keeps the first occurrence and removes the rest.
    """
    pipeline = [
        {"$group": {"_id": "$postcode", "count": {"$sum": 1}, "ids": {"$push": "$_id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    duplicates = list(collection.aggregate(pipeline))
    for doc in duplicates:
        # Keep the first occurrence and remove the rest
        ids_to_remove = doc["ids"][1:]
        collection.delete_many({"_id": {"$in": ids_to_remove}})
        logging.info(f"Removed {len(ids_to_remove)} duplicate entries for postcode {doc['_id']}.")

def save_to_mongodb(client, state_name, transformed_data):
    try:
        # Sanitize the state name for MongoDB database name (replace spaces with underscores)
        db_name = re.sub(r'\s+', '_', state_name)
        db = client[db_name]
        postalcodes_collection = db["postalcodes"]

        # Remove existing duplicates
        remove_duplicates(postalcodes_collection)

        # Ensure unique index on 'postcode'
        postalcodes_collection.create_index("postcode", unique=True)
        logging.info("Ensured unique index on 'postcode' in 'postalcodes' collection.")

        inserted_count = 0
        duplicate_count = 0

        for doc in transformed_data:
            try:
                result = postalcodes_collection.update_one(
                    {"postcode": doc["postcode"]},  # Filter
                    {"$set": doc},                   # Update
                    upsert=True                      # Insert if not exists
                )
                if result.upserted_id:
                    inserted_count += 1
                elif result.modified_count > 0:
                    # Document was updated
                    pass
            except errors.PyMongoError as e:
                logging.error(f"Error inserting/updating postcode {doc['postcode']}: {e}")

        logging.info(f"Upserted {inserted_count} new records into MongoDB.")
        logging.info("Script completed successfully.")
    except errors.PyMongoError as e:
        logging.error(f"MongoDB operation failed: {e}")
        sys.exit(1)

# ------------------ Main Function ------------------ #
def main():
    # Step 1: Fetch the webpage
    html_content = fetch_page(BASE_URL, HEADERS)

    # Step 2: Parse the zip codes and state name
    state_name, zip_data = parse_zipcodes(html_content)

    # Step 3: Transform the scraped data into desired format
    transformed_data = transform_zip_data(state_name, zip_data)

    # Step 4: Save the data to a JSON file
    save_to_json(state_name, transformed_data)

    # Step 5: Save the data to MongoDB
    mongo_client = get_mongo_client()
    save_to_mongodb(mongo_client, state_name, transformed_data)

    # Close the MongoDB connection
    mongo_client.close()
    logging.info("MongoDB connection closed.")

if __name__ == "__main__":
    main()
