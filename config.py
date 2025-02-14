# Contains all configuration settings for the scraper

SCRAPER_CONFIG = {
    # Browser settings
    'HEADLESS': True,
    'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    
    # Rate limiting
    'REQUESTS_PER_SECOND': 1,
    'DELAY_BETWEEN_REQUESTS': 2,  # seconds
    
    # Retry settings
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 5,  # seconds
    
    # Timeouts
    'PAGE_LOAD_TIMEOUT': 30000,  # 30000 milliseconds = 30 seconds
    'SCRIPT_TIMEOUT': 30000,  # 30000 milliseconds = 30 seconds
    
    # Storage settings
    'S3_BUCKET': 'testjsbucket2025',
    'S3_REGION': 'us-east-1',
    
    # Database settings
    'DB_HOST': 'localhost',
    'DB_PORT': 5432,
    'DB_NAME': 'beng',
    'DB_USER': 'jcr',
    'DB_PASSWORD': 'health',

    # Update frequency settings
    'UPDATE_FREQUENCY_DAYS': 30,  # Rescrape URLs every 30 days
    'UPDATE_BATCH_SIZE': 50      # Number of URLs to process in one batch
}

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add your AWS credentials here
AWS_CREDENTIALS = {
    'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),
    'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY')
}