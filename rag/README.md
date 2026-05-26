# RAG — Retrieval-Augmented Generation

Context enrichment layer that provides agents with relevant background information during extraction and proposal generation.

| Module | Purpose |
|---|---|
| `contractor_context.py` | Load contractor preferences, markup rules, past proposals |
| `embeddings.py` | Text embedding generation and similarity search |
| `few_shot_selector.py` | Select best few-shot examples for a given document |
| `supplier_catalog.py` | Supplier-specific extraction hints and known formats |

## Design

RAG modules are called *before* agent invocation to enrich the system prompt with relevant context. This keeps agent prompts lean (static instructions only) while dynamically injecting the most relevant examples and preferences.
