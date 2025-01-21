import streamlit as st
import pandas as pd
import gmap_utils

import firestore_helper

st.sidebar.header("Event Filters")
selected_locations_high = st.sidebar.multiselect("High Priority Locations", firestore_helper.get_locations(priority="high"))
selected_locations_all = st.sidebar.multiselect("All Locations", firestore_helper.get_locations())
selected_locations = selected_locations_high + selected_locations_all

location = selected_locations[0] if selected_locations else "Berlin Berlin"

events = firestore_helper.get_events_by_location(location)
geo_coordinates = gmap_utils.geocode_location(location + ", Germany")
center_lat = geo_coordinates["lat"]
center_lng = geo_coordinates["lng"]

df = pd.DataFrame(events).assign(size_num=lambda x: x["size"].map({"S": 100, "M": 500, "L": 750, "XL": 1000}))
df = df.dropna(subset=['lat', 'lng'])

filtered_df = df.copy()

st.map(df, zoom=10, latitude="lat", longitude="lng", size="size_num")

# df = pd.DataFrame(
#     {
#         "col1": np.random.randn(1000) / 50 + 37.76,
#         "col2": np.random.randn(1000) / 50 + -122.4,
#         "col3": np.random.randn(1000) * 100,
#         "col4": np.random.rand(1000, 4).tolist(),
#     }
# )

# st.map(df, latitude="col1", longitude="col2", size="col3", color="col4")
