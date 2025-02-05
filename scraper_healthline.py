import asyncio
from playwright.async_api import async_playwright
import aiohttp
from datetime import datetime
import uuid
import boto3
import markdown
from config import SCRAPER_CONFIG, AWS_CREDENTIALS
from logger_setup import setup_logger
from bs4 import BeautifulSoup, Comment
import html2markdown
import re
import psycopg2
from psycopg2.extras import RealDictCursor

class WebScraperEngine:
    def __init__(self):
        self.logger = setup_logger('web_scraper')
        
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
                
                # Get HTML content
                content = await page.content()
                
                # Convert to markdown
                markdown_content = self._html_to_markdown(content)
                
                self.logger.info(f"Successfully scraped {url}")
                
                await browser.close()
                return markdown_content
                
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

async def main():
    scraper = WebScraperEngine()
    url = "https://www.healthline.com/health/sexual-health/the-state-of-sex-education"
    
    try:
        markdown_content = await scraper.scrape_url(url)
        
        # Save to file
        with open('test_output.md', 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        print("Scraping completed! Check test_output.md for results")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())