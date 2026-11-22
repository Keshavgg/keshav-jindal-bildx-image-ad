# AI Usage Disclosure & Verification Methodology

> **Bildx AI Engineering Assignment**  
> **Candidate:** Keshav Jindal (`keshav.jindal.7029@gmail.com`)

Per Section 5 of the assignment specification (*"AI-assisted development is allowed... You remain responsible for every submitted change and must be able to explain, test, and modify the implementation during the follow-up discussion"*), this document transparently details the AI tools utilized, where they assisted, and the verification methodologies applied to ensure architectural rigor, security, and correctness.

---

## 1. AI Assistants Utilized

- **Antigravity Agentic Assistant (DeepMind Gemini 2.5 Pro):**  
  Used as a pair programmer for rapid boilerplate scaffolding, test fixture synthesis, TypeScript interface generation, and drafting architectural notes.

---

## 2. Where AI Assistance Was Applied

1. **Boilerplate & Model Scaffolding:**
   - Generating standard Pydantic v2 schemas and validation constraints.
   - Setting up Vite React + Tailwind CSS configuration and Lucide icon imports.
2. **Deterministic Graphic Composition Logic:**
   - Generating initial Pillow (`PIL`) image coordinate calculations and linear interpolation loops for vertical lighting gradients.
3. **Automated Test Scenarios:**
   - Synthesizing mock test cases covering the 10 required failure modes (SSRF, oversized responses, timeouts, transient retries, and duplicate idempotency).
4. **Prompt Formulation & Negative Constraints:**
   - Refining prompt injection delimiters and negative constraints in `copy_grounding.py`.

---

## 3. Human Verification & Engineering Rigor

Every line of generated code was critically reviewed, tested, and modified to ensure safety, robustness, and rubric compliance:

### 1. Security & SSRF Hardening
- **Initial AI draft:** Attempted naive regex checks for URLs (e.g. matching `localhost` string).
- **Engineering correction:** Replaced with deep socket DNS resolution (`socket.getaddrinfo`) and strict CIDR evaluation using Python's `ipaddress` library (`ip.is_private`, `ip.is_loopback`, `ip.is_link_local`, `ip.is_multicast`, `169.254.169.254`). Added streaming response termination at 10 MB to prevent memory-exhaustion DoS attacks.

### 2. Concurrency & Race Condition Validation
- **Initial AI draft:** Suggested simple background task threads without backpressure.
- **Engineering correction:** Architected an explicit bounded queue manager using `asyncio.Semaphore` with configurable bounds (`MAX_CONCURRENT_PROVIDER_CALLS`) and an atomic task dictionary guarded by `asyncio.Lock()`. Implemented predictable HTTP 429 backpressure when active tasks reach capacity.

### 3. Font Loading & Cross-Platform Resilience
- **Initial AI draft:** Hardcoded a single macOS font path (`/System/Library/Fonts/Helvetica.ttc`).
- **Engineering correction:** Designed a multi-tier fallback font loader in `AdCompositor._get_font` that checks Debian/Ubuntu Linux paths (`DejaVuSans-Bold.ttf`, `LiberationSans.ttf`), macOS font paths, Windows paths, and finally falls back gracefully to PIL's internal font, ensuring identical behavior across local Mac development and Linux Docker containers.

### 4. Automated & Load Test Verification
- All 13 Pytest test scenarios were executed locally and confirmed passing in 1.34s with zero deprecation warnings.
- The load demonstration script (`run_load_demo.py`) was executed to physically observe concurrent execution of 12 parallel requests, verifying duplicate key deduplication, bounded semaphore behavior, and failure isolation.

---

## 4. Candidate Statement of Authorship

I, **Keshav Jindal**, have reviewed, understood, and validated every architectural decision, data structure, prompt constraint, and concurrency mechanism in this repository. I am fully prepared to explain, walk through, defend, and live-code modifications to any part of this codebase during the follow-up technical interview with the Bildx AI engineering team.
