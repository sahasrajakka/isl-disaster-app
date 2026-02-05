# isl-disaster-app
This platform utilizes Real-time Nowcasting and Satellite GIS integration to detect environmental hazards, using AI to synthesize hyper-local safety strategies for at-risk zones.


# 🛰️ Project Sentinel: AI-Powered GEOINT for Disaster Response
**A Geospatial Decision Support System (DSS) for Real-Time Hazard Monitoring**

## 📖 Project Overview
Project Sentinel is a cloud-native **Geospatial Intelligence (GEOINT)** pipeline designed to bridge the gap between raw satellite observations and actionable ground-level response. The system automates the ingestion of thermal anomaly data and leverages Generative AI to synthesize coordinate-specific emergency protocols.

## 🚀 Key Functionalities
- **Live Nowcasting:** Real-time ingestion and visualization of thermal anomalies and active fire hotspots using the **NASA FIRMS (LANCE) API**.
- **Intelligent Logic Engine:** Integration with **Google Gemini Pro** to analyze disaster proximity and generate localized evacuation strategies.
- **Interactive Decision Dashboard:** A high-performance interface built with **Streamlit** for real-time situational awareness and geospatial data manipulation.

## 🛠️ System Architecture
- **Data Layer:** Automated telemetry fetching from NASA VIIRS/MODIS satellite constellations.
- **Processing Layer:** Python-based logic for coordinate filtering and hazard proximity calculation.
- **Intelligence Layer:** Large Language Model (LLM) integration for context-aware disaster response generation.
- **Presentation Layer:** Interactive mapping using Folium and Streamlit-Folium.

## 💻 Tech Stack
- **Language:** Python
- **API Integration:** NASA LANCE APIs, Google Gemini API
- **Geospatial Tools:** Folium, Geopandas
- **Deployment:** Streamlit Cloud / GitHub Version Control

## 📂 Project Structure
- `app.py`: Core application logic and UI framework.
- `requirements.txt`: Python environment dependencies.
- `research/`: Technical documentation on GIS and disaster response workflows.

---
**Developer:** Sahasra Jakka
**Field:** Computer Science & Engineering  
**Focus:** Space-Tech | AI | Geospatial Data
