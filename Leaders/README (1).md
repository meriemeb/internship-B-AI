
# Leaders

## Description 
This project contains Python scripts for scraping articles from 'Leaders' website. The scripts in this file are designed to scrape articles from the different sections in this website.

## Project Structure
- `Leaders-Blog.py`: Script for scraping all the articles from the section 'Blog'.
- `Leaders-Dossier.py`: Script for scraping all the articles from the section 'Dossiers'.
- `Leaders-Hommage.py`: Script for scraping all the articles from the section 'Hommage à ...'.
- `Leaders-Lifestyle.py`: Script for scraping all the articles from the section 'Lifestyle'.
- `Leaders-News.py`: Script for scraping all the articles from the section 'News'.
- `Leaders-Notes.py`: Script for scraping all the articles from the section 'Notes&Docs'.
- `Leaders-Opininon.py`: Script for scraping all the articles from the section 'Opininon'.
- `Leaders-Success.py`: Script for scraping all the articles from the section 'Success story'.
- `Leaders-TV.py`: Script for scraping all the articles from the section 'Leaders TV'.
- `Leaders-Who.py`: Script for scraping all the articles from the section 'Who's who'.

- `requirements.txt`: File listing all the Python dependencies required for the project.
- `blog.json`: Output file where the scraped data from the specified section will be stored.
- `dossiers.json`: Output file where the scraped data from the specified section will be stored.
- `hommage.json`: Output file where the scraped data from the specified section will be stored.
- `news.json`: Output file where the scraped data from the specified section will be stored.
- `note.json`: Output file where the scraped data from the specified section will be stored.
- `opinion.json`: Output file where the scraped data from the specified section will be stored.
- `success.json`: Output file where the scraped data from the specified section will be stored.
- `TV.json`: Output file where the scraped data from the specified section will be stored.
- `who.json`: Output file where the scraped data from the specified section will be stored.
- `config.json`: Configuration file to keep track of the last scraped page for each category.
- `config1.json`: Configuration file to keep track of the last scraped page for each category.
- `config2.json`: Configuration file to keep track of the last scraped page for each category.
- `config3.json`: Configuration file to keep track of the last scraped page for each category.
- `config4.json`: Configuration file to keep track of the last scraped page for each category.
- `config5.json`: Configuration file to keep track of the last scraped page for each category.
- `config6.json`: Configuration file to keep track of the last scraped page for each category.
- `config7.json`: Configuration file to keep track of the last scraped page for each category.
- `config8.json`: Configuration file to keep track of the last scraped page for each category.
- `config9.json`: Configuration file to keep track of the last scraped page for each category.

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
python Leaders-Blog.py
python Leaders-Dossier.py
python Leaders-Hommage.py
python Leaders-Lifestyle.py
python Leaders-News.py
python Leaders-Notes.py
python Leaders-Opinion.py
python Leaders-Success.py
python Leaders-TV.py
python Leaders-Who.py
```
The scripts will scrape articles from the different sections save the data into json files. 

## Scheduled Scraping
The schedule module is used to run the scraping job every hour. You can adjust the frequency of the job by modifying the schedule.every().hour.do(job) line each file

## JSON Output Structure
The scraped data is stored in json files with the following structure:
```json
{
    "nom de la presse":"Leaders",
    "categories"{
        "name of the section"{
            "articles":[
                {
                    "url": "https://www.leaders.com.tn/article-url",
                    "title": "Article Title",
                    "contenu": "Full article content",
                    "auteur": "Author name",
                    "tags": [
                        "URL1",
                        "URL2"
                    ],
                    "date_publish": "DD.MM.YYYY"
                    
                },
            ]
        }
    }
    
}

```
## Configuration File
The config.json files are used to store the last page scraped for each category. This allows the scraper to resume from where it left off in subsequent runs.
## Logging
The script uses the logging module to log the scraping process. Logs include information about fetched URLs, warnings for missing pages, and errors during the scraping process.





