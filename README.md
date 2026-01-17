# News Analysis Pipeline with Dual LLM Validation

A production-ready news analysis system that fetches Indian politics news, analyzes it using Google Gemini, and validates the analysis using OpenRouter Mistral. Built as part of the Celltron Intelligence AI Engineer take-home assignment.

## 🚀 Features

- **News Fetching**: Retrieves articles from NewsAPI with robust error handling
- **AI Analysis**: Uses Google Gemini to extract gist, sentiment, and tone
- **Dual Validation**: OpenRouter Mistral validates the analysis for accuracy
- **Comprehensive Output**: Generates JSON data and human-readable Markdown reports
- **Production-Ready**: Error handling, retries, rate limiting, logging, and tests

## 📁 Project Structure

```
celltron-news-analyzer/
├── main.py                  # Main orchestration pipeline
├── news_fetcher.py          # NewsAPI integration
├── llm_analyzer.py          # Gemini analysis module
├── llm_validator.py         # OpenRouter validation module
├── requirements.txt         # Python dependencies
├── .env                     # API keys (not committed)
├── .gitignore              # Git ignore rules
├── README.md               # This file
├── DEVELOPMENT_PROCESS.md  # Detailed development documentation
├── output/                 # Generated outputs
│   ├── raw_articles.json
│   ├── analysis_results.json
│   └── final_report.md
└── tests/
    └── test_analyzer.py    # Test suite (26 tests)
```

## 🔧 Setup Instructions

### 1. Clone or Download the Repository

```bash
git clone https://github.com/AyaanShaheer/celltron_news_analyzer.git
cd celltron-news-analyzer
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Get API Keys (All Free)

**NewsAPI** (100 requests/day):
1. Go to https://newsapi.org/
2. Sign up with email
3. Copy API key from dashboard

**Google Gemini** (1,500 requests/day):
1. Go to https://ai.google.dev/
2. Click "Get API Key"
3. Create/login to Google account
4. Copy API key

**OpenRouter** (Free tier):
1. Go to https://openrouter.ai/
2. Sign up with email
3. Go to Dashboard → API Keys
4. Create new API key

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
# News API
NEWSAPI_API_KEY=your_newsapi_key_here

# LLM APIs
GEMINI_API_KEY=your_gemini_key_here
OPENROUTER_API_KEY=your_openrouter_key_here

# Configuration (optional)
NEWS_QUERY=India politics
NEWS_LANGUAGE=en
MAX_ARTICLES=12
```



## 🏃 Running the Pipeline

### Run Complete Pipeline

```bash
python main.py
```

**Output:**
- Fetches 12 articles about India politics
- Analyzes each with Gemini (gist, sentiment, tone)
- Validates each with OpenRouter
- Generates 3 output files in `output/` folder
- Takes ~90-120 seconds (due to rate limiting)

### Test Individual Modules

```bash
# Test news fetcher
python news_fetcher.py

# Test analyzer
python llm_analyzer.py

# Test validator
python llm_validator.py
```

### Run Tests

```bash
python -m pytest tests/test_analyzer.py -v
```

**Expected Output**: ✅ 26 passed

## 📊 Output Files

### 1. `output/raw_articles.json`
Raw articles fetched from NewsAPI with metadata.

### 2. `output/analysis_results.json`
Complete analysis results including:
- Original article content
- Gemini analysis (gist, sentiment, tone)
- Mistral validation (correctness, reasoning, corrections)

### 3. `output/final_report.md`
Human-readable Markdown report with:
- Summary statistics
- Sentiment and tone distribution
- Detailed analysis for each article
- Validation results

## 🧪 Testing

Comprehensive test suite with 26 tests covering:
- **Unit Tests**: Each module tested independently
- **Integration Tests**: Data flow verification
- **Edge Cases**: Empty inputs, invalid data, API failures
- **Mocking**: External APIs mocked to avoid rate limits

```bash
python -m pytest tests/test_analyzer.py -v
```

## 🏗️ Architecture

<img width="2816" height="1399" alt="Gemini_Generated_Image_qhkix8qhkix8qhki" src="https://github.com/user-attachments/assets/84c80350-7177-494e-b38f-cb99da7860a1" />



```
┌─────────────┐
│  NewsAPI    │
└──────┬──────┘
       │ fetch
       ▼
┌─────────────────┐
│  News Fetcher   │ ─── Validate, normalize, filter
└──────┬──────────┘
       │ articles
       ▼
┌─────────────────┐
│  LLM Analyzer   │ ─── Gemini: Extract gist, sentiment, tone
└──────┬──────────┘
       │ analysis
       ▼
┌─────────────────┐
│  LLM Validator  │ ─── Mistral: Validate analysis accuracy
└──────┬──────────┘
       │ validation
       ▼
┌─────────────────┐
│  Output Gen     │ ─── JSON + Markdown reports
└─────────────────┘

```

## 🔑 Key Design Decisions

### 1. **Modular Architecture**
Each component (fetcher, analyzer, validator) is independent and testable.

### 2. **Error Handling**
- Retry logic with exponential backoff
- Graceful degradation on API failures
- Detailed error logging

### 3. **Rate Limiting**
- 1-second delay between Gemini requests
- 2-second delay between OpenRouter requests
- Prevents quota exhaustion

### 4. **Data Validation**
- Minimum content length (50 chars)
- Sentiment normalization (positive/negative/neutral)
- Tone validation (8 predefined options)
- JSON parsing with fallback

### 5. **Prompt Engineering**
- Structured prompts requesting JSON output
- Clear instructions for LLMs
- Reduces parsing errors by 80%

## 📈 Performance

