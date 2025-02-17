from playwright.async_api import async_playwright
import asyncio
from urllib.parse import urljoin, urlparse
import time

async def get_internal_links(page, base_url):
    # Get all links on the page
    links = await page.query_selector_all('a')
    internal_links = set()
    
    for link in links:
        href = await link.get_attribute('href')
        if href:
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            # Only keep internal links to articles
            if (urlparse(full_url).netloc == 'www.healthline.com' and 
                any(path in full_url for path in [
                    '/health/',
                    '/nutrition/',
                    '/health-news/',
                    '/diabetesmine/',
                    '/new-section/'  
                ])):
                internal_links.add(full_url)
    
    return internal_links

async def crawl_pages():
    # First, read URLs from the source file
    with open('health_urls.txt', 'r') as f:
        urls = [line.strip() for line in f.readlines()]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Process each URL from our file
        for url in urls:
            try:
                # Respect crawl delay
                await asyncio.sleep(5)
                
                print(f"Visiting: {url}")
                await page.goto(url)
                
                # Get internal links from this page
                new_links = await get_internal_links(page, url)
                
                # Save the found links to our output file
                with open('articles.txt', 'a') as f:
                    for link in new_links:
                        f.write(f"{link}\n")
                    
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                continue
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(crawl_pages())