import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
import schedule
import time
from urllib.parse import urljoin

# Chemins de sortie
output_file = os.path.join(os.getcwd(), 'OpCaricature.json')
config_file = os.path.join(os.getcwd(), 'configb4.json')

# URL de base pour les articles
base_url_first_page = 'https://www.businessnews.com.tn/Caricatures'
base_url_other_pages = 'https://www.businessnews.com.tn/liste/Caricatures/527/'
article_base_url = 'https://www.businessnews.com.tn/'

# Limiter le nombre de requêtes simultanées
semaphore = asyncio.Semaphore(5)

async def fetch(session, url):
    """Fonction asynchrone pour récupérer le contenu HTML d'une URL"""
    retries = 3
    for i in range(retries):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    print(f"Fetching URL: {url}")
                    return await response.text()
                elif response.status == 404:
                    print(f"Page not found (404 error) for URL: {url}")
                    return None
                else:
                    print(f"Unexpected response {response.status} for URL: {url}")
                    return None
        except aiohttp.ClientError as e:
            print(f"Error fetching URL {url}: {e}")
            if i < retries - 1:
                await asyncio.sleep(2 ** i)  # Exponential backoff
            else:
                raise
    return None

async def scrape_page(session, page_number):
    if page_number == 1:
        url = base_url_first_page
    else:
        url = base_url_other_pages + str(page_number)
    
    print(f"Scraping page {page_number} with URL: {url}")
    html_content = await fetch(session, url)
    if html_content is None:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    articles = []

    article_elements = soup.find_all('div', class_='ligneListeArticle')
    if not article_elements:
        print(f"No articles found on page {page_number}")
        return None

    for item in article_elements:
        article = {}

        # Extract title
        title_tag = item.find('a', class_='titreArticleListe')
        article['titre'] = title_tag.get_text(strip=True) if title_tag else 'Titre non disponible'

        # Extract article URL
        article_url = urljoin(article_base_url, title_tag['href']) if title_tag and 'href' in title_tag.attrs else None
        article['url'] = article_url if article_url else 'URL non disponible'

        # Extract image URL
        image_tag = item.find('img', src=True)
        article['image_url'] = urljoin(article_base_url, image_tag['src']) if image_tag and 'src' in image_tag.attrs else 'Image non disponible'

        # Extract publish date
        date_tag = item.find('div', class_='heureArticle fas fa-calendar')
        article['date'] = date_tag.get_text(strip=True) if date_tag else 'Date non disponible'

        articles.append(article)

    print(f"Scraped {len(articles)} articles from page {page_number}")
    return articles

async def save_articles(data):
    """Fonction asynchrone pour sauvegarder les articles dans un fichier JSON"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Saved {len(data['Opinion_Caricature']['articles'])} articles to {output_file}")
    except IOError as e:
        print(f"Error saving articles: {e}")

async def save_config(config):
    """Fonction asynchrone pour sauvegarder les configurations dans un fichier JSON"""
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        print(f"Saved config to {config_file}")
    except IOError as e:
        print(f"Error saving config: {e}")

async def scrape_all_articles():
    print("Starting scraping process...")
    all_articles = []

    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_articles = data.get("Opinion_Caricature", {}).get("articles", [])
                all_articles.extend(existing_articles)
        except IOError as e:
            print(f"Error loading existing file: {e}")
            data = {
                "nom_de_la_presse": "Business News",
                "Opinion_Caricature": {
                    "articles": []
                }
            }
    else:
        print(f"File not found. Creating new structure.")
        data = {
            "nom_de_la_presse": "Business News",
            "Opinion_Caricature": {
                "articles": []
            }
        }

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                last_page_scraped = config.get('last_page_scraped', 1)
        except IOError as e:
            print(f"Error loading config file: {e}")
            last_page_scraped = 1
    else:
        last_page_scraped = 1

    async with aiohttp.ClientSession() as session:
        page_number = last_page_scraped
        while True:
            articles = await scrape_page(session, page_number)
            if not articles:
                break
            all_articles.extend(articles)
            page_number += 1

            data["Opinion_Caricature"]["articles"].extend(articles)
            await save_articles(data)
            await save_config({'last_page_scraped': page_number})

    print("Scraping process completed.")

def run_scraping_job():
    asyncio.run(scrape_all_articles())

if __name__ == "__main__":
    # Exécuter une fois au démarrage
    run_scraping_job()

    # Planifier l'exécution toutes les heures
    schedule.every().hour.do(run_scraping_job)

    while True:
        schedule.run_pending()
        time.sleep(1)
