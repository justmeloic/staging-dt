import streamlit as st
import pandas as pd
import json
from model_utils import generate
## USE below for local dataset management ##
import data_manager_flat as data_manager

## USE below for datastore dataset management ##
# import data_manager_datastore as data_manager

@st.cache_data
def fetch_data():
    data = data_manager.read_all("events_of_interest")
    return data


# Convert to Pandas DataFrame
df = pd.DataFrame(fetch_data())

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# Date Filter
unique_dates = df['date'].unique()
selected_dates = st.sidebar.multiselect("Date", unique_dates)

# Location Filter
unique_locations = df['location'].unique()
selected_locations = st.sidebar.multiselect("Location", unique_locations)

# Name Filter
unique_names = df['name'].unique()
selected_names = st.sidebar.multiselect("Name", unique_names)

# Size Filter
unique_sizes = df['size'].unique()
selected_sizes = st.sidebar.multiselect("Size", unique_sizes)

# Time Filter
unique_times = df['time'].unique()
selected_times = st.sidebar.multiselect("Time", unique_times)

# Event Type Filter (NEW)
unique_event_types = df['event_type'].unique()
selected_event_types = st.sidebar.multiselect("Event Type", unique_event_types)

# --- Apply Filters ---
filtered_df = df.copy()

if selected_dates:
    filtered_df = filtered_df[filtered_df['date'].isin(selected_dates)]
if selected_locations:
    filtered_df = filtered_df[filtered_df['location'].isin(selected_locations)]
if selected_names:
    filtered_df = filtered_df[filtered_df['name'].isin(selected_names)]
if selected_sizes:
    filtered_df = filtered_df[filtered_df['size'].isin(selected_sizes)]
if selected_times:
    filtered_df = filtered_df[filtered_df['time'].isin(selected_times)]
if selected_event_types:
    filtered_df = filtered_df[filtered_df['event_type'].isin(selected_event_types)]

# --- Display Table ---
st.header("Events of Interest")
st.dataframe(filtered_df, hide_index=True, use_container_width=True)

from streamlit_calendar import calendar

calendar_options = {
    "editable": False,
    "selectable": True,
    "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "dayGridDay,dayGridWeek,dayGridMonth",
            },
    "slotMinTime": "06:00:00",
    "slotMaxTime": "18:00:00",
    "initialView": "dayGridMonth",
    "callback": "eventClick",

}

custom_css="""
    .fc-event-past {
        opacity: 0.8;
    }
    .fc-event-time {
        font-style: italic;
    }
    .fc-event-title {
        font-weight: 700;
    }
    .fc-toolbar-title {
        font-size: 2rem;
    }
"""
calendar_events = [
    {
        **d, 
        "title": d.get("name"),
        "created_at":d.get("created_at").isoformat(),
        "updated_at":d.get("updated_at").isoformat() if d.get("updated_at") else None,
        "backgroundColor": "#FF4B4B" if d.get('size').lower()=='large' else "#FFBD45"
        } for d in filtered_df.to_dict(orient="records")
]

selected_event = calendar(events=calendar_events, options=calendar_options, custom_css=custom_css)

if selected_event:
    if selected_event.get("eventClick") and selected_event["eventClick"].get("event"):
        all_props = selected_event["eventClick"].get("event")
        extended_props = selected_event["eventClick"]["event"]["extendedProps"]
        st.write("Event Details (extendedProps):")
        # st.json(selected_event["eventClick"].get("event"))  # Or display individually as before

        # First row of metrics
        col00, col01 = st.columns(2)  # Create 2 columns
        with col00:
            if "title" in all_props:
                st.metric("Title", all_props["title"])
        with col01:
            if "start" in all_props:
                st.metric("Date", all_props["start"])

        # Another row of metrics
        col1, col2 = st.columns(2)  # Create 2 columns
        with col1:
            if "size" in extended_props:
                st.metric("Size", extended_props["size"])
        with col2:
            if "event_type" in extended_props:
                st.metric("Event Type", extended_props["event_type"])

        # Another row of metrics
        col3, col4 = st.columns(2)  # Create another 2 columns
        with col3:
            if "location" in extended_props:
                st.metric("Location", extended_props["location"])
        with col4:
            if "time" in extended_props:
                st.metric("Time", extended_props["time"])
    else:
        st.write("No event selected or event data not available.")