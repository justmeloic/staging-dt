# Setup

Create a .env file with the following keys:

```
GOOGLE_MAPS_API_KEY=YOUR_API_KEY
```

```
poetry install
poetry run python event_scout/set_up.py 
```

# Create People Events DB

```
poetry install
poetry run python event_scout/orchestrator.py 
```

# Run Event UI
```
poetry run streamlit run event_scout/streamlit_events_ui.py 
```