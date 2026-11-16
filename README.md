# EDITH
Hackverse Hackthon Problem Statement solution
# 🚶‍♂️‍➡️ QAdapt AI — Smart Queue Prediction & Optimization System

## Problem Statement
Public-facing organizations (banks, hospitals, government offices) face unpredictable queues and overcrowding. LineInsight AI predicts queue buildup and recommends optimal resource allocation in real-time.

##  Key Features
- ** CCTV Camera Simulation** — Simulated computer vision feed with YOLO-style people detection
- ** ML Prediction Engine** — GradientBoosting + RandomForest models trained on 60 days of data
- ** Future Forecasting** — 2-hour queue growth trajectory with threshold alerts
- ** Smart Recommendations** — Dynamic counter routing, staff reallocation, fast-track triggers
- ** Crisis Sandbox** — Simulate lunch rush, server outages, staff shortages
- ** Live Dashboard** — Auto-refreshing dark-themed UI with gauges and heatmaps
- ** Export Reports** — One-click CSV download of analysis

##  Quick Start
```bash
pip install -r requirements.txt
streamlit run app.py
