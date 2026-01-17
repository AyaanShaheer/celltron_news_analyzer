"""
Main Orchestration Module
Coordinates the entire news analysis pipeline:
1. Fetch news articles
2. Analyze with LLM#1 (Gemini)
3. Validate with LLM#2 (OpenRouter)
4. Generate outputs (JSON + Markdown report)
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

from news_fetcher import NewsFetcher
from llm_analyzer import LLMAnalyzer
from llm_validator import LLMValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsAnalysisPipeline:
    """
    Complete news analysis pipeline with dual LLM validation.
    """
    
    def __init__(
        self,
        newsapi_key: str,
        gemini_key: str,
        openrouter_key: str,
        output_dir: str = "output"
    ):
        """
        Initialize pipeline with API keys.
        
        Args:
            newsapi_key: NewsAPI key
            gemini_key: Google Gemini key
            openrouter_key: OpenRouter key
            output_dir: Directory for output files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize components
        logger.info("Initializing pipeline components...")
        self.fetcher = NewsFetcher(newsapi_key)
        self.analyzer = LLMAnalyzer(gemini_key)
        self.validator = LLMValidator(openrouter_key)
        logger.info("✅ Pipeline initialized successfully")
    
    def run(
        self,
        query: str = "India politics",
        max_articles: int = 12,
        language: str = "en"
    ) -> Dict:
        """
        Run the complete pipeline.
        
        Args:
            query: Search query for news
            max_articles: Maximum articles to process
            language: Language code
            
        Returns:
            Dict with pipeline results and statistics
        """
        start_time = datetime.now()
        logger.info(f"Starting pipeline: query='{query}', max_articles={max_articles}")
        
        try:
            # Step 1: Fetch articles
            logger.info("=" * 80)
            logger.info("STEP 1: Fetching news articles...")
            logger.info("=" * 80)
            articles = self.fetcher.fetch_articles(
                query=query,
                max_articles=max_articles,
                language=language
            )
            
            if not articles:
                raise ValueError("No articles fetched")
            
            logger.info(f"✅ Fetched {len(articles)} articles")
            
            # Save raw articles
            self._save_json(articles, "raw_articles.json")
            
            # Step 2: Analyze with Gemini
            logger.info("=" * 80)
            logger.info("STEP 2: Analyzing articles with Gemini...")
            logger.info("=" * 80)
            analyses = self.analyzer.analyze_batch(articles, delay=1.0)
            logger.info(f"✅ Analyzed {len(analyses)} articles")
            
            # Step 3: Validate with OpenRouter
            logger.info("=" * 80)
            logger.info("STEP 3: Validating analyses with OpenRouter/Mistral...")
            logger.info("=" * 80)
            validations = self.validator.validate_batch(articles, analyses, delay=2.0)
            logger.info(f"✅ Validated {len(validations)} analyses")
            
            # Step 4: Combine results
            logger.info("=" * 80)
            logger.info("STEP 4: Combining results...")
            logger.info("=" * 80)
            combined_results = self._combine_results(articles, analyses, validations)
            
            # Save analysis results
            self._save_json(combined_results, "analysis_results.json")
            
            # Step 5: Generate report
            logger.info("=" * 80)
            logger.info("STEP 5: Generating final report...")
            logger.info("=" * 80)
            report = self._generate_report(combined_results, query)
            self._save_report(report, "final_report.md")
            
            # Calculate statistics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            stats = self._calculate_statistics(combined_results, duration)
            
            logger.info("=" * 80)
            logger.info("✅ PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Total articles processed: {stats['total_articles']}")
            logger.info(f"Time taken: {stats['duration']:.2f} seconds")
            logger.info(f"Output files saved in: {self.output_dir}/")
            
            return {
                'success': True,
                'statistics': stats,
                'output_dir': self.output_dir
            }
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {str(e)}")
            raise
    
    def _combine_results(
        self,
        articles: List[Dict],
        analyses: List[Dict],
        validations: List[Dict]
    ) -> List[Dict]:
        """Combine all results into unified structure."""
        combined = []
        
        for article, analysis, validation in zip(articles, analyses, validations):
            combined.append({
                'article': {
                    'id': article['id'],
                    'title': article['title'],
                    'source': article['source'],
                    'author': article['author'],
                    'url': article['url'],
                    'published_at': article['published_at'],
                    'content': article['full_text']
                },
                'analysis': {
                    'gist': analysis.get('gist', 'N/A'),
                    'sentiment': analysis.get('sentiment', 'neutral'),
                    'tone': analysis.get('tone', 'informative'),
                    'model': analysis.get('model_used', 'unknown')
                },
                'validation': {
                    'is_valid': validation.get('is_valid', True),
                    'result': validation.get('validation_result', 'N/A'),
                    'reasoning': validation.get('reasoning', 'N/A'),
                    'corrections': validation.get('corrections', {}),
                    'validator_model': validation.get('validator_model', 'unknown')
                }
            })
        
        return combined
    
    def _calculate_statistics(self, results: List[Dict], duration: float) -> Dict:
        """Calculate statistics from results."""
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        tone_counts = {}
        validation_counts = {'valid': 0, 'invalid': 0}
        
        for result in results:
            # Count sentiments
            sentiment = result['analysis']['sentiment']
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
            
            # Count tones
            tone = result['analysis']['tone']
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
            
            # Count validations
            if result['validation']['is_valid']:
                validation_counts['valid'] += 1
            else:
                validation_counts['invalid'] += 1
        
        return {
            'total_articles': len(results),
            'duration': duration,
            'sentiment_distribution': sentiment_counts,
            'tone_distribution': tone_counts,
            'validation_stats': validation_counts
        }
    
    def _generate_report(self, results: List[Dict], query: str) -> str:
        """Generate Markdown report."""
        stats = self._calculate_statistics(results, 0)
        
        report = f"""# News Analysis Report

**Date:** {datetime.now().strftime('%B %d, %Y at %I:%M %p IST')}  
**Query:** {query}  
**Articles Analyzed:** {len(results)}  
**Source:** NewsAPI

---

## Summary

### Sentiment Distribution
- **Positive:** {stats['sentiment_distribution']['positive']} articles
- **Negative:** {stats['sentiment_distribution']['negative']} articles
- **Neutral:** {stats['sentiment_distribution']['neutral']} articles

### Tone Distribution
"""
        
        for tone, count in sorted(stats['tone_distribution'].items(), key=lambda x: x[1], reverse=True):
            report += f"- **{tone.capitalize()}:** {count} articles\n"
        
        report += f"""
### Validation Results
- **Valid Analyses:** {stats['validation_stats']['valid']} / {len(results)}
- **Issues Found:** {stats['validation_stats']['invalid']} / {len(results)}

---

## Detailed Analysis

"""
        
        for idx, result in enumerate(results, 1):
            article = result['article']
            analysis = result['analysis']
            validation = result['validation']
            
            report += f"""### Article {idx}: {article['title']}

**Source:** [{article['source']}]({article['url']})  
**Published:** {article['published_at']}  
**Author:** {article['author']}

#### Analysis (LLM#1: {analysis['model']})
- **Gist:** {analysis['gist']}
- **Sentiment:** {analysis['sentiment'].capitalize()}
- **Tone:** {analysis['tone'].capitalize()}

#### Validation (LLM#2: {validation['validator_model']})
- **Result:** {validation['result']}
- **Reasoning:** {validation['reasoning']}
"""
            
            if validation['corrections'] and any(validation['corrections'].values()):
                report += "\n**Suggested Corrections:**\n"
                for field, correction in validation['corrections'].items():
                    if correction:
                        report += f"- {field.capitalize()}: {correction}\n"
            
            report += "\n---\n\n"
        
        return report
    
    def _save_json(self, data: any, filename: str):
        """Save data as JSON."""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved: {filepath}")
    
    def _save_report(self, report: str, filename: str):
        """Save report as Markdown."""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"📄 Saved: {filepath}")


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()
    
    # Get API keys
    newsapi_key = os.getenv('NEWSAPI_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    # Validate keys
    if not all([newsapi_key, gemini_key, openrouter_key]):
        logger.error("❌ Missing API keys in .env file")
        logger.error("Required: NEWSAPI_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY")
        return
    
    # Get configuration
    query = os.getenv('NEWS_QUERY', 'India politics')
    max_articles = int(os.getenv('MAX_ARTICLES', 12))
    
    try:
        # Initialize and run pipeline
        pipeline = NewsAnalysisPipeline(newsapi_key, gemini_key, openrouter_key)
        result = pipeline.run(query=query, max_articles=max_articles)
        
        if result['success']:
            print("\n" + "=" * 80)
            print("✅ SUCCESS! All outputs generated.")
            print("=" * 80)
            print(f"\nOutput files in '{result['output_dir']}/':")
            print("  📄 raw_articles.json - Original fetched articles")
            print("  📄 analysis_results.json - Combined analysis & validation")
            print("  📄 final_report.md - Human-readable report")
            print("\nStatistics:")
            stats = result['statistics']
            print(f"  • Total articles: {stats['total_articles']}")
            print(f"  • Processing time: {stats['duration']:.2f}s")
            print(f"  • Positive: {stats['sentiment_distribution']['positive']}, "
                  f"Negative: {stats['sentiment_distribution']['negative']}, "
                  f"Neutral: {stats['sentiment_distribution']['neutral']}")
            print("=" * 80)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
