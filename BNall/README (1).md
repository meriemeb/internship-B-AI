
# Business news: one script for the whole e-newspaper

## Description
This project contains Python script for scraping articles from 'Business News' website. The script `BN.py` is designed to scrape articles across multiple categories and save the data into a JSON file. 

## Project Structure
- `BN.py`: Main script for scraping articles from all categories.
- `requirements.txt`: File listing all the Python dependencies required for the project.


## Setup
1. Clone the repository or download the script files.
2. Install the required Python packages using `pip` (see [Installation](#installation) below).
3. Run the script to start the initial scraping process.
## Installation
To install the necessary packages, run:

```sh
pip install -r requirements.txt
```
## Usage
Run the main script to start the initial scraping process:
```bash
python BN.py
```
The script will scrape the specified categories from the "Business News" website and save the data into Artciles.json. It will also create a config.json file to keep track of the last page scraped for each category.

## Scheduled Scraping
The schedule module is used to run the scraping job every hour. You can adjust the frequency of the job by modifying the schedule.every().hour.do(job) line in BN.py
## JSON Output Structure
The scraped data is stored in Articles.json with the following structure:
```json
{
   {
    "journal_info": {
        "journal_name": "Business news",
        "journal_url": "https://www.businessnews.com.tn"
    },
    "articles": {
        "category_name_1": [
            {
                "url": "https://www.businessnews.com.tn/article-url",
                "title": "Article Title",
                "date_of_publication": "YYYY-MM-DD | HH:MM",
                "content": "Full article content",
                "author":"Author name"
                "tags": [
                    "url1",
                    "url2"
                ]
            },
            ...
        ],
        "category_name_2": [
            ...
        ],
        ...
    }
}

```
## Configuration File
The config.json file is used to store the last page scraped for each category. This allows the scraper to resume from where it left off in subsequent runs.
## Logging
The script uses the logging module to log the scraping process. Logs include information about fetched URLs, warnings for missing pages, and errors during the scraping process.