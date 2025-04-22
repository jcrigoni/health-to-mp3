-- Initial creation of documents table for web scraping results
-- Created: 2025-04-22

CREATE TABLE scraped_pages (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add index for timestamp-based queries
CREATE INDEX idx_scraped_pages_timestamps ON scraped_pages(created_at DESC);

-- Add helpful comment about the purpose of this table
COMMENT ON TABLE scraped_pages IS 'Stores metadata for scraped web documents';