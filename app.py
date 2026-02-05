import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
from io import StringIO

# --- 1. SETUP ---
st.set_page_config(page_title="Project Sentinel", layout="wide")

st.title("🛰️ Project Sentinel: AI-Powered GEOINT")
st.subheader("Real-Time Disaster Nowcasting System")

# --- 2. DATA LAYER (NASA API) ---
# Paste your key inside the quotes below
NASA_KEY = "992b32694a52d2b8e8f7d36bd3396e63" 

def fetch_nowcast_data():
    """Fetches real-time thermal anomalies for India from NASA VIIRS satellites"""
    # This URL targets India (IND) for the last 24 hours (1 day)
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv{NASA_KEY}/VIIRS_SNPP_NRT/IND/1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return pd.read_csv(StringIO(response.text))
    except Exception as e:
        st.error(f"Failed to fetch satellite data: {e}")
    return None

# --- 3. LOGIC & VISUALIZATION ---
fire_data = fetch_nowcast_data()

# Sidebar Stats
st.sidebar.title("System Status")
if fire_data is not None:
    st.sidebar.success(f"Satellite Connection: Active")
    st.sidebar.metric("Active Hotspots Detected", len(fire_data))
else:
    st.sidebar.error("Satellite Connection: Offline")

# Initialize the Map (Centered on India)
m = folium.Map(location=[20.5937, 78.9629], zoom_start=5, tiles="cartodbpositron")

# Plotting the Data
if fire_data is not None and not fire_data.empty:
    for _, row in fire_data.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5,
            color='red',
            fill=True,
            fill_color='red',
            popup=f"Brightness: {row['brightness']}K"
        ).add_to(m)

# Display Map in Streamlit
st_folium(m, width=1200, height=600)

st.info("Note: Map displays thermal anomalies detected within the last 24 hours.")

