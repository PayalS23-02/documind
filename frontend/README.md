# DocuMind — Frontend

React + Vite chat UI for DocuMind. Talks to the FastAPI backend in `../backend`.

## What's here

```
frontend/
├── src/
│   ├── App.jsx                 # top-level layout, backend health check
│   ├── api.js                  # fetch wrappers for /ingest, /query, /health
│   ├── index.css                # dark chat UI styling
│   ├── main.jsx                 # React entry point
│   └── components/
│       ├── UploadPanel.jsx      # drag-and-drop PDF upload -> /ingest
│       ├── ChatWindow.jsx       # message list + input box -> /query
│       ├── MessageBubble.jsx    # renders one chat message
│       └── SourceCitations.jsx  # renders cited sources under an answer
├── index.html
├── vite.config.js
├── package.json
└── .env.example
```

All components were syntax-checked with esbuild (bundled cleanly, no errors),
but **not yet run in a real browser** — no network access was available to
`npm install` in the environment this was built in. You'll need to install
and run it yourself.

## Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Point it at your backend**
   ```bash
   cp .env.example .env
   # defaults to http://localhost:8000, change if needed
   ```

3. **Make sure the backend is running first** (see `../backend/README.md`):
   ```bash
   cd ../backend
   uvicorn app.main:app --reload
   ```

4. **Run the frontend dev server**
   ```bash
   cd ../frontend
   npm run dev
   ```
   Then open `http://localhost:5173`.

## How it works

- On load, `App.jsx` pings `/health` to show whether the backend is reachable
  and how many chunks are indexed.
- `UploadPanel` lets you drag-and-drop or select PDFs, which are sent to
  `/ingest` as multipart form data.
- `ChatWindow` sends questions to `/query` and renders the grounded answer
  plus a `SourceCitations` block underneath (document, section, page,
  similarity %) — pulled directly from the backend's response.

## Next steps

- [ ] Run `npm install && npm run dev` and confirm it actually renders/works
      in a real browser (untested here due to no network access)
- [ ] Test the full flow: upload sample_handbook.pdf -> ask a question ->
      confirm the citation shown matches the source
- [ ] Add a loading state / disable upload while ingesting
- [ ] Add basic responsive styling for mobile if needed
- [ ] Consider persisting chat history (currently resets on page reload)
