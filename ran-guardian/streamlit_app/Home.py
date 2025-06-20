import json
import re
import time
from datetime import datetime

import requests
import streamlit as st
from streamlit import fragment


def parse_line(line: str):
    line_str = line.decode("utf-8")
    pattern = r"^data:\s*\{.*\}$"
    if re.match(pattern, line_str):
        try:
            data_str = line_str.split("data:")[
                1
            ].strip()  # Split at the first "data: " and take the second part
            print(data_str)
            data = json.loads(data_str)
            timestamp_str = data.get("timestamp", "N/A")
            timestamp = (
                datetime.fromisoformat(timestamp_str).strftime("%Y-%m-%d %H:%M:%S")
                if timestamp_str != "N/A"
                else "N/A"
            )
            step = data.get("step", "N/A")
            level = data.get("level", "info")  # Default to info if level is missing
            event_id = data.get("event_id", "N/A")
            issue_id = data.get("issue_id", "NA")
            node_id = data.get("node_id", "N/A")
            message = data.get("message", "N/A")

            # Define colors for different log levels
            level_colors = {
                "info": "green",
                "warning": "orange",
                "error": "red",
            }
            level_color = level_colors.get(
                level, "blue"
            )  # Default to blue if level is unknown

            formatted_line = f"""
            <div style="border: 1px solid #eee; padding: 0.5em; margin-bottom: 0.5em; border-radius: 5px;">
                <p style="margin-bottom: 0.2em;">
                    <span style="font-weight: bold;">Time:</span> {timestamp}
                </p>
                <p style="margin-bottom: 0.2em;">
                    <span style="font-weight: bold;">Step:</span> {step}
                </p>
                <p style="margin-bottom: 0.2em;">
                    <span style="font-weight: bold;">Event ID:</span> {event_id}
                </p>
                <p style="margin-bottom: 0.2em;">
                    <span style="font-weight: bold; color: {level_color};">Level:</span> <span style="color: {level_color};">{level.upper()}</span>
                </p>
                <p style="margin-bottom: 0;">
                    <span style="font-weight: bold;">Message:</span> {message}
                </p>
            </div>
            """
            return formatted_line
        except Exception as e:
            print(f"Error parsing line: {line_str} - {e}")
            return None
    return None


def display_stream(url):
    """Fetches a stream of logs and displays parsed output in Streamlit with a placeholder.

    Args:
        url (str): The URL to stream logs from.
    """
    placeholder_container = st.empty()  # Create an empty placeholder
    placeholder_container.markdown(
        "<p style='color: grey;'>Waiting for logs from server...</p>",
        unsafe_allow_html=True,
    )  # Show waiting message initially
    first_log_received = False  # Flag to track if the first log is received

    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()  # Check HTTP status

            for line in response.iter_lines():
                parsed_line = parse_line(line)
                if parsed_line:
                    if not first_log_received:
                        placeholder_container.empty()  # Clear the placeholder once first log is received
                        first_log_received = True
                    st.write(
                        parsed_line, unsafe_allow_html=True
                    )  # Display logs in the log_area container
                    time.sleep(2)  # sleep 2 seconds

    except requests.exceptions.RequestException as e:
        placeholder_container.empty()  # Clear waiting message in case of error
        st.error(f"Error during streaming: {e}")


# Streamlit App
st.title("RAN Guardian Agent Flow")
st.markdown("Click 'Start Streaming' to view agent logs:")

# Endpoint URL (you might want to make this configurable in Streamlit)
endpoint_url = "http://localhost:8000/logs/stream"

if st.button("Start Streaming"):
    with st.container(border=True):
        display_stream(endpoint_url)
