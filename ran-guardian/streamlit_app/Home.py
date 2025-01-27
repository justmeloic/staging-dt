import streamlit as st
from streamlit import fragment
import requests
import threading
import time
import json
from queue import Queue


def parse_line(line: str):
    line_str = line.decode("utf-8")
    if line_str.startswith("data: "):
        try:
            data = json.loads(line_str[5:])
            print(data["message"])
            return data["message"]
        except Exception:
            print(f"Error parsing line: {line_str}")
            return None           
    return None


def display_stream(url, max_lines=10):
    """Fetches a stream of logs in a separate thread and puts it in a queue.

    Args:
        url (str): The URL to stream logs from.
        log_queue (Queue): A queue to pass received log lines.
        stop_event (threading.Event): An event to signal when to stop.
    """
    n_line = 0
    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()  # Check HTTP status
            # todo: add events to stop the streaming of response

            for line in response.iter_lines():
                line = parse_line(line)
                if n_line > max_lines:
                    break
                if line:
                    st.write(line)
                    n_line += 1
    except requests.exceptions.RequestException as e:
        print(f"Error during streaming: {e}")

# Streamlit App
st.title("RAN Guardian Agent log")

# Endpoint URL (you might want to make this configurable in Streamlit)
endpoint_url = "http://localhost:8000/logs/stream"

now = time.time()
print(f"running now {now}")

# Initialize LogStreamer (outside the session state for persistence)

if st.button("Start Streaming"):
    with st.container(border=True):
        display_stream(endpoint_url, max_lines=50)
