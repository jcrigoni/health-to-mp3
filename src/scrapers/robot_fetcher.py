import requests
import os
from urllib.parse import urlparse
import time
import json

from src.utils import setup_logger


class RobotFetcher:
    def __init__(self, output_dir="robot_job/output_robot"):
        self.logger = setup_logger('robot_fetcher')
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
    def get_robots_txt(self, url):
        """Fetches robots.txt from a given domain"""
        try:
            # Parse the URL to get the domain
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            robots_url = f"{base_url}/robots.txt"
            
            self.logger.info(f"Fetching robots.txt from {robots_url}")
            
            # Make the request with a timeout
            response = requests.get(robots_url, timeout=10)
            
            # Check if successful
            if response.status_code == 200:
                return response.text
            else:
                self.logger.warning(f"Failed to fetch robots.txt: Status code {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching robots.txt from {url}: {str(e)}")
            return None
            
    def fetch_and_save(self, url):
        """Fetches robots.txt and saves it to a file"""
        try:
            robots_content = self.get_robots_txt(url)
            
            if robots_content:
                # Extract domain for the filename
                domain = urlparse(url).netloc
                
                # Clean up domain for filename
                domain = domain.replace(".", "_")
                
                # Create filename with timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{domain}_{timestamp}_robots.txt"
                
                # Save to file
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(robots_content)
                    
                self.logger.info(f"Saved robots.txt to {filepath}")
                return filepath
            else:
                self.logger.warning(f"No robots.txt content to save for {url}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error saving robots.txt for {url}: {str(e)}")
            return None
            
    def fetch_multiple(self, urls):
        """Fetches robots.txt for multiple URLs"""
        results = {
            "successful": [],
            "failed": []
        }
        
        for url in urls:
            try:
                result = self.fetch_and_save(url)
                if result:
                    results["successful"].append({
                        "url": url,
                        "file": result
                    })
                else:
                    results["failed"].append({
                        "url": url,
                        "reason": "Failed to fetch or save"
                    })
            except Exception as e:
                results["failed"].append({
                    "url": url,
                    "reason": str(e)
                })
                
        # Save summary
        summary_path = os.path.join(self.output_dir, f"summary_{time.strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
        self.logger.info(f"Processed {len(urls)} URLs, {len(results['successful'])} successful, {len(results['failed'])} failed")
        return results


def fetch_robots_txt(url):
    """Helper function to fetch robots.txt for a single URL"""
    fetcher = RobotFetcher()
    return fetcher.fetch_and_save(url)
    
def fetch_multiple_robots_txt(urls):
    """Helper function to fetch robots.txt for multiple URLs"""
    fetcher = RobotFetcher()
    return fetcher.fetch_multiple(urls)