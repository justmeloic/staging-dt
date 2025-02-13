#!/bin/bash

# Load environment variables from .env (if you are using python-dotenv in your apps)
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Start FastAPI servers in the background
poetry run uvicorn data_generator.main:app --port 8001 --host 0.0.0.0 &
poetry run uvicorn app.main:app --port 8000 --host 0.0.0.0 &

# Start Streamlit in the foreground (keeps the container running)
poetry run streamlit run event_scout/st_events_explorer_ui.py --server.port=8501 --server.headless=true --server.address=0.0.0.0

# Keep the script running to prevent container exit (optional, Streamlit usually does this)
# wait
