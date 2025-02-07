# Use the official Python image as the base image
FROM python:3.11-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Install poetry
RUN pip install --upgrade pip && \
    pip install poetry

# Copy the poetry.lock and pyproject.toml files first (for caching)
COPY poetry.lock pyproject.toml ./

# Install project dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the application code
COPY . .

# Expose the port Streamlit will run on (default is 8501)
EXPOSE 8501

# Define the command to run your Streamlit application using poetry
CMD ["poetry", "run", "streamlit", "run", "event_scout/st_events_explorer_ui.py", "--server.port=8501", "--server.headless=true"]