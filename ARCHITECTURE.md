# System Architecture & Reliability Design

> **Bildx AI Engineering Assignment**  
> **Candidate:** Keshav Jindal (`keshav.jindal.7029@gmail.com`)

This document outlines the software architecture, parallel queue management, failure isolation, capacity controls, and security measures implemented in the Bildx AI Image-Ad Generator.

---

## 1. High-Level System Architecture

The application is architected around an asynchronous vertical slice pattern, cleanly separating the user-facing API from long-running image retrieval, AI inference, and graphic composition tasks:

```
[ Client Browser / SPA ]
         │
         │  1. POST /api/generate (with Idempotency-Key)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ FastAPI Application (main.py)                                   │
│  ├── Pydantic Input Validation (schemas.py)                     │
│  └── GenerationQueueManager (queue_manager.py)                  │
│       ├── Idempotency Cache Check (task_id mapping)             │
│       ├── Capacity Check (active_tasks < MAX_QUEUE_CAPACITY)    │
│       └── Spawn Async Worker Task (asyncio.create_task)         │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Returns 202 Accepted + task_id
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Isolated Worker Pipeline (Per-Task Execution)                   │
│                                                                 │
│ 1. SSRF & Image Downloader (image_downloader.py)                │
│    ├── Scheme & DNS Hostname IP Resolution Check                │
│    ├── Filter RFC 1918, Loopback, Link-Local & Metadata IPs     │
│    └── Streaming Download with 10 MB Cutoff                     │
│                                                                 │
│ 2. Bounded Concurrency Semaphore (asyncio.Semaphore)            │
│    └── Limits concurrent AI provider calls                      │
│                                                                 │
│ 3. Replaceable AI Provider (providers/)                         │
│    ├── Grounded LLM Prompt (copy_grounding.py)                  │
│    ├── Exponential Backoff Retry Loop (503 / 429 / timeouts)   │
│    └── Visual Backdrop Synthesizer                              │
│                                                                 │
│ 4. Deterministic Ad Compositor (composer.py)                    │
│    ├── Atmospheric Backdrop Resizing (1080x1080)                │
│    ├── Readability Scrims (Top & Bottom Linear Gradients)       │
│    ├── Product Placement with Ambient Drop Shadow               │
│    └── Crisp Typography (Headline <= 8w, Body <= 20w, CTA <= 4w)│
│                                                                 │
│ 5. Task State Transition (COMPLETED / FAILED)                   │
│    └── Output PNG saved to backend/output_ads/{task_id}.png     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Parallel Queue & Bounded Concurrency

### Why an In-Process Async Queue for This Vertical Slice?
For a production vertical slice designed to run seamlessly via `docker compose up --build` without requiring external multi-container dependencies (e.g. RabbitMQ, Redis, or Celery workers), an in-memory `asyncio` task queue provides:
- **Instant startup:** Zero setup overhead or external broker failure points.
- **Microsecond responsiveness:** New jobs are accepted, validated, and scheduled in under 5 milliseconds.
- **Precise concurrency controls:** Native Python asynchronous primitives (`asyncio.Semaphore`, `asyncio.Lock`, and `asyncio.create_task`) manage resource contention with zero race conditions.

### Bounded Concurrency via Semaphore
External AI model providers impose strict rate limits and token ceilings. Unbounded concurrent outbound HTTP requests risk mass 429 rate limit errors or socket exhaustion.

```python
# Centrally configurable in config.py / .env
self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_PROVIDER_CALLS)

async with self._semaphore:
    # Only MAX_CONCURRENT_PROVIDER_CALLS can invoke the model concurrently
    copy = await self._provider.generate_ad_copy(request)
```

- When 12 requests arrive simultaneously (as demonstrated in `run_load_demo.py`), all 12 are immediately assigned task IDs and return `202 Accepted`.
- Exactly `MAX_CONCURRENT_PROVIDER_CALLS` (default: 3) execute inference at any instant. As soon as one finishes, the next pending job acquires the semaphore slot.

---

## 3. Task State Machine & Lifecycle

Every task transitions strictly through the following state machine:

```
                  ┌─────────┐
                  │ PENDING │  (Accepted and queued)
                  └────┬────┘
                       │
                       ▼
                 ┌────────────┐
       ┌─────────│ PROCESSING │◄───────────┐
       │         └─────┬──────┘            │
       │               │                   │
(Permanent Err)        │ (Transient Err    │ (Wait backoff)
       │               │  & attempts left) │
       │               ▼                   │
       │         ┌───────────┐             │
       │         │ RETRYING  │─────────────┘
       │         └─────┬─────┘
       │               │ (Retries exhausted)
       ▼               ▼
 ┌──────────┐    ┌───────────┐
 │  FAILED  │    │ COMPLETED │
 └──────────┘    └───────────┘
