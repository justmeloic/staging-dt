import logging
import os
from contextlib import asynccontextmanager

from data_generator.mock_data_generator import MockDataGenerator
from data_generator.routes import router
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Store mockdata generator in app state
    app.state.mock_data_generator = MockDataGenerator()  # default config ...
    app.state.mock_data_generator.run()

    # Start agent task on startup


app = FastAPI(
    title="Synthtic data generator",
    description="Synthetic data generator which mimick the behavior of Tardis API",
    # add a lifespan which are the generated node datasets
)

# Include the router
app.include_router(router)
