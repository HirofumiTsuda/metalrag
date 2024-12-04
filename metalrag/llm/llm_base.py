from abc import ABC
from typing import Any

class LLMBase(ABC):
    """A base class to handle llms"""

    def login(self, *args, **kwargs) -> None:
        """login to use LLMs"""
        pass

    def chat(self, messages: list[dict[str, str]], model: str, tools = dict | None, *args,**kwargs) -> Any:
        """login to use LLMs"""
        pass