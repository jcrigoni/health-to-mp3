# Health-MP3

A complete pipeline for scraping health blogs, summarizing content, and converting to MP3.

## Features

- **Web Crawling**: Discover URLs on health websites with a stealth crawler
- **Content Scraping**: Extract article content and convert to clean markdown
- **Summarization**: Generate concise summaries using BART-large-CNN
- **Translation**: Translate content from English to French
- **Data Storage**: Store metadata in PostgreSQL database

## Installation

1. Clone the repository

```bash
git clone https://github.com/jcrigoni/health-mp3.git
cd health-mp3
```

2. Install dependencies with Pipenv

```bash
pipenv install
```

3. Activate the virtual environment

```bash
pipenv shell
```

## Usage

### Command Line Interface

The project provides a comprehensive CLI:

```bash
# Crawl a website for URLs
python main.py crawl --site example.com --start-url https://example.com/ --max-pages 100

# Scrape content from URLs
python main.py scrape --urls-file pipeline_20250422_150845/urls/urls.json 

# Summarize markdown content
python main.py summarize --input-dir output_data_2025_04_11_105443

# Translate content to "Language"
python main.py translate --input-dir summaries --pattern "*.txt"

# Run the complete pipeline (crawl, scrape, translate)
python main.py pipeline --site example.com --start-url https://example.com/ --max-pages 100

# If you want to use the summarizer (standalone)
python main.py summarize --input-dir output_data_20250411_105443 --output-dir summaries
```

### Environment Variables

Create a `.env` file with the following variables:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=health_articles
DB_USER=postgres
DB_PASSWORD=your_password
HEADLESS=true
DELAY_BETWEEN_REQUESTS=3.0
```

## Project Structure

- **/src/scrapers**: Web crawling and content extraction
- **/src/processors**: Text summarization and translation
- **/src/utils**: Shared utilities like logging
- **/src/config**: Configuration management
- **/src/cli**: Command-line interface

## License

This project is licensed under the MIT License - see the LICENSE file for details.