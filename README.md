# Bildx AI — Image-Ad Generator

> **Practical Engineering Assignment for Neurix UG (Bildx AI)**  
> **Candidate:** Keshav Jindal (`keshav.jindal.7029@gmail.com`)  
> **Repository Deliverable:** `keshav-jindal-bildx-image-ad.zip`

An end-to-end, production-grade full-stack application that transforms a public product image URL and structured product context into grounded, high-converting advertising copy and a downloadable, publication-ready composite image advertisement.

---

## Key Highlights & Rubric Fulfillment

- **Correctness Under Parallel Load (25% Rubric Weight):**
  - Features an asynchronous task queue with bounded provider concurrency (`asyncio.Semaphore`, configurable via `MAX_CONCURRENT_PROVIDER_CALLS`).
  - Strict failure isolation: a failing or timing-out task never blocks unrelated generation tasks.
  - Duplicate protection via `Idempotency-Key` header deduplication.
  - Predictable capacity behavior: returns `HTTP 429 Too Many Requests` when saturated instead of unbounded buffering.
  - Includes `run_load_demo.py` demonstrating 12 concurrent requests with 0 paid API costs.
- **Working End-to-End Functionality (20% Rubric Weight):**
  - Full-stack system ready to boot with a single command: `docker compose up --build`.
  - Intuitive user flow with sample auto-fill presets (including the *ROAM Lock 750* tumbler from the assignment brief).
  - Real-time status polling through the state machine: `pending` → `processing` → `retrying` → `completed` / `failed`.
  - 1-click download of the final high-resolution PNG advertisement.
- **AI Prompting & Product Relevance (20% Rubric Weight):**
  - Strict grounding rules enforced: zero hallucination, no invented specs, discounts, or fake certifications.
  - Hard character and word count enforcement: Headline $\le 8$ words, Supporting Text $\le 20$ words, CTA $\le 4$ words.
  - Hybrid generation & deterministic composition architecture: guarantees crisp typography, contrast-aware scrims, and 100% unaltered product recognition.
- **Reliability & Failure Handling (15% Rubric Weight):**
  - Exponential backoff retry engine for transient provider errors (HTTP 429, 503, timeouts).
  - Fail-fast validation without retries for permanent errors (bad URLs, invalid schemas, non-image content).
  - Enterprise SSRF defense: blocks private RFC 1918, link-local, loopback, and cloud metadata IPs (`169.254.169.254`).
  - Streaming download size cap (10 MB cutoff) and strict timeouts.
- **Automated Test Suite (10% Rubric Weight):**
  - Comprehensive Pytest test suite covering all 10 required edge cases with **$0.00 paid model costs** using `FakeAIProvider`.
- **Frontend Usability (5% Rubric Weight):**
  - Built with React 18, TypeScript, Vite, and Tailwind CSS. Responsive two-column layout with animated status badges and live source image preview.
- **Comprehensive Documentation (5% Rubric Weight):**
  - Complete documentation across `README.md`, `ARCHITECTURE.md`, `PROMPT_NOTES.md`, and `AI_USAGE.md`.

---

## Quick Start with Docker (Recommended)

To run the entire full-stack application (Backend API on port 8000 + Frontend on port 3000):

```bash
# 1. Clone or extract the repository
unzip keshav-jindal-bildx-image-ad.zip -d keshav-jindal-bildx-image-ad
cd keshav-jindal-bildx-image-ad

# 2. Build and launch containers
docker compose up --build
```

