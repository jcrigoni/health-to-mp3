import argparse
import asyncio
import os
import json
from datetime import datetime

from src.config import config
from src.utils import setup_logger
from src.scrapers.web_scraper import WebScraper, process_urls_from_json
from src.scrapers.crawler import Crawler, run_crawler
from src.processors.summarizer import Summarizer, summarize_directory
from src.processors.translator import Translator, translate_directory
from src.processors.voicerizor import process_directory as process_to_speech


def setup_parser():
    parser = argparse.ArgumentParser(description='Article Processing Toolkit')
    parser.add_argument('--version', action='version', version='Health-MP3 1.0.0')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Crawler command 
    crawler_parser = subparsers.add_parser('crawl', help='Crawl a website for URLs')
    crawler_parser.add_argument('--site', default=config.CRAWLER_CONFIG['SITE_PATH'], help='Site to crawl')
    crawler_parser.add_argument('--start-url', default=config.CRAWLER_CONFIG['START_URL'], help='Starting URL')
    crawler_parser.add_argument('--output-dir', default=config.CRAWLER_CONFIG['OUTPUT_DIR'], help='Output directory')
    crawler_parser.add_argument('--max-pages', type=int, default=config.CRAWLER_CONFIG['MAX_PAGES'], help='Maximum pages to crawl')
    
    # Scraper command
    scraper_parser = subparsers.add_parser('scrape', help='Scrape content from URLs')
    scraper_parser.add_argument('--urls-file', required=True, help='Path to JSON file with URLs')
    scraper_parser.add_argument('--output-dir', help='Output directory (default: timestamped directory)')
    
    # Summarize command
    summarize_parser = subparsers.add_parser('summarize', help='Summarize content')
    summarize_parser.add_argument('--input-dir', required=True, help='Directory with markdown files to summarize')
    summarize_parser.add_argument('--output-dir', help='Output directory for summaries')
    
    # Translate command
    translate_parser = subparsers.add_parser('translate', help='Translate content')
    translate_parser.add_argument('--input-dir', required=True, help='Directory with files to translate')
    translate_parser.add_argument('--output-dir', help='Output directory for translations')
    translate_parser.add_argument('--pattern', default='*.md', help='File pattern to match for translation')
    
    # Text to Speech command
    speech_parser = subparsers.add_parser('speech', help='Convert markdown to MP3 audio files')
    speech_parser.add_argument('--input-dir', required=True, help='Directory with markdown files to convert')
    speech_parser.add_argument('--output-dir', help='Output directory for MP3 files')
    speech_parser.add_argument('--lang', default='f', help='Language code: f for French, a for American English, etc.')
    speech_parser.add_argument('--voice', default='ff_siwis', help='Voice model to use')
    
    # Pipeline command (crawl, scrape, translate - no summarization)
    pipeline_parser = subparsers.add_parser('pipeline', help='Run the full pipeline (crawl, scrape, translate)')
    pipeline_parser.add_argument('--site', default=config.CRAWLER_CONFIG['SITE_PATH'], help='Site to crawl')
    pipeline_parser.add_argument('--start-url', default=config.CRAWLER_CONFIG['START_URL'], help='Starting URL')
    pipeline_parser.add_argument('--max-pages', type=int, default=100, help='Maximum pages to crawl')
    pipeline_parser.add_argument('--with-speech', action='store_true', help='Include text-to-speech generation')
    pipeline_parser.add_argument('--lang', default='f', help='Language code for text-to-speech')
    pipeline_parser.add_argument('--voice', default='ff_siwis', help='Voice model for text-to-speech')
    
    return parser


def print_custom_help():
    help_text = """
Health-MP3 - A toolkit for scraping health blogs, summarizing, translating, and converting content to audio

Basic Usage:
  python main.py <command> [options]

Available Commands:
  crawl      - Crawl a website to discover URLs
  scrape     - Scrape content from URLs saved in a JSON file
  translate  - Translate content from English to French
  summarize  - Summarize content using BART-large-CNN
  speech     - Convert markdown files to MP3 audio files
  pipeline   - Run complete pipeline (crawl, scrape, translate, optional speech)

Examples:
  python3 main.py crawl --site example.com --start-url https://example.com/ --max-pages 100
  python3 main.py scrape --urls-file urls_job/output_url/urls.json
  python3 main.py translate --input-dir content_dir --output-dir translations
  python3 main.py summarize --input-dir content_dir --output-dir summaries
  python3 main.py speech --input-dir data --output-dir audio_files
  python3 main.py pipeline --site example.com --start-url https://example.com/ --with-speech

For detailed help on any command:
  python main.py <command> --help
"""
    print(help_text)

