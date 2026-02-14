# Project Sentinel  
### Wind-Amplified Wildfire Hazard Intelligence System

---

## Overview

Project Sentinel is a geospatial hazard intelligence prototype that analyzes wind-amplified wildfire risk using real-time satellite hotspot detection and meteorological wind data.

The system integrates NASA FIRMS wildfire data with wind speed and direction modeling to estimate forward fire spread potential and visualize high-risk zones interactively.

---

## Key Features

- NASA FIRMS VIIRS Near Real-Time Fire Hotspots
- Wind Speed & Direction Integration (Open-Meteo)
- Geodesic Distance Calculation (Haversine Formula)
- Exponential Distance-Decay Risk Model
- Forward Spread Projection Simulation
- Interactive GIS Visualization (Folium)
- Satellite Cloud Overlay (NASA GIBS WMTS)
- Precipitation Rate Overlay

---

## Methodology

1. Retrieve active wildfire hotspots from NASA FIRMS.
2. Sample regional wind field data using Open-Meteo API.
3. Compute geodesic distance between fire and wind grid points.
4. Apply exponential decay model to quantify wind amplification.
5. Classify risk into Moderate / High / Extreme tiers.
6. Project forward spread along prevailing wind bearing.
7. Render interactive visualization with satellite overlays.

---

## Data Sources

- NASA FIRMS (VIIRS NRT)
- NASA GIBS WMTS Satellite Imagery
- Open-Meteo Weather API

---

## Technologies Used

- Python
- Streamlit
- Folium
- NumPy
- Pandas
- REST APIs
