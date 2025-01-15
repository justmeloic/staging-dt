# Setup

Create a .env file with the following keys:

```
GOOGLE_MAPS_API_KEY=YOUR_API_KEY
```

```
poetry install
poetry run python ran_guardian/set_up.py 
```

# Create People Events DB

```
poetry install
poetry run python ran_guardian/orchestrator.py 
```