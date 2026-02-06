import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
from io import StringIO

# --- 1. SETUP ---
st.set_page_config(page_title="Project Sentinel", layout="wide")

st.title("🛰️ Project Sentinel: AI-Powered GEOINT")
st.subheader("Real-Time Multi-Hazard Nowcasting System")

# --- 2. SECURITY LAYER ---
# Once you move to 'secrets.toml', replace these with st.secrets["KEY_NAME"]
NASA_KEY = "992b32694a52d2b8e8f7d36bd3396e63" 
WEATHER_KEY = "068f5f337167419136f75ca883eb3770" # <--- Put your key here

# --- 3. DATA LAYER (NASA API) ---
def fetch_nowcast_data():    
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv{NASA_KEY}/VIIRS_SNPP_NRT/IND/1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return pd.read_csv(StringIO(response.text))
    except Exception as e:
        st.error(f"Failed to fetch satellite data: {e}")
    return None

# --- 4. SIDEBAR & CONTROLS ---
st.sidebar.title("🛡️ Command Centre")

# STEP 2 ADD-ON: The Hazard Selector
hazard_choice = st.sidebar.radio(
    "Live Hazard Overlays:",
    ("None", "Precipitation (Rain)", "Wind Speed", "Cloud Coverage")
)

fire_data = fetch_nowcast_data()

if fire_data is not None:
    st.sidebar.success(f"Satellite Connection: Active")
    st.sidebar.metric("Active Hotspots", len(fire_data))
else:
    st.sidebar.error("Satellite Offline")

# --- 5. MAPPING ENGINE ---
m = folium.Map(location=[20.5937, 78.9629], zoom_start=5, tiles="cartodbpositron")

# 5a. Logic for OpenWeather Multi-Hazard Layers
if hazard_choice != "None":
    layer_map = {
        "Precipitation (Rain)": "precipitation_new",
        "Wind Speed": "wind_new",
        "Cloud Coverage": "clouds_new"
    }
    selected_layer = layer_map[hazard_choice]
    
    # Professional Tile URL
    weather_url = f"https://tile.openweathermap.org{selected_layer}/{{z}}/{{x}}/{{y}}.png?appid={WEATHER_KEY}"
    
    folium.TileLayer(
        tiles=weather_url,
        attr='OpenWeatherMap',
        name=hazard_choice,
        overlay=True,
        control=True,
        opacity=0.6 # Transparent so dots show through
    ).add_to(m)

# 5b. NASA Fire Dots
if fire_data is not None and not fire_data.empty:
    for _, row in fire_data.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=4,
            color='red',
            fill=True,
            fill_color='orange',
            popup=f"Brightness: {row['brightness']}K",
            tooltip="Thermal Anomaly"
        ).add_to(m)

# --- 6. DISPLAY ---
st_folium(m, width=1200, height=600)

if hazard_choice != "None":
    st.info(f"Analysis Mode: NASA Thermal Data fused with {hazard_choice} data.")
