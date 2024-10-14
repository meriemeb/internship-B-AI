import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
import schedule
import time
from urllib.parse import urljoin

# Chemins de sortie
output_file = os.path.join(os.getcwd(), 'OpTribunes.json')
config_file = os.path.join(os.getcwd(), 'configb3.json')

# URL de base pour les articles
base_url_first_page = 'https://www.businessnews.com.tn/Tribunes'
base_url_other_pages = 'https://www.businessnews.com.tn/liste/Tribunes/526/'
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

async def fetch_article_content(session, url):
    async with semaphore:
        print(f"Fetching article content from URL: {url}")
        html_content = await fetch(session, url)
        if html_content is None:
            return {
                'titre': 'Titre non disponible',
                'auteur': 'Auteur non disponible',
                'date': 'Date non disponible',
                'contenu': 'Contenu non disponible',
                'url': url,
                'sublinks': []
            }

        soup = BeautifulSoup(html_content, 'html.parser')

        article_content = {
            'titre': '',
            'auteur': '',
            'date': '',
            'contenu': '',
            'url': url,
            'sublinks': []
        }

        # Extract title
        title_div = soup.find('div', class_='titreArticleZen')
        article_content['titre'] = title_div.get_text(strip=True) if title_div else 'Titre non disponible'

        # Extract publish date if available
        date_div = soup.find('div', class_='heureArticle fas fa-calendar')
        article_content['date'] = date_div.get_text(strip=True) if date_div else 'Date non disponible'

        # Extract content from 'contenue_article_zen' or 'div[dir="auto"]'
        content_div = soup.find('div', class_='contenue_article_zen')
        if content_div:
            content_html = content_div.decode_contents()
        else:
            content_div = soup.find('div', dir='auto')
            if content_div:
                content_html = content_div.decode_contents()
            else:
                content_html = 'Contenu non disponible'

        # Extract author if available
        author_text = None
        # Check different locations for author information
        author_div1 = soup.find('div', style='text-align: right;', dir='auto')
        author_div2 = soup.find('p', style='text-align: right;')

        if author_div1 and author_div1.find('strong'):
            author_text = author_div1.find('strong').get_text(strip=True)
        elif author_div2:
            if author_div2.find('em') and author_div2.find('strong'):
                author_text = author_div2.find('em').get_text(strip=True) + " " + author_div2.find('strong').get_text(strip=True)
            elif author_div2.find('strong'):
                author_text = author_div2.find('strong').get_text(strip=True)

        article_content['auteur'] = author_text if author_text else 'Auteur non disponible'

        # Remove author from content if present
        if author_text:
            content_html = content_html.replace(author_text, '').strip()

        # Extract sublinks if available
        sublinks_div = content_div.find_all('a', href=True) if content_div else []
        article_content['sublinks'] = [urljoin(url, link['href']) for link in sublinks_div]

        # Process content to remove unwanted tags and whitespace
        soup_content = BeautifulSoup(content_html, 'html.parser')
        for tag in soup_content.find_all(['strong', 'em']):
            tag.unwrap()
        article_content['contenu'] = soup_content.get_text(separator='\n', strip=True)

        return article_content

    
async def scrape_page(session, page_number, seen_urls):
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

    article_elements = soup.find_all('div', class_='contBlockArticleliste')
    if not article_elements:
        print(f"No articles found on page {page_number}")
        return None

    tasks = []

    for item in article_elements:
        article = {}
        article_link = item.find('a', href=True)
        if article_link:
            article_url = urljoin(article_base_url, article_link['href'])
            if article_url in seen_urls:
                continue
            seen_urls.add(article_url)
            article['url'] = article_url

        if 'url' in article:
            tasks.append(fetch_article_content(session, article['url']))
            articles.append(article)

    contents = await asyncio.gather(*tasks, return_exceptions=True)
    for article, content in zip(articles, contents):
        if isinstance(content, dict):
            article.update(content)

    print(f"Scraped {len(articles)} articles from page {page_number}")
    return articles

async def save_articles(data):
    """Fonction asynchrone pour sauvegarder les articles dans un fichier JSON"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Saved {len(data['Opinion_Tribunes']['articles'])} articles to {output_file}")
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
    seen_urls = set()

    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_articles = data.get("Opinion_Tribunes", {}).get("articles", [])
                for article in existing_articles:
                    seen_urls.add(article["url"])
        except IOError as e:
            print(f"Error loading existing file: {e}")
            data = {
                "nom_de_la_presse": "Business News",
                "Opinion_Tribunes": {
                    "articles": []
                }
            }
    else:
        print(f"File not found. Creating new structure.")
        data = {
            "nom_de_la_presse": "Business News",
            "Opinion_Tribunes": {
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
            articles = await scrape_page(session, page_number, seen_urls)
            if not articles:
                break
            all_articles.extend(articles)
            page_number += 1

            data["Opinion_Tribunes"]["articles"].extend(articles)
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
