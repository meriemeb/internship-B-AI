
# Business news 

## Description 
This project contains Python scripts for scraping articles from 'Business News' website. The scripts in this file are designed to scrape articles from the different sections in this website.

## Project Structure
- `Business-Actualités.py`: Script for scraping all the articles from the section 'Actualités'.
- `Business-Auto.py`: Script for scraping all the articles from the section 'Auto'.
- `Business-BNTv.py`: Script for scraping all the articles from the section 'BN TV'.
- `Business-Dossiers.py`: Script for scraping all the articles from the section 'Dossiers'.
- `Business-BNcheck.py`: Script for scraping all the articles from the section 'BN Check'.
- `Business-OpCaricature.py`: Script for scraping all the articles from the section 'Opininon Caricature'.
- `Business-OpChroniques.py`: Script for scraping all the articles from the section 'Opininon Chroniques'.
- `Business-OpTribunes.py`: Script for scraping all the articles from the section 'Opinion Tribunes'.
- `Business-SurReseaux.py`: Script for scraping all the articles from the section 'Sur Reseaux'.
- `requirements.txt`: File listing all the Python dependencies required for the project.
- `Actualite.json`: Output file where the scraped data from the specified section will be stored.
- `Auto.json`: Output file where the scraped data from the specified section will be stored.
- `BNcheck.json`: Output file where the scraped data from the specified section will be stored.
- `BNdossier.json`: Output file where the scraped data from the specified section will be stored.
- `BNTV.json`: Output file where the scraped data from the specified section will be stored.
- `OpCaricature.json`: Output file where the scraped data from the specified section will be stored.
- `OpChronique.json`: Output file where the scraped data from the specified section will be stored.
- `OpTribunes.json`: Output file where the scraped data from the specified section will be stored.
- `SurResau.json`: Output file where the scraped data from the specified section will be stored.
- `config.json`: Configuration file to keep track of the last scraped page for each category.
- `config1.json`: Configuration file to keep track of the last scraped page for each category.
- `config2.json`: Configuration file to keep track of the last scraped page for each category.
- `config3.json`: Configuration file to keep track of the last scraped page for each category.
- `config4.json`: Configuration file to keep track of the last scraped page for each category.
- `config5.json`: Configuration file to keep track of the last scraped page for each category.
- `config6.json`: Configuration file to keep track of the last scraped page for each category.
- `config7.json`: Configuration file to keep track of the last scraped page for each category.
- `config8.json`: Configuration file to keep track of the last scraped page for each category.

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
python Business-Actualités.py.py
python Business-Auto.py
python Business-BNTv.py
python Business-Dossiers.py
python Business-BNcheck.py
python Business-OpCaricature.py
python Business-OpChroniques.py
python Business-OpTribunes.py
python Business-SurReseaux.py
```
The scripts will scrape articles from the different sections save the data into json files. 

## Scheduled Scraping
The schedule module is used to run the scraping job every hour. You can adjust the frequency of the job by modifying the schedule.every().hour.do(job) line in Lead10j.py.

## JSON Output Structure
The scraped data is stored in json files with the following structure:
```json
{
    "nom de la presse":"Business News",
    "category"{
        "articles": {
            {
                "url": "https://www.leaders.com.tn/article-url",
                "title": "Article Title",
                "auteur": "Author name",
                "date": "YYYY-MM-DD | HH:MM",
                "contenu": "Full article content",
                "tags": [
                   "URL1",
                   "URL2"
                ]
            },
    }
    
}

```
## Configuration File
The config.json files are used to store the last page scraped for each category. This allows the scraper to resume from where it left off in subsequent runs.
## Logging
The script uses the logging module to log the scraping process. Logs include information about fetched URLs, warnings for missing pages, and errors during the scraping process.





