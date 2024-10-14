import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import logging
from urllib.parse import urljoin
import schedule
import time

logging.basicConfig(level=logging.DEBUG)  # Passer à DEBUG pour plus de détails
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
    'Dossiers': {'first_page': '/Dossiers', 'subsequent_pages': '/liste/Dernieres_News/520/'}
    # Ajoutez ici d'autres catégories avec leurs URLs respectifs
}
output_file = os.path.join(os.getcwd(), 'businessnews.json')
journal_name = "Business News"
journal_url = "https://www.businessnews.com.tn"
semaphore = asyncio.Semaphore(5)  # Limite de requêtes simultanées

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

        title = extract_title_from_url(url)  # Extract the title from the URL
        content = 'Contenu non disponible'
        author = 'Auteur non disponible'
        date_of_publication = ''
        tags = []

        try:
            # Rechercher l'auteur dans différents emplacements
            author_tag = soup.find('div', class_='auteur_artilce_zen') or soup.find('p', style="text-align: right;")
            if author_tag:
                author = author_tag.text.strip()

            # Rechercher la date de publication
            date_tag = soup.find('div', class_='heureArticle fas fa-calendar')
            if date_tag:
                date_of_publication = date_tag.text.strip()
                # Convertir la date en objet datetime
                publication_date = parse_date(date_of_publication)

                # Vérifier si l'article est publié dans les 10 derniers jours
                days_ago = datetime.now() - timedelta(days=10)
                if publication_date < days_ago:
                    logger.info("Article publié il y a plus de 10 jours. Ignorer.")
                    return None, None, None, None, None

            # Rechercher le contenu de l'article
            content_div = soup.find('div', class_='contenue_article_zen')
            if content_div:
                paragraphs = [p.get_text(strip=True) for p in content_div.find_all('p')]
                content = ' '.join(paragraphs)

            sublinks_div = content_div.find_all('a', href=True) if content_div else []
            sublinks = [urljoin(base_url, link['href']) for link in sublinks_div]

        except Exception as e:
            logger.error(f"Error parsing article content from URL: {url}: {e}")

        return title, content, author, date_of_publication, sublinks
    
def extract_title_from_url(url):
    try:
        # Extraire le chemin de l'URL après la base
        path = url.replace(base_url, '').lstrip('/')
        # Extraire la partie du titre avant la première virgule
        title_part = path.split(',', 1)[0]
        # Remplacer les tirets par des espaces
        title = title_part.replace('-', ' ')
        return title
    except Exception as e:
        logger.error(f"Error extracting title from URL: {url}: {e}")
        return 'Titre non trouvé'

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
        # Construire l'URL en fonction de la page à scraper
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
        article_elements = soup.find_all('div', class_='ligneListeArticle')

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
        for article, (title, content, author, date_of_publication, tags) in zip(articles, contents_titles_authors_dates_tags):
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
        # Assurez-vous que le format de date correspond à celui utilisé dans les articles
        return datetime.strptime(date_string, "%d/%m/%Y | %H:%M")
    except ValueError as e:
        logging.error(f"Unable to parse date: {date_string}")
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
