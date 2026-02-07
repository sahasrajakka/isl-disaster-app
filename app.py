import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
from io import StringIO
from branca.element import Template, MacroElement
from folium.plugins import HeatMap

# --- 1. SETUP ---
st.set_page_config(page_title="Project Sentinel", layout="wide")
st.title("🛰️ Project Sentinel: AI-Powered GEOINT")
st.subheader("Real-Time Multi-Hazard Nowcasting System")

NASA_KEY = "992b32694a52d2b8e8f7d36bd3396e63" 

# --- 2. DATA LAYER ---
@st.cache_data(ttl=3600)
def fetch_nowcast_data(api_key):    
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{api_key}/VIIRS_SNPP_NRT/IND/1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return pd.read_csv(StringIO(response.text))
    except Exception as e:
        st.error(f"Satellite data error: {e}")
    return None

# --- 3. SIDEBAR & CONTROLS ---
st.sidebar.title("Command Centre")
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
m = folium.Map(location=[20.5937, 78.9629], zoom_start=5, tiles="cartodbpositron")

# 4a. RainViewer (Radar & Satellite)
if hazard_choice in ["Precipitation (Rain)", "Cloud Coverage"]:
    RVIEW_API_URL = "https://api.rainviewer.com/public/weather-maps.json"
    try:
        rview_data = requests.get(RVIEW_API_URL).json()
        host = rview_data['host']
        product = "radar" if hazard_choice == "Precipitation (Rain)" else "satellite"
        
        if product == "radar":
            latest_frame = rview_data['radar']['past'][-1]
            color_scheme = 2 
        else:
            latest_frame = rview_data['satellite']['infrared'][-1]
            color_scheme = 0
            
        tile_url = f"{host}{latest_frame['path']}/256/{{z}}/{{x}}/{{y}}/{color_scheme}/1_0.png"
        folium.TileLayer(
            tiles=tile_url, attr='RainViewer.com', name=hazard_choice,
            overlay=True, opacity=0.6, show=True
        ).add_to(m)
    except Exception as e:
        st.warning(f"RainViewer Error: {e}")

# 4b. NASA Fire Dots
if fire_data is not None and not fire_data.empty:
    for _, row in fire_data.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5, color='red', fill=True, fill_color='orange',
            fill_opacity=0.7, popup=f"Brightness: {row['brightness']}K"
        ).add_to(m)

# 4c. Open-Meteo Wind Heatmap
if hazard_choice == "Wind Speed":
    lats, lons = [10, 15, 20, 25, 30], [70, 75, 80, 85, 90]
    coords = [[lat, lon] for lat in lats for lon in lons]
    lat_str = ",".join([str(c[0]) for c in coords])
    lon_str = ",".join([str(c[1]) for c in coords])
    meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&current=wind_speed_10m"
    
    try:
        res = requests.get(meteo_url).json()
        heat_data = []
        # Open-Meteo returns a list if multiple coords are queried
        results = res if isinstance(res, list) else [res]
        for entry in results:
            heat_data.append([entry['latitude'], entry['longitude'], entry['current']['wind_speed_10m']])
        
        if heat_data:
            HeatMap(heat_data, radius=45, blur=25, min_opacity=0.4).add_to(m)
            st.sidebar.info(f"Max Wind: {max([d[2] for d in heat_data])} km/h")
    except Exception as e:
        st.sidebar.warning(f"Wind Error: {e}")

# --- 5. LEGEND & DISPLAY ---
legend_html = f"""
{{% macro html(this, kwargs) %}}
<div style="position: fixed; bottom: 50px; left: 50px; width: 180px; height: 110px; 
    background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
    padding: 10px; border-radius: 5px; color: black;">
    <b>Map Legend</b><br>
    <i style="background:red; width:12px; height:12px; display:inline-block; border-radius:50%"></i> Fire Hotspot<br>
    <i style="background:blue; width:12px; height:12px; display:inline-block; opacity:0.5"></i> {hazard_choice}<br>
    <hr style="margin: 5px 0;"><small>Source: NASA & RainViewer</small>
</div>
{{% endmacro %}}"""
legend = MacroElement(); legend._template = Template(legend_html)
m.get_root().add_child(legend)

st_folium(m, width=1200, height=600, key=f"map_{hazard_choice}")
