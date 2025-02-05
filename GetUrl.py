import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import json
import time
import random

def get_filtered_urls(base_url, total_pages, min_delay=4, max_delay=6):
    urls = set()
    
    for page in range(1, total_pages + 1):
        # Construire l'URL de la page avec pagination
        page_url = f"{base_url}{page}"
        print(f"Scraping page: {page_url}")
        
        while True:
            try:
                # Faire une requête pour obtenir le contenu de la page
                response = requests.get(page_url)
                
                if response.status_code == 429:
                    # Attendre plus longtemps en cas de statut 429
                    print(f"Rate limit exceeded on page {page}. Sleeping for {max_delay * 1} seconds.")
                    time.sleep(max_delay * 3)
                    continue
                
                if response.status_code != 200:
                    print(f"Failed to retrieve the page. Status code: {response.status_code}")
                    break

                # Parser le contenu de la page avec BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')

                # Trouver toutes les balises <a> sur la page
                links = soup.find_all('a')

                for link in links:
                    href = link.get('href')
                    if href:
                        # Joindre l'URL de base avec l'URL relative
                        full_url = urljoin(base_url, href)
                        # Filtrer les URL selon le format désiré
                        if re.match(r'https://www.healthline.com/', full_url):
                            urls.add(full_url)
                
                break  # Sortir de la boucle while si tout s'est bien passé
                
            except requests.RequestException as e:
                print(f"Request failed: {e}. Retrying after {max_delay * 1} seconds.")
                time.sleep(max_delay * 1)
        
        # Pause entre les requêtes pour éviter d'être limité par le serveur
        delay = random.uniform(min_delay, max_delay)
        print(f"Sleeping for {delay} seconds before next request.")
        time.sleep(delay)

    return list(urls)

def save_urls_to_json(urls, filename):
    with open(filename, 'w') as file:
        json.dump(urls, file, indent=4, ensure_ascii=False)

def main():
    base_url = 'https://www.healthline.com/health/type-2-diabetes/best-exercises-heart-health'
    total_pages = 700  # Nombre total de pages à scraper
    min_delay_between_requests = 5  # Délai minimum en secondes entre chaque requête
    max_delay_between_requests = 7  # Délai maximum en secondes entre chaque requête
    urls = get_filtered_urls(base_url, total_pages, min_delay_between_requests, max_delay_between_requests)

    print(f"Found {len(urls)} filtered URLs.")
    
    # Sauvegarder les URL dans un fichier JSON
    output_filename = 'urls_MarionADecouvert.json'
    save_urls_to_json(urls, output_filename)
    print(f"URLs have been saved to {output_filename}.")

if __name__ == "__main__":
    main()
