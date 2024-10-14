import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

base_url = 'https://www.leaders.com.tn'
categories = ['who-s-who', 'blogs', 'opinions', 'hommage-a', 'lifestyle', 'news', 'notes-et-docs', 'success-story', 'leadertv', 'dossiers']
output_file = os.path.join(os.getcwd(), 'leaders.json')
journal_name = "Leaders"
journal_url = "https://www.leaders.com.tn"
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
        full_url = f"{base_url}{url}"
        logger.info(f"Fetching article content from URL: {full_url}")
        html_content = await fetch(session, full_url)
        if not html_content:
            logger.warning(f"No HTML content fetched for URL: {full_url}")
            return None, None, None, None, None

        soup = BeautifulSoup(html_content, 'html.parser')

        title = extract_title_from_url(url)
        content = None
        date_of_publication = None
        tags = []
        author = None

        try:
            date_tag = soup.find('div', class_='infos')
            if date_tag:
                date_string = date_tag.text.strip()
                # Extract the date from the string
                date_str = date_string.split('-')[-1].strip()
                date_of_publication = datetime.strptime(date_str, '%d.%m.%Y').date()

                # Check if the article is within the last 10 days
                if date_of_publication >= datetime.now().date() - timedelta(days=10):
                    logger.info(f"Article is within the last 10 days, processing URL: {full_url}")
                else:
                    logger.info(f"Article is older than 10 days, skipping URL: {full_url}")
                    return None, None, None, None, None

            # Find the author tag and verify it starts with 'Par'
            author_tag = soup.find('span', style="color: rgb(128, 0, 0);") or \
                         soup.find('span', style='color: rgb(128, 0, 0); font-size: smaller;') 
                        

            if author_tag:
                author_text = author_tag.text.strip()
                if author_text.startswith('Par'):
                    author = author_text
            else:
                author_black = soup.find('p', style="text-align: right;")
                if author_black :
                    author_s = soup.find('strong')
                    if author_s:
                        author_texts = author_s.text.strip()
                        author = author_texts
                        
            content_tag = soup.find('div', class_='desc article_body')
            if content_tag:
                paragraphs = content_tag.find_all(['p', 'div', 'h2', 'li'])
                content = '\n'.join([para.get_text(strip=True) for para in paragraphs if para.get_text(strip=True)])
                if not content:
                    content = "Contenu non trouvé"
                # Remove author from content if present
                if author and content:
                    content = content.replace(author, '')

                for link in content_tag.find_all('a', href=True):
                    href = link['href']
                    if not href.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        tags.append({'title': link.text.strip(), 'url': f"{base_url}{href}"})

            # Log the extracted information for debugging
            logger.debug(f"Extracted article data: Title: {title}, Date: {date_of_publication}, Author: {author}, Tags: {tags[:5]}, Content: {content[:50]}...")

        except Exception as e:
            logger.error(f"Error parsing article content from URL: {full_url}: {e}")

        return title, content, date_of_publication, tags, author

def extract_title_from_url(url):
    try:
        # Trouver l'index de la fin de '/article/'
        start_index = url.find('/article/') + len('/article/')
        
        # Extraire la partie de l'URL après '/article/'
        title_part = url[start_index:]
        
        # Trouver l'index de la première occurrence du tiret '-'
        end_index = title_part.find('-')
        
        # Extraire le titre en enlevant le numéro et les tirets
        title = title_part[end_index + 1:].replace('-', ' ')
        
        return title.strip()
    
    except Exception as e:
        logger.error(f"Error extracting title from URL: {url}: {e}")
        return 'Titre non trouvé'



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
        def date_converter(obj):
            if isinstance(obj, datetime.date):
                return obj.isoformat()
            return obj   

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_with_journal, f, default=str, ensure_ascii=False, indent=4)
        logger.info(f"Saved articles to {output_file}")
    except Exception as e:
        logger.error(f"Error saving articles to {output_file}: {e}")


async def scrape_page(session, category, page_number, seen_urls):
    try:
        if category == 'leadertv':
            if page_number == 1:
                url = f"{base_url}/videos"
            else:
                url = f"{base_url}/videos/?page={page_number}"
        elif category == 'dossiers':
            if page_number == 1:
                url = f"{base_url}/dossiers"
            else: 
                url = f"{base_url}/dossiers?page={page_number}"
        else:
            if page_number == 1:
                url = f"{base_url}/categorie/{category}"
            else:
                url = f"{base_url}/categorie/{category}?page={page_number}"
        logger.info(f"Scraping page {page_number} for category '{category}'")
        html_content = await fetch(session, url)
        if not html_content:
            logger.warning(f"No HTML content found for page {page_number} in category '{category}'")
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        article_elements = soup.find_all('div', class_='news') or soup.find_all('div', class_="col-xs-6 col-sm-4 col-md-4")
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

                tasks.append(fetch_article_content(session, article_url))
                articles.append({'url': base_url + article_url, 'title': article_link.text.strip()})
        contents_titles_authors_dates_tags = await asyncio.gather(*tasks)

        filtered_articles = []
        for article, (title, content, date_of_publication, tags, author) in zip(articles, contents_titles_authors_dates_tags):
            if title is None:
                continue  # Article non valide, passer au suivant
            article['title'] = title
            article['date_of_publication'] = date_of_publication
            article['content'] = content
            article['author'] = author
            article['tags'] = tags
            filtered_articles.append(article)

        logger.info(f"Scraped {len(filtered_articles)} articles from page {page_number} in category '{category}'")
        return filtered_articles

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

    return all_articles

def parse_date(date_string):
    try:
        return datetime.strptime(date_string, '%d.%m.%Y')
    except ValueError:
        return datetime.min

async def scrape_all_categories():
    logger.info("Starting scraping process for all categories...")
    all_category_articles = {}

    for category in categories:
        category_articles = await scrape_category(category)
        all_category_articles[category] = category_articles

    await save_articles(all_category_articles, journal_name, journal_url)
    logger.info("Scraping process completed for all categories.")

if __name__ == "__main__":
    asyncio.run(scrape_all_categories())