async def main():
    logger = setup_logger('main')
    parser = setup_parser()
    args = parser.parse_args()
    
    if not args.command:
        print_custom_help()
        return
    
    try:
        if args.command == 'crawl':
            # Override config with command line arguments
            crawler_config = config.CRAWLER_CONFIG.copy()
            crawler_config['SITE_PATH'] = args.site
            crawler_config['START_URL'] = args.start_url
            crawler_config['OUTPUT_DIR'] = args.output_dir
            crawler_config['MAX_PAGES'] = args.max_pages
            
            logger.info(f"Starting crawler for {args.site}")
            result = await run_crawler(crawler_config)
            logger.info(f"Crawling complete. Found {result['urls_count']} URLs.")
            
        elif args.command == 'scrape':
            output_dir = args.output_dir or config.get_output_dir()
            logger.info(f"Starting scraper with URLs from {args.urls_file}")
            result = await process_urls_from_json(args.urls_file, output_dir)
            logger.info(f"Scraping complete. Results saved to {result['output_dir']}")
            
        elif args.command == 'summarize':
            logger.info(f"Starting summarization of files in {args.input_dir}")
            result = summarize_directory(args.input_dir, args.output_dir)
            logger.info(f"Summarization complete. Processed {result['processed']} files.")
            
        elif args.command == 'translate':
            logger.info(f"Starting translation of files in {args.input_dir}")
            result = translate_directory(args.input_dir, args.output_dir, args.pattern)
            logger.info(f"Translation complete. Processed {result['processed']} files.")
        
        elif args.command == 'speech':
            output_dir = args.output_dir or f"audio_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Starting text-to-speech conversion of files in {args.input_dir}")
            mp3_files = process_to_speech(
                args.input_dir,
                output_dir,
                lang_code=args.lang,
                voice=args.voice
            )
            logger.info(f"Text-to-speech conversion complete. Generated {len(mp3_files)} MP3 files in {output_dir}")
            
        elif args.command == 'pipeline':
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pipeline_dir = f"pipeline_{timestamp}"
            os.makedirs(pipeline_dir, exist_ok=True)
            
            # Step 1: Crawl
            crawler_config = config.CRAWLER_CONFIG.copy()
            crawler_config['SITE_PATH'] = args.site
            crawler_config['START_URL'] = args.start_url
            crawler_config['OUTPUT_DIR'] = os.path.join(pipeline_dir, "urls")
            crawler_config['MAX_PAGES'] = args.max_pages
            
            logger.info("PIPELINE STEP 1: Crawling")
            crawler_result = await run_crawler(crawler_config)
            
            # Step 2: Scrape
            logger.info("PIPELINE STEP 2: Scraping")
            scrape_dir = os.path.join(pipeline_dir, "content")
            scrape_result = await process_urls_from_json(crawler_result['output_file'], scrape_dir)
            
            # Step 3: Translate directly from scraped content
            logger.info("PIPELINE STEP 3: Translating")
            translation_dir = os.path.join(pipeline_dir, "translations")
            translation_result = translate_directory(scrape_dir, translation_dir, "*.md")
            
            # Step 4 (Optional): Text-to-speech conversion
            speech_result = None
            if args.with_speech:
                logger.info("PIPELINE STEP 4: Text-to-speech conversion")
                speech_dir = os.path.join(pipeline_dir, "audio")
                mp3_files = process_to_speech(
                    translation_dir,  # Use translated files as input
                    speech_dir,
                    lang_code=args.lang,
                    voice=args.voice
                )
                speech_result = {
                    "mp3_count": len(mp3_files),
                    "output_dir": speech_dir
                }
            
            # Save pipeline results
            pipeline_results = {
                "timestamp": timestamp,
                "crawler": crawler_result,
                "scraper": {
                    "output_dir": scrape_result["output_dir"],
                    "successful": scrape_result["successful"],
                    "failed": scrape_result["failed"],
                },
                "translator": {
                    "processed": translation_result["processed"],
                    "failed": translation_result["failed"],
                }
            }
            
            if speech_result:
                pipeline_results["speech"] = speech_result
                
            with open(os.path.join(pipeline_dir, "results.json"), "w") as f:
                json.dump(pipeline_results, f, indent=2)
                
            logger.info(f"Pipeline complete! All outputs saved in: {pipeline_dir}")
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}", exc_info=True)
        
        
if __name__ == "__main__":
    asyncio.run(main())