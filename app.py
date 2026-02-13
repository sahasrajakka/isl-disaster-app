import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
import numpy as np
from io import StringIO
from datetime import datetime, timedelta

# ======================================================
# 1. SETTINGS
# ======================================================

st.set_page_config(page_title="Project Sentinel", layout="wide")
st.title("🛰️ Project Sentinel: Wildfire Hazard Intelligence System")
st.subheader("Wind + Rain Adjusted Spread Modeling with Satellite Overlay")

NASA_KEY = "YOUR_NASA_KEY_HERE"  # Replace with real key


# ======================================================
# 2. GEOSPATIAL CORE FUNCTIONS
# ======================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1-a))


def compute_wind_effect(speed, distance, decay=50):
    return speed * np.exp(-distance / decay)


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
# 3. FETCH FIRE DATA
# ======================================================

@st.cache_data(ttl=3600)
def fetch_fire_data(api_key):
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{api_key}/VIIRS_SNPP_NRT/IND/1"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return pd.read_csv(StringIO(r.text))
    except:
        pass
    return None


# ======================================================
# 4. FETCH WIND DATA
# ======================================================

@st.cache_data(ttl=1800)
def fetch_wind_data():
    lats = np.arange(8, 38, 3)
    lons = np.arange(68, 98, 3)
    wind_results = []

    for lat in lats:
        for lon in lons:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}"
                f"&longitude={lon}"
                "&current=wind_speed_10m,wind_direction_10m"
            )
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = r.json()["current"]
                    wind_results.append({
                        "lat": lat,
                        "lon": lon,
                        "speed": data["wind_speed_10m"],
                        "direction": data["wind_direction_10m"]
                    })
            except:
                continue

    return wind_results


# ======================================================
# 5. FETCH PRECIPITATION (SUPPRESSION FACTOR)
# ======================================================

@st.cache_data(ttl=900)
def fetch_precipitation(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}"
        f"&longitude={lon}"
        "&current=precipitation"
    )
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()["current"]["precipitation"]
    except:
        pass
    return 0


# ======================================================
# 6. LOAD DATA
# ======================================================

fire_df = fetch_fire_data(NASA_KEY)
wind_data = fetch_wind_data()

risk_alerts = []


# ======================================================
# 7. RISK + SUPPRESSION + PROJECTION
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

            wind_effect = compute_wind_effect(
                closest_wind["speed"],
                distance
            )

            rainfall = fetch_precipitation(
                fire["latitude"],
                fire["longitude"]
            )

            rain_effect = rainfall * 6  # Suppression weight

            risk_score = wind_effect - rain_effect
            risk_score = max(risk_score, 0)

            risk_level = classify_risk(risk_score)

            if risk_level in ["High", "Extreme"]:

                spread_distance = min(30, closest_wind["speed"] * 0.7)

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
                    "rainfall_mm_hr": rainfall,
                    "wind_speed": closest_wind["speed"],
                    "direction": closest_wind["direction"],
                    "proj_lat": proj_lat,
                    "proj_lon": proj_lon
                })


# ======================================================
# 8. MAP SETUP
# ======================================================

m = folium.Map(
    location=[22.5937, 78.9629],
    zoom_start=6,
    tiles="cartodbpositron"
)

target_date = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")

# Plot risk + arrow projection
for alert in risk_alerts:

    folium.CircleMarker(
        location=[alert["lat"], alert["lon"]],
        radius=9,
        color="darkred",
        fill=True,
        fill_opacity=0.85
    ).add_to(m)

    # Direction arrow
    folium.PolyLine(
        locations=[
            [alert["lat"], alert["lon"]],
            [alert["proj_lat"], alert["proj_lon"]]
        ],
        color="purple",
        weight=3
    ).add_to(m)


# ======================================================
# 9. HIGH-RES CLOUD + PRECIP OVERLAY
# ======================================================

overlay = st.sidebar.selectbox(
    "Satellite Overlay",
    ["None", "TrueColor Cloud", "Precipitation Rate"]
)

if overlay == "TrueColor Cloud":

    layer = "MODIS_Terra_CorrectedReflectance_TrueColor"
    ext = "jpg"

    nasa_url = (
        f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
        f"{layer}/default/{target_date}/"
        f"GoogleMapsCompatible_Level12/{{z}}/{{y}}/{{x}}.{ext}"
    )

    folium.TileLayer(
        tiles=nasa_url,
        attr="NASA EOSDIS",
        overlay=True,
        opacity=1
    ).add_to(m)

elif overlay == "Precipitation Rate":

    layer = "GPM_IMERG_Late_Precipitation_Rate"
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

st_folium(m, width=1400, height=750)

if risk_alerts:
    st.subheader("High-Risk Zones with Rain Suppression Modeling")
    st.dataframe(pd.DataFrame(risk_alerts), use_container_width=True)
