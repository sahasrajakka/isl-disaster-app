import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
import numpy as np
from io import StringIO
from branca.element import Template, MacroElement

# --- 1. SETTINGS & SECRETS ---
st.set_page_config(page_title="Project Sentinel", layout="wide")
st.title("🛰️ Project Sentinel: AI-Powered GEOINT")
st.subheader("Automated Hazard Correlation & Risk Analysis")

# In production, use st.secrets["NASA_KEY"]
NASA_KEY = "992b32694a52d2b8e8f7d36bd3396e63" 

# --- 2. CORE COMPUTATION ENGINE ---
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates KM distance between two points on Earth."""
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1-a))

@st.cache_data(ttl=3600)
def fetch_fire_data(api_key):    
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{api_key}/VIIRS_SNPP_NRT/IND/1"
    try:
        res = requests.get(url)
        return pd.read_csv(StringIO(res.text)) if res.status_code == 200 else None
    except: return None

@st.cache_data(ttl=1800)
def fetch_wind_grid():
    """Generates a spatial grid over India and fetches current wind speeds."""
    # Create a 2.5-degree grid (National Coverage)
    lats_range = np.arange(8, 38, 2.5)
    lons_range = np.arange(68, 98, 2.5)
    grid_coords = [{"lat": round(la, 2), "lon": round(lo, 2)} for la in lats_range for lo in lons_range]
    
    lat_str = ",".join([str(c['lat']) for c in grid_coords])
    lon_str = ",".join([str(c['lon']) for c in grid_coords])
    
    w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&current=wind_speed_10m"
    try:
        res = requests.get(w_url).json()
        # Open-Meteo returns a list if multiple coords are queried
        data = res if isinstance(res, list) else [res]
        return [{"lat": d['latitude'], "lon": d['longitude'], "speed": d['current']['wind_speed_10m']} for d in data]
    except: return []

# --- 3. LOGIC & DATA PROCESSING ---
fire_df = fetch_fire_data(NASA_KEY)
wind_data = fetch_wind_grid()

risk_alerts = []
if fire_df is not None and wind_data:
    with st.spinner("Analyzing Spatial Correlations..."):
        for _, fire in fire_df.iterrows():
            for wind in wind_data:
                dist = haversine_distance(fire['latitude'], fire['longitude'], wind['lat'], wind['lon'])
                # Threshold: Fire within 100km of wind gust > 25km/h
                if dist < 100 and wind['speed'] > 25:
                    risk_alerts.append({
                        'lat': fire['latitude'], 'lon': fire['longitude'],
                        'wind': wind['speed'], 'dist': round(dist, 1)
                    })
                    break

# --- 4. SIDEBAR COMMAND CENTRE ---
st.sidebar.header("System Status")
if fire_df is not None:
    st.sidebar.success(f"Satellite Active: {len(fire_df)} Hotspots")
    st.sidebar.metric("Critical Risk Zones", len(risk_alerts))

hazard_overlay = st.sidebar.selectbox("Active Overlay", ["None", "Rain Radar", "Cloud Coverage"])

# --- 5. MAPPING ENGINE ---
m = folium.Map(location=[22.5937, 78.9629], zoom_start=5, tiles="cartodbpositron")

# Risk Layer (The "Intelligence" Layer)
for alert in risk_alerts:
    folium.CircleMarker(
        location=[alert['lat'], alert['lon']],
        radius=10, color='darkred', fill=True, fill_opacity=0.8,
        popup=f"CRITICAL: Fire fanned by {alert['wind']}km/h winds within {alert['dist']}km"
    ).add_to(m)

# Standard Fire Layer
if fire_df is not None:
    for _, row in fire_df.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=3, color='orange', fill=True, opacity=0.4
        ).add_to(m)

# Weather Layers (RainViewer)
if hazard_overlay != "None":
    try:
        rv_meta = requests.get("https://api.rainviewer.com").json()
        path = rv_meta['radar']['past'][-1]['path'] if hazard_overlay == "Rain Radar" else rv_meta['satellite']['infrared'][-1]['path']
        tile_url = f"{rv_meta['host']}{path}/256/{{z}}/{{x}}/{{y}}/2/1_1.png"
        folium.TileLayer(tiles=tile_url, attr="RainViewer", name=hazard_overlay, overlay=True, opacity=0.5).add_to(m)
    except: st.error("Weather overlay timeout.")

# --- 6. LEGEND ---
legend_html = """
{% macro html(this, kwargs) %}
<div style="position: fixed; bottom: 50px; left: 50px; width: 160px; height: 100px; 
    background-color: white; border:2px solid grey; z-index:9999; font-size:12px;
    padding: 10px; border-radius: 5px;">
    <b>Legend</b><br>
    <i style="background:darkred; width:10px; height:10px; display:inline-block; border-radius:50%"></i> High Risk Zone<br>
    <i style="background:orange; width:10px; height:10px; display:inline-block; border-radius:50%"></i> Active Fire<br>
    <small>Spatial Step: 2.5° Grid</small>
</div>
{% endmacro %}"""
legend = MacroElement(); legend._template = Template(legend_html)
m.get_root().add_child(legend)

# Display
st_folium(m, width=1400, height=700, returned_objects=[])

# --- 7. DATA TABLE ---
if risk_alerts:
    st.subheader("Critical Warning Log")
    st.dataframe(pd.DataFrame(risk_alerts), use_container_width=True)
