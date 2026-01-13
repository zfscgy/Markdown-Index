from openai import OpenAI


class LLMChat:
    def __init__(self, model: str, api_key: str, api_base: str, timeout: float = 1000):
        self.client = OpenAI(api_key=api_key, base_url=api_base)
        self.model = model
        self.timeout = timeout

    def __call__(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.timeout
        )
        return response.choices[0].message.content