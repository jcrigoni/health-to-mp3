import aiohttp
import asyncio
from bs4 import BeautifulSoup, Comment
from config import SCRAPER_CONFIG
from datetime import datetime
import html2markdown
import json
from logger_setup import setup_logger
import markdown
import os
from playwright.async_api import async_playwright
import psycopg2
from psycopg2.extras import RealDictCursor
import re
import uuid


class WebScraperEngine:
    def __init__(self):
        self.logger = setup_logger('web_scraper')
        
        self.db_conn = psycopg2.connect(
            host=SCRAPER_CONFIG['DB_HOST'],
            port=SCRAPER_CONFIG['DB_PORT'],
            dbname=SCRAPER_CONFIG['DB_NAME'],
            user=SCRAPER_CONFIG['DB_USER'],
            password=SCRAPER_CONFIG['DB_PASSWORD']
        )
        self.last_request_time = {}
        
    async def _check_rate_limit(self, domain):
        """Implements rate limiting per domain"""
        now = datetime.now().timestamp()
        if domain in self.last_request_time:
            time_passed = now - self.last_request_time[domain]
            if time_passed < SCRAPER_CONFIG['DELAY_BETWEEN_REQUESTS']:
                await asyncio.sleep(
                    SCRAPER_CONFIG['DELAY_BETWEEN_REQUESTS'] - time_passed
                )
        self.last_request_time[domain] = now

    async def _handle_page_load(self, page, url):
        """Handles page loading with retries"""
        for attempt in range(SCRAPER_CONFIG['MAX_RETRIES']):
            try:
                self.logger.info(f"Attempting to load {url} (attempt {attempt + 1})")
                await page.goto(
                    url, 
                    timeout=SCRAPER_CONFIG['PAGE_LOAD_TIMEOUT']
                )
                return True
            except Exception as e:
                self.logger.error(
                    f"Failed to load {url} on attempt {attempt + 1}: {str(e)}"
                )
                if attempt < SCRAPER_CONFIG['MAX_RETRIES'] - 1:
                    await asyncio.sleep(SCRAPER_CONFIG['RETRY_DELAY'])
                else:
                    return False

    async def _handle_cookies_popup(self, page):
        """Handles common cookie consent popups"""
        try:
            # Add common cookie consent button selectors
            common_selectors = [
                'button[id*="accept"]',
                'button[class*="accept"]',
                'button[id*="cookie"]',
                # Add more selectors as needed
            ]
            
            for selector in common_selectors:
                try:
                    await page.click(selector, timeout=5000)
                    self.logger.debug("Handled cookie popup")
                    break
                except:
                    continue
        except Exception as e:
            self.logger.warning(f"Cookie popup handling failed: {str(e)}")

    async def scrape_url(self, url):
        """Main scraping function"""
        document_id = str(uuid.uuid4())
        
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    headless=SCRAPER_CONFIG['HEADLESS']
                )
                context = await browser.new_context(
                    user_agent=SCRAPER_CONFIG['USER_AGENT']
                )
                page = await context.new_page()
                
                # Rate limiting
                domain = url.split('/')[2]
                await self._check_rate_limit(domain)
                
                # Load page
                self.logger.info(f"Starting scrape of {url}")
                if not await self._handle_page_load(page, url):
                    raise Exception("Failed to load page after all retries")
                
                # Handle cookie popups
                await self._handle_cookies_popup(page)
                
                # Get page title
                title = await page.title()

                # Get HTML content
                content = await page.content()
                
                # Convert to markdown
                markdown_content = self._html_to_markdown(content)
                
                # Store metadata in database
                await self._store_metadata(document_id, title, url)
                
                self.logger.info(f"Successfully scraped {url}")
                
                await browser.close()
                return {
                'content': markdown_content,
                'document_id': document_id
                }
                
        except Exception as e:
            self.logger.error(
                f"Error scraping {url}: {str(e)}", 
                exc_info=True
            )
            raise

    def _html_to_markdown(self, html_content):
        try:
            # First, let's clean the HTML using BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements more aggressively
            unwanted_tags = [
                'script', 'style', 'iframe', 'nav', 'footer', 
                'header', 'aside', 'noscript', 'meta', 'link',
                'button', 'form', 'input', 'svg', 'path'
            ]
        
            # Remove all unwanted tags
            for tag in unwanted_tags:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Remove all class and id attributes
            for tag in soup.find_all(True):
                if tag.has_attr('class'):
                    del tag['class']
                if tag.has_attr('id'):
                    del tag['id']
            
            # Convert relative links to absolute
            for a in soup.find_all('a', href=True):
                if not a['href'].startswith(('http://', 'https://')):
                    a.decompose()  # Remove relative links entirely
            
            # Extract just the text from specific tags
            for p in soup.find_all('p'):
                if p.string:
                    p.replace_with(soup.new_string(p.string))
            
            # Convert to markdown
            markdown_content = html2markdown.convert(str(soup))
            
            # Enhanced cleaning
            markdown_content = self._clean_markdown(markdown_content)
            
            return markdown_content
            
        except Exception as e:
            self.logger.error(
                f"Error converting HTML to markdown: {str(e)}", 
                exc_info=True
            )
            raise

    def _clean_markdown(self, markdown_content):
        """
        Enhanced markdown cleaning for better readability
        """
        # Remove multiple consecutive blank lines
        cleaned = re.sub(r'\n\s*\n', '\n\n', markdown_content)
        
        # Remove HTML tags that might have survived
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Remove URLs
        cleaned = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', cleaned)
        
        # Remove markdown links but keep text
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
        
        # Remove extra spaces
        cleaned = re.sub(r' +', ' ', cleaned)
        
        # Remove lines that are just punctuation or special characters
        cleaned = re.sub(r'^\W+$\n', '', cleaned, flags=re.MULTILINE)
        
        # Ensure proper paragraph spacing
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()

    async def _store_metadata(self, document_id, title, url):
        """
        Stores document metadata in PostgreSQL with proper error handling.
        """
        try:
            with self.db_conn.cursor() as cursor:
                insert_query = """
                    INSERT INTO health (
                        id, title, url, created_at
                    ) VALUES (%s, %s, %s, %s)
                """
                
                cursor.execute(
                    insert_query,
                    (
                        document_id,
                        title, 
                        url, 
                        datetime.now()
                    )
                )
                
                self.db_conn.commit()
                
                self.logger.info(
                    f"Successfully stored metadata for document {document_id}"
                )
                
        except Exception as e:
            self.db_conn.rollback()
            self.logger.error(
                f"Error storing metadata for document {document_id}: {str(e)}", 
                exc_info=True
            )
            raise

    def __del__(self):
        """
        Cleanup database connection when object is destroyed
        """
        if hasattr(self, 'db_conn'):
            self.db_conn.close()


