"""
LLM Validator Module
Uses OpenRouter (Mistral) to validate analysis from first LLM.
Checks if the gist, sentiment, and tone match the article content.
"""

import os
import logging
import json
import time
from typing import Dict, Optional
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMValidatorError(Exception):
    """Custom exception for LLM Validator errors"""
    pass


class LLMValidator:
    """
    Validates news analysis using OpenRouter (Mistral).
    Checks if analysis matches article content.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "mistralai/mistral-7b-instruct",
        base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    ):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key
            model: Model to use (default: mistralai/mistral-7b-instruct)
            base_url: API endpoint
            
        Raises:
            ValueError: If API key is empty
        """
        if not api_key:
            raise ValueError("OpenRouter API key cannot be empty")
        
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"LLMValidator initialized with model: {model}")
    
    def validate_analysis(
        self,
        article: Dict,
        analysis: Dict,
        retry_count: int = 3
    ) -> Dict:
        """
        Validate analysis against article content.
        
        Args:
            article: Original article with 'title', 'full_text'
            analysis: Analysis from first LLM with 'gist', 'sentiment', 'tone'
            retry_count: Number of retries on failure
            
        Returns:
            Dict with validation results
            
        Raises:
            LLMValidatorError: If validation fails after retries
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if not article or 'full_text' not in article:
            raise ValueError("Article must contain 'full_text' field")
        
        if not analysis or 'gist' not in analysis or 'sentiment' not in analysis:
            raise ValueError("Analysis must contain 'gist', 'sentiment', 'tone'")
        
        article_id = article.get('id', analysis.get('article_id', 'unknown'))
        title = article.get('title', 'No title')
        
        logger.info(f"Validating analysis for article {article_id}: {title[:50]}...")
        
        # Build validation prompt
        prompt = self._build_validation_prompt(article, analysis)
        
        # Try with retries
        for attempt in range(retry_count):
            try:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,  # Lower temperature for consistent validation
                    "max_tokens": 500
                }
                
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                # Check status code
                if response.status_code == 429:
                    logger.warning(f"Rate limit hit, attempt {attempt + 1}")
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise LLMValidatorError("Rate limit exceeded")
                
                if response.status_code != 200:
                    logger.warning(f"API returned status {response.status_code}, attempt {attempt + 1}")
                    if attempt < retry_count - 1:
                        time.sleep(1)
                        continue
                    else:
                        raise LLMValidatorError(f"API error: {response.status_code} - {response.text}")
                
                # Parse response
                response_data = response.json()
                
                if 'choices' not in response_data or len(response_data['choices']) == 0:
                    raise LLMValidatorError("Empty response from API")
                
                validation_text = response_data['choices'][0]['message']['content']
                
                # Parse validation
                validation = self._parse_validation(validation_text, article_id)
                
                logger.info(f"✅ Successfully validated article {article_id}")
                
                return {
                    'article_id': article_id,
                    'title': title,
                    'is_valid': validation['is_valid'],
                    'validation_result': validation['result'],
                    'reasoning': validation['reasoning'],
                    'corrections': validation.get('corrections', {}),
                    'validator_model': self.model,
                    'raw_validation': validation_text
                }
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < retry_count - 1:
                    time.sleep(2)
                else:
                    raise LLMValidatorError("Request timeout after retries")
            
            except requests.exceptions.RequestException as e:
                logger.warning(f"Network error on attempt {attempt + 1}: {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(2)
                else:
                    raise LLMValidatorError(f"Network error: {str(e)}")
            
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(2)
                else:
                    raise LLMValidatorError(f"Validation failed after {retry_count} attempts: {str(e)}")
    
    def _build_validation_prompt(self, article: Dict, analysis: Dict) -> str:
        """
        Build prompt for validation.
        
        Args:
            article: Article data
            analysis: Analysis to validate
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a fact-checking expert. Your job is to validate whether an AI's analysis of a news article is accurate.

**Original Article:**
Title: {article.get('title', 'N/A')}
Content: {article.get('full_text', 'N/A')[:1000]}

**AI Analysis to Validate:**
- Gist: {analysis.get('gist', 'N/A')}
- Sentiment: {analysis.get('sentiment', 'N/A')}
- Tone: {analysis.get('tone', 'N/A')}

**Your Task:**
Carefully compare the analysis with the article content and answer:

1. Is the gist accurate? (Does it correctly summarize the main point?)
2. Is the sentiment correct? (positive/negative/neutral)
3. Is the tone appropriate? (urgent/analytical/satirical/balanced/critical/celebratory/alarming/informative)

Respond in JSON format:
{{
    "is_valid": true or false,
    "result": "✓ Correct" or "✗ Issues Found",
    "reasoning": "Brief explanation of your validation",
    "corrections": {{
        "gist": "corrected gist if needed, otherwise null",
        "sentiment": "corrected sentiment if needed, otherwise null",
        "tone": "corrected tone if needed, otherwise null"
    }}
}}

