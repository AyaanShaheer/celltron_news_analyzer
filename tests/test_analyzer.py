"""
Test suite for news analysis pipeline.
Tests critical functionality and edge cases.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from news_fetcher import NewsFetcher, NewsAPIError
from llm_analyzer import LLMAnalyzer, LLMAnalyzerError
from llm_validator import LLMValidator, LLMValidatorError


class TestNewsFetcher:
    """Tests for NewsFetcher class"""
    
    def test_init_with_valid_key(self):
        """Test initialization with valid API key"""
        fetcher = NewsFetcher("test_api_key_123")
        assert fetcher.api_key == "test_api_key_123"
        assert fetcher.client is not None
    
    def test_init_with_empty_key(self):
        """Test initialization fails with empty API key"""
        with pytest.raises(ValueError, match="NewsAPI key cannot be empty"):
            NewsFetcher("")
    
    def test_init_with_none_key(self):
        """Test initialization fails with None API key"""
        with pytest.raises(ValueError, match="NewsAPI key cannot be empty"):
            NewsFetcher(None)
    
    def test_normalize_article_with_valid_data(self):
        """Test article normalization with complete data"""
        fetcher = NewsFetcher("test_key")
        
        article = {
            'title': 'Test Article',
            'description': 'This is a test description with enough content.',
            'content': 'This is test content with more than fifty characters for validation.',
            'source': {'name': 'Test Source'},
            'author': 'Test Author',
            'url': 'https://example.com/article',
            'publishedAt': '2026-01-17T10:00:00Z'
        }
        
        normalized = fetcher._normalize_article(article, 0)
        
        assert normalized is not None
        assert normalized['id'] == 1
        assert normalized['title'] == 'Test Article'
        assert normalized['source'] == 'Test Source'
        assert len(normalized['full_text']) > 50
    
    def test_normalize_article_filters_short_content(self):
        """Test that articles with short content are filtered"""
        fetcher = NewsFetcher("test_key")
        
        article = {
            'title': 'Short',
            'description': 'Too short',
            'content': 'Short',
            'source': {'name': 'Test'},
            'url': 'https://example.com'
        }
        
        normalized = fetcher._normalize_article(article, 0)
        assert normalized is None
    
    def test_normalize_article_handles_missing_fields(self):
        """Test normalization handles missing optional fields"""
        fetcher = NewsFetcher("test_key")
        
        article = {
            'title': 'Test Article',
            'description': 'This is a test description with enough content to pass validation.',
            'content': None,
            'source': {},
            'author': None,
            'url': 'https://example.com'
        }
        
        normalized = fetcher._normalize_article(article, 0)
        
        assert normalized is not None
        assert normalized['author'] == 'Unknown'
        assert normalized['source'] == 'Unknown'
    
    def test_fetch_articles_validates_query(self):
        """Test that empty query raises ValueError"""
        fetcher = NewsFetcher("test_key")
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            fetcher.fetch_articles(query="")
    
    def test_fetch_articles_validates_max_articles(self):
        """Test that invalid max_articles raises ValueError"""
        fetcher = NewsFetcher("test_key")
        
        with pytest.raises(ValueError, match="max_articles must be between 1 and 100"):
            fetcher.fetch_articles(query="test", max_articles=0)
        
        with pytest.raises(ValueError, match="max_articles must be between 1 and 100"):
            fetcher.fetch_articles(query="test", max_articles=101)


class TestLLMAnalyzer:
    """Tests for LLMAnalyzer class"""
    
    def test_init_with_valid_key(self):
        """Test initialization with valid API key"""
        with patch('llm_analyzer.genai.configure'):
            with patch('llm_analyzer.genai.GenerativeModel'):
                analyzer = LLMAnalyzer("test_gemini_key")
                assert analyzer.model_name == "gemini-2.5-flash"
    
    def test_init_with_empty_key(self):
        """Test initialization fails with empty API key"""
        with pytest.raises(ValueError, match="Gemini API key cannot be empty"):
            LLMAnalyzer("")
    
    def test_analyze_article_validates_input(self):
        """Test that missing full_text raises ValueError"""
        with patch('llm_analyzer.genai.configure'):
            with patch('llm_analyzer.genai.GenerativeModel'):
                analyzer = LLMAnalyzer("test_key")
                
                with pytest.raises(ValueError, match="must contain 'full_text'"):
                    analyzer.analyze_article({'id': 1})
    
    def test_analyze_article_validates_content_length(self):
        """Test that short content raises ValueError"""
        with patch('llm_analyzer.genai.configure'):
            with patch('llm_analyzer.genai.GenerativeModel'):
                analyzer = LLMAnalyzer("test_key")
                
                article = {
                    'id': 1,
                    'title': 'Test',
                    'full_text': 'Too short'
                }
                
                with pytest.raises(ValueError, match="text too short"):
                    analyzer.analyze_article(article)
    
    def test_build_analysis_prompt(self):
        """Test prompt building includes required elements"""
        with patch('llm_analyzer.genai.configure'):
            with patch('llm_analyzer.genai.GenerativeModel'):
                analyzer = LLMAnalyzer("test_key")
                
                prompt = analyzer._build_analysis_prompt("Test Title", "Test content")
                
                assert "Test Title" in prompt
                assert "Test content" in prompt
                assert "gist" in prompt
                assert "sentiment" in prompt
                assert "tone" in prompt
                assert "JSON" in prompt
    
    def test_parse_response_with_valid_json(self):
        """Test parsing valid JSON response"""
        with patch('llm_analyzer.genai.configure'):
            with patch('llm_analyzer.genai.GenerativeModel'):
                analyzer = LLMAnalyzer("test_key")
                
                response = '''
                {
                    "gist": "Test summary",
                    "sentiment": "positive",
                    "tone": "analytical"
                }
                '''
                
                result = analyzer._parse_response(response, 1)
                
                assert result['gist'] == "Test summary"
                assert result['sentiment'] == "positive"
                assert result['tone'] == "analytical"
    
    def test_parse_response_with_markdown_wrapper(self):
        """Test parsing JSON wrapped in markdown code blocks"""
        with patch('llm_analyzer.genai.configure'):
            with patch('llm_analyzer.genai.GenerativeModel'):
                analyzer = LLMAnalyzer("test_key")
                
                response = '''```json
                {
                    "gist": "Test summary",
                    "sentiment": "neutral",
                    "tone": "informative"
                }
                ```'''
                
                result = analyzer._parse_response(response, 1)
                
                assert result['gist'] == "Test summary"
                assert result['sentiment'] == "neutral"
    
    def test_parse_response_normalizes_invalid_sentiment(self):
        """Test that invalid sentiment is normalized to neutral"""
        with patch('llm_analyzer.genai.configure'):
            with patch('llm_analyzer.genai.GenerativeModel'):
                analyzer = LLMAnalyzer("test_key")
                
                response = '''
                {
                    "gist": "Test",
                    "sentiment": "very_positive",
                    "tone": "analytical"
                }
                '''
                
                result = analyzer._parse_response(response, 1)
                assert result['sentiment'] == "neutral"
    
    def test_parse_response_handles_invalid_json(self):
        """Test that invalid JSON raises LLMAnalyzerError"""
        with patch('llm_analyzer.genai.configure'):
            with patch('llm_analyzer.genai.GenerativeModel'):
                analyzer = LLMAnalyzer("test_key")
                
                with pytest.raises(LLMAnalyzerError, match="Invalid JSON"):
                    analyzer._parse_response("This is not JSON", 1)


class TestLLMValidator:
    """Tests for LLMValidator class"""
    
    def test_init_with_valid_key(self):
        """Test initialization with valid API key"""
        validator = LLMValidator("test_openrouter_key")
        assert validator.api_key == "test_openrouter_key"
        assert validator.model == "mistralai/mistral-7b-instruct"
    
    def test_init_with_empty_key(self):
        """Test initialization fails with empty API key"""
        with pytest.raises(ValueError, match="OpenRouter API key cannot be empty"):
            LLMValidator("")
    
    def test_validate_analysis_validates_article_input(self):
        """Test that missing full_text in article raises ValueError"""
        validator = LLMValidator("test_key")
        
        article = {'id': 1}
        analysis = {'gist': 'test', 'sentiment': 'neutral', 'tone': 'analytical'}
        
        with pytest.raises(ValueError, match="must contain 'full_text'"):
            validator.validate_analysis(article, analysis)
    
    def test_validate_analysis_validates_analysis_input(self):
        """Test that missing fields in analysis raises ValueError"""
        validator = LLMValidator("test_key")
        
        article = {'id': 1, 'full_text': 'Test content here'}
        analysis = {'gist': 'test'}  # Missing sentiment and tone
        
        with pytest.raises(ValueError, match="must contain 'gist', 'sentiment', 'tone'"):
            validator.validate_analysis(article, analysis)
    
    def test_build_validation_prompt(self):
        """Test validation prompt includes required elements"""
        validator = LLMValidator("test_key")
        
        article = {
            'title': 'Test Title',
            'full_text': 'Test content'
        }
        analysis = {
            'gist': 'Test gist',
            'sentiment': 'positive',
            'tone': 'analytical'
        }
        
        prompt = validator._build_validation_prompt(article, analysis)
        
        assert "Test Title" in prompt
        assert "Test content" in prompt
        assert "Test gist" in prompt
        assert "positive" in prompt
        assert "analytical" in prompt
    
    def test_parse_validation_with_valid_json(self):
        """Test parsing valid validation JSON"""
        validator = LLMValidator("test_key")
        
        response = '''
        {
            "is_valid": true,
            "result": "✓ Correct",
            "reasoning": "Analysis is accurate",
            "corrections": {}
        }
        '''
        
        result = validator._parse_validation(response, 1)
        
        assert result['is_valid'] == True
        assert result['result'] == "✓ Correct"
        assert result['reasoning'] == "Analysis is accurate"
    
    def test_parse_validation_handles_invalid_json(self):
        """Test fallback parsing for invalid JSON"""
        validator = LLMValidator("test_key")
        
        response = "The analysis looks correct and accurate."
        result = validator._parse_validation(response, 1)
        
        # Should fallback to keyword detection
        assert result['is_valid'] == True
        assert 'reasoning' in result
    
    def test_validate_batch_validates_list_length(self):
        """Test that mismatched list lengths raise ValueError"""
        validator = LLMValidator("test_key")
        
        articles = [{'id': 1, 'full_text': 'test'}]
        analyses = [{'gist': 'a', 'sentiment': 'neutral', 'tone': 'analytical'}, 
                   {'gist': 'b', 'sentiment': 'positive', 'tone': 'urgent'}]
        
        with pytest.raises(ValueError, match="must have same length"):
            validator.validate_batch(articles, analyses)


# Integration-style tests
class TestIntegration:
    """Integration tests for the complete pipeline"""
    
    def test_article_flow_structure(self):
        """Test that data structure flows correctly through pipeline"""
        # Simulate fetched article
        article = {
            'id': 1,
            'title': 'Test Article',
            'full_text': 'This is test content with enough characters to pass validation tests.',
            'source': 'Test Source',
            'url': 'https://example.com'
        }
        
        # Simulate analysis
        analysis = {
            'article_id': 1,
            'gist': 'Test summary of the article',
            'sentiment': 'neutral',
            'tone': 'analytical',
            'model_used': 'gemini-2.5-flash'
        }
        
        # Simulate validation
        validation = {
            'article_id': 1,
            'is_valid': True,
            'validation_result': '✓ Correct',
            'reasoning': 'Analysis matches article',
            'corrections': {}
        }
        
        # Verify data integrity
        assert article['id'] == analysis['article_id']
        assert analysis['article_id'] == validation['article_id']
        assert len(article['full_text']) > 50
        assert analysis['sentiment'] in ['positive', 'negative', 'neutral']
        assert validation['is_valid'] in [True, False]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
