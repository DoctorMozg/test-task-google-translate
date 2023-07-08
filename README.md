# Test task: Google Translate Service

### Objectives:
- Should call Google API in order to get translated word, synonyms, definitions and examples
- Store all of this info inside DB
- Return everything using FastAPI

### What can be improved:
- More units (especially corner cases, empty words, wrong languages etc.)
- Restrict input to one word
- REDIS-based caching system for web-requests
- More docs
- More settings

### How-to start
- Using `docker-compose.yml` (Postgres should be started independently)