# Memory System

Multi-tier memory architecture for the proposal engine agents.

| Store | Purpose | Persistence |
|---|---|---|
| `working_state.py` | Current envelope state during processing | In-memory (request-scoped) |
| `cache.py` | LRU cache for recent classifications and extractions | In-memory (TTL-based) |
| `static_store.py` | Supplier catalog, known formats, extraction templates | Disk (loaded at startup) |
| `learned_store.py` | Patterns learned from corrections and reviews | Database |
| `retrieval_store.py` | Embedding-based retrieval for few-shot examples | Vector DB |
