# Setup

Create a .env file with the following keys:

```
GOOGLE_MAPS_API_KEY=YOUR_API_KEY
```

Install dependencies
```
poetry install
```

# Create People Events DB

```
poetry run python ran_guardian/run_event_scout.py
```

# Set up Events Explorer UI as a Cloud Run service
```
gcloud builds submit --tag gcr.io/[PROJECT_NAME]/[REPO_NAME]/events-explorer-ui:latest .
```
```
gcloud run deploy events-explorer-ui \
    --image gcr.io/[PROJECT_NAME]/[REPO_NAME]/events-explorer-ui:latest \
    --platform managed \
    --region europe-west1 \
    --port 8501 \
    --set-env-vars GOOGLE_APPLICATION_CREDENTIALS_CONTENT="$(base64 ../events_explorer_key.json)" \
    --set-env-vars KEY1=VALUE1,KEY2=VALUE2
```
# Run FastAPI for mock data server
In another terminal
```
poetry run uvicorn data_generator.main:app --reload --port 8001
```

# Run FastAPI for backend
First in one terminal start the server
```
poetry run uvicorn app.main:app --reload
```
