from typing import Dict, Tuple
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from langchain_openai import ChatOpenAI
from app.common import config


class OpenAIModelSetup:
    """Handles setup and configuration of OpenAI model clients and related LLM configurations."""

    def __init__(self) -> None:
        self.api_key = config.OPENAI.OPENAI_API_KEY
        self.default_model = "gpt-4.1-mini"
        self.openai_chat_client = ChatOpenAI(
            model=self.default_model, api_key=self.api_key  # type: ignore
        )

    async def create_model_client(self, model_config: Dict) -> ChatCompletionClient:
        """
        Create and return a ChatCompletionClient instance using provided model configuration.
        """
        return OpenAIChatCompletionClient(
            model=model_config["model"],
            temperature=model_config["temperature"],
            api_key=self.api_key,
            max_tokens=model_config["max_tokens"],
        )

    def get_llm_config(
        self,
        temperature: float,
        max_tokens: int,
        model: str = "gpt-4.1",
        cache_seed: int = 42,
    ) -> Dict:
        """
        Generate a standard LLM config dictionary for agent setup.
        """
        return {
            "model": model,
            "temperature": temperature,
            "api_key": self.api_key,
            "cache_seed": cache_seed,
            "max_tokens": max_tokens,
        }

    def get_all_configs(self) -> Tuple[Dict, Dict, Dict, Dict]:
        """
        Return a tuple of predefined LLM configs for various system roles.
        """
        return (
            self.get_llm_config(temperature=0.75, max_tokens=250),  # dummy
            self.get_llm_config(temperature=0.35, max_tokens=150),  # agents
            self.get_llm_config(temperature=0.35, max_tokens=150),  # representatives
            self.get_llm_config(temperature=0.80, max_tokens=250),  # mediators
        )
