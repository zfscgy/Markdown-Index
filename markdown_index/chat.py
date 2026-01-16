import os
import dotenv
dotenv.load_dotenv()

from openai import OpenAI


class LLMChat:
    def __init__(self, model: str, api_key: str = None, base_url: str = None, timeout: float = 1000):
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"), 
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            timeout=timeout)
        self.model = model

    def __call__(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content