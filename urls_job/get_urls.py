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
            # Only keep internal links
            if urlparse(full_url).netloc == 'www.healthline.com' and '/directory/' in full_url:
                internal_links.add(full_url)
    
    return internal_links

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
                
                # Save the URL to our collection
                with open('health_urls.txt', 'a') as f:
                    f.write(f"{current_url}\n")
                    
            except Exception as e:
                print(f"Error processing {current_url}: {str(e)}")
                continue
        
        await browser.close()

async def main():
    start_url = 'https://www.healthline.com/directory/topics'
    await crawl_pages(start_url)

if __name__ == "__main__":
    asyncio.run(main())