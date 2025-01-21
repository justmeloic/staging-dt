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

# Run FastAPI and test endpoint
First in one terminal start the server
```
poetry run uvicorn app.main:app --reload
``` 

Then, open a new terminal, and run the pytest
```
poetry run pytest
```
