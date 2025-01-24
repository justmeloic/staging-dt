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
gcloud builds submit --tag europe-west1-docker.pkg.dev/events-explorer-448816/events-db-repo/events-explorer-ui:v1 .
```
```
gcloud run deploy events-explorer-ui \
    --image europe-west1-docker.pkg.dev/events-explorer-448816/events-db-repo/events-explorer-ui:v1 \
    --platform managed \
    --region europe-west1 \
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
