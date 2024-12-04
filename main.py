import os
from metalrag.llm.groq import GroqLLM
from metalrag.agent.agent import Agent
from dotenv import load_dotenv

load_dotenv()

groq_llm = GroqLLM(
    api_key=os.environ.get("GROQ_API_KEY"),
    model="llama-3.1-70b-versatile",
)

agent = Agent(llm=groq_llm)

print(agent.chat("please tell me about the album Dystopia"))
print(agent.chat("please tell me about the megadeth's album called Dystopia"))
