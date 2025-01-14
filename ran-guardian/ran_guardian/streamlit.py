import streamlit as st
import pandas as pd
import json

# Load the JSON data
try:
    with open("data/events_of_interest.json", "r") as f:
        data = json.load(f)
except FileNotFoundError:
    st.error("Error: data/events_of_interest.json not found.")
    st.stop()

# Convert to Pandas DataFrame
df = pd.DataFrame(data)

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