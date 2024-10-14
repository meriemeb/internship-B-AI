
# Leaders 10jrs

## Description 
This project contains Python scripts for scraping articles from 'Leaders' website. The script `Lead10.py` is designed to scrape articles from the last 10 days.

## Project Structure
- `Lead10.py`: Script for scraping articles from the last 10 days.
- `requirements.txt`: File listing all the Python dependencies required for the project.
- `leaders.json`: Output file where the scraped data from the last 10 days will be stored.

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
python Lead10.py
```
The script will scrape articles from the last 10 days save the data into leaders.json. 

## Scheduled Scraping
The schedule module is used to run the scraping job every hour. You can adjust the frequency of the job by modifying the schedule.every().hour.do(job) line in Lead10j.py.

## JSON Output Structure
The scraped data is stored in Lead10j.json with the following structure:
```json
{
   {
    "journal_info": {
        "journal_name": "Leaders",
        "journal_url": "https://www.leaders.com.tn"
    },
    "articles": {
        "category_name_1": [
            {
                "url": "https://www.leaders.com.tn/article-url",
                "title": "Article Title",
                "date_of_publication": "YYYY-MM-DD",
                "content": "Full article content",
                "author": "Author name",
                "tags": [
                    {
                        "title": "Tag1",
                        "url": "tag1-url"
                    },
                    {
                        "title": "Tag2",
                        "url": "tag2-url"
                    }
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
## Logging
The script uses the logging module to log the scraping process. Logs include information about fetched URLs, warnings for missing pages, and errors during the scraping process.