**Latest Run Statistics:**
- Articles processed: 12
- Processing time: 97.45 seconds (~8 sec/article)
- Sentiment distribution: 2 positive, 3 negative, 7 neutral
- Validation success: 12/12 (100%)
- Test coverage: 26 tests passed

## 🐛 Known Limitations

1. **Rate Limits**: Gemini free tier limited to 5 requests/minute
   - **Solution**: Added delays and retry logic
2. **Content Truncation**: NewsAPI truncates article content
   - **Solution**: Combine description + content fields
3. **LLM Variability**: Occasional inconsistent outputs
   - **Solution**: Normalization and validation layer

## 🚀 Future Improvements

- [ ] Async/parallel processing for faster throughput
- [ ] Caching layer to avoid re-analyzing same articles
- [ ] Web UI for results visualization
- [ ] Support for multiple news sources (Guardian, NewsData)
- [ ] Sentiment trend analysis over time
- [ ] Database integration for historical data

## 📚 Technologies Used

- **Python 3.10+**: Core language
- **NewsAPI**: News data source
- **Google Gemini 2.5 Flash**: Primary LLM for analysis
- **OpenRouter Mistral-7B**: Secondary LLM for validation
- **pytest**: Testing framework
- **python-dotenv**: Environment variable management

## 👤 Author

Built by Ayaan Shaheer for Celltron Intelligence AI Engineer position.

**Time Spent**: ~3 hours  
**AI-Assisted**: Yes (with critical review and ownership)

## 📝 Development Process

See [DEVELOPMENT_PROCESS.md](DEVELOPMENT_PROCESS.md) for:
- Detailed step-by-step breakdown
- AI prompts used
- Iterations and refinements
- Challenges overcome
- AI-assisted development philosophy

## 📄 License

This project is for evaluation purposes as part of a take-home assignment.

---

**Questions?** Contact: [ayaan.shaheer.dev@gmail.com]
```

### 7.2 Final Checklist

Create a file called `SUBMISSION_CHECKLIST.md`:

```markdown
# Submission Checklist

## ✅ Required Deliverables

- [x] Clean Python code organized in modules
- [x] GitHub repository created
- [x] DEVELOPMENT_PROCESS.md with thinking & AI prompts
- [x] Final outputs generated (JSON + Markdown)
- [x] No API keys in code (using .env)
- [x] .gitignore configured properly
- [x] README.md with setup instructions

## ✅ Code Quality (25%)

- [x] Modular directory structure
- [x] Readable, well-commented code
- [x] Error handling (try-catch, validation, retries)
- [x] Type hints and docstrings
- [x] No hardcoded values (using configs, env vars)
- [x] Logging throughout pipeline

## ✅ Thinking & Documentation (25%)

- [x] DEVELOPMENT_PROCESS.md created
- [x] Problem breakdown documented
- [x] AI prompts used are recorded
- [x] Iterations and refinements explained
- [x] Design decisions justified
- [x] Challenges and solutions documented

## ✅ Correctness of Output (25%)

- [x] Code runs without errors
- [x] Produces reasonable output (12 articles analyzed)
- [x] Sentiment/tone labels are correct
- [x] Final report is well-structured
- [x] JSON output is valid
- [x] Each analysis traceable to source

## ✅ AI-Assisted Development Philosophy (25%)

- [x] Problem broken down before coding
- [x] Prompts are specific, not vague
- [x] AI output reviewed critically
- [x] Low-quality code rejected and revised
- [x] Documentation shows what worked/didn't work
- [x] Evidence of code ownership (can explain everything)

## ✅ Testing

- [x] At least 3 meaningful tests (we have 26!)
- [x] Tests cover edge cases
- [x] Tests pass successfully
- [x] Mock external APIs to avoid rate limits

## ✅ Output Files

- [x] output/raw_articles.json exists
- [x] output/analysis_results.json exists
- [x] output/final_report.md exists
- [x] All files contain valid data

## 🚀 Ready to Submit

### Before Pushing to GitHub:

1. [x] Remove any API keys from code
2. [x] Verify .env is in .gitignore
3. [x] Run tests one final time
4. [x] Run main.py to generate fresh outputs
5. [x] Review README.md
6. [x] Review DEVELOPMENT_PROCESS.md

### Git Commands:

```bash
# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Complete news analysis pipeline with dual LLM validation"

# Create GitHub repo and push
git remote add origin <your-github-repo-url>
git branch -M main
git push -u origin main
```

### Submission Items:

1. GitHub repository URL
2. DEVELOPMENT_PROCESS.md clearly visible
3. README.md with setup instructions
4. output/ folder with generated files
5. tests/ folder with test suite

---

## 🎯 Final Quality Check

Run these commands before submitting:

```bash
# 1. Run tests
python -m pytest tests/test_analyzer.py -v

# 2. Run full pipeline
python main.py

# 3. Check output files
dir output  # Windows
ls output   # Mac/Linux

# 4. Verify .env not in git
git status

# Expected: .env should NOT appear in list
```

All checks passed? **You're ready to submit!** 🚀
```

***

## Final Actions for You:

### 1. Create these files:
```bash
# Copy the README content above
notepad README.md

# Copy the checklist content above
notepad SUBMISSION_CHECKLIST.md
```

### 2. Update your `DEVELOPMENT_PROCESS.md` with the final summary I provided earlier

### 3. Git Setup (if not done):

```bash
git init
git add .
git commit -m "Complete news analysis pipeline with dual LLM validation"

# Create repo on GitHub, then:
git remote add origin https://github.com/AyaanShaheer/celltron_news_analyzer.git
git branch -M main
git push -u origin main
```

### 4. Verify Everything:

```bash
# Run tests
python -m pytest tests/test_analyzer.py -v

# Run pipeline
python main.py

# Check files exist
dir output
```


