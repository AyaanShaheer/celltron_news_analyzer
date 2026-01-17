"""
LLM Analyzer Module
Uses Google Gemini to analyze news articles for gist, sentiment, and tone.
"""

import os
import logging
import json
import time
from typing import Dict, Optional
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMAnalyzerError(Exception):
    """Custom exception for LLM Analyzer errors"""
    pass


class LLMAnalyzer:
    """
    Analyzes news articles using Google Gemini.
    Extracts: gist, sentiment, tone
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google Gemini API key
            model_name: Model to use (default: gemini-2.5-flash)
            
        Raises:
            ValueError: If API key is empty
        """
        if not api_key:
            raise ValueError("Gemini API key cannot be empty")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        logger.info(f"LLMAnalyzer initialized with model: {model_name}")
    
    def analyze_article(self, article: Dict, retry_count: int = 3) -> Dict:
        """
        Analyze a single article for gist, sentiment, and tone.
        
        Args:
            article: Article dict with 'title', 'full_text', 'id'
            retry_count: Number of retries on failure
            
        Returns:
            Dict with analysis results
            
        Raises:
            LLMAnalyzerError: If analysis fails after retries
            ValueError: If article is invalid
        """
        # Validate input
        if not article or 'full_text' not in article:
            raise ValueError("Article must contain 'full_text' field")
        
        article_id = article.get('id', 'unknown')
        title = article.get('title', 'No title')
        text = article.get('full_text', '')
        
        if len(text.strip()) < 30:
            raise ValueError(f"Article {article_id} text too short for analysis")
        
        logger.info(f"Analyzing article {article_id}: {title[:50]}...")
        
        # Build the prompt
        prompt = self._build_analysis_prompt(title, text)
        
        # Try with retries
        for attempt in range(retry_count):
            try:
                response = self.model.generate_content(prompt)
                
                # Check if response was blocked
                if not response.text:
                    logger.warning(f"Empty response for article {article_id}, attempt {attempt + 1}")
                    if attempt < retry_count - 1:
                        time.sleep(1)
                        continue
                    else:
                        raise LLMAnalyzerError("Response was empty or blocked")
                
                # Parse the response
                analysis = self._parse_response(response.text, article_id)
                
                logger.info(f"✅ Successfully analyzed article {article_id}")
                return {
                    'article_id': article_id,
                    'title': title,
                    'gist': analysis['gist'],
                    'sentiment': analysis['sentiment'],
                    'tone': analysis['tone'],
                    'model_used': self.model_name,
                    'raw_response': response.text
                }
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for article {article_id}: {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise LLMAnalyzerError(f"Failed to analyze article {article_id} after {retry_count} attempts: {str(e)}")
    
    def _build_analysis_prompt(self, title: str, text: str) -> str:
        """
        Build the prompt for Gemini analysis.
        
        Args:
            title: Article title
            text: Article text
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a news analysis expert. Analyze the following news article and provide a structured response.

Article Title: {title}

Article Text: {text}

Provide your analysis in the following JSON format:
{{
    "gist": "A concise 1-2 sentence summary of the main news",
    "sentiment": "positive OR negative OR neutral",
    "tone": "Choose ONE from: urgent, analytical, satirical, balanced, critical, celebratory, alarming, informative"
}}

Rules:
1. Gist must be factual and concise (1-2 sentences max)
2. Sentiment must be exactly one of: positive, negative, neutral
3. Tone must be exactly one of the options provided
4. Return ONLY valid JSON, no additional text

JSON Response:"""
        
        return prompt
    
    def _parse_response(self, response_text: str, article_id: str) -> Dict:
        """
        Parse LLM response and extract structured data.
        
        Args:
            response_text: Raw response from LLM
            article_id: Article ID for error reporting
            
        Returns:
            Parsed analysis dict
            
        Raises:
            LLMAnalyzerError: If parsing fails
        """
        try:
            # Try to find JSON in the response
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1])
            
            # Try to parse JSON
            analysis = json.loads(response_text)
            
            # Validate required fields
            required_fields = ['gist', 'sentiment', 'tone']
            for field in required_fields:
                if field not in analysis:
                    raise LLMAnalyzerError(f"Missing required field: {field}")
            
            # Normalize sentiment
            sentiment = analysis['sentiment'].lower().strip()
            valid_sentiments = ['positive', 'negative', 'neutral']
            if sentiment not in valid_sentiments:
                logger.warning(f"Invalid sentiment '{sentiment}', defaulting to 'neutral'")
                sentiment = 'neutral'
            
            # Normalize tone
            tone = analysis['tone'].lower().strip()
            valid_tones = ['urgent', 'analytical', 'satirical', 'balanced', 'critical', 
                          'celebratory', 'alarming', 'informative']
            if tone not in valid_tones:
                logger.warning(f"Invalid tone '{tone}', defaulting to 'informative'")
                tone = 'informative'
            
            return {
                'gist': analysis['gist'].strip(),
                'sentiment': sentiment,
                'tone': tone
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for article {article_id}: {str(e)}")
            logger.error(f"Raw response: {response_text[:200]}")
            raise LLMAnalyzerError(f"Invalid JSON response: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error parsing response for article {article_id}: {str(e)}")
            raise LLMAnalyzerError(f"Failed to parse response: {str(e)}")
    
    def analyze_batch(self, articles: list, delay: float = 1.0) -> list:
        """
        Analyze multiple articles with rate limiting.
        
        Args:
            articles: List of article dicts
            delay: Delay between requests in seconds
            
        Returns:
            List of analysis results
        """
        results = []
        
        for idx, article in enumerate(articles):
            try:
                result = self.analyze_article(article)
                results.append(result)
                
                # Rate limiting
                if idx < len(articles) - 1:
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Failed to analyze article {article.get('id')}: {str(e)}")
                # Add error result
                results.append({
                    'article_id': article.get('id', 'unknown'),
                    'title': article.get('title', 'Unknown'),
                    'error': str(e),
                    'gist': 'Analysis failed',
                    'sentiment': 'neutral',
                    'tone': 'informative'
                })
        
        return results


def main():
    """Test the LLM analyzer"""
    from dotenv import load_dotenv
    from news_fetcher import NewsFetcher
    
    load_dotenv()
    
    # Get API keys
    gemini_key = os.getenv('GEMINI_API_KEY')
    newsapi_key = os.getenv('NEWSAPI_API_KEY')
    
    if not gemini_key or not newsapi_key:
        print("ERROR: API keys not found in .env file")
        return
    
    try:
        # Fetch articles
        print("📰 Fetching articles...")
        fetcher = NewsFetcher(newsapi_key)
        articles = fetcher.fetch_articles(query="India politics", max_articles=3)
        print(f"✅ Fetched {len(articles)} articles\n")
        
        # Analyze articles
        print("🤖 Analyzing with Gemini...")
        analyzer = LLMAnalyzer(gemini_key)
        
        for article in articles:
            print(f"\n{'='*80}")
            print(f"Article {article['id']}: {article['title']}")
            print(f"{'='*80}")
            
            result = analyzer.analyze_article(article)
            
            print(f"\n📝 Gist: {result['gist']}")
            print(f"😊 Sentiment: {result['sentiment']}")
            print(f"🎭 Tone: {result['tone']}")
            print(f"🤖 Model: {result['model_used']}")
            
            time.sleep(1)  # Rate limiting
        
        print("\n\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
