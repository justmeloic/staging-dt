from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="RAN Troubleshooting Service",
    description="Service for network operators to diagnose RAN performance issues"
)

app.include_router(router)