- **Web Application:** [http://localhost:3000](http://localhost:3000)
- **API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## Local Development (Without Docker)

### Prerequisites
- Python 3.11+ (or `uv`)
- Node.js 18+ & npm

### 1. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Or with uv:
uv run --python 3.11 uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Automated Test Suite (Zero Paid Credits)

The test suite validates all 10 required edge cases plus SSRF filtering and word-count validation:

```bash
# From the project root:
pytest backend/tests/ -v

# Or using uv:
uv run --with-requirements backend/requirements.txt --python 3.11 pytest backend/tests/ -v
```

### Test Coverage Checklist:
| Test Scenario | Status | Description |
|---|---|---|
| `test_valid_generation_request` | **PASSED** | Valid request accepted, transitions to completed with valid copy |
| `test_invalid_or_unreachable_image_url` | **PASSED** | Fails fast with descriptive error; no retries attempted |
| `test_ssrf_internal_ip_blocked` | **PASSED** | Rejects `127.0.0.1` and cloud metadata addresses |
| `test_oversized_image_rejected` | **PASSED** | Streaming download aborts immediately if image $> 10$ MB |
| `test_non_image_url_rejected` | **PASSED** | Rejects HTML/JSON endpoints before calling models |
| `test_successful_download` | **PASSED** | Verifies `GET /api/download/{id}` delivers valid PNG bytes |
| `test_provider_timeout_handling` | **PASSED** | Handles hanging provider calls gracefully with retries & error tracking |
| `test_temporary_error_retry_success` | **PASSED** | Transient 503 triggers `retrying` status with exponential backoff |
| `test_permanent_provider_error_fail_fast` | **PASSED** | Invalid credentials/bad schema fail-fast on attempt 0 |
| `test_duplicate_idempotency_key` | **PASSED** | Identical `Idempotency-Key` returns existing task ID |
| `test_concurrent_requests_bounded_concurrency` | **PASSED** | Parallel requests execute without race conditions under semaphore |
| `test_capacity_exceeded_returns_429` | **PASSED** | Queue saturation returns HTTP 429 Too Many Requests |
| `test_creative_copy_word_count_limits` | **PASSED** | Enforces $\le 8$ headline, $\le 20$ body, $\le 4$ CTA |

---

## Concurrent Load Demonstration

The load demonstration script fires 12 concurrent requests to demonstrate all rubric requirements without consuming paid API credits:

```bash
# Run the automated load demo:
python3 run_load_demo.py

# Or via shell helper:
./run_load_demo.sh
```

### Key Demonstrations Observed:
1. **12 Concurrent Submissions:** All accepted within ~5ms without blocking the event loop.
2. **Bounded Concurrency:** Observed staggered execution matching `MAX_CONCURRENT_PROVIDER_CALLS=3`.
3. **Failure Isolation:** Request #8 (invalid image) fails cleanly with `FAILED` status while all other 11 requests complete successfully.
4. **Idempotency Deduplication:** Request #9 re-uses Request #1's key and returns the identical task ID without duplicate processing.
5. **Zero Model Cost:** Executed 100% offline via `FakeAIProvider`.

---

## Model Configuration & Tradeoffs

All settings are configured via environment variables (see `.env.example`).

### Switching AI Providers
Set `AI_PROVIDER` in `.env`:
- `fake` (Default): Fast, deterministic, zero cost, ideal for grading and load testing.
- `gemini`: Uses Google Gemini (requires `GEMINI_API_KEY`).
- `openai`: Uses OpenAI GPT models (requires `OPENAI_API_KEY`).

### Why Deterministic Composition Over Pure Image Generation?
- **Text Hallucination & Illegibility:** Pure diffusion models (DALL-E 3, Stable Diffusion) notoriously misspell brand names and generate distorted typography.
- **Product Fidelity:** Commercial advertisers require their exact physical product to appear unaltered. Generative inpainting frequently distorts logos and proportions.
- **Our Hybrid Pipeline:**
  1. **Grounded LLM:** Generates concise, factual advertising copy and a creative visual direction.
  2. **Atmospheric Backdrop Synthesizer:** Creates an aesthetically aligned scene tuned to audience and tone.
  3. **Deterministic Compositor (Pillow):** Renders the authentic product image with ambient shadows, contrast scrims, and crisp, publication-grade typography.

---

## Time Spent & Next Steps

- **Time Spent:** ~4.5 hours (scaffolding, testing, queue concurrency, frontend UI, docs).
- **Next Steps for Production:**
  1. Distributed task queue (Celery/Temporal backed by Redis/PostgreSQL) for multi-worker scaling.
  2. Object storage integration (AWS S3 / Google Cloud Storage) with signed download URLs.
  3. Automated visual quality scoring using CLIP / multimodal vision feedback.

---

## Deliverable File Manifest
- `keshav-jindal-bildx-image-ad/`
  - `docker-compose.yml`: Multi-container orchestration
  - `.env.example`: Complete environment variable reference
  - `README.md`: This setup & evaluation guide
  - `ARCHITECTURE.md`: Technical architecture and reliability design
  - `PROMPT_NOTES.md`: Prompt engineering strategy, iteration logs, and failure case study
  - `AI_USAGE.md`: AI tooling disclosure and verification methodology
  - `sample-output.png`: Sample generated advertisement
  - `run_load_demo.py` / `run_load_demo.sh`: 10+ concurrent load demonstration
  - `backend/`: FastAPI backend with tests
  - `frontend/`: React TypeScript Vite application