async def process_urls_from_json(json_path: str) -> None:
    """
    Processes URLs from a JSON file containing a simple array of URLs.
    
    The function reads a JSON file that looks like:
    [
        "https://example1.com",
        "https://example2.com"
    ]
    
    For each URL, it:
    1. Creates a scraper instance
    2. Scrapes the content
    3. Converts it to markdown
    4. Stores it in the database
    5. Write the md file and store it in the directory output_data
    """
    # Create output directory if it doesn't exist
    output_dir = 'output_data'
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Read the JSON file and parse it as a simple array
        with open(json_path, 'r', encoding='utf-8') as file:
            urls = json.load(file)
        
        # Create a single scraper instance to reuse database connections
        scraper = WebScraperEngine()
        
        # Keep track of successful and failed URLs
        successful_urls = []
        failed_urls = []
        
        # Process each URL in the array
        for url in urls:
            try:
                print(f"\nStarting to process: {url}")
                
                # Scrape the URL and get markdown content
                scraped_data = await scraper.scrape_url(url)
                markdown_content = scraped_data['content']
                document_id = scraped_data['document_id']
                
                # Save to file in the output directory
                output_path = os.path.join(output_dir, f'{document_id}.md')
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

                print(f"Successfully processed {url}")
                
                successful_urls.append(url)
                
                # Add a polite delay between requests
                await asyncio.sleep(SCRAPER_CONFIG.get('DELAY_BETWEEN_REQUESTS', 5))
                
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                failed_urls.append(url)
                continue
                
        # Print summary at the end
        print("\nScraping Summary:")
        print(f"Successfully processed: {len(successful_urls)} URLs")
        print(f"Failed to process: {len(failed_urls)} URLs")
        
        if failed_urls:
            print("\nFailed URLs:")
            for url in failed_urls:
                print(f"- {url}")
            
            # Save failed URLs to a file for later retry
            with open('failed_urls.json', 'w') as f:
                json.dump(failed_urls, f, indent=2)
            print("\nFailed URLs have been saved to 'failed_urls.json'")
                
    except Exception as e:
        print(f"Error reading JSON file: {str(e)}")
        raise

async def main():
    """
    Main entry point for the scraper application.
    Sets up the scraping process and handles any top-level errors.
    """
    json_path = 'urls_job/test_articles.json'
    
    try:
        print("Starting the scraping process...")
        await process_urls_from_json(json_path)
        print("\nScraping process completed!")
        
    except Exception as e:
        print(f"A critical error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())