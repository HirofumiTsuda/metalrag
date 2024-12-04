from metalrag.llm.llm_base import LLMBase
from groq import Groq
import json
class GroqLLM(LLMBase):
    """A class to handle Groq LLM"""
    client: Groq
    model: str

    def __init__(self, api_key: str, model: str) -> None:
        self.login(api_key)
        self.model = model

    def login(self, api_key: str) -> None:
        """Login to groq and create a client""" 
        self.client = Groq(
            api_key = api_key
        )

    def chat(
        self, messages: list[dict[str, str]], tools: dict | None = None, **kwargs
    ) -> tuple[str | list[dict[str, str]]]:
        """login to use LLMs"""
        arguments = {
            "messages": messages,
            "model" : self.model,
        }
        arguments = arguments | kwargs
        if tools is not None:
            arguments["tools"] = tools
        chat_completion = self.client.chat.completions.create(**arguments)
        content = chat_completion.choices[0].message.content
        function_data = [{
            "function_name": c.function.name,
            "arguments": json.loads(c.function.arguments),
        } for c in chat_completion.choices[0].message.tool_calls] if chat_completion.choices[0].message.tool_calls else {}
        return content, function_data


    