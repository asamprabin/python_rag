# Chat With Your Docs

A small, local-first document Q&A application. Upload a `.txt` file, then ask questions about it. The backend embeds overlapping text chunks, retrieves the closest matches from ChromaDB, and asks a locally running Ollama model to answer from those excerpts.

## Features

- Upload and index one .txt document.
- Split text into overlapping word-based chunks and embed locally.
- Persist embeddings in a local ChromaDB collection.
- Retrieve up to three relevant chunks for a question.
- Generate a grounded answer using a local Ollama model.
- Show upload, loading, answer, and error states in a React UI.

## Quick setup

### Prerequisites

- Python 3.12 or later.
- Node.js.

### 1. Start Ollama and download the model

If Ollama is not already running as a service, start it in a separate terminal:

```bash
ollama serve
```

Then fetch the model used by the app:

```bash
ollama pull llama3.2:3b
```

The backend expects Ollama at `http://localhost:11434` and the model name `llama3.2:3b`; these are currently constants in `app.py`.

### 2. Install and start the backend

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

On Windows, activate the environment with `.venv\Scripts\activate` instead. The Flask development server listens on `http://127.0.0.1:5000`.

The first request that needs embeddings downloads `all-MiniLM-L6-v2` through Sentence Transformers if it is not already cached. ChromaDB data is stored in `./chroma_db` relative to the backend's working directory; keep that directory to retain the current index.

### 3. Install and start the frontend

In a second terminal:

```bash
cd front-end
npm ci
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). In development, Vite proxies `/api` requests to the Flask server. To point a built frontend at a different backend, set `VITE_API_BASE_URL` at build time; the backend must then be configured to accept that origin and route.

### 4. Try it

Upload one `.txt` file using the page, then ask a question whose answer appears in that text. Two small example policies are included under `static/files/`. Uploading either one replaces the current indexed content.

## Architecture

```text
Browser (React 19 + Vite)
    │ /api/upload_file, /api/ask
    │ (Vite development proxy)
    ▼
Flask API (app.py)
    ├── Sentence Transformers: all-MiniLM-L6-v2
    ├── ChromaDB: persistent local collection (./chroma_db)
    └── Ollama HTTP API: llama3.2:3b at localhost:11434
```

### Request flow

1. The browser sends the selected `.txt` file as multipart form data to `POST /upload_file`.
2. The API checks the extension, UTF-8 encoding, and that the file is non-empty. It splits the text into 40-word chunks with 8 words of overlap, creates embeddings, clears the existing collection contents, and stores the new chunks with the filename as metadata.
3. The browser sends a question as JSON to `POST /ask`.
4. The API embeds the question, retrieves up to three nearest chunks, and supplies their text to Ollama.
5. The model is instructed to answer only from the excerpts and to say when they do not contain enough information. The API returns the answer to the browser.

## Engineering decisions and standards

### Implemented

- Keep the initial stack small and local: Flask, React/Vite, local embeddings, local vector storage, and local generation.
- Validate the uploaded file type, encoding, and empty content, and reject blank questions.
- Return HTTP errors for invalid input and unavailable generation; log backend processing failures.
- Use locks around lazy model initialization and operations that modify or query the shared Chroma collection.
- Use semantic HTML forms, disabled/loading states, and status/error announcements in the UI.

## Productionization and scaling

Before exposing this application to real users or sensitive documents, I would:

1. **Secure the boundary:** add authentication and server-side authorization; enforce document ownership/tenant filters in the backend; add upload limits, rate limits, file validation, and safe error handling. Treat document content as untrusted input.
2. **Make processing reliable:** move ingestion and generation to a production WSGI server and background jobs; add job status, retries, idempotency, and explicit re-index/delete operations.
3. **Separate configuration and data:** configure model names, endpoints, storage, and timeouts through validated environment/configuration; use managed secrets; persist uploads and indexes in durable, access-controlled storage with backups and retention policies.
4. **Scale the components:** containerize the API and worker, deploy behind a gateway/load balancer on AWS, GCP, Azure, or another platform, and choose a managed or clustered vector store based on measured needs. Scale inference separately or use an appropriately governed hosted model.
5. **Add quality controls:** build a representative question/answer dataset; measure retrieval precision/recall and answer correctness/faithfulness; compare changes against a fixed baseline; add citations and abstention checks.
6. **Operate it safely:** add structured logs, request IDs, latency/error metrics, traces, resource and cost monitoring, alerts, and audit events without logging document contents or secrets by default.
7. **Harden delivery:** pin and audit dependencies, add automated tests and CI, scan images/dependencies, document deployment and rollback, and test backup/restore and deletion workflows.

The right cloud services and scaling strategy depend on expected document volume, concurrency, data residency, privacy requirements, and budget; those requirements have not been established for this demo.

## Screenshots

Screenshots are available on `static/screenshots/`.


## What I would do next

1. Add backend tests for chunking, upload validation, empty-index behavior, retrieval, and Ollama failures, plus frontend interaction tests.
2. Return source filenames and chunk references with answers, and show those citations in the UI.
3. Support multiple documents with explicit add, list, and delete operations rather than replacing the entire collection.
4. Add configurable chunking/retrieval settings and evaluate them against a small, labeled set of questions.
5. Add upload limits and document-level access controls before supporting more than a trusted local user.
6. Improve the UI with document management, conversation history, and a way to inspect retrieved excerpts.
