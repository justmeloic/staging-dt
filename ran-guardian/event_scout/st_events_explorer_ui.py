import streamlit as st
import pandas as pd
import gmap_utils
import folium
from streamlit_folium import st_folium
import firestore_helper
from branca.element import Template, MacroElement

st.set_page_config(page_title="RAN Guardian Events Explorer", layout="wide")

stats = firestore_helper.get_global_stats()
num_events = str(stats["num_events"])
num_locations = str(stats["num_locations"])
st.sidebar.header(f":primary[AI Discovered Events:] :primary-background[{num_events}]")
st.sidebar.header(f":primary[New Events (last 24 hours):] :primary-background[656]")
st.sidebar.header(f":primary[Locations Scanned:] :primary-background[{firestore_helper.get_num_scanned_locations()}/{num_locations}]")
st.sidebar.text("")

show_locations = st.sidebar.checkbox("Show DT Site Locations")

st.sidebar.subheader("Filter Events")
selected_location_high = st.sidebar.radio("**Featured Locations (Germany)**", firestore_helper.get_locations(priority="high"), index=1)
selected_locations_all = st.sidebar.multiselect("All Locations", firestore_helper.get_locations())
selected_locations = [selected_location_high] + selected_locations_all

location = selected_locations[0] if selected_locations else "Berlin Berlin"

st.title(f":primary[RAN Guardian Events Explorer] - {location}")
events = firestore_helper.get_events_by_location(location)
print(f"Retrieved {len(events)} for location {location}")

geo_coordinates = gmap_utils.geocode_location(location + ", Germany")
print(geo_coordinates)
center_lat = geo_coordinates["lat"]
center_lng = geo_coordinates["lng"]

df = pd.DataFrame(events).assign(size_num=lambda x: x["size"].map({"S": 100, "M": 500, "L": 750, "XL": 1000})).fillna(100)
df = df.dropna(subset=['lat', 'lng'])

df["start_date_formatted"] = pd.to_datetime(df["start_date"], errors='coerce')
today = pd.to_datetime('today').normalize()
df["start_date_formatted"] = df["start_date"].fillna(today)
df["start_date_formatted"] = pd.to_datetime(df["start_date_formatted"], errors='coerce')
df['days_diff'] = (df["start_date_formatted"] - today).dt.days

def assign_color(days_diff):
    if days_diff < 0:
        return "gray"
    elif days_diff <= 30:
        return "red"
    elif days_diff <= 90:
        return "blue"
    else:
        return "green"
    
df['color'] = df['days_diff'].apply(assign_color)

unique_event_types = df['event_type'].unique()   
selected_event_types = st.sidebar.multiselect("Event Type", unique_event_types)

filtered_df = df.copy()
if selected_event_types:
    filtered_df = filtered_df[filtered_df['event_type'].isin(selected_event_types)]

unique_event_sizes = df['size'].unique()   
selected_event_sizes = st.sidebar.multiselect("Event Size", unique_event_sizes)

if selected_event_sizes:
    filtered_df = filtered_df[filtered_df['size'].isin(selected_event_sizes)]

size_definitions = """
**S:** Up to 100 people

**M:** Up to 500 people

**L:** Up to 5000 people

**XL:** More than 5000 people
"""
st.sidebar.markdown(size_definitions)

map = folium.Map(location=[center_lat, center_lng], zoom_start=12)
for index, row in filtered_df.iterrows():
    popup_html = f"""
        <b><a href="{row["url"]}" target="_blank">{row["name"]}</a></b><br>
        <b>Start Date:</b> {row["start_date"]}<br>
        <b>Event Type:</b> {row["event_type"]}<br>
        <b>Size:</b> {row["size"]}<br>
    """
    folium.Circle(
        location=[row['lat'], row['lng']],
        radius=row['size_num'],  # Use event radius from DataFrame
        popup=folium.Popup(popup_html, max_width=300),  # Display event name in popup
        color=row['color'],      # Use event-specific color
        fill=True,
        fill_opacity=0.6,
        line_opacity=0.2,
    ).add_to(map)

template = """
{% macro html(this, kwargs) %}

<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>jQuery UI Draggable - Default functionality</title>
  <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css">

  <script src="https://code.jquery.com/jquery-1.12.4.js"></script>
  <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>
  
  <script>
  $( function() {
    $( "#maplegend" ).draggable({
                    start: function (event, ui) {
                        $(this).css({
                            right: "auto",
                            top: "auto",
                            bottom: "auto"
                        });
                    }
                });
});

  </script>
</head>
<body>

 
<div id='maplegend' class='maplegend' 
    style='position: absolute; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.8);
     border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px;'>
     
<div class='legend-title'>Event Colors</div>
<div class='legend-scale'>
  <ul class='legend-labels'>
    <li><span style='background:red;opacity:0.7;'></span>Within next 30 days</li>
    <li><span style='background:orange;opacity:0.7;'></span>Within next 90 days</li>
    <li><span style='background:green;opacity:0.7;'></span>Beyond 90 days</li>
    <li><span style='background:gray;opacity:0.7;'></span>Past events</li>
  </ul>
</div>
</div>
 
</body>
</html>

<style type='text/css'>
  .maplegend .legend-title {
    text-align: left;
    margin-bottom: 5px;
    font-weight: bold;
    font-size: 90%;
    }
  .maplegend .legend-scale ul {
    margin: 0;
    margin-bottom: 5px;
    padding: 0;
    float: left;
    list-style: none;
    }
  .maplegend .legend-scale ul li {
    font-size: 80%;
    list-style: none;
    margin-left: 0;
    line-height: 18px;
    margin-bottom: 2px;
    }
  .maplegend ul.legend-labels li span {
    display: block;
    float: left;
    height: 16px;
    width: 30px;
    margin-right: 5px;
    margin-left: 0;
    border: 1px solid #999;
    }
  .maplegend .legend-source {
    font-size: 80%;
    color: #777;
    clear: both;
    }
  .maplegend a {
    color: #777;
    }
</style>
{% endmacro %}"""

macro = MacroElement()
macro._template = Template(template)

map.get_root().add_child(macro)

if show_locations:
    nodes_df = firestore_helper.get_nodes_within_radius(center_lng, center_lat, 15000)
    print("Retrieved nodes: ", len(nodes_df))
        
    for index, row in nodes_df.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=row['MS_MSRBS_HERSTELLER'],  # Optional: Add a popup with the location name
            icon=folium.Icon(color='blue', icon='info-sign') # Optional: Customize the icon
        ).add_to(map)

st_data = st_folium(map, use_container_width=True, height=1100)

