import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import logging
import schedule
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

base_url = 'https://www.challenges.tn/category/'
categories = ['economie', 'entrepreneur', 'afrique', 'maghreb', 'moyen-orient', 'zone-euro', 'international', 'high-tech', 'auto-moto']
output_file = os.path.join(os.getcwd(), 'challenges.json')
journal_name = "Challenges"
journal_url = "https://www.challenges.tn"
semaphore = asyncio.Semaphore(5)  # Limite de requêtes simultanées

async def fetch(session, url):
    retries = 3
    for i in range(retries):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    logger.info(f"Fetching URL: {url}")
                    return await response.text()
                elif response.status == 404:
                    logger.warning(f"Page not found: {url}")
                    return None
                else:
                    logger.warning(f"Unexpected response {response.status} for URL: {url}")
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching URL {url}: {e}")
            if i < retries - 1:
                await asyncio.sleep(2 ** i)  # Exponential backoff
            else:
                raise

async def fetch_article_content(session, url):
    async with semaphore:
        logger.info(f"Fetching article content from URL: {url}")
        html_content = await fetch(session, url)
        if not html_content:
            logger.warning(f"No HTML content fetched for URL: {url}")
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        content = 'Contenu non disponible'

        try:
            content_tags = soup.find('div', class_="td_block_wrap tdb_single_content tdi_99 td-pb-border-top td_block_template_1 td-post-content tagdiv-type", attrs={"data-td-block-uid": 'tdi_99'}) or soup.find('p', style="text-align: justify;")
            if content_tags:
                paragraphs = [p.get_text(strip=True) for p in content_tags.find_all('p')]
                content = ' '.join(paragraphs)
                logger.debug(f"Content found: {content[:100]}...")  # Log first 100 characters
        except Exception as e:
            logger.error(f"Error parsing article content from URL: {url}: {e}")

        return content

async def save_articles(data, journal_name, journal_url):
    try:
        # Ajout des informations du journal
        journal_info = {
            'journal_name': journal_name,
            'journal_url': journal_url
        }
        
        # Insérer ces informations au début du fichier JSON
        data_with_journal = {
            'journal_info': journal_info,
            'articles': data
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_with_journal, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved articles to {output_file}")
    except Exception as e:
        logger.error(f"Error saving articles to {output_file}: {e}")

async def scrape_page(session, category, page_number, seen_urls):
    try:
        if page_number == 1:
            url = f"{base_url}/{category}/"
        else:
            url = f"{base_url}/{category}/page/{page_number}/"

        logger.info(f"Scraping page {page_number} for category '{category}'")
        html_content = await fetch(session, url)
        if not html_content:
            logger.warning(f"No HTML content found for page {page_number} in category '{category}'")
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        article_elements = soup.find_all('div', class_="tdb_module_loop td_module_wrap td-animation-stack td-cpt-post")

        if not article_elements:
            logger.warning(f"No articles found on page {page_number} in category '{category}'")
            return None

        tasks = []
        articles = []

        for item in article_elements:
            article_link = item.find('a', href=True)
            if article_link:
                article_url = article_link['href']
                if article_url in seen_urls:
                    continue
                seen_urls.add(article_url)

                title = item.find('h3', class_="entry-title td-module-title").text.strip()
                author = item.find('span', class_="td-post-author-name").text.strip() if item.find('span', class_="td-post-author-name") else 'Auteur non disponible'
                date_of_publication_tag = item.find('time', class_="entry-date updated td-module-date")
                date_of_publication = date_of_publication_tag.text.strip() if date_of_publication_tag else ''

                # Convertir la date en objet datetime
                publication_date = parse_date(date_of_publication)
                days_ago = datetime.now() - timedelta(days=10)
                if publication_date < days_ago:
                    logger.info("Article publié il y a plus de 10 jours. Passage à l'article suivant.")
                    continue

                articles.append({
                    'url': article_url,
                    'title': title,
                    'author': author,
                    'date_of_publication': date_of_publication,
                    'content': 'Contenu non disponible',  # Placeholder for content
                    'tags': []
                })
                tasks.append(fetch_article_content(session, article_url))

        contents = await asyncio.gather(*tasks)

        for article, content in zip(articles, contents):
            article['content'] = content

        logger.info(f"Scraped {len(articles)} articles from page {page_number} in category '{category}'")
        return articles

    except Exception as e:
        logger.error(f"Exception while scraping page {page_number} in category '{category}': {e}")
        return None

async def scrape_category(category):
    logger.info(f"Starting scraping process for category '{category}'...")
    all_articles = []
    seen_urls = set()

    async with aiohttp.ClientSession() as session:
        page_number = 1
        while True:
            articles = await scrape_page(session, category, page_number, seen_urls)
            if not articles:
                break

            all_articles.extend(articles)
            page_number += 1

    logger.info(f"Total articles scraped for category '{category}': {len(all_articles)}")
    return all_articles

def parse_date(date_string):
    try:
        months = {
            "janvier": "01", "février": "02", "mars": "03", "avril": "04",
            "mai": "05", "juin": "06", "juillet": "07", "août": "08",
            "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"
        }
        
        # Replace French month names with numeric equivalents
        for french, num in months.items():
            date_string = date_string.replace(french, num)
        
        # Attempt to parse using various formats
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d", "%d %m %Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_string, fmt).replace(tzinfo=None)
            except ValueError:
                pass
        
        raise ValueError(f"Date format not recognized: {date_string}")
    
    except ValueError as e:
        logger.error(f"Unable to parse date: {date_string} - {e}")
        return None


async def scrape_all_categories():
    logger.info("Starting scraping process for all categories...")
    all_category_articles = {}

    for category in categories:
        category_articles = await scrape_category(category)
        all_category_articles[category] = category_articles

    logger.info(f"Total articles scraped: {sum(len(articles) for articles in all_category_articles.values())}")
    await save_articles(all_category_articles, journal_name, journal_url)
    logger.info("Scraping process completed for all categories.")
    
def job():
    asyncio.run(scrape_all_categories())

if __name__ == "__main__":
    # Planifier l'exécution de la tâche toutes les heures
    schedule.every().hour.do(job)
    # Run the initial scraping process synchronously
    asyncio.run(scrape_all_categories())

    while True:
        schedule.run_pending()
        time.sleep(1)
