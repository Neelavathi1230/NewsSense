# NewsSense – News Text & Speech Analysis System
Paste a news article or upload a news audio clip; get topics, keywords, entities, sentiment, tone, readability, key facts and summaries, plus a dashboard across stories.

## Run
```bash
pip install -r requirements.txt
cd backend && uvicorn main:app --reload      # http://127.0.0.1:8000
```

## Analysis (`backend/nlp.py`, local, replaceable)
- **Topics:** lexicon-based scoring over 10 categories (Politics, Business, Technology, Sports, Health, Science, Entertainment, World, Education, Environment).
- **Keywords / entities:** unigram + bigram frequency; capitalization-based people/places/organizations.
- **Sentiment:** sentence-level lexicon with simple negation handling.
- **Tone:** counts opinion words, exclamations, first-person language. **Readability:** Flesch score.
- **Summary:** extractive, lead-biased, favors sentences with figures. **Key facts:** sentences containing numbers.

## Speech
`pip install faster-whisper` for real transcription of audio. Without it, uploaded audio gets a built-in sample story labelled "demo". Pasted text always works.

## API
`POST /api/auth/{register,login,logout}` · `POST /api/analyze` · `GET /api/articles` · `GET|DELETE /api/articles/{id}`

## Limits
Lexicon methods are English-only and miss sarcasm and context; entity detection is heuristic; the tone score does not detect media bias or fake news. Future work: spaCy NER, transformer sentiment/classification, URL import, multilingual support, fact-checking.
