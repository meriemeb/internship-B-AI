import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
import schedule
import time

# Chemins de sortie
output_file = os.path.join(os.getcwd(), 'blog.json')
config_file = os.path.join(os.getcwd(), 'config7.json')

# URL de base pour les articles
base_url = 'https://www.leaders.com.tn/categorie/blogs?page='
article_base_url = 'https://www.leaders.com.tn'

# Limiter le nombre de requêtes simultanées
semaphore = asyncio.Semaphore(5)

async def fetch(session, url):
    """ Fonction asynchrone pour récupérer le contenu HTML d'une URL """
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
                'contenu': 'Contenu non disponible',
                'titre': 'Titre non disponible',
                'auteur': 'Auteur non disponible',
                'tags': [],
                'date_publish': 'Date non disponible',
                'url': url
            }

        soup = BeautifulSoup(html_content, 'html.parser')

        article_content = {
            'contenu': '',
            'titre': '',
            'auteur': '',
            'tags': [],
            'date_publish': '',
            'url': url
        }

        # Récupérer le titre de l'article
        titre_div = soup.find('h1')
        article_content['titre'] = titre_div.get_text(strip=True) if titre_div else 'Titre non trouvé'

        # Récupérer l'auteur de l'article
        author_spans = soup.find_all('span', style="color: rgb(128, 0, 0);")
        for span in author_spans:
            if span.find('span', style="font-size: smaller;"):
                # Extraire le nom de l'auteur
                author_name = span.find_next('strong').get_text(strip=True) if span.find_next('strong') else 'Auteur non trouvé'
                article_content['auteur'] = author_name
                span.decompose()  # Élimine l'élément span de l'auteur du contenu
                break
        else:
            article_content['auteur'] = 'Hedi Behi'  # Par défaut, définir l'auteur à "Hedi Behi"

        # Récupérer la date de publication
        date_div = soup.find('div', class_='infos')
        if date_div:
            date_publish = date_div.get_text(separator=' ', strip=True)
            # Supprimer toute mention de 'Blogs -' et ses espaces environnants
            article_content['date_publish'] = date_publish.replace('Blogs -', '').strip()
        else:
            article_content['date_publish'] = 'Date non trouvée'

        # Récupérer le contenu de l'article
        content_div = soup.find('div', class_='desc article_body')
        if content_div:
            # Supprimer les éléments de l'auteur du contenu
            for span in content_div.find_all('span', style="color: rgb(128, 0, 0);"):
                span.decompose()
            paragraphs = content_div.find_all(['p', 'div'])
            article_content['contenu'] = '\n'.join([para.get_text(strip=True) for para in paragraphs if para.get_text(strip=True)])
            if not article_content['contenu']:
                article_content['contenu'] = "Contenu non trouvé"
        else:
            article_content['contenu'] = "Contenu non trouvé"

        article_content['url'] = url
        return article_content

async def scrape_page(session, page_number, seen_urls):
    url = base_url + str(page_number)
    print(f"Scraping page {page_number}")
    html_content = await fetch(session, url)
    if html_content is None:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    articles = []

    article_elements = soup.find_all('div', class_='news')
    if not article_elements:
        print(f"No articles found on page {page_number}")
        return None

    tasks = []

    for item in article_elements:
        article = {}
        article_link = item.find('a', href=True)
        if article_link:
            article_url = article_base_url + article_link['href']
            if article_url in seen_urls:
                continue
            seen_urls.add(article_url)
            article['url'] = article_url
            article['titre'] = article_link.get('title', '')

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
    """ Fonction asynchrone pour sauvegarder les articles dans un fichier JSON """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Saved {len(data['categories']['Blogs']['articles'])} articles to {output_file}")
    except IOError as e:
        print(f"Error saving articles: {e}")

async def save_config(config):
    """ Fonction asynchrone pour sauvegarder la configuration dans un fichier JSON """
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        print(f"Saved config to {config_file}")
    except IOError as e:
        print(f"Error saving config: {e}")

async def scrape_all_articles():
    """ Fonction asynchrone pour scraper tous les articles disponibles """
    print("Starting scraping process...")
    all_articles = []
    seen_urls = set()

    # Charger le fichier existant s'il existe
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_articles = data.get("categories", {}).get("Blogs", {}).get("articles", [])
                for article in existing_articles:
                    seen_urls.add(article["url"])
        except IOError as e:
            print(f"Error loading existing file: {e}")
            data = {
                "nom_de_la_presse": "Leaders",
                "categories": {
                    "Blogs": {
                        "articles": []
                    }
                }
            }
    else:
        print(f"File not found. Creating new structure.")
        data = {
            "nom_de_la_presse": "Leaders",
            "categories": {
                "Blogs": {
                    "articles": []
                }
            }
        }

    # Charger la configuration existante s'il existe
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

            # Mettre à jour les données et sauvegarder au fur et à mesure
            data["categories"]["Blogs"]["articles"].extend(articles)
            await save_articles(data)
            await save_config({'last_page_scraped': page_number})

    print("Scraping process completed.")

def run_scraping_job():
    """ Fonction pour exécuter le scraping de tous les articles une fois """
    asyncio.run(scrape_all_articles())

if __name__ == "__main__":
    # Exécuter une fois au démarrage
    run_scraping_job()

    # Planifier l'exécution toutes les heures
    schedule.every().hour.do(run_scraping_job)

    while True:
        schedule.run_pending()
        time.sleep(1)