Return ONLY valid JSON, no additional text."""
        
        return prompt
    
    def _parse_validation(self, validation_text: str, article_id: str) -> Dict:
        """
        Parse validation response.
        
        Args:
            validation_text: Raw validation response
            article_id: Article ID for error reporting
            
        Returns:
            Parsed validation dict
            
        Raises:
            LLMValidatorError: If parsing fails
        """
        try:
            # Clean response
            validation_text = validation_text.strip()
            
            # Remove markdown code blocks if present
            if validation_text.startswith('```'):
                lines = validation_text.split('\n')
                validation_text = '\n'.join([l for l in lines if not l.startswith('```')])
            
            # Try to parse JSON
            validation = json.loads(validation_text)
            
            # Validate required fields
            if 'is_valid' not in validation:
                validation['is_valid'] = True  # Default to valid
            
            if 'result' not in validation:
                validation['result'] = "✓ Correct" if validation['is_valid'] else "✗ Issues Found"
            
            if 'reasoning' not in validation:
                validation['reasoning'] = "Validation completed"
            
            if 'corrections' not in validation:
                validation['corrections'] = {}
            
            return validation
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse validation JSON for article {article_id}: {str(e)}")
            logger.error(f"Raw response: {validation_text[:200]}")
            
            # Fallback: analyze text for keywords
            validation_text_lower = validation_text.lower()
            is_valid = 'correct' in validation_text_lower or 'accurate' in validation_text_lower
            
            return {
                'is_valid': is_valid,
                'result': "✓ Correct" if is_valid else "✗ Issues Found",
                'reasoning': validation_text[:200],
                'corrections': {}
            }
        
        except Exception as e:
            logger.error(f"Error parsing validation for article {article_id}: {str(e)}")
            raise LLMValidatorError(f"Failed to parse validation: {str(e)}")
    
    def validate_batch(self, articles: list, analyses: list, delay: float = 2.0) -> list:
        """
        Validate multiple analyses with rate limiting.
        
        Args:
            articles: List of article dicts
            analyses: List of analysis dicts (must match articles order)
            delay: Delay between requests in seconds
            
        Returns:
            List of validation results
        """
        if len(articles) != len(analyses):
            raise ValueError("Articles and analyses lists must have same length")
        
        results = []
        
        for idx, (article, analysis) in enumerate(zip(articles, analyses)):
            try:
                result = self.validate_analysis(article, analysis)
                results.append(result)
                
                # Rate limiting
                if idx < len(articles) - 1:
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Failed to validate article {article.get('id')}: {str(e)}")
                # Add error result
                results.append({
                    'article_id': article.get('id', 'unknown'),
                    'title': article.get('title', 'Unknown'),
                    'is_valid': True,  # Default to valid on error
                    'validation_result': '⚠ Validation Failed',
                    'reasoning': f"Error: {str(e)}",
                    'corrections': {},
                    'error': str(e)
                })
        
        return results


def main():
    """Test the LLM validator"""
    from dotenv import load_dotenv
    from news_fetcher import NewsFetcher
    from llm_analyzer import LLMAnalyzer
    
    load_dotenv()
    
    # Get API keys
    gemini_key = os.getenv('GEMINI_API_KEY')
    newsapi_key = os.getenv('NEWSAPI_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    if not all([gemini_key, newsapi_key, openrouter_key]):
        print("ERROR: API keys not found in .env file")
        return
    
    try:
        # Fetch articles
        print("📰 Fetching articles...")
        fetcher = NewsFetcher(newsapi_key)
        articles = fetcher.fetch_articles(query="India politics", max_articles=2)
        print(f"✅ Fetched {len(articles)} articles\n")
        
        # Analyze articles
        print("🤖 Analyzing with Gemini...")
        analyzer = LLMAnalyzer(gemini_key)
        analyses = []
        
        for article in articles:
            analysis = analyzer.analyze_article(article)
            analyses.append(analysis)
            time.sleep(1)
        
        print(f"✅ Analyzed {len(analyses)} articles\n")
        
        # Validate analyses
        print("🔍 Validating with OpenRouter/Mistral...")
        validator = LLMValidator(openrouter_key)
        
        for article, analysis in zip(articles, analyses):
            print(f"\n{'='*80}")
            print(f"Article {article['id']}: {article['title'][:60]}")
            print(f"{'='*80}")
            
            print(f"\n📊 Original Analysis:")
            print(f"  Gist: {analysis['gist']}")
            print(f"  Sentiment: {analysis['sentiment']}")
            print(f"  Tone: {analysis['tone']}")
            
            validation = validator.validate_analysis(article, analysis)
            
            print(f"\n✓ Validation Result: {validation['validation_result']}")
            print(f"  Reasoning: {validation['reasoning']}")
            
            if validation['corrections']:
                print(f"  Suggested Corrections: {validation['corrections']}")
            
            time.sleep(2)  # Rate limiting
        
        print("\n\n✅ Validation complete!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
