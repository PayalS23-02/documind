# DocuMind — Backend

RAG pipeline for querying academic PDFs in natural language, with grounded,
cited answers. Built with FastAPI, ChromaDB, and the Gemini API.

## What's here so far

```
backend/
├── app/
│   ├── config.py        # settings loaded from .env
│   ├── chunking.py       # custom section-aware chunker (tested, works)
│   ├── ingestion.py       # PDF -> pages -> chunks (tested, works)
│   ├── embeddings.py      # Gemini embedding calls (needs API key)
│   ├── vectorstore.py     # ChromaDB storage + similarity search
│   ├── retrieval.py       # top-k retrieval + similarity threshold filter
│   ├── generation.py      # grounded answer generation via Gemini
│   ├── schemas.py         # Pydantic request/response models
│   └── main.py            # FastAPI app (ingest / query / health endpoints)
├── sample_docs/
│   └── sample_handbook.pdf   # sample doc for testing (has real rules in it)
├── cli.py                 # quick test script, no need to run FastAPI/React yet
├── requirements.txt
└── .env.example
```

## Setup

1. **Create a virtual environment and install dependencies**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Get a Gemini API key**
   - Go to https://aistudio.google.com/apikey
   - Create a key (free tier available, with rate limits)

3. **Set up your .env file**
   ```bash
   cp .env.example .env
   # then edit .env and paste your key into GEMINI_API_KEY=
   ```

## Test the pipeline (no FastAPI/React needed yet)

```bash
# 1. Ingest the sample handbook
python cli.py ingest sample_docs/sample_handbook.pdf

# 2. Ask a question
python cli.py ask "What's the minimum attendance requirement for a backlog course?"
```

Expected: it should retrieve the ATTENDANCE POLICY chunk and answer "65%",
citing sample_handbook, page 1.

## Run the API server

```bash
uvicorn app.main:app --reload
```

Then visit `http://localhost:8000/docs` for interactive API docs (Swagger UI),
where you can test `/ingest` and `/query` directly from the browser.

## What's already verified (without needing an API key)

- ✅ Custom chunker correctly splits on section headers and keeps
  paragraphs/rules intact (tested on sample data)
- ✅ PDF parsing + chunking pipeline runs end-to-end on a real PDF
- ⏳ Embeddings, vector storage, and generation need your Gemini API key to test

## Next steps

- [ ] Add your Gemini API key and run `cli.py` to verify the full pipeline
- [ ] Add more real handbook/policy PDFs to `sample_docs/`
- [ ] Build the React frontend (chat UI) once the API is confirmed working
- [ ] Add error handling for empty/malformed PDFs
- [ ] Consider adding a `/documents` endpoint to list what's been ingested
