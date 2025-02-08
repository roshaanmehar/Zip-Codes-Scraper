# **Zip Code Scraper**

### **Overview**
This project provides a robust solution to extract and store zip code data from a state-specific webpage. Data is transformed into structured formats and saved to both JSON files and MongoDB collections.

---

## **Features**
- **Web Scraping:** Extracts state-specific zip code information, common cities, county details, and area codes.
- **Data Transformation:** Converts the raw extracted data into structured JSON and MongoDB documents.
- **MongoDB Integration:** Supports upserts and deduplication for efficient database management.
- **Logging:** Comprehensive logging to monitor scraping activities and errors.

---

## **Prerequisites**
1. **Python 3.x** installed
2. **MongoDB** installed and running locally or accessible via URI
3. Install required dependencies:
    ```bash
    pip install requests beautifulsoup4 pymongo
    ```

---

## **Usage Instructions**

### **1. Script Configuration**
To customize the script behavior, modify the following constants in the code:

- **BASE_URL:** URL of the state-specific page to scrape. For example, to scrape Georgia zip codes:
  ```python
  BASE_URL = "https://www.unitedstateszipcodes.org/ga/"
  ```
  Update the state abbreviation (`ga`) for different states.

- **OUTPUT_DIR:** Directory to store the JSON output file. Default is `output`.
- **HEADERS:** User-agent and request headers for HTTP requests. These can be left as-is or customized if needed.

### **2. Running the Script**
To execute the script, run the following command:
```bash
python script_name.py
```
### Upon successfull execution you should see something like this output on your terminal:
<img src="https://github.com/roshaanmehar/Zip-Codes-Scraper/blob/main/Screenshot%202025-02-08%20201146.png" width="300">


Ensure that MongoDB is running if you intend to save the data to MongoDB.

### **3. Output**
- **JSON Output:** A JSON file is saved in the `output` directory with the format:
  ```json
  [
    {
      "postcode": 30301,
      "scrapedsuccessfully": false,
      "processing": false,
      "totalrecordsfound": 0,
      "totaluniquerecordsfound": 0,
      "didresultsloadcompletely": false,
      "state": "Georgia",
      "recordsfoundwithemail": 0,
      "commoncities": "Atlanta",
      "county": "Fulton",
      "areacode": "404"
    }
  ]
  ```
  ### A single record in the json file should look something like this:
  <img src="https://github.com/roshaanmehar/Zip-Codes-Scraper/blob/main/Screenshot%202025-02-08%20201434.png" width="400">

  
- **MongoDB Output:** Data is stored in a collection named `postalcodes` within a database named after the state (e.g., `Georgia`).

- This is the website from where this tool fetches data.
<img src="https://github.com/roshaanmehar/Zip-Codes-Scraper/blob/main/Screenshot%202025-02-08%20225017.png" width="400">
<img src="https://github.com/roshaanmehar/Zip-Codes-Scraper/blob/main/Screenshot%202025-02-08%20225044.png" width="400">

---

## **MongoDB Usage**
### **1. Connection Setup**
Ensure MongoDB is running locally or provide a custom URI in the following function:
```python
get_mongo_client(uri="mongodb://localhost:27017/")
```

### **2. Database and Collection Structure**
- Each state has a separate MongoDB database.
- Zip code information is stored in a collection named `postalcodes`.
- Duplicate entries are automatically handled by the unique index on the `postcode` field.

---

## **Functionality Breakdown**
- **fetch_page:** Retrieves the webpage content for the given state.
- **parse_zipcodes:** Extracts and parses zip code information from the page.
- **transform_zip_data:** Transforms the parsed data into MongoDB-compatible document format.
- **save_to_json:** Saves the transformed data as a JSON file.
- **save_to_mongodb:** Inserts or updates data in MongoDB and removes duplicates.
- **remove_duplicates:** Ensures there are no duplicate zip code entries in the MongoDB collection.

---

## **Error Handling and Logging**
- Comprehensive logging tracks the progress of the scraping process and errors.
- Logs are saved in the `zipcode_scraper.log` file and displayed in the console.

---

## **Contributing**
1. Fork this repository.
2. Create a new branch:
    ```bash
    git checkout -b feature/your-feature
    ```
3. Commit your changes:
    ```bash
    git commit -m 'Add new feature'
    ```
4. Push to the branch:
    ```bash
    git push origin feature/your-feature
    ```
5. Create a pull request.

---

## **License**
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

