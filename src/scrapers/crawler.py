from urllib.parse import urlparse, urljoin
import asyncio
import json
import os
import random
import time
from playwright.async_api import async_playwright

from src.config import config
from src.utils import setup_logger

# User agent rotation list for stealth browsing
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]


class Crawler:
    def __init__(self, site_config=None):
        self.logger = setup_logger('crawler')
        self.config = site_config or config.CRAWLER_CONFIG
        self.site_path = self.config['SITE_PATH']
        self.start_url = self.config['START_URL']
        self.output_dir = self.config['OUTPUT_DIR']
        self.output_file = self.config['OUTPUT_FILE']
        self.max_pages = self.config['MAX_PAGES']
        self.delay_min = self.config['DELAY_MIN']
        self.delay_max = self.config['DELAY_MAX']
        self.timeout = self.config['TIMEOUT']
        self.retries = self.config['RETRIES']
        self.stealth_mode = self.config['STEALTH_MODE']
        
    async def load_existing_urls(self):
        """Load URLs already discovered from JSON file"""
        try:
            filepath = os.path.join(self.output_dir, self.output_file)
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    return set(data.get("urls", []))
            return set()
        except Exception as e:
            self.logger.error(f"Error loading existing URLs: {e}")
            return set()

    async def configure_browser(self):
        """Configure the browser with advanced settings to avoid detection"""
        playwright = await async_playwright().start()
        
        # Browser launch options
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-web-security',
            '--disable-notifications',
            '--disable-popup-blocking',
            '--disable-dev-shm-usage',  # To avoid crashes in Docker environments
            '--no-sandbox',
            '--window-size=1920,1080',
        ]
        
        # Launch browser (using Chromium as it's more stable for scraping)
        browser = await playwright.chromium.launch(
            headless=self.stealth_mode,  # Visible mode can help avoid detection
            args=browser_args,
            ignore_default_args=['--enable-automation']  # Important to avoid detection
        )
        
        # Create browser context with specific settings
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(USER_AGENTS),
            has_touch=True,  # Simulate a touch device
            java_script_enabled=True,
            locale='fr-FR',  # French localization
            timezone_id='Europe/Paris',  # French timezone
            bypass_csp=True,  # Bypass content security policy
            accept_downloads=True,
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fr,fr-FR;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        # Add scripts to avoid detection
        if self.stealth_mode:
            await context.add_init_script("""
            // Hide Playwright/Puppeteer indicators
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr', 'en-US', 'en'] });
            
            // WebGL modifications to avoid fingerprinting
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
              if (parameter === 37445) {
                return 'Intel Inc.';
              } else if (parameter === 37446) {
                return 'Intel Iris Pro Graphics';
              }
              return getParameter.apply(this, arguments);
            };
            
            // Hide Playwright-specific variables
            delete window.playwright;
            """)
        
        return playwright, browser, context

    async def extract_links_with_multiple_methods(self, page, url):
        """Extract links using different methods to maximize success chance"""
        all_links = set()
        
        # Method 1: Direct extraction via <a> selectors
        try:
            links = await page.query_selector_all('a[href]')
            for link in links:
                href = await link.get_attribute('href')
                if href and not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    full_url = urljoin(url, href)
                    all_links.add(full_url)
        except Exception as e:
            self.logger.error(f"Error extracting links via selectors: {e}")
        
        # Method 2: Use JavaScript to extract all possible links
        try:
            js_links = await page.evaluate("""
            () => {
                const extractedLinks = new Set();
                
                // Get all elements with href attribute
                document.querySelectorAll('[href]').forEach(el => {
                    if (el.href && !el.href.startsWith('javascript:') && 
                        !el.href.startsWith('mailto:') && !el.href.startsWith('tel:')) {
                        extractedLinks.add(el.href);
                    }
                });
                
                // Find links in onclick, data-attributes, etc.
                document.querySelectorAll('*').forEach(el => {
                    // Search in onclick
                    if (el.onclick) {
                        const onclickStr = el.onclick.toString();
                        const matches = onclickStr.match(/window\.location\.href\s*=\s*['"]([^'"]+)['"]/g);
                        if (matches) {
                            matches.forEach(match => {
                                const url = match.replace(/window\.location\.href\s*=\s*['"]/g, '').replace(/['"]$/, '');
                                if (url) extractedLinks.add(url);
                            });
                        }
                    }
                    
                    // Search in data-attributes
                    if (el.dataset) {
                        Object.values(el.dataset).forEach(value => {
                            if (value && value.startsWith('http')) {
                                extractedLinks.add(value);
                            }
                        });
                    }
                });
                
                return Array.from(extractedLinks);
            }
            """)
            all_links.update(js_links)
        except Exception as e:
            self.logger.error(f"Error extracting links via JavaScript: {e}")
        
        return all_links

    async def visit_page(self, context, url, visited_links, all_links, failed_links):
        """Visit a page and extract all internal links"""
        page = None
        try:
            # Create a new page for each visit (to avoid state problems)
            page = await context.new_page()
            
            # Actions to act like a real user
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            
            # Wait a random time like a real user would
            await asyncio.sleep(random.uniform(1, 2))
            
            # Simulate random mouse movements
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            
            # Wait for the page to be truly loaded
            await page.wait_for_load_state("networkidle", timeout=self.timeout)
            
            # Scroll the page like a real user
            await page.evaluate("""
            async () => {
                const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
                
                // Progressive scrolling with random pauses
                const height = document.body.scrollHeight;
                const steps = 10;
                const stepSize = height / steps;
                
                for (let i = 1; i <= steps; i++) {
                    window.scrollTo(0, stepSize * i);
                    await sleep(Math.random() * 500 + 200);  // Random pause
                }
                
                // Scroll back a bit
                window.scrollTo(0, height * 0.7);
                await sleep(300);
                
                // Scroll back to top
                window.scrollTo(0, 0);
            }
            """)
            
            # Try to close popups and cookies
            try:
                # List of common selectors for cookie banners and popups
                popup_selectors = [
                    'button[aria-label="Close"]',
                    '.cookie-banner button', 
                    '#cookieConsent button',
                    '.consent-banner button',
                    '.popup-close',
                    '.modal-close',
                    '.close-button',
                    '.cookie-accept',
                    '.cookies-accept',
                    '.accept-cookies',
                    'button:has-text("Accepter")',
                    'button:has-text("J\'accepte")',
                    'button:has-text("Accepter les cookies")',
                    'a:has-text("Accepter")',
                    '[data-testid="cookie-policy-dialog-accept-button"]',
                    '[class*="cookie"] [class*="accept"]',
                    '[class*="cookie"] [class*="close"]',
                    '[id*="cookie"] [id*="accept"]',
                    '[id*="cookie"] [id*="close"]'
                ]
                
                for selector in popup_selectors:
                    try:
                        if await page.query_selector(selector):
                            await page.click(selector, timeout=5000)
                            await asyncio.sleep(0.5)
                    except Exception:
                        continue  # Ignore if the selector doesn't exist or isn't clickable
            except Exception as e:
                self.logger.error(f"Error closing popups: {e}")
            
            # Wait a bit longer to make sure everything is loaded
            await asyncio.sleep(1)
            
            # Extract all links
            raw_links = await self.extract_links_with_multiple_methods(page, url)
            
            # Filter to keep only internal links
            internal_links = set()
            for link in raw_links:
                try:
                    # URL cleaning and normalization
                    parsed = urlparse(link)
                    
                    # Check if it's an internal link
                    if parsed.netloc == self.site_path or parsed.netloc == f"www.{self.site_path}":
                        # Ignore files and images
                        if not any(link.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif', '.zip', '.mp3', '.mp4']):
                            # Normalize the URL
                            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                            if parsed.path.endswith('/'):
                                normalized_url = normalized_url[:-1]
                                
                            # Keep important parameters
                            if parsed.query:
                                params = parsed.query.split('&')
                                important_params = [p for p in params if p.startswith(('id=', 'page=', 'category=', 'p='))]
                                if important_params:
                                    normalized_url += '?' + '&'.join(important_params)
                                    
                            internal_links.add(normalized_url)
                except Exception:
                    continue
            
            # Add discovered links
            new_links_found = 0
            for link in internal_links:
                if link not in all_links:
                    all_links.add(link)
                    new_links_found += 1
            
            self.logger.info(f"  → {new_links_found} new URLs discovered on this page")
            
            # Close the page
            await page.close()
            return internal_links, True
        
        except Exception as e:
            self.logger.error(f"Error visiting {url}: {e}")
            if page:
                try:
                    await page.close()
                except:
                    pass
            return set(), False

    def save_urls_to_json(self, urls):
        """Save the URL list to a JSON file"""
        try:
            # Create the output directory if needed
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Full path of the file
            filepath = os.path.join(self.output_dir, self.output_file)
            
            # Prepare the data
            data = {
                "urls": sorted(list(urls)),
                "count": len(urls),
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"URLs saved to {filepath}")
            return filepath
        
        except Exception as e:
            self.logger.error(f"Error saving URLs: {e}")
            return None

    async def crawl(self):
        """Main crawling function with advanced techniques"""
        # Load already discovered URLs
        existing_urls = await self.load_existing_urls()
        self.logger.info(f"Loaded {len(existing_urls)} already discovered URLs.")
        
        all_links = existing_urls.copy()  # Known URLs
        visited_links = set()  # URLs visited in this session
        failed_links = set()  # Failed URLs
        
        # Determine URLs to visit
        if existing_urls:
            # Start with existing unvisited URLs
            links_to_visit = existing_urls.copy()
            self.logger.info(f"Resuming crawling with {len(links_to_visit)} URLs to explore.")
        else:
            # New crawling, start with the starting URL
            links_to_visit = {self.start_url}
            self.logger.info(f"Starting new crawling from {self.start_url}")
        
        # Configure the browser with advanced settings
        playwright, browser, context = await self.configure_browser()
        
        try:
            # Page visit counter
            pages_visited = 0
            
            # While there are links to visit and we haven't reached the limit
            while links_to_visit and pages_visited < self.max_pages:
                # Take a random link (more human-like behavior than a FIFO queue)
                current_url = random.choice(list(links_to_visit))
                links_to_visit.remove(current_url)
                
                # Check if already visited
                if current_url in visited_links:
                    continue
                
                # Mark as visited
                visited_links.add(current_url)
                pages_visited += 1
                
                self.logger.info(f"Visiting page {pages_visited}/{self.max_pages}: {current_url}")
                
                # Make multiple attempts if needed
                success = False
                for attempt in range(self.retries):
                    if attempt > 0:
                        self.logger.info(f"  Attempt {attempt+1}/{self.retries}")
                    
                    # Visit the page and extract links
                    internal_links, visit_success = await self.visit_page(
                        context, current_url, visited_links, all_links, failed_links
                    )
                    
                    if visit_success:
                        success = True
                        
                        # Add new links to visit
                        for link in internal_links:
                            if link not in visited_links and link not in links_to_visit and link not in failed_links:
                                links_to_visit.add(link)
                        
                        # Save periodically
                        if pages_visited % 5 == 0:
                            self.save_urls_to_json(all_links)
                            
                        break  # Exit the attempt loop
                    
                    # In case of failure, wait a bit longer before retrying
                    await asyncio.sleep(random.uniform(5, 10))
                
                if not success:
                    failed_links.add(current_url)
                    self.logger.error(f"  All attempts failed for {current_url}")
                
                # Wait between each page (variable delay to appear human)
                await asyncio.sleep(random.uniform(self.delay_min, self.delay_max))
        
        except Exception as e:
            self.logger.error(f"Error in the main crawling loop: {e}")
        
        finally:
            # Close the browser
            await browser.close()
            await playwright.stop()
            
            # Display statistics
            self.logger.info(f"\nCrawling finished.")
            self.logger.info(f"- {len(all_links)} unique links total")
            self.logger.info(f"- {pages_visited} pages visited in this session")
            self.logger.info(f"- {len(failed_links)} failed pages")
            
            # Save final results
            output_file = self.save_urls_to_json(all_links)
            
            return {
                "urls_count": len(all_links),
                "pages_visited": pages_visited,
                "failed_urls": len(failed_links),
                "output_file": output_file
            }


async def run_crawler(config_override=None):
    """Helper function to create and run a crawler instance"""
    crawler = Crawler(config_override)
    return await crawler.crawl()