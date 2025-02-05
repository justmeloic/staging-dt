import os
from dotenv import load_dotenv
from llm.reasoning_agent import ReasoningAgent

load_dotenv()

PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("VERTEXAI_LOCATION")

if __name__ == "__main__":
    agent = ReasoningAgent(project=PROJECT_ID, location=LOCATION)
    agent.set_up()
    print(agent.query(message="Get product details for shoes"))
