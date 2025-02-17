import asyncio
from config_url import URL_CONFIG
import json
import os
from playwright.async_api import async_playwright
import time
from urllib.parse import urljoin, urlparse

async def get_internal_links(page, base_url):
    # Get all links on the page
    links = await page.query_selector_all('a')
    internal_links = set()
    
    for link in links:
        href = await link.get_attribute('href')
        if href:
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            # Only keep internal links
            if urlparse(full_url).netloc == URL_CONFIG['site_path'] and '/directory/' in full_url:
                internal_links.add(full_url)
    
    return internal_links

import json
import os

# Save the URL to our collection
def append_url_to_json(url, output_dir='output_url', filename='health_urls.json'):
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Construct full file path
        filepath = os.path.join(output_dir, filename)

        # Read existing URLs if file exists
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {"urls": []}
        else:
            data = {"urls": []}
        
        # Append new URL if it's not already in the list
        if url not in data["urls"]:
            data["urls"].append(url)
            
            # Write back to file
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
                
    except Exception as e:
        print(f"Error saving URL to JSON: {str(e)}")

async def crawl_pages(start_url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Track visited and to-visit URLs
        visited_urls = set()
        to_visit = {start_url}
        
        while to_visit:
            current_url = to_visit.pop()
            if current_url in visited_urls:
                continue
                
            try:
                # Respect crawl delay
                await asyncio.sleep(5)
                
                print(f"Visiting: {current_url}")
                await page.goto(current_url)
                
                # Get internal links from this page
                new_links = await get_internal_links(page, current_url)
                
                # Add new unvisited links to our to-visit set
                to_visit.update(new_links - visited_urls)
                
                # Mark current URL as visited
                visited_urls.add(current_url)
                
                append_url_to_json(current_url)

                    
            except Exception as e:
                print(f"Error processing {current_url}: {str(e)}")
                continue
        
        await browser.close()

async def main():
    start_url = URL_CONFIG['site_long_path']
    await crawl_pages(start_url)

if __name__ == "__main__":
    asyncio.run(main())