import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
import numpy as np
from io import StringIO
from datetime import datetime, timedelta

# ======================================================
# 1. APP SETTINGS
# ======================================================

st.set_page_config(page_title="Project Sentinel", layout="wide")
st.title("🛰️ Project Sentinel: Wildfire Hazard Intelligence System")
st.subheader("Wind-Amplified Risk Detection & Forward Spread Projection")

NASA_KEY = "YOUR_NASA_KEY_HERE"  # Replace with real key


# ======================================================
# 2. CORE GEOSPATIAL FUNCTIONS
# ======================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def compute_risk(wind_speed, distance, decay_constant=50):
    return wind_speed * np.exp(-distance / decay_constant)


def classify_risk(score):
    if score > 30:
        return "Extreme"
    elif score > 18:
        return "High"
    elif score > 8:
        return "Moderate"
    else:
        return "Low"


def project_point(lat, lon, distance_km, bearing_deg):
    R = 6371
    bearing = np.radians(bearing_deg)

    lat1 = np.radians(lat)
    lon1 = np.radians(lon)

    lat2 = np.arcsin(
        np.sin(lat1) * np.cos(distance_km / R) +
        np.cos(lat1) * np.sin(distance_km / R) * np.cos(bearing)
    )

    lon2 = lon1 + np.arctan2(
        np.sin(bearing) * np.sin(distance_km / R) * np.cos(lat1),
        np.cos(distance_km / R) - np.sin(lat1) * np.sin(lat2)
    )

    return np.degrees(lat2), np.degrees(lon2)


# ======================================================
# 3. FETCH NASA FIRE DATA
# ======================================================

@st.cache_data(ttl=3600)
def fetch_fire_data(api_key):
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{api_key}/VIIRS_SNPP_NRT/IND/1"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return pd.read_csv(StringIO(res.text))
    except:
        pass
    return None


# ======================================================
# 4. FETCH WIND DATA (Speed + Direction)
# ======================================================

@st.cache_data(ttl=1800)
def fetch_wind_grid():

    lats = np.arange(8, 38, 2.5)
    lons = np.arange(68, 98, 2.5)
    coords = [{"lat": la, "lon": lo} for la in lats for lo in lons]

    chunks = [coords[i:i + 72] for i in range(0, len(coords), 72)]
    wind_results = []

    for chunk in chunks:
        lat_str = ",".join(str(c["lat"]) for c in chunk)
        lon_str = ",".join(str(c["lon"]) for c in chunk)

        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat_str}"
            f"&longitude={lon_str}"
            "&current=wind_speed_10m,wind_direction_10m"
        )

        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue

            data = res.json()
            data = data if isinstance(data, list) else [data]

            for c, d in zip(chunk, data):
                wind_results.append({
                    "lat": c["lat"],
                    "lon": c["lon"],
                    "speed": d["current"]["wind_speed_10m"],
                    "direction": d["current"]["wind_direction_10m"]
                })

        except:
            continue

    return wind_results


# ======================================================
# 5. LOAD DATA
# ======================================================

fire_df = fetch_fire_data(NASA_KEY)
wind_data = fetch_wind_grid()

risk_alerts = []

# ======================================================
# 6. RISK + FORWARD SPREAD CALCULATION
# ======================================================

if fire_df is not None and wind_data:

    for _, fire in fire_df.iterrows():

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

        if distance < 150:

            risk_score = compute_risk(
                closest_wind["speed"],
                distance
            )

            risk_level = classify_risk(risk_score)

            if risk_level in ["High", "Extreme"]:

                spread_distance = min(25, closest_wind["speed"] * 0.6)

                proj_lat, proj_lon = project_point(
                    fire["latitude"],
                    fire["longitude"],
                    spread_distance,
                    closest_wind["direction"]
                )

                risk_alerts.append({
                    "lat": fire["latitude"],
                    "lon": fire["longitude"],
                    "risk_level": risk_level,
                    "risk_score": round(risk_score, 2),
                    "wind_speed": closest_wind["speed"],
                    "proj_lat": proj_lat,
                    "proj_lon": proj_lon
                })


# ======================================================
# 7. SIDEBAR
# ======================================================

st.sidebar.header("System Status")

if fire_df is not None:
    st.sidebar.success(f"Active Fires: {len(fire_df)}")
    st.sidebar.metric("High-Risk Zones", len(risk_alerts))
else:
    st.sidebar.error("Fire data unavailable")

overlay_option = st.sidebar.selectbox(
    "NASA Overlay",
    ["None", "TrueColor Cloud", "Precipitation Rate"]
)


# ======================================================
# 8. MAP INITIALIZATION
# ======================================================

m = folium.Map(
    location=[22.5937, 78.9629],
    zoom_start=5,
    tiles="cartodbpositron"
)

target_date = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")


# Plot Fire + Projection
for alert in risk_alerts:

    folium.CircleMarker(
        location=[alert["lat"], alert["lon"]],
        radius=9,
        color="darkred",
        fill=True,
        fill_opacity=0.85,
        popup=f"{alert['risk_level']} Risk | Wind {alert['wind_speed']} km/h"
    ).add_to(m)

    folium.CircleMarker(
        location=[alert["proj_lat"], alert["proj_lon"]],
        radius=6,
        color="purple",
        fill=True,
        fill_opacity=0.7,
        popup="Predicted Spread"
    ).add_to(m)


# Plot all fire hotspots
if fire_df is not None:
    for _, row in fire_df.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=3,
            color="orange",
            fill=True,
            opacity=0.4
        ).add_to(m)


# ======================================================
# 9. NASA OVERLAY (FIXED VERSION)
# ======================================================

if overlay_option != "None":

    if overlay_option == "TrueColor Cloud":
        layer = "MODIS_Terra_CorrectedReflectance_TrueColor"
        ext = "jpg"
    else:
        layer = "GPM_IMERG_Early_Precipitation_Rate"
        ext = "png"

    nasa_url = (
        f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
        f"{layer}/default/{target_date}/"
        f"GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.{ext}"
    )

    folium.TileLayer(
        tiles=nasa_url,
        attr="NASA EOSDIS",
        overlay=True,
        opacity=1
    ).add_to(m)


# ======================================================
# 10. DISPLAY
# ======================================================

st_folium(m, width=1400, height=700)

if risk_alerts:
    st.subheader("Detected High-Risk & Predicted Spread Zones")
    st.dataframe(pd.DataFrame(risk_alerts), use_container_width=True)
