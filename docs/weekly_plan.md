# PLAN.md — SRE Postmortem RAG Assistant, Week-by-Week Build Plan

Guiding rule for every week below: **simple, working, and evaluated beats sophisticated
and half-finished.** Each week ends with something you can actually run and show — not a
partial feature, not "mostly working." If a week's scope starts creeping toward something
new/unfamiliar, cut it and push it to next week rather than half-finish two things.

Reference `CLAUDE.md` for the full rules, scope, and tech decisions behind every choice
made here.

---

## Week 1 — Core RAG, local script only

**Goal:** Prove the basic retrieval → generation loop works, end to end, with zero
infrastructure around it.

**Tasks:**
1. Clone `github.com/danluu/post-mortems` locally.
2. Write a plain Python script (no FastAPI, no Docker yet) that:
   - Loads a handful of the postmortem markdown files
   - Chunks them (`RecursiveCharacterTextSplitter`)
   - Embeds chunks locally (`sentence-transformers/all-MiniLM-L6-v2` via
     `langchain-huggingface`)
   - Builds an in-memory vector store (Chroma or `InMemoryVectorStore`)
   - Takes a hardcoded question, retrieves top-k chunks, sends them + the question to
     Groq (`groq/openai/gpt-oss-120b`, with `groq/openai/gpt-oss-20b` as fallback) via
     LiteLLM, and prints the answer

**Definition of done (runnable):** `python week1_rag.py` prints a grounded answer to a
hardcoded question, sourced from the postmortem corpus, in your terminal.

**Explicitly not this week:** FastAPI, guardrails, multi-turn memory, Docker, evaluation.
Just prove the core loop works.

---

## Week 2 — Wrap it in a FastAPI endpoint

**Goal:** Turn Week 1's script into a real HTTP service, still single-turn (no memory yet).

**Tasks:**
1. Move the Week 1 logic into a FastAPI app (`main.py`).
2. Build the vector store once at startup (not per-request).
3. Expose `POST /ask` — takes `{"question": "..."}`, returns `{"answer": "...", "sources": [...]}`.
4. Add a `GET /health` endpoint (simple liveness check — good practice, easy interview
   talking point about production readiness).
5. Confirm the auto-generated Swagger UI at `/docs` works and lets you test `/ask`
   interactively.

**Definition of done (runnable):** `uvicorn main:app --reload`, then open
`http://localhost:8000/docs`, use "Try it out" on `/ask`, get a real grounded answer back
through the browser.

**Explicitly not this week:** Guardrails, memory, Docker, evaluation.

---

## Week 3 — Guardrails

**Goal:** Add the input guardrails from the course, applied to real incoming requests.

**Tasks:**
1. Add the PII redaction guardrail (email, phone, SSN/Aadhaar/PAN patterns) as a
   pre-processing step on the incoming `question` before it's embedded/sent to Groq.
2. Add the prompt-injection detection guardrail (regex patterns for "ignore previous
   instructions," jailbreak phrasing, etc.) — reject the request with a clear message if
   triggered.
3. Write 3-4 manual test requests: one normal question, one with PII in it, one injection
   attempt — confirm each behaves correctly.

**Definition of done (runnable):** Hit `/ask` with a PII-containing question and see it
get redacted before reaching the model; hit it with an injection attempt and see it
rejected with a clear message; hit it with a normal question and see it work exactly as
before.

**Explicitly not this week:** Memory, Docker, evaluation.

---

## Week 4 — Multi-turn conversation memory (Upstash Redis)

**Goal:** Let a client have an actual back-and-forth conversation, not just one-shot Q&A.

**Tasks:**
1. Sign up for Upstash (free, no card), create a Redis database, grab the REST URL + token.
2. Add `session_id` to the `/ask` request body (client generates/reuses a UUID per
   conversation).
3. On each request: read the session's prior turns from Upstash Redis, include them as
   conversation context in the prompt to Groq, then write the new turn back to Redis.
4. Set a reasonable history cap (e.g., last 6 turns) so prompts don't grow unbounded.
5. Test manually: send 3 questions in a row with the same `session_id` and confirm the
   third answer can correctly reference something from the first.

**Definition of done (runnable):** A short manual test script or curl sequence
demonstrates a 3-turn conversation where the model's later answers are clearly using
earlier context, and the conversation still works after restarting the local server
(proving it's actually reading from Redis, not an in-memory variable).

**Explicitly not this week:** Docker, deployment, evaluation.

---

## Week 5 — Evaluation

**Goal:** Produce real, defensible numbers — this is the week that makes the project
resume-credible rather than just "a chatbot that works."

**Tasks:**
1. From the postmortems you've actually indexed, hand-write 15-20 question/answer pairs
   (the question, and a correct reference answer drawn from the real text).
2. Create a LangSmith dataset from this test set (`client.create_dataset` +
   `client.create_examples`, idempotent — check `has_dataset` first).
3. Adapt the course's `correctness`, `relevance`, and `groundedness` evaluators to run
   against Groq (`method="function_calling"` for structured output, since Groq doesn't
   support OpenAI's strict `json_schema` mode).
4. Run `client.evaluate(...)` against your `/ask` logic (wrapped as the target function)
   with all three evaluators.
5. Record the resulting scores (e.g., "18/20 correctness, 19/20 groundedness") — these are
   the numbers that go on your resume and get discussed in interviews.

**Definition of done (runnable):** A LangSmith experiment URL exists, showing per-question
scores across correctness/relevance/groundedness, that you can open and walk someone
through live.

**Explicitly not this week:** Docker, deployment. Get the eval numbers first — deploying
something unevaluated isn't the point of this project.

---

## Week 6 — Dockerize and deploy

**Goal:** Get a real public URL an interviewer can open cold, with everything from Weeks
1-5 working inside it.

**Tasks:**
1. Write a `Dockerfile` (CPU-only base image, install deps, copy the bundled postmortem
   corpus + app code, expose port `7860` — HF Spaces' expected port for Docker SDK).
2. Add a `.gitignore` covering `.env` and any local vector store cache files.
3. Create a Hugging Face Space (Docker SDK, CPU Basic, **Public** visibility).
4. Add all required secrets in the Space settings: `GROQ_API_KEY`, `LANGSMITH_API_KEY`,
   `LANGSMITH_ENDPOINT`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`.
5. Push the repo to the Space's git remote and watch the build logs.
6. Once live, deliberately let it sit idle until it sleeps, then reopen the URL cold and
   confirm it wakes and works correctly (vector index rebuilds, guardrails still fire,
   memory still reads from Redis).
7. Write `README.md` (see the companion file) — architecture, eval results, and the live
   Space link.

**Definition of done (runnable):** A public URL
(`https://<username>-<space-name>.hf.space/docs`) that a stranger can open with no setup
and get a real, grounded, guarded, multi-turn answer from — this is the finished project.

---

## After Week 6

Go through the resume-worthiness checklist in `CLAUDE.md` Section 10 before calling this
"done." If every box is checked and every claim in the resume bullet is something you can
demo live on request, the project is complete — move to the next thing (agentic/MCP work,
per the Future Updates section of `CLAUDE.md`), rather than adding more scope here.