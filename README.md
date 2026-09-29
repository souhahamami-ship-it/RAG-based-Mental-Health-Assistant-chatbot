# Mindful — Mental Health RAG Chatbot

A learning project that explores how to build a **Retrieval-Augmented Generation (RAG)** chatbot for mental health support using **FastAPI, FAISS, Sentence Transformers, Cross-Encoder reranking, and Docker**.

> **Educational purpose:** This project is designed to understand the architecture of modern AI applications. It is **not a substitute for professional mental health care**.

---

## Project goal

The objective is to build a chatbot that can:

* Hold natural conversations with users.
* Retrieve reliable information from a mental health knowledge base.
* Re-rank retrieved documents before generating an answer.
* Detect crisis messages and stop the normal conversation flow.
* Expose the chatbot through a FastAPI API.
* Provide a minimal and privacy-focused web interface.
* Be packaged and deployed with Docker.

---

## Architecture

The chatbot follows this pipeline:

```text
                 User
                  │
                  ▼
           Safety Filter
                  │
      ┌───────────┴───────────┐
      │                       │
   Crisis                 Normal
      │                       │
      ▼                       ▼
 Safety Response        Knowledge Search
                              │
                              ▼
                           FAISS
                              │
                              ▼
                      CrossEncoder
                              │
                              ▼
                       Retrieved Context
                              │
                              ▼
                              LLM
                              │
                              ▼
                         Final Response
```

### Why this architecture?

Instead of asking the LLM to answer everything from memory, the chatbot first searches a **trusted knowledge base** and only then generates a conversational response.

This makes the system more scalable because future scientific articles can simply be added to the knowledge base.

---

## Technologies used

| Technology              | Purpose                     |
| ----------------------- | --------------------------- |
| FastAPI                 | Backend API                 |
| Groq API                | Large Language Model        |
| Sentence Transformers   | Text embeddings             |
| FAISS                   | Vector similarity search    |
| CrossEncoder            | Re-ranking retrieved chunks |
| HTML / CSS / JavaScript | Frontend                    |
| Docker                  | Containerization            |

---

## Project structure

```
mental_health_chatbot/
├── main.py           # composition root: builds every shared object ONCE at startup
├── config.py          # centralized, validated environment configuration
├── api.py              # HTTP routes only (/chat, /health) — no business logic
├── chatbot.py            # stateless chat orchestration (singleton)
├── knowledge.py            # RAG: embeddings, FAISS index, reranking, relevance threshold
├── loader.py                 # raw .txt loading + chunking (zero ML dependencies, on purpose)
├── memory.py                   # per-conversation session state (in-RAM, TTL-evicted, never persisted)
├── safety.py                     # pre-generation crisis-keyword gate
├── ingest.py                       # offline CLI: raw .txt -> trust-tagged knowledge.json
├── test_local.py                     # smoke test against a REAL running server
├── data/
│   ├── raw/                            # source .txt files (input to ingest.py)
│   └── knowledge.json                    # built by ingest.py; what knowledge.py actually loads
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js                             # talks to the backend via fetch()
├── .env                                        # secrets, never committed
├── Dockerfile / docker-compose.yml               # containerization (separate concern, see §7)
└── requirements.txt
```

## . The whole pipeline, start to finish
 
```
user message
    │
    ▼
safety.check(message)  ──── fails ───▶ static crisis response, no AI touched at all
    │ passes
    ▼
embed the query (SentenceTransformer) → same vector space as the indexed chunks
    │
    ▼
FAISS search: fast, coarse, wide net → top `retrieval_k` candidates
    │
    ▼
CrossEncoder rerank: slow, precise → re-score just the shortlist
    │
    ▼
relevance threshold: drop everything below `min_rerank_score`
    │
    ▼
format survivors into a grounding block → inserted right before the user's message
    │
    ▼
send [system prompt, trimmed history, grounding block, user message] to Groq
    │
    ▼
LLM generates a reply, instructed to use the grounding text but not invent beyond it
    │
    ▼
reply appended to session history, trimmed to the history limit, returned to the user
```



---

# Running locally

 
```powershell
# one-time setup
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ingest.py --input data/raw --output data/knowledge.json --trust-tier ai_drafted_needs_review
 
# terminal 1 — backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
 
# terminal 2 — frontend
cd frontend
python -m http.server 5500
# open http://127.0.0.1:5500 in a browser
 
# terminal 3 — automated check against the real running backend
python test_local.py
```


---

# Docker

Build the containers:

```bash
docker compose build
```

Run the application:

```bash
docker compose up
```

Services:

| Service  | Port |
| -------- | ---- |
| Frontend | 5500 |
| FastAPI  | 8000 |

---

# Current features

* RAG pipeline
* Paragraph-based chunking
* FAISS retrieval
* CrossEncoder reranking
* Humanized prompting
* Conversation memory
* Crisis detection
* Session blocking
* FastAPI backend
* Minimal web interface
* Docker support

---

# Future improvements

This project is intentionally built in stages.

Planned improvements include:

* Scientific article knowledge base
* Medium-risk safety classification


---

# Important note

This project is for **learning and research purposes**. The chatbot provides supportive information but is **not a medical professional** and should not replace qualified mental health care, especially during emergencies.
