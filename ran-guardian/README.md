# Setup

Create a .env file with the following keys:

```
GOOGLE_MAPS_API_KEY=YOUR_API_KEY
PROJECT_ID=GCP_PROJECT_ID
GEMINI_MODEL_LOCATION=us-central1
GEMINI_MODEL_NAME=gemini-2.0-flash-001
FIREBASE_DB_NAME=NATIVE_FIREBASE_DB_NAME
GOOGLE_APPLICATION_CREDENTIALS=PATH_TO_JSON_FILE
VERTEXAI_LOCATION=europe-west3
```

Install dependencies
```
poetry install
```

# Create People Events DB

```
poetry run python ran_guardian/run_event_scout.py 
```

# Run the Events Explorer UI locally

```
streamlit run ran_guardian/st_events_explorer_ui.py 
```

# Set up Events Explorer UI as a Cloud Run service

```
gcloud run deploy events-explorer \
    --image europe-west3-docker.pkg.dev/de1000-dev-mwc-ran-agent/ran-guardian/events-explorer:latest \
    --platform managed \
    --region europe-west3 \
    --port 8501 \
    --set-env-vars GOOGLE_APPLICATION_CREDENTIALS_CONTENT="$(base64 ../events_explorer_key.json)" \
    --set-env-vars KEY1=VALUE1,KEY2=VALUE2
```

# Run FastAPI and test endpoint
First in one terminal start the server
```
poetry run uvicorn app.main:app --reload
``` 

Then, open a new terminal, and run the pytest
```
poetry run pytest
```