```

### State Semantics:
1. `pending`: The request passed Pydantic validation, was assigned a UUID, and is queued in memory.
2. `processing`: The background worker is actively downloading the image, calling the provider, or compositing layers.
3. `retrying`: A transient failure (e.g., HTTP 503, rate limit, or provider timeout) occurred. The system is paused in an exponential backoff sleep before re-attempting.
4. `completed`: Creative copy was generated, word limits verified, composite image rendered to disk, and download URL generated.
5. `failed`: Execution terminated due to a permanent validation error or retry exhaustion. A clean, non-leaking error description is stored.

---

## 4. Failure Handling & Isolation

### 1. Failure Isolation
A critical requirement of resilient systems is that **the failure of Task A must never block or degrade Task B**.
- Each incoming request is wrapped in an independent `asyncio.create_task()`.
- Pipeline exceptions are caught inside `_process_task(task_id)` and mapped to that task's state record.
- Unhandled exceptions never escape to crash the event loop or cancel neighboring coroutines.
- As demonstrated in `run_load_demo.py` (Request #8), an unreachable image URL fails immediately and updates Task #8 to `failed`, while the other 11 requests complete successfully.

### 2. Transient vs. Permanent Error Classification
| Error Type | Examples | Policy |
|---|---|---|
| **Transient Error** | HTTP 429, HTTP 503, socket dropped, provider timeout | **Retry:** Transitions to `retrying`. Retries up to `MAX_RETRIES` (default: 3) with exponential backoff delay: `delay = initial * (backoff_factor ** attempt)`. |
| **Permanent Error** | SSRF blocked, invalid image format, payload > 10MB, bad model credentials, invalid JSON schema | **Fail-Fast:** Transitions directly to `failed` on attempt 0. Never retries futile operations. |

---

## 5. Capacity Controls & Rate Limiting

Unbounded queue ingestion causes unbounded memory usage and degradation under traffic spikes.

### Capacity Enforcement:
- We track active tasks: `active_count = sum(status in [pending, processing, retrying])`.
- If `active_count >= settings.MAX_QUEUE_CAPACITY` (default: 20):
  - Request is rejected **immediately at the route boundary** with `HTTP 429 Too Many Requests`.
  - The client receives:
    ```json
    {
      "detail": "Server capacity reached (20 active jobs). Please retry shortly."
    }
    ```
  - This preserves stability for already queued work and provides immediate backpressure to callers.

---

## 6. Idempotency & Duplicate Protection

Network retries and accidental double-clicks from marketers could spawn duplicate expensive generation jobs.

### Mechanism:
1. The client sends an `Idempotency-Key: <unique-string>` header (e.g., UUID or hashed payload).
2. `GenerationQueueManager` maintains an atomic mapping: `idempotency_map: Dict[str, str]`.
3. If a duplicate key is observed:
   - The server identifies the existing `task_id`.
   - Returns the existing task's current status and metadata (`202 Accepted` or `200 OK`).
   - **Zero duplicate background tasks or AI provider calls are made.**

---

## 7. Security Architecture & SSRF Defense

Allowing users to submit arbitrary image URLs introduces Server-Side Request Forgery (SSRF) and Denial of Service (DoS) risks.

### Defensive Measures (`services/image_downloader.py`):
1. **Scheme Whitelisting:** Accepts only `http` and `https`. Rejects `file://`, `ftp://`, `gopher://`, etc.
2. **DNS & IP Resolution Validation:**
   - Resolves the hostname via `socket.getaddrinfo`.
   - Inspects all resolved IP addresses using Python's `ipaddress` module.
   - Blocks:
     - Private IP ranges (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
     - Loopback addresses (`127.0.0.0/8`, `::1`)
     - Link-local addresses (`169.254.0.0/16`)
     - Cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`)
     - Multicast and reserved ranges
3. **Streaming Size Limit (10 MB):**
   - Inspects `Content-Length` header upfront.
   - Streams chunks with an atomic counter; aborts the connection immediately if cumulative bytes exceed `IMAGE_DOWNLOAD_MAX_BYTES` (10 MB).
4. **Content-Type & Magic Byte Validation:**
   - Validates `Content-Type` is an image.
   - Pillow decodes raw bytes in memory (`image.load()`) to catch corrupted or polyglot files.
5. **No Credential or Stack Trace Leakage:**
   - Global exception handler catches unhandled exceptions and returns generic `500 Internal Server Error` without stack traces or environment variables.

---

## 8. Production Scalability Roadmap

While the in-memory architecture is self-contained and zero-dependency, migrating to a multi-instance enterprise cluster involves:

1. **State Persistence:** Replace in-memory task dictionary with a relational database (PostgreSQL with SQLAlchemy) for durable job history.
2. **Distributed Queue:** Migrate `asyncio.create_task` to Celery or Temporal backed by Redis, enabling worker node autoscaling.
3. **Blob Storage:** Replace local disk `output_ads/` with S3/GCS buckets using signed time-limited URLs for downloads.
4. **CDN Edge Caching:** Cache source product images at the edge using Cloudflare or CloudFront to eliminate redundant external network fetches.
