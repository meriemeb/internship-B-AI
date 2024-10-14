import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
import logging
from urllib.parse import urljoin
import schedule
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

base_url = 'https://www.businessnews.com.tn'
categories = {
    'Actualites': {'first_page': '/dernieres-news', 'subsequent_pages': '/liste/Dernieres_News/520/'},
    'Auto': {'first_page': '/Autos', 'subsequent_pages': '/liste/Autos/521/'},
    'BN_TV': {'first_page': '/BN_TV', 'subsequent_pages': '/liste/BN_TV/534/'},
    'BN_Check': {'first_page': '/bncheck', 'subsequent_pages': '/liste/bncheck/540/'},
    'Caricature': {'first_page': '/Caricatures', 'subsequent_pages': '/liste/Caricatures/527/'},
    'Chroniques': {'first_page': '/Chroniques', 'subsequent_pages': '/liste/Chroniques/523/'},
    'Tribunes': {'first_page': '/Tribunes', 'subsequent_pages': '/liste/Tribunes/526/'},
    'Sur les Reseaux': {'first_page': '/sur-les-reseaux', 'subsequent_pages': '/liste/sur-les-reseaux/537/'},
    'Dossiers': {'first_page': '/Dossiers', 'subsequent_pages': '/liste/Dossiers/520/'}
    # Add more categories here with their respective URLs
}

output_file = os.path.join(os.getcwd(), 'Articles.json')
config_file = os.path.join(os.getcwd(), 'config.json')
semaphore = asyncio.Semaphore(5)

if not os.path.exists(output_file):
    initial_data = {
        'journal_info': {
            'journal_name': "Business News",  # Replace with actual journal name
            'journal_url': "https://www.businessnews.com.tn"  # Replace with actual journal URL
        },
        'articles': {}
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(initial_data, f, ensure_ascii=False, indent=4)
    logger.info(f"Created initial JSON file: {output_file}")

if os.path.exists(config_file):
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
else:
    config = {'last_scraped_pages': {category: 1 for category in categories}}

async def fetch(session, url):
    retries = 3
    for i in range(retries):
        try:
            async with session.get(url) as response:
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
        sublinks = []  # Initialize sublinks here

        try:
            # Search for title in different places
            title_tag = soup.find('div', class_='titreArticleZen') or soup.find('span', class_='field-content', itemprop='name')
            if title_tag:
                title = title_tag.text.strip()

            # Search for publication date
            date_tag = soup.find('div', class_='heureArticle fas fa-calendar') or \
                       soup.find('time', {'class': 'entry-date updated'}) or \
                       soup.find('div', class_="date_artilce_zen")
            if date_tag:
                date_of_publication = date_tag.text.strip()

            # Search for article content
            content_div = soup.find('div', class_='contenue_article_zen')
            if content_div:
                paragraphs = [p.get_text(strip=True) for p in content_div.find_all(['p', 'div'])]  # Find both <p> and <div> tags
                content = ' '.join(paragraphs)

                # Now search for the last <p> containing <strong> to find the author
                last_p_tag = content_div.find_all(['p', 'div'])[-1] if content_div.find_all(['p', 'div']) else None
                if last_p_tag and last_p_tag.find('strong'):
                    author = last_p_tag.find('strong').text.strip()

                # Extract sublinks if available
                sublinks = [urljoin(url, link['href']) for link in content_div.find_all('a', href=True)]

        except Exception as e:
            logger.error(f"Error parsing article content from URL: {url}: {e}")

        return title, content, author, date_of_publication, sublinks 

async def save_articles(data):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved articles to {output_file}")
    except Exception as e:
        logger.error(f"Error saving articles to {output_file}: {e}")

async def save_config(config):
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved config to {config_file}")
    except Exception as e:
        logger.error(f"Error saving config to {config_file}: {e}")

async def scrape_article(session, article_url, seen_urls, all_category_articles, category):
    title, content, author, date_of_publication, tags = await fetch_article_content(session, article_url)
    if not title:
        return  # Skip invalid articles

    article = {
        'url': article_url,
        'title': title,
        'date_of_publication': date_of_publication,
        'content': content,
        'author': author,
        'tags': tags
    }

    all_category_articles.setdefault(category, []).append(article)

    # Save articles and update seen URLs after scraping each article
    data = {
        'journal_info': {
            'journal_name': "Business News",  # Replace with actual journal name
            'journal_url': "https://www.businessnews.com.tn"  # Replace with actual journal URL
        },
        'articles': all_category_articles
    }
    await save_articles(data)
    seen_urls.add(article_url)

async def scrape_category(category, seen_urls, all_category_articles):
    async with aiohttp.ClientSession() as session:
        page_number = config['last_scraped_pages'].get(category, 1)
        while True:
            success = await scrape_page(session, category, page_number, seen_urls, all_category_articles)
            if not success:
                break
            config['last_scraped_pages'][category] = page_number
            await save_config(config)
            page_number += 1

async def scrape_page(session, category, page_number, seen_urls, all_category_articles):
    try:
        base_first_page = categories[category]['first_page']
        base_subsequent_pages = categories[category]['subsequent_pages']

        if page_number == 1:
            url = f"{base_url}{base_first_page}"
        else:
            url = f"{base_url}{base_subsequent_pages}{page_number}/"

        logger.debug(f"Scraping page {page_number} for category '{category}'")
        html_content = await fetch(session, url)
        if not html_content:
            logger.warning(f"No HTML content found for page {page_number} in category '{category}'")
            return False

        soup = BeautifulSoup(html_content, 'html.parser')
        article_elements = soup.find_all('div', class_='ligneListeArticle')

        if not article_elements:
            logger.warning(f"No articles found on page {page_number} in category '{category}'")
            return False

        tasks = []
        for item in article_elements:
            article_link = item.find('a', href=True) or item.find('a', href=True, class_='titreArticleListe')
            if article_link:
                article_url = urljoin(base_url, article_link['href'])
                if article_url in seen_urls:
                    continue
                seen_urls.add(article_url)
                tasks.append(scrape_article(session, article_url, seen_urls, all_category_articles, category))

        await asyncio.gather(*tasks)
        logger.info(f"Scraped articles from page {page_number} in category '{category}'")

        return True

    except Exception as e:
        logger.error(f"Exception while scraping page {page_number} in category '{category}': {e}")
        return False

async def scrape_all_categories():
    logger.info("Starting scraping process for all categories...")
    all_category_articles = {}

    for category in categories:
        seen_urls = set()
        await scrape_category(category, seen_urls, all_category_articles)

    await save_articles(all_category_articles)
    logger.info("Scraping process completed for all categories.")

def job():
    logger.info("Scheduled job started.")
    asyncio.run(scrape_all_categories())
    
if __name__ == "__main__":
    logger.info("Script started")

    # Run the initial scraping process synchronously
    asyncio.run(scrape_all_categories())

    # Schedule the job to run every hour after the initial run
    schedule.every().hour.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
