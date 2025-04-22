import aiohttp
import asyncio
from bs4 import BeautifulSoup, Comment
from datetime import datetime
import html2markdown
import json
import markdown
import os
import re
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from playwright.async_api import async_playwright

from src.config import config
from src.utils import setup_logger


class WebScraper:
    def __init__(self):
        self.logger = setup_logger('web_scraper')
        self.scraper_config = config.SCRAPER_CONFIG
        
        self.db_conn = psycopg2.connect(
            host=self.scraper_config['DB_HOST'],
            port=self.scraper_config['DB_PORT'],
            dbname=self.scraper_config['DB_NAME'],
            user=self.scraper_config['DB_USER'],
            password=self.scraper_config['DB_PASSWORD']
        )
        self.last_request_time = {}
        
    async def _check_rate_limit(self, domain):
        """Implements rate limiting per domain"""
        now = datetime.now().timestamp()
        if domain in self.last_request_time:
            time_passed = now - self.last_request_time[domain]
            if time_passed < self.scraper_config['DELAY_BETWEEN_REQUESTS']:
                await asyncio.sleep(
                    self.scraper_config['DELAY_BETWEEN_REQUESTS'] - time_passed
                )
        self.last_request_time[domain] = now

    async def _handle_page_load(self, page, url):
        """Handles page loading with retries"""
        for attempt in range(self.scraper_config['MAX_RETRIES']):
            try:
                self.logger.info(f"Attempting to load {url} (attempt {attempt + 1})")
                await page.goto(
                    url, 
                    timeout=self.scraper_config['PAGE_LOAD_TIMEOUT']
                )
                return True
            except Exception as e:
                self.logger.error(
                    f"Failed to load {url} on attempt {attempt + 1}: {str(e)}"
                )
                if attempt < self.scraper_config['MAX_RETRIES'] - 1:
                    await asyncio.sleep(self.scraper_config['RETRY_DELAY'])
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
                    headless=self.scraper_config['HEADLESS']
                )
                context = await browser.new_context(
                    user_agent=self.scraper_config['USER_AGENT']
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
                title_end = await page.title()

                # Get URL Slug
                url_slug = url.split('/')[-1]

                # Concatenate URL Slug with title_end
                title = url_slug + ' ' + title_end

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
                    'document_id': document_id,
                    'title': title
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
        Enhanced markdown cleaning that extracts content between article tags
        """
        # First extract content between article tags
        pattern = r'<article[^>]*>([\s\S]*?)</article>'
        match = re.search(pattern, markdown_content, re.DOTALL)
        
        if not match:
            self.logger.debug("No article tags found")
            # Return original content if no article tags found
            cleaned = markdown_content
        else:
            cleaned = match.group(1)  # Get the content between article tags
            
        # Apply the rest of the cleaning operations
        # Remove multiple consecutive blank lines
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)

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
                    INSERT INTO scraped_pages (
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


async def process_urls_from_json(json_path, output_dir=None):
    """
    Processes URLs from a JSON file containing URLs
    """
    # Create output directory with timestamp if not provided
    if output_dir is None:
        output_dir = config.get_output_dir()
    
    # Create directory
    os.makedirs(output_dir, exist_ok=True)
    
    logger = setup_logger('url_processor')
    
    try:
        # Read the JSON file and parse it as a simple array
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            urls = data.get('urls', [])
        
        # Create a single scraper instance to reuse database connections
        scraper = WebScraper()
        
        # Keep track of successful and failed URLs
        successful_urls = []
        failed_urls = []
        
        # Process each URL in the array
        for url in urls:
            try:
                logger.info(f"Starting to process: {url}")
                
                # Scrape the URL and get markdown content
                result = await scraper.scrape_url(url)
                
                markdown_content = result['content']
                document_id = result['document_id']
                
                # Save to file in the output directory
                output_path = os.path.join(output_dir, f'{document_id}.md')
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

                logger.info(f"Successfully processed {url}")
                
                successful_urls.append(url)
                
                # Add a polite delay between requests
                await asyncio.sleep(config.SCRAPER_CONFIG.get('DELAY_BETWEEN_REQUESTS', 3))
                
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                failed_urls.append(url)
                continue
                
        # Print summary at the end
        logger.info("\nScraping Summary:")
        logger.info(f"Successfully processed: {len(successful_urls)} URLs")
        logger.info(f"Failed to process: {len(failed_urls)} URLs")
        
        if failed_urls:
            logger.info("\nFailed URLs:")
            for url in failed_urls:
                logger.info(f"- {url}")
            
            # Save failed URLs to a file for later retry
            failed_urls_path = os.path.join(output_dir, 'failed_urls.json')
            failed_data = {"urls": failed_urls}
            with open(failed_urls_path, 'w') as f:
                json.dump(failed_data, f, indent=2)
            logger.info("\nFailed URLs have been saved to 'failed_urls.json'")
            
        return {
            "output_dir": output_dir,
            "successful": len(successful_urls),
            "failed": len(failed_urls)
        }
                
    except Exception as e:
        logger.error(f"Error reading JSON file: {str(e)}")
        raise