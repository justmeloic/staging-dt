import logging
import os
from contextlib import asynccontextmanager

from data_generator.routes import router
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Start agent task on startup


app = FastAPI(
    title="Synthtic data generator",
    description="Synthetic data generator which mimick the behavior of Tardis API",
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
