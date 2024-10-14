import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
import ssl
import certifi
from datetime import datetime, timedelta
import logging
from urllib.parse import urljoin
import schedule
import time


logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG for more details
logger = logging.getLogger(__name__)

base_url = 'https://www.webmanagercenter.com'
categories = {
    'Actualites': {'first_page': '/actualite/', 'subsequent_pages': '/actualite/page/'},
    'Ecofinance': {'first_page': '/actualite/eco-finance/', 'subsequent_pages': '/actualite/eco-finance/page/'},
    'Entreprises': {'first_page': '/actualite/entreprises-cat/', 'subsequent_pages': '/actualite/entreprises-cat/page/'},
    'Bourse': {'first_page': '/marches-financiers/bourse-cat/', 'subsequent_pages': '/marches-financiers/bourse-cat/page/'},
    'Opinion': {'first_page': '/le-cercle/idees-et-debats/', 'subsequent_pages': '/le-cercle/idees-et-debats/page/'},
    'Dossiers': {'first_page': '/le-cercle/dossiers/', 'subsequent_pages': '/le-cercle/dossiers/page/'},
    'RSE': {'first_page': '/entreprises/rse-initiatives/', 'subsequent_pages': '/entreprises/rse-initiatives/page/'},
    'Entreprendre': {'first_page': '/challenge/entreprendre-cat/', 'subsequent_pages': '/challenge/entreprendre-cat/page/'},
    'Startups': {'first_page': '/challenge/start-ups/', 'subsequent_pages': '/challenge/start-ups/page/'},
    'Success Story': {'first_page': '/challenge/success-story/', 'subsequent_pages': '/challenge/success-story/page/'},
    'Campus': {'first_page': '/challenge/campus/', 'subsequent_pages': '/challenge/campus/page/'},
    'Tendances': {'first_page': '/challenge/tendances/', 'subsequent_pages': '/challenge/tendances/page/'},
    'La tunisie qui gagne': {'first_page': '/challenge/la-tunisie-qui-gagne/', 'subsequent_pages': '/challenge/la-tunisie-qui-gagne/page/'}
}
output_file = os.path.join(os.getcwd(), 'WebManCenter.json')
journal_name = "Web Manager Center"
journal_url = "https://www.webmanagercenter.com"
semaphore = asyncio.Semaphore(5)  # Limit simultaneous requests
ssl_context = ssl.create_default_context(cafile=certifi.where())
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

async def fetch(session, url):
    retries = 3
    for i in range(retries):
        try:
            async with session.get(url, ssl=ssl_context, headers=headers) as response:
                if response.status == 200:
                    logger.debug(f"Fetching URL: {url}")
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
        logger.debug(f"Fetching article content from URL: {url}")
        html_content = await fetch(session, url)
        if not html_content:
            logger.warning(f"No HTML content fetched for URL: {url}")
            return None, None, None, None, None

        soup = BeautifulSoup(html_content, 'html.parser')

        title = 'Titre non trouvé'
        content = 'Contenu non disponible'
        author = 'Auteur non disponible'
        date_of_publication = ''
        tags = []
        sublinks = []

        try:
            title_tag = soup.find('h1', class_="entry-title")
            if title_tag:
                title = title_tag.text.strip()

            author_tag = soup.find('a', style="color:#444; text-decoration:none;")
            if author_tag:
                author = author_tag.text.strip()

            date_tag = soup.find('time', class_="entry-date updated td-module-date")
            if date_tag and date_tag.has_attr('datetime'):
                date_of_publication = date_tag['datetime']
                publication_date = parse_date(date_of_publication, from_datetime=True)
            elif date_tag:
                date_of_publication = date_tag.text.strip()
                publication_date = parse_date(date_of_publication)
            else:
                publication_date = None

            if publication_date:
                days_ago = datetime.now() - timedelta(days=10)
                if publication_date < days_ago:
                    logger.info(f"Article publié il y a plus de 10 jours: {url}. Ignorer.")
                    return None, None, None, None, None

            content_div = soup.find('div', class_="td-post-content")
            if content_div:
                paragraphs = [p.get_text(strip=True) for p in content_div.find_all('p')]
                content = ' '.join(paragraphs)
                sublinks_div = content_div.find_all('a', href=True)
                sublinks = [urljoin(base_url, link['href']) for link in sublinks_div]

        except AttributeError as e:
            logger.error(f"Attribute error while parsing article content from URL: {url}: {e}")
        except Exception as e:
            logger.error(f"Error parsing article content from URL: {url}: {e}")

        return title, content, author, date_of_publication, sublinks

async def save_articles(data, journal_name, journal_url):
    try:
        journal_info = {
            'journal_name': journal_name,
            'journal_url': journal_url
        }
        
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
            url = f"{base_url}{categories[category]['first_page']}"
        else:
            url = f"{base_url}{categories[category]['subsequent_pages']}{page_number}/"

        logger.debug(f"Scraping page {page_number} for category '{category}'")
        html_content = await fetch(session, url)
        if not html_content:
            logger.warning(f"No HTML content found for page {page_number} in category '{category}'")
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        article_elements = soup.find_all('div', class_='td_module_10 td_module_wrap td-animation-stack')

        if not article_elements:
            logger.warning(f"No articles found on page {page_number} in category '{category}'")
            return None

        tasks = []
        articles = []

        for item in article_elements:
            article_link = item.find('a', href=True)
            if article_link:
                article_url = urljoin(base_url, article_link['href'])
                if article_url in seen_urls:
                    continue
                seen_urls.add(article_url)

                tasks.append(fetch_article_content(session, article_url))
                articles.append({'url': article_url, 'title': article_link.text.strip()})

        contents_titles_authors_dates_tags = await asyncio.gather(*tasks)

        filtered_articles = []
        all_articles_older_than_10_days = True  # To track if all articles are older than 10 days

        for article, (title, content, author, date_of_publication, tags) in zip(articles, contents_titles_authors_dates_tags):
            if title is None:
                continue  # Article non valide, passer au suivant
            article['title'] = title
            article['date_of_publication'] = date_of_publication
            article['content'] = content
            article['author'] = author
            article['tags'] = tags

            publication_date = parse_date(date_of_publication, from_datetime=True if 'T' in date_of_publication else False)
            days_ago = datetime.now() - timedelta(days=10)
            if publication_date and publication_date >= days_ago:
                all_articles_older_than_10_days = False

            filtered_articles.append(article)

        logger.info(f"Scraped {len(filtered_articles)} articles from page {page_number} in category '{category}'")

        return filtered_articles, all_articles_older_than_10_days

    except Exception as e:
        logger.error(f"Exception while scraping page {page_number} in category '{category}': {e}")
        return None, False

async def scrape_category(category):
    logger.info(f"Starting scraping process for category '{category}'...")
    all_articles = []
    seen_urls = set()

    async with aiohttp.ClientSession() as session:
        page_number = 1
        all_articles_older_than_10_days = False

        while not all_articles_older_than_10_days:
            articles, all_articles_older_than_10_days = await scrape_page(session, category, page_number, seen_urls)
            if articles:
                all_articles.extend(articles)
            page_number += 1

    return all_articles

def parse_date(date_string, from_datetime=False):
    try:
        if from_datetime:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00')).replace(tzinfo=None)
        else:
            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d", "%d %B %Y", "%d/%m/%Y"):
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