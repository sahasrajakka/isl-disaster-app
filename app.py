import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
from io import StringIO
from branca.element import Template, MacroElement

# --- 1. SETUP ---
st.set_page_config(page_title="Project Sentinel", layout="wide")

st.title("🛰️ Project Sentinel: AI-Powered GEOINT")
st.subheader("Real-Time Multi-Hazard Nowcasting System")

# SECURITY: Use st.secrets in production! 
# NASA_KEY = st.secrets["NASA_KEY"]
NASA_KEY = "992b32694a52d2b8e8f7d36bd3396e63" 
WEATHER_KEY = "068f5f337167419136f75ca883eb3770" 

# --- 2. DATA LAYER ---
@st.cache_data(ttl=3600) # Cache for 1 hour to prevent API hitting limits
def fetch_nowcast_data(api_key):    
    # Corrected NASA FIRMS URL structure for Country CSV 
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv{NASA_KEY}/VIIRS_SNPP_NRT/IND/1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return pd.read_csv(StringIO(response.text))
    except Exception as e:
        st.error(f"Satellite data error: {e}")
    return None

# --- 3. SIDEBAR & CONTROLS ---
st.sidebar.title("🛡️ Command Centre")
hazard_choice = st.sidebar.radio(
    "Live Hazard Overlays:",
    ("None", "Precipitation (Rain)", "Wind Speed", "Cloud Coverage")
)

fire_data = fetch_nowcast_data(NASA_KEY)

if fire_data is not None:
    st.sidebar.success("Satellite Connection: Active")
    st.sidebar.metric("Active Hotspots (IND)", len(fire_data))
else:
    st.sidebar.error("Satellite Offline")

# --- 4. MAPPING ENGINE ---
# Center on India
m = folium.Map(location=[20.5937, 78.9629], zoom_start=5, tiles="cartodbpositron")

# 4a. OpenWeather Layers
if hazard_choice != "None":
    layer_map = {
        "Precipitation (Rain)": "precipitation_new",
        "Wind Speed": "wind_new",
        "Cloud Coverage": "clouds_new"
    }
    selected_layer = layer_map[hazard_choice]
    
    # Corrected Tile URL for OpenWeatherMap 1.0
    weather_url = f"https://tile.openweathermap.org/map/{selected_layer}/{{z}}/{{x}}/{{y}}.png?appid={WEATHER_KEY}"
    
    folium.TileLayer(
        tiles=weather_url,
        attr='OpenWeatherMap',
        name=hazard_choice,
        overlay=True,
        opacity=0.6
    ).add_to(m)

# 4b. NASA Fire Dots
if fire_data is not None and not fire_data.empty:
    for _, row in fire_data.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5,
            color='red',
            fill=True,
            fill_color='orange',
            fill_opacity=0.7,
            popup=f"Brightness: {row['brightness']}K",
            tooltip="Thermal Anomaly (Fire)"
        ).add_to(m)

# --- 5. LEGEND COMPONENT ---
legend_html = f"""
{{% macro html(this, kwargs) %}}
<div style="
    position: fixed; 
    bottom: 50px; left: 50px; width: 180px; height: 110px; 
    background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
    padding: 10px; border-radius: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    ">
    <b>Map Legend</b><br>
    <i style="background:red; width:12px; height:12px; display:inline-block; border-radius:50%"></i> Fire Hotspot<br>
    <i style="background:blue; width:12px; height:12px; display:inline-block; opacity:0.5"></i> {hazard_choice}<br>
    <hr style="margin: 5px 0;">
    <small>Source: NASA & OWM</small>
</div>
{{% endmacro %}}
"""
legend = MacroElement()
legend._template = Template(legend_html)
m.get_root().add_child(legend)

# --- 6. DISPLAY ---
# IMPORTANT: The 'key' ensures the map re-renders when hazard_choice changes
st_folium(m, width=1200, height=600, key=f"hazard_map_{hazard_choice}")

if hazard_choice != "None":
    st.info(f"Fusing NASA Thermal data with OpenWeather {hazard_choice} layer.")
