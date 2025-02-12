from dotenv import load_dotenv
from fastapi import FastAPI
import asyncio
import os
import logging
from contextlib import asynccontextmanager

from app.routes import router
from app.agent import Agent
from app.data_manager import DataManager
from app.network_manager import NetworkConfigManager

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Initialize your managers
data_manager = DataManager(project_id=PROJECT_ID)
network_manager = NetworkConfigManager()

# Create agent instance
agent = Agent(data_manager, network_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Store agent in app state
    app.state.agent = agent

    # Start agent task on startup
    if os.environ.get("START_AGENT_ON_STARTUP", "true") == "true":
        agent_task = asyncio.create_task(agent.start())

    yield  # Run FastAPI

    # Cleanup on shutdown
    if os.environ.get("START_AGENT_ON_STARTUP", "true") == "true":
        await agent.stop()
        await agent_task

app = FastAPI(
    title="RAN Troubleshooting Service",
    description="Service for network operators to diagnose RAN performance issues",
    lifespan=lifespan,
)

# Include the router
app.include_router(router)
