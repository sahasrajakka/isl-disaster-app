# Project Sentinel
### Real-Time Multi-Hazard Nowcasting and Risk Correlation System

Project Sentinel is a **Geospatial Intelligence (GEOINT)** engine developed to automate the detection and risk assessment of wildfires across the Indian subcontinent. Moving beyond static data visualization, the system executes **Sensor Fusion**—the algorithmic correlation of thermal anomalies with atmospheric wind vectors—to identify high-probability spread zones. 

---

## Systemic Capabilities

*   **Thermal Hotspot Detection:** Near real-time data ingestion from the **NASA VIIRS (SNPP)** sensor via the MODAPS FIRMS API.
*   **Spatial Grid Generation:** Automated synthesis of a 2.5° atmospheric grid over India to retrieve high-resolution meteorological data.
*   **Spatial Correlation Engine:** Computational implementation of the **Haversine Formula** to determine spherical distances between non-synchronous datasets.
*   **Predictive Risk Modeling:** Dynamic identification of **"Critical Risk Zones"** where high-velocity wind vectors (>25km/h) intersect with active fire clusters within a 100km proximity.
*   **Multi-Layer Overlays:** Integration of the **RainViewer API** for infrared satellite and Doppler radar analysis.

---

## Development Stack

| Component | Technology |
| :--- | :--- |
| **Architecture** | Streamlit (Data Engineering Framework) |
| **Geospatial Visualization** | Folium and Leaflet.js |
| **Numerical Computation** | Pandas and NumPy |
| **Data Providers** | NASA FIRMS, Open-Meteo GFS, and RainViewer |
