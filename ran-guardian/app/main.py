import asyncio
import logging
import os
from contextlib import asynccontextmanager

from app.agent import Agent
from app.data_manager import DataManager
from app.routes import router
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Initialize your managers
data_manager = DataManager(project_id=PROJECT_ID)

# Create agent instance
agent = Agent(data_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Store agent in app state
    app.state.agent = agent

    # Start agent task on startup
    # if os.environ.get("START_AGENT_ON_STARTUP", "true") == "true":
    #    agent_task = asyncio.create_task(agent.start())

    yield  # Run FastAPI

    # Cleanup on shutdown
    # if os.environ.get("START_AGENT_ON_STARTUP", "true") == "true":
    #    await agent.stop()
    #    await agent_task


app = FastAPI(
    title="RAN Troubleshooting Service",
    description="Service for network operators to diagnose RAN performance issues",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include the router
app.include_router(router)
