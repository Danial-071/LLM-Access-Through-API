import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)

res = client.chat.completions.create(
    model=os.environ["LLM"],
    messages=[{"role": "user", "content": "Reply with exactly the word: ready"}],
)

if res.choices:
    print(res.choices[0].message.content)
else:
    print("Failed response:", res)