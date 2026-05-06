import os
import json
import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class AIClient:
    def __init__(self):
        self.use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
        
        if self.use_ollama:
            self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
            self.api_key = "ollama"
        else:
            self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            self.api_key = os.getenv("DEEPSEEK_API_KEY")

        # Use the pre-configured OpenAI client from the environment if possible
        if not self.use_ollama and os.getenv("OPENAI_API_KEY"):
            self.client = OpenAI() # Uses pre-configured env vars
            self.model = "gpt-4.1-mini"
        else:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def analyze(self, prompt, content):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"AI Analysis Error: {e}")
            return None
