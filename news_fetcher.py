"""
News Fetcher Module
Fetches news articles from NewsAPI about Indian politics.
Handles errors, validates data, and normalizes output.
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime
import requests
from newsapi import NewsApiClient
from newsapi.newsapi_exception import NewsAPIException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsAPIError(Exception):
    """Custom exception for NewsAPI-related errors"""
    pass


class NewsFetcher:
    """
    Fetches and normalizes news articles from NewsAPI.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize NewsAPI client.
        
        Args:
            api_key: NewsAPI API key
            
        Raises:
            ValueError: If API key is empty or None
        """
        if not api_key:
            raise ValueError("NewsAPI key cannot be empty")
        
        self.api_key = api_key
        self.client = NewsApiClient(api_key=api_key)
        logger.info("NewsFetcher initialized successfully")
    
    def fetch_articles(
        self,
        query: str = "India politics",
        language: str = "en",
        max_articles: int = 12,
        sort_by: str = "publishedAt"
    ) -> List[Dict]:
        """
        Fetch news articles from NewsAPI.
        
        Args:
            query: Search query
            language: Language code (en, hi, etc.)
            max_articles: Maximum number of articles to fetch
            sort_by: Sort order (publishedAt, relevancy, popularity)
            
        Returns:
            List of normalized article dictionaries
            
        Raises:
            NewsAPIError: If API call fails
            ValueError: If parameters are invalid
        """
        # Validate inputs
        if not query or len(query.strip()) == 0:
            raise ValueError("Query cannot be empty")
        
        if max_articles < 1 or max_articles > 100:
            raise ValueError("max_articles must be between 1 and 100")
        
        logger.info(f"Fetching articles: query='{query}', max={max_articles}")
        
        try:
            # Fetch articles from NewsAPI
            response = self.client.get_everything(
                q=query,
                language=language,
                sort_by=sort_by,
                page_size=min(max_articles, 100)  # API limit is 100
            )
            
            # Check response status
            if response.get('status') != 'ok':
                raise NewsAPIError(f"API returned status: {response.get('status')}")
            
            articles = response.get('articles', [])
            
            if not articles:
                logger.warning(f"No articles found for query: '{query}'")
                return []
            
            # Normalize and validate articles
            normalized_articles = []
            for idx, article in enumerate(articles[:max_articles]):
                try:
                    normalized = self._normalize_article(article, idx)
                    if normalized:
                        normalized_articles.append(normalized)
                except Exception as e:
                    logger.warning(f"Failed to normalize article {idx}: {str(e)}")
                    continue
            
            logger.info(f"Successfully fetched {len(normalized_articles)} articles")
            return normalized_articles
            
        except NewsAPIException as e:
            logger.error(f"NewsAPI error: {str(e)}")
            raise NewsAPIError(f"Failed to fetch articles: {str(e)}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {str(e)}")
            raise NewsAPIError(f"Network error while fetching articles: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise NewsAPIError(f"Unexpected error: {str(e)}")
    
    def _normalize_article(self, article: Dict, index: int) -> Optional[Dict]:
        """
        Normalize and validate a single article.
        
        Args:
            article: Raw article from NewsAPI
            index: Article index for ID generation
            
        Returns:
            Normalized article dict or None if invalid
        """
        # Extract fields with defaults
        title = article.get('title', '').strip()
        description = (article.get('description') or '').strip()
        content = (article.get('content') or '').strip()
        
        # Skip if no meaningful content
        if not title or (not description and not content):
            logger.warning(f"Article {index} missing title or content")
            return None
        
        # Combine description and content for analysis
        full_text = f"{description} {content}".strip()
        
        # Remove common NewsAPI truncation markers
        if full_text.endswith('[+'):
            full_text = full_text[:-2].strip()
        if ' chars]' in full_text:
            full_text = full_text.split(' chars]')[0].strip()
        
        # Check minimum content length
        if len(full_text) < 50:
            logger.warning(f"Article {index} content too short: {len(full_text)} chars")
            return None
        
        # Parse published date
        published_at = article.get('publishedAt', '')
        try:
            published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            published_str = published_date.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            published_str = published_at
        
        return {
            'id': index + 1,
            'title': title,
            'description': description,
            'content': content,
            'full_text': full_text,
            'source': article.get('source', {}).get('name') or 'Unknown',
            'author': article.get('author') or 'Unknown',
            'url': article.get('url', ''),
            'published_at': published_str,
            'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def main():
    """Test the news fetcher"""
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('NEWSAPI_API_KEY')
    if not api_key:
        print("ERROR: NEWSAPI_API_KEY not found in .env file")
        return
    
    try:
        fetcher = NewsFetcher(api_key)
        articles = fetcher.fetch_articles(
            query="India politics",
            max_articles=5
        )
        
        print(f"\n✅ Successfully fetched {len(articles)} articles\n")
        
        for article in articles:
            print(f"ID: {article['id']}")
            print(f"Title: {article['title']}")
            print(f"Source: {article['source']}")
            print(f"Published: {article['published_at']}")
            print(f"Content length: {len(article['full_text'])} chars")
            print("-" * 80)
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
