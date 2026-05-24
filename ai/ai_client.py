import os
import json
import httpx
import time
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self):
        self.runtime_config = {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            "ollama_model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        }
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

    def update_runtime_config(self, payload: dict):
        if "openai_api_key" in payload:
            self.runtime_config["openai_api_key"] = str(payload.get("openai_api_key") or "").strip()
        if "deepseek_api_key" in payload:
            self.runtime_config["deepseek_api_key"] = str(payload.get("deepseek_api_key") or "").strip()
        if "deepseek_base_url" in payload and payload.get("deepseek_base_url"):
            self.runtime_config["deepseek_base_url"] = str(payload.get("deepseek_base_url")).strip()
        if "deepseek_model" in payload and payload.get("deepseek_model"):
            self.runtime_config["deepseek_model"] = str(payload.get("deepseek_model")).strip()
        if "ollama_base_url" in payload and payload.get("ollama_base_url"):
            self.runtime_config["ollama_base_url"] = str(payload.get("ollama_base_url")).strip()
        if "ollama_model" in payload and payload.get("ollama_model"):
            self.runtime_config["ollama_model"] = str(payload.get("ollama_model")).strip()

    def _build_runtime(self, llm: str | None = None):
        """
        Resolve runtime client/model for a request.
        llm supports: auto/openai/deepseek/ollama.
        """
        choice = self._resolve_choice(llm)
        if choice == "openai":
            key = self.runtime_config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            if not key:
                return self.client, self.model
            return OpenAI(api_key=key), "gpt-4.1-mini"
        if choice == "ollama":
            base_url = self.runtime_config.get("ollama_base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            model = self.runtime_config.get("ollama_model") or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
            return OpenAI(api_key="ollama", base_url=base_url), model
        if choice == "deepseek":
            base_url = self.runtime_config.get("deepseek_base_url") or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            model = self.runtime_config.get("deepseek_model") or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            api_key = self.runtime_config.get("deepseek_api_key") or os.getenv("DEEPSEEK_API_KEY")
            return OpenAI(api_key=api_key, base_url=base_url), model
        return self.client, self.model

    def _resolve_choice(self, llm: str | None = None) -> str:
        choice = (llm or "auto").strip().lower()
        if choice != "auto":
            return choice
        if (self.runtime_config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")):
            return "openai"
        if (self.runtime_config.get("deepseek_api_key") or os.getenv("DEEPSEEK_API_KEY")):
            return "deepseek"
        return "ollama"

    def _provider_config(self, provider: str) -> dict:
        if provider == "openai":
            return {
                "provider": "openai",
                "configured": bool(self.runtime_config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": "gpt-4.1-mini",
            }
        if provider == "deepseek":
            return {
                "provider": "deepseek",
                "configured": bool(self.runtime_config.get("deepseek_api_key") or os.getenv("DEEPSEEK_API_KEY")),
                "base_url": self.runtime_config.get("deepseek_base_url") or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                "model": self.runtime_config.get("deepseek_model") or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            }
        return {
            "provider": "ollama",
            "configured": True,
            "base_url": self.runtime_config.get("ollama_base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            "model": self.runtime_config.get("ollama_model") or os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        }

    def check_connectivity(self, llm: str | None = None) -> dict:
        provider = self._resolve_choice(llm)
        config = self._provider_config(provider)
        configured = bool(config.get("configured"))
        if not configured:
            return {
                "ok": True,
                "requested": (llm or "auto"),
                "provider": provider,
                "configured": False,
                "available": False,
                "latency_ms": None,
                "message": f"{provider} API Key 未配置",
            }

        timeout_s = 25 if provider == "ollama" else 10
        started = time.perf_counter()
        try:
            runtime_client, runtime_model = self._build_runtime(provider)
            runtime_client.chat.completions.create(
                model=runtime_model,
                messages=[
                    {"role": "system", "content": "health check"},
                    {"role": "user", "content": "ping"},
                ],
                max_tokens=1,
                timeout=timeout_s,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            message = f"{provider} 可用（{latency_ms}ms）"
            if provider == "ollama" and latency_ms > 8000:
                message = f"{provider} 可用，但响应较慢（{latency_ms}ms，可能在加载本地模型）"
            return {
                "ok": True,
                "requested": (llm or "auto"),
                "provider": provider,
                "configured": True,
                "available": True,
                "latency_ms": latency_ms,
                "message": message,
            }
        except Exception as e:
            raw = str(e)
            if provider == "ollama":
                msg = "Ollama 不可用，请确认本地服务已启动并已拉取模型（首次加载可能较慢）"
            else:
                msg = f"{provider} 连通失败，请检查 Key 与网络"
            if "timed out" in raw.lower():
                msg = f"{provider} 请求超时，请稍后重试"
            return {
                "ok": True,
                "requested": (llm or "auto"),
                "provider": provider,
                "configured": True,
                "available": False,
                "latency_ms": None,
                "message": msg,
                "error": raw,
            }

    def analyze(self, prompt, content, llm: str | None = None):
        try:
            provider = self._resolve_choice(llm)
            runtime_client, runtime_model = self._build_runtime(provider)
            response = runtime_client.chat.completions.create(
                model=runtime_model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content}
                ],
                response_format={"type": "json_object"},
                timeout=45 if provider == "ollama" else 20,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.exception("ai_analysis_error")
            return None
