# ⚙️ Configuration Reference

DockAI is 100% configurable via Environment Variables. You can set these in your shell or in a `.env` file.

---

## 🔑 LLM Provider

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_LLM_PROVIDER` | `openai`, `azure`, `gemini`, `anthropic`, `ollama` | `openai` |
| `OPENAI_API_KEY` | Your OpenAI API Key | - |
| `GOOGLE_API_KEY` | Gemini API Key | - |
| `ANTHROPIC_API_KEY` | Claude API Key | - |
| `AZURE_OPENAI_API_KEY` | Azure API Key | - |
| `AZURE_OPENAI_ENDPOINT` | Azure Endpoint | - |
| `OLLAMA_BASE_URL` | URL for local Ollama | `http://localhost:11434` |

---

## 🧠 Smart Context (RAG) - v4.0

These settings control how DockAI reads your codebase.

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_USE_RAG` | Enable semantic search (Vector DB). Recommended for repos > 50 files. | `false` |
| `DOCKAI_READ_ALL_FILES` | If true, tries to read all file contents (truncated) alongside RAG. If false, strictly relies on RAG + critical files. | `true` |
| `DOCKAI_EMBEDDING_MODEL` | HuggingFace model for embeddings. Runs locally. | `all-MiniLM-L6-v2` |
| `DOCKAI_TOKEN_LIMIT` | Max tokens to send to the LLM. | `100000` |
| `DOCKAI_MAX_FILE_LINES` | Truncate files larger than this (lines). | `5000` |

---

## 🏗️ Generation & Validation

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_RETRIES` | Max attempts to fix a failing build. | `3` |
| `DOCKAI_VALIDATION_MEMORY` | Memory limit for build sandbox. | `512m` |
| `DOCKAI_MAX_IMAGE_SIZE_MB` | Warn if image exceeds this size. | `500` |
| `DOCKAI_SKIP_SECURITY_SCAN` | Skip Trivy scanning (faster). | `false` |
| `DOCKAI_SKIP_HADOLINT` | Skip Dockerfile linting. | `false` |

---

## 📊 Observability

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_ENABLE_TRACING` | Enable OpenTelemetry tracing. | `false` |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing. | `false` |
| `LANGCHAIN_API_KEY` | LangSmith API Key. | - |

---

## 🤖 Per-Agent Models

You can granularly override the model used for each agent.

| Variable | Agent Role | Default |
|----------|------------|---------|
| `DOCKAI_MODEL_ANALYZER` | Stack detection | `gpt-4o-mini` |
| `DOCKAI_MODEL_GENERATOR` | Dockerfile writing | `gpt-4o` |
| `DOCKAI_MODEL_REVIEWER` | Security audit | `gpt-4o-mini` |
| `DOCKAI_MODEL_REFLECTOR` | Failure analysis | `gpt-4o` |

Example: Use Ollama for simple tasks and GPT-4o for complex ones:
```bash
DOCKAI_MODEL_ANALYZER=ollama/llama3
DOCKAI_MODEL_GENERATOR=openai/gpt-4o
```
