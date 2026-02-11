import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
import numpy as np
from io import StringIO
from branca.element import Template, MacroElement
from datetime import datetime, timedelta

# -------------------- 1. SETTINGS --------------------

st.set_page_config(page_title="Project Sentinel", layout="wide")
st.title("🛰️ Project Sentinel: Geospatial Hazard Intelligence System")
st.subheader("Wind-Amplified Wildfire Risk Detection & Spatial Analysis")

NASA_KEY = "YOUR_NASA_API_KEY_HERE"  # <-- Replace with your key


# -------------------- 2. CORE FUNCTIONS --------------------

def haversine_distance(lat1, lon1, lat2, lon2):
    """Compute great-circle distance between two lat/lon points (km)."""
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def classify_risk(score):
    """Classify wildfire risk level based on computed score."""
    if score > 30:
        return "Extreme"
    elif score > 18:
        return "High"
    elif score > 8:
        return "Moderate"
    else:
        return "Low"


def compute_risk(wind_speed, distance, decay_constant=50):
    """
    Exponential decay model:
    Wind influence decreases with spatial separation.
    """
    return wind_speed * np.exp(-distance / decay_constant)


# -------------------- 3. DATA FETCHING --------------------

@st.cache_data(ttl=3600)
def fetch_fire_data(api_key):
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{api_key}/VIIRS_SNPP_NRT/IND/1"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return pd.read_csv(StringIO(res.text))
        return None
    except:
        return None


@st.cache_data(ttl=1800)
def fetch_wind_grid():
    lats_range = np.arange(8, 38, 2.5)
    lons_range = np.arange(68, 98, 2.5)

    grid_coords = [
        {"lat": round(la, 2), "lon": round(lo, 2)}
        for la in lats_range for lo in lons_range
    ]

    lat_str = ",".join([str(c["lat"]) for c in grid_coords])
    lon_str = ",".join([str(c["lon"]) for c in grid_coords])

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&current=wind_speed_10m"

    try:
        res = requests.get(url, timeout=10).json()
        data = res if isinstance(res, list) else [res]

        return [
            {
                "lat": d["latitude"],
                "lon": d["longitude"],
                "speed": d["current"]["wind_speed_10m"]
            }
            for d in data
        ]
    except:
        return []


# -------------------- 4. DATA PROCESSING --------------------

fire_df = fetch_fire_data(NASA_KEY)
wind_data = fetch_wind_grid()

risk_alerts = []

if fire_df is not None and wind_data:
    with st.spinner("Analyzing Wind-Amplified Hazard Zones..."):

        for _, fire in fire_df.iterrows():

            # Find closest wind grid cell (performance optimized)
            closest_wind = min(
                wind_data,
                key=lambda w: haversine_distance(
                    fire["latitude"], fire["longitude"],
                    w["lat"], w["lon"]
                )
            )

            distance = haversine_distance(
                fire["latitude"], fire["longitude"],
                closest_wind["lat"], closest_wind["lon"]
            )

            search_radius = 150  # km (long-range ember transport buffer)

            if distance < search_radius:
                risk_score = compute_risk(
                    closest_wind["speed"],
                    distance
                )

                risk_level = classify_risk(risk_score)

                if risk_level in ["High", "Extreme"]:
                    risk_alerts.append({
                        "lat": fire["latitude"],
                        "lon": fire["longitude"],
                        "wind_speed": closest_wind["speed"],
                        "distance_km": round(distance, 1),
                        "risk_score": round(risk_score, 2),
                        "risk_level": risk_level
                    })


# -------------------- 5. SIDEBAR --------------------

st.sidebar.header("System Status")

if fire_df is not None:
    st.sidebar.success(f"Satellite Active: {len(fire_df)} Hotspots")
    st.sidebar.metric("Detected Risk Zones", len(risk_alerts))
else:
    st.sidebar.error("Fire Data Unavailable")

hazard_overlay = st.sidebar.selectbox(
    "NASA GIBS Overlays",
    ["None", "Precipitation Rate", "TrueColor Cloud (MODIS)"]
)


# -------------------- 6. MAP ENGINE --------------------

m = folium.Map(
    location=[22.5937, 78.9629],
    zoom_start=5,
    tiles="cartodbpositron"
)

target_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

# Plot high-risk zones
for alert in risk_alerts:
    folium.CircleMarker(
        location=[alert["lat"], alert["lon"]],
        radius=9,
        color="darkred",
        fill=True,
        fill_opacity=0.85,
        popup=(
            f"{alert['risk_level']} Risk<br>"
            f"Wind: {alert['wind_speed']} km/h<br>"
            f"Score: {alert['risk_score']}"
        )
    ).add_to(m)

# Plot active fire hotspots
if fire_df is not None:
    for _, row in fire_df.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=3,
            color="orange",
            fill=True,
            opacity=0.4
        ).add_to(m)


# -------------------- 7. NASA GIBS OVERLAY --------------------

if hazard_overlay != "None":

    layer = (
        "MODIS_Terra_CorrectedReflectance_TrueColor"
        if "TrueColor" in hazard_overlay
        else "GPM_IMERG_Late_Precipitation_Rate"
    )

    ext = "jpg" if "TrueColor" in hazard_overlay else "png"

    nasa_url = (
        f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
        f"{layer}/default/{target_date}/"
        f"GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.{ext}"
    )

    folium.TileLayer(
        tiles=nasa_url,
        attr="NASA EOSDIS",
        name=f"{hazard_overlay} ({target_date})",
        overlay=True,
        opacity=0.55
    ).add_to(m)


# -------------------- 8. LEGEND --------------------

legend_html = """
{% macro html(this, kwargs) %}
<div style='position: fixed; bottom: 50px; left: 50px; width: 200px;
background-color: white; border:2px solid grey; z-index:9999;
font-size:14px; padding: 10px; border-radius: 6px; color: black;'>

<b>Map Legend</b><br>
<span style="color:darkred;">●</span> High / Extreme Risk<br>
<span style="color:orange;">●</span> Active Fire<br>
<hr style="margin: 5px 0;">
<small>Data: NASA FIRMS & GIBS</small>
</div>
{% endmacro %}
"""

macro = MacroElement()
macro._template = Template(legend_html)
m.get_root().add_child(macro)


# -------------------- 9. DISPLAY --------------------

st_folium(m, width=1400, height=700)

if risk_alerts:
    st.subheader("Detected High-Risk Zones")
    st.dataframe(pd.DataFrame(risk_alerts), use_container_width=True)
