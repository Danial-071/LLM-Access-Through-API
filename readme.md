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