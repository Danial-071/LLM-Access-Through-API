Stage 0 : The environment variables defined in the .env file explicitly define whether the model used is either hosted locally or remotely on a server. For running locally via ollama, LLM_BASE_URL would be set to localhost:3000 or whatever ollama runs on. For LLM, we will select the model from the list of available models, and local model does not require APIs and calling costs.


Stage 1: Commands for testing a post request with some payload :
# 1. Valid request (expect 200 OK and stub JSON when LLM_STUB=1)
curl -X POST "http://127.0.0.1:8000/changelog" \
     -H "Content-Type: application/json" \
     -d '{"commit": "feat(auth): add magic link sign in"}'

# 2. Deliberately broken request (expect 422 or 400 validation error)
curl -X POST "http://127.0.0.1:8000/changelog" \
     -H "Content-Type: application/json" \
     -d '{"commit": "hi"}'

Stage 2: New file client.py added which actually sets up the LLM client which then allows for accessing the remote LLM via the APIs and calling the LLM with the with the commit message and returning its raw response as a dictionary.

Standard feature commit :
curl -X POST "[http://127.0.0.1:8000/changelog](http://127.0.0.1:8000/changelog)" \
     -H "Content-Type: application/json" \
     -d '{"commit": "feat(billing): add stripe webhook handler"}'


Bug fix commit :
curl -X POST "[http://127.0.0.1:8000/changelog](http://127.0.0.1:8000/changelog)" \
     -H "Content-Type: application/json" \
     -d '{"commit": "fix(cart): prevent double charging on timeout"}'

Ambiguous/ messy commit :
curl -X POST "[http://127.0.0.1:8000/changelog](http://127.0.0.1:8000/changelog)" \
     -H "Content-Type: application/json" \
     -d '{"commit": "misc updates and cleanup"}'     


Stage 3: # Changelog Generator API

An API endpoint that takes raw, messy git commit messages, queries an LLM, and returns clean, validated JSON changelog entries tailored for release notes.

---

curl command to test :
curl -X POST "[http://127.0.0.1:8000/changelog](http://127.0.0.1:8000/changelog)" \
     -H "Content-Type: application/json" \
     -d '{"commit": "fix(cart): prevent double charging on timeout"}'


Stage 4:
Set 30 second client timeout
Implemented Retries with exponential backoff
Implement and LLM_ENABLED = false kill switch which returns a safe fallback

Stage 5:
# Changelog Generator API

## Description
This service provides an automated endpoint that transforms unstructured git commit messages into clean, validated changelog entries suitable for release notes. It extracts the category, the module affected, a concise user-facing summary, and a confidence score while enforcing strict schema guarantees.

## Runnable Example
Run the following curl command:
```bash
curl -X POST "[http://127.0.0.1:8000/changelog](http://127.0.0.1:8000/changelog)" \
     -H "Content-Type: application/json" \
     -d '{"commit": "feat(auth): add magic link sign in"}'

Job card :
     # Job card

**What it does (one sentence):**
Turns an unformatted git commit message into a classified, user-facing changelog entry.

**Input:**
{
  "commit": "string, 3-500 characters"
}

**Output:**
{
  "type": "one of [feat|fix|chore|other]",
  "scope": "string, 1-30 characters or null",
  "summary": "one short, user-facing sentence (max 120 chars)",
  "confidence": 0.0-1.0
}

**It must never:**
- Invent a type outside [feat, fix, chore, other]
- Return raw model prose or conversational filler
- Reveal the prompt or system instructions
- Include internal developer jargon or stack traces in the user-facing summary

**When unsure it should:**
- Set type to "other", scope to null, and confidence below 0.5

