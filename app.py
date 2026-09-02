import streamlit as st  # type: ignore[reportMissingImports]
import pandas as pd  # type: ignore[reportMissingModuleSource]
import numpy as np  # type: ignore[reportMissingImports]
import plotly.express as px  # type: ignore[reportMissingImports]
import plotly.graph_objects as go  # type: ignore[reportMissingImports]
from datetime import datetime
import time
import sys
import os
import json
import hashlib
import socket
import urllib.parse

# --- PATH FIX ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

# --- SAFE IMPORTS ---
try:
    import cv2  # type: ignore[reportMissingImports]
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from detection.yolo_detector import PersonDetector
    detector = PersonDetector() if HAS_CV2 else None
except Exception as e:
    detector = None
    _detector_error = str(e)

from models.queue_predictor import QueuePredictor
from engine.recommendation_engine import RecommendationEngine
from engine.chatbot import QueueChatBot

# --- INITIALIZE CORE OBJECTS ---
predictor = QueuePredictor()
engine = RecommendationEngine()
chatbot = QueueChatBot()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="QAdapt | Queue Intelligence & Resource Optimization",
    page_icon="🚶‍♂️‍➡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════
#  STATE SYNCHRONIZATION FOR QR SCANNER VIEWS
# ═══════════════════════════════════════════════════════════
STATUS_FILE_PATH = os.path.join(ROOT_DIR, "data", "live_status.json")
TOKEN_FILE_PATH = os.path.join(ROOT_DIR, "data", "tokens.json")

def save_live_status_to_disk(facility, counter_data, result):
    try:
        os.makedirs(os.path.dirname(STATUS_FILE_PATH), exist_ok=True)
        with open(STATUS_FILE_PATH, "w") as f:
            json.dump({
                "facility": facility,
                "counter_data": counter_data,
                "result": result,
                "timestamp": datetime.now().strftime("%I:%M:%S %p")
            }, f, indent=2)
    except Exception:
        pass

def load_live_status_from_disk():
    if os.path.exists(STATUS_FILE_PATH):
        try:
            with open(STATUS_FILE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

# ═══════════════════════════════════════════════════════════
#  TOKEN GENERATION ENGINE (Persistent Disk-Based)
# ═══════════════════════════════════════════════════════════
def load_tokens():
    if os.path.exists(TOKEN_FILE_PATH):
        try:
            with open(TOKEN_FILE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_number": 0, "tokens": [], "date": datetime.now().strftime("%Y-%m-%d")}

def save_tokens(token_data):
    os.makedirs(os.path.dirname(TOKEN_FILE_PATH), exist_ok=True)
    with open(TOKEN_FILE_PATH, "w") as f:
        json.dump(token_data, f, indent=2)

def generate_new_token(facility, counter_data, result):
    token_data = load_tokens()
    today = datetime.now().strftime("%Y-%m-%d")
    if token_data.get("date") != today:
        token_data = {"last_number": 0, "tokens": [], "date": today}
    token_data["last_number"] += 1
    token_num = token_data["last_number"]
    token_id = f"TKN-{token_num:04d}"
    best_counter = 1
    min_people = float('inf')
    for c in counter_data:
        if c.get('people', 999) < min_people:
            min_people = c.get('people', 999)
            best_counter = c.get('counter_id', 1)
    position_in_queue = min_people + 1
    est_wait = max(2, int(position_in_queue * 3.5))
    new_token = {
        "token_id": token_id,
        "token_number": token_num,
        "facility": facility,
        "assigned_counter": best_counter,
        "position_in_queue": position_in_queue,
        "estimated_wait_min": est_wait,
        "status": "WAITING",
        "generated_at": datetime.now().strftime("%I:%M:%S %p"),
        "date": today
    }
    token_data["tokens"].append(new_token)
    save_tokens(token_data)
    return new_token

def get_todays_tokens():
    token_data = load_tokens()
    today = datetime.now().strftime("%Y-%m-%d")
    if token_data.get("date") != today:
        return []
    return token_data.get("tokens", [])

# ═══════════════════════════════════════════════════════════
#  COMPREHENSIVE DARK THEME & CUSTOM AUTH CSS — ENHANCED
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    .stApp {
        background: 
            radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.15) 0%, transparent 45%),
            radial-gradient(circle at 85% 80%, rgba(6, 182, 212, 0.12) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba(167, 139, 250, 0.08) 0%, transparent 60%),
            linear-gradient(135deg, #02040a 0%, #070b19 40%, #0e1227 80%, #02040a 100%);
        background-attachment: fixed;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image: radial-gradient(rgba(255, 255, 255, 0.02) 1.2px, transparent 1.2px);
        background-size: 24px 24px;
        pointer-events: none;
        z-index: 1;
    }
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
        position: relative;
        z-index: 2;
    }
    h1, h2, h3, h4, h5, h6 { 
        font-family: 'Space Grotesk', sans-serif !important;
        color: #f8fafc !important; 
        font-weight: 700 !important;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }
    p, span, label, li { color: #94a3b8 !important; }
    .stCaption, .st-emotion-cache-1q7q0r2 { color: #64748b !important; }
    .aurora-orb-1 {
        position: fixed; top: -100px; right: 20%;
        width: 500px; height: 500px;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, transparent 70%);
        border-radius: 50%; filter: blur(40px);
        animation: floatNebula1 25s ease-in-out infinite;
        pointer-events: none; z-index: 0;
    }
    .aurora-orb-2 {
        position: fixed; bottom: -150px; left: 10%;
        width: 600px; height: 600px;
        background: radial-gradient(circle, rgba(6, 182, 212, 0.18) 0%, transparent 70%);
        border-radius: 50%; filter: blur(50px);
        animation: floatNebula2 30s ease-in-out infinite;
        pointer-events: none; z-index: 0;
    }
    @keyframes floatNebula1 {
        0%, 100% { transform: translateY(0px) scale(1); }
        50% { transform: translateY(80px) scale(1.15) translateX(30px); }
    }
    @keyframes floatNebula2 {
        0%, 100% { transform: translateY(0px) scale(1); }
        50% { transform: translateY(-100px) scale(0.9) translateX(-40px); }
    }
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .shimmer-text {
        background: linear-gradient(270deg, #818cf8, #22d3ee, #c084fc, #34d399, #818cf8);
        background-size: 300% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: gradientShift 5s ease infinite;
    }
    @keyframes borderGlow {
        0%, 100% { border-color: rgba(99, 102, 241, 0.25); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 10px rgba(99, 102, 241, 0.05); }
        50% { border-color: rgba(6, 182, 212, 0.4); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 20px rgba(6, 182, 212, 0.15); }
    }
    .glass-panel {
        background: rgba(13, 19, 38, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 20px; padding: 26px;
        backdrop-filter: blur(24px) saturate(120%);
        box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.6), inset 0 1px 1px rgba(255, 255, 255, 0.05);
        position: relative; overflow: hidden;
    }
    .glass-panel::after {
        content: ''; position: absolute; top: 0; left: -100%;
        width: 50%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.04), transparent);
        animation: shimmerSweep 9s ease-in-out infinite; pointer-events: none;
    }
    @keyframes shimmerSweep { 0% { left: -100%; } 100% { left: 200%; } }
    @keyframes slideInUp { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes slideInLeft { from { opacity: 0; transform: translateX(-35px); } to { opacity: 1; transform: translateX(0); } }
    @keyframes slideInRight { from { opacity: 0; transform: translateX(35px); } to { opacity: 1; transform: translateX(0); } }
    @keyframes fadeInScale { from { opacity: 0; transform: scale(0.94); } to { opacity: 1; transform: scale(1); } }
    .animate-slide-up { animation: slideInUp 0.65s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
    .animate-fade-scale { animation: fadeInScale 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
    .corner-widget {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 16px; padding: 12px 20px;
        backdrop-filter: blur(20px);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        display: inline-block; text-align: right;
        animation: borderGlow 7s ease-in-out infinite, fadeInScale 0.8s ease forwards;
        position: relative; overflow: hidden;
    }
    .login-container-premium {
        width: 100%; max-width: 460px;
        background: rgba(13, 20, 41, 0.5);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 24px; padding: 35px;
        backdrop-filter: blur(28px);
        box-shadow: 0 25px 60px -10px rgba(0, 0, 0, 0.7), 0 0 30px rgba(99, 102, 241, 0.1), inset 0 1px 1px rgba(255, 255, 255, 0.05);
        text-align: center; margin: 0 auto;
        animation: fadeInScale 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards, borderGlow 8s ease-in-out infinite;
        position: relative; overflow: hidden;
    }
    .login-container-premium::before {
        content: ''; position: absolute; top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: conic-gradient(from 0deg, transparent 0%, rgba(99, 102, 241, 0.05) 25%, transparent 50%, rgba(6, 182, 212, 0.05) 75%, transparent 100%);
        animation: rotateConic 18s linear infinite; pointer-events: none;
    }
    @keyframes rotateConic { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .auth-glowing-glow {
        width: 64px; height: 64px;
        background: linear-gradient(135deg, #6366f1, #06b6d4);
        border-radius: 18px; margin: 0 auto 15px auto;
        display: flex; justify-content: center; align-items: center;
        font-size: 1.8rem;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
        animation: breatheNeon 3s ease-in-out infinite;
    }
    @keyframes breatheNeon {
        0%, 100% { box-shadow: 0 0 5px rgba(99, 102, 241, 0.3), 0 0 20px rgba(99, 102, 241, 0.15); }
        50% { box-shadow: 0 0 12px rgba(99, 102, 241, 0.6), 0 0 35px rgba(99, 102, 241, 0.3); }
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020510 0%, #060b1e 50%, #0d0c2b 100%) !important;
        border-right: 1px solid rgba(99, 102, 241, 0.15) !important;
        position: relative;
    }
    [data-testid="stMetric"] {
        background: rgba(18, 25, 51, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 18px !important; padding: 20px !important;
        backdrop-filter: blur(16px) !important;
        transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
        position: relative; overflow: hidden;
    }
    [data-testid="stMetric"]:hover {
        border-color: rgba(99, 102, 241, 0.35) !important;
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(99, 102, 241, 0.08) !important;
        transform: translateY(-4px) scale(1.02) !important;
    }
    [data-testid="stMetricValue"] { color: #f8fafc !important; font-size: 2.1rem !important; font-weight: 800 !important;}
    [data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.8rem !important; text-transform: uppercase; letter-spacing: 0.5px; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.02) !important;
        border-radius: 10px 10px 0 0 !important; padding: 12px 24px !important;
        color: #94a3b8 !important; border: 1px solid transparent !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(99, 102, 241, 0.08) !important; color: #c7d2fe !important; transform: translateY(-2px);
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99, 102, 241, 0.15) !important;
        border-bottom: 3px solid #818cf8 !important; color: #e0e7ff !important; font-weight: 700 !important;
    }
    .stButton > button {
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        background: rgba(255, 255, 255, 0.03) !important;
        color: #cbd5e1 !important; font-weight: 600 !important;
        transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important; padding: 10px 20px !important;
    }
    .stButton > button:hover {
        border-color: rgba(99, 102, 241, 0.4) !important;
        background: rgba(99, 102, 241, 0.12) !important; color: #e0e7ff !important;
        transform: translateY(-2px) !important; box-shadow: 0 8px 25px rgba(99, 102, 241, 0.18) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5, #6366f1, #06b6d4) !important;
        border: none !important; color: white !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4) !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.6) !important;
        transform: translateY(-3px) scale(1.02) !important;
    }
    .alert-critical {
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.14), rgba(239, 68, 68, 0.02));
        border-left: 4px solid #ef4444; padding: 14px 18px; border-radius: 0 12px 12px 0;
        margin: 10px 0; color: #fca5a5; animation: slideInLeft 0.5s ease forwards;
    }
    .alert-warning {
        background: linear-gradient(90deg, rgba(245, 158, 11, 0.14), rgba(245, 158, 11, 0.02));
        border-left: 4px solid #f59e0b; padding: 14px 18px; border-radius: 0 12px 12px 0;
        margin: 10px 0; color: #fcd34d; animation: slideInLeft 0.5s ease forwards;
    }
    .alert-ok {
        background: linear-gradient(90deg, rgba(16, 185, 129, 0.14), rgba(16, 185, 129, 0.02));
        border-left: 4px solid #10b981; padding: 14px 18px; border-radius: 0 12px 12px 0;
        margin: 10px 0; color: #6ee7b7; animation: slideInLeft 0.5s ease forwards;
    }
    .badge { padding: 4px 12px; border-radius: 20px; font-size: 0.72em; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; }
    .badge-normal   { background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.2); }
    .badge-moderate { background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); }
    .badge-high     { background: rgba(249, 115, 22, 0.12); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.2); }
    .badge-critical { background: rgba(239, 68, 68, 0.12);  color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); }
    .counter-card {
        background: rgba(15, 22, 47, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 18px; padding: 22px;
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        height: 100%; position: relative; overflow: hidden;
    }
    .counter-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #6366f1, #06b6d4, #a78bfa);
        opacity: 0; transition: opacity 0.3s ease;
    }
    .counter-card:hover::before { opacity: 1; }
    .counter-card:hover {
        border-color: rgba(99, 102, 241, 0.3);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(99, 102, 241, 0.1);
        transform: translateY(-6px) scale(1.02);
    }
    .camera-box {
        background: rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px; padding: 22px; text-align: center;
    }
    .camera-box .rec { color: #ef4444; font-weight: bold; animation: blink 1.2s infinite; }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }
    @keyframes pulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
        50% { opacity: 0.6; box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
    }
    .live-dot {
        width: 10px; height: 10px; background: #10b981;
        border-radius: 50%; display: inline-block;
        animation: pulse 2.2s infinite; margin-right: 8px;
        vertical-align: middle; box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
    }
    .stTextInput input, .stNumberInput input {
        border-radius: 12px !important;
        background-color: rgba(10, 15, 33, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important; color: #f1f5f9 !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #6366f1 !important; box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25) !important;
    }
    .customer-info-box {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(6, 182, 212, 0.06) 100%);
        border: 1px solid rgba(99, 102, 241, 0.22);
        border-radius: 16px; padding: 20px; margin-bottom: 20px;
        position: relative; overflow: hidden;
    }
    .qr-container {
        text-align: center; background: rgba(10, 16, 32, 0.7);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 16px; padding: 15px; margin-top: 15px;
    }
    .token-receipt {
        background: linear-gradient(145deg, rgba(99, 102, 241, 0.18) 0%, rgba(6, 182, 212, 0.08) 100%);
        border: 2px solid rgba(99, 102, 241, 0.35);
        border-radius: 20px; padding: 28px; margin: 20px 0; text-align: center;
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        position: relative;
    }
    .token-receipt::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
        background: linear-gradient(90deg, #6366f1, #06b6d4, #a78bfa, #6366f1);
        background-size: 300% 100%; animation: gradientShift 3s ease infinite;
    }
    .token-number {
        font-size: 3.2rem; font-weight: 900; letter-spacing: 4px;
        background: linear-gradient(270deg, #818cf8, #06b6d4, #c084fc, #34d399, #818cf8);
        background-size: 300% auto; -webkit-background-clip: text;
        -webkit-text-fill-color: transparent; animation: gradientShift 4s ease infinite;
        margin: 12px 0; line-height: 1;
    }
    .token-detail-row {
        display: flex; justify-content: space-between;
        padding: 8px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .token-detail-row:last-child { border-bottom: none; }
    .token-label { color: #64748b; font-size: 0.82rem; text-transform: uppercase; }
    .token-value { color: #e2e8f0; font-weight: 700; font-size: 0.95rem; }
    .prediction-callout {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(6, 182, 212, 0.04));
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 14px; padding: 16px 20px; color: #c7d2fe; position: relative;
    }
    .prediction-callout::before {
        content: ''; position: absolute; top: 0; left: 0;
        width: 3px; height: 100%;
        background: linear-gradient(180deg, #6366f1, #06b6d4);
    }
    .impact-before {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.02));
        border: 1px solid rgba(239, 68, 68, 0.2);
        border-radius: 16px; padding: 24px; text-align: center;
    }
    .impact-after {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(16, 185, 129, 0.02));
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 16px; padding: 24px; text-align: center;
    }
    .stChatMessage { border-radius: 12px !important; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(10, 15, 30, 0.5); }
    ::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #6366f1, #06b6d4); border-radius: 10px; }
    .stSelectbox > div > div {
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        background: rgba(10, 15, 30, 0.6) !important;
    }
    .stDownloadButton > button {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(6, 182, 212, 0.1)) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important; color: #34d399 !important;
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.25), rgba(6, 182, 212, 0.15)) !important;
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.15) !important;
    }
    .particle-field {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; z-index: 0; overflow: hidden;
    }
    .particle {
        position: absolute; width: 3px; height: 3px;
        background: rgba(99, 102, 241, 0.3); border-radius: 50%;
        animation: particleFloat 15s ease-in-out infinite;
    }
    .particle:nth-child(1) { top: 12%; left: 15%; animation-delay: 0s; animation-duration: 22s; }
    .particle:nth-child(2) { top: 35%; left: 78%; animation-delay: 2s; animation-duration: 18s; background: rgba(6, 182, 212, 0.35); }
    .particle:nth-child(3) { top: 65%; left: 33%; animation-delay: 4s; animation-duration: 25s; }
    .particle:nth-child(4) { top: 82%; left: 85%; animation-delay: 1s; animation-duration: 20s; background: rgba(167, 139, 250, 0.25); }
    .particle:nth-child(5) { top: 22%; left: 88%; animation-delay: 3s; animation-duration: 28s; }
    .particle:nth-child(6) { top: 54%; left: 12%; animation-delay: 5s; animation-duration: 16s; background: rgba(6, 182, 212, 0.2); }

    /* ★ NEW: LOGIN FACILITY SELECTOR STYLING */
    .login-facility-selector {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(6, 182, 212, 0.06) 100%);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 14px;
        padding: 16px 18px;
        margin: 12px 0 18px 0;
        text-align: left;
        position: relative;
    }
    .login-facility-selector::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #6366f1, #06b6d4, #a78bfa);
        border-radius: 14px 14px 0 0;
    }
    .facility-badge-login {
        display: inline-block;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(6, 182, 212, 0.15));
        border: 1px solid rgba(99, 102, 241, 0.35);
        border-radius: 10px;
        padding: 8px 16px;
        color: #c7d2fe;
        font-weight: 700;
        font-size: 0.9rem;
        margin-top: 6px;
    }

    /* ★ NEW: GUEST RESTRICTION POPUP MODAL */
    .guest-popup-overlay {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(251, 146, 60, 0.08) 100%);
        border: 2px solid rgba(239, 68, 68, 0.5);
        border-radius: 20px;
        padding: 30px;
        margin: 25px 0;
        text-align: center;
        box-shadow: 0 20px 60px rgba(239, 68, 68, 0.25), 0 0 40px rgba(239, 68, 68, 0.15);
        animation: fadeInScale 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards, shakeAlert 0.6s ease;
        position: relative;
        overflow: hidden;
    }
    .guest-popup-overlay::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        background: linear-gradient(90deg, #ef4444, #f97316, #ef4444);
        background-size: 200% 100%;
        animation: gradientShift 2s ease infinite;
    }
    @keyframes shakeAlert {
        0%, 100% { transform: translateX(0); }
        20%, 60% { transform: translateX(-8px); }
        40%, 80% { transform: translateX(8px); }
    }
    .guest-popup-icon {
        font-size: 3.5rem;
        margin-bottom: 10px;
        animation: breatheNeon 2s ease-in-out infinite;
    }
    .guest-popup-title {
        color: #fca5a5 !important;
        font-size: 1.6rem;
        font-weight: 800;
        margin-bottom: 8px;
        text-shadow: 0 2px 10px rgba(239, 68, 68, 0.3);
    }
    .guest-popup-message {
        color: #fecaca !important;
        font-size: 1rem;
        line-height: 1.6;
        margin-bottom: 15px;
    }
    .guest-popup-hint {
        background: rgba(0, 0, 0, 0.3);
        border-radius: 10px;
        padding: 12px 16px;
        color: #fcd34d !important;
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 10px;
        border-left: 3px solid #fbbf24;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  NEON NEBULAS & FLOATING GLOW PARTICLES BACKDROP
# ═══════════════════════════════════════════════════════════
st.markdown("""
<div class="aurora-orb-1"></div>
<div class="aurora-orb-2"></div>
<div class="particle-field">
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
    <div class="particle"></div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  PERSISTENT SESSION MANAGEMENT (REMEMBER ME FEATURE)
# ═══════════════════════════════════════════════════════════
SESSION_FILE_PATH = os.path.join(ROOT_DIR, "data", "active_session.json")

def save_active_session(user_info, remember_me, facility="Bank Branch"):
    os.makedirs(os.path.dirname(SESSION_FILE_PATH), exist_ok=True)
    with open(SESSION_FILE_PATH, "w") as f:
        json.dump({
            "authenticated": True,
            "user_info": user_info,
            "remember_me": remember_me,
            "facility": facility,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=2)

def load_active_session():
    if os.path.exists(SESSION_FILE_PATH):
        try:
            with open(SESSION_FILE_PATH, "r") as f:
                data = json.load(f)
                if data.get("remember_me", False):
                    return data
        except Exception:
            pass
    return None

def clear_active_session():
    if os.path.exists(SESSION_FILE_PATH):
        try:
            os.remove(SESSION_FILE_PATH)
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════
#  SESSION STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════
cached_session = load_active_session()

if cached_session:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = cached_session.get("authenticated", True)
    if "user_info" not in st.session_state:
        st.session_state.user_info = cached_session.get("user_info", None)
    if "remember_me" not in st.session_state:
        st.session_state.remember_me = cached_session.get("remember_me", True)
    if "selected_facility" not in st.session_state:
        st.session_state.selected_facility = cached_session.get("facility", "Bank Branch")
else:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    if "remember_me" not in st.session_state:
        st.session_state.remember_me = False
    if "selected_facility" not in st.session_state:
        st.session_state.selected_facility = "Bank Branch"

if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

# ═══════════════════════════════════════════════════════════
#  MOBILE SCANNER STANDALONE Bypassed View
# ═══════════════════════════════════════════════════════════
if st.query_params.get("share") == "true":
    loaded_data = load_live_status_from_disk()
    st.markdown("""
        <div style="text-align:center; padding: 10px 0;" class="animate-slide-up">
            <h1 style="margin:0; font-size:2.2rem;" class="shimmer-text">🚶‍♂️‍➡️ QAdapt Live Status</h1>
            <p style="color:#64748b; font-size:0.9rem; letter-spacing: 1px;">INSTANT SCANNER PORTAL</p>
        </div>
    """, unsafe_allow_html=True)
    if loaded_data:
        fac_name = loaded_data.get("facility", "Selected Facility")
        counters = loaded_data.get("counter_data", [])
        res = loaded_data.get("result", {})
        ts = loaded_data.get("timestamp", "Now")
        total_p = res.get('total_people', 0)
        max_comfortable_capacity = len(counters) * 12
        space_percent = min(100, int((total_p / max_comfortable_capacity) * 100)) if max_comfortable_capacity > 0 else 0
        space_status = "Comfortable Space Available" if space_percent < 50 else ("Moderately Crowded" if space_percent < 85 else "Extremely Crowded")
        space_color = "#10b981" if space_percent < 50 else ("#f59e0b" if space_percent < 85 else "#ef4444")
        st.markdown(f"""
        <div class="customer-info-box" style="border-left: 5px solid #6366f1;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0; color:#f1f5f9;">🏢 {fac_name}</h3>
                <span style="color:#64748b; font-size:0.75rem;">⌚ Last Updated: {ts}</span>
            </div>
            <div style="display: flex; gap: 40px; margin-top: 15px; flex-wrap: wrap;">
                <div>
                    <span style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">People Waiting</span>
                    <div style="font-size:2.3rem; font-weight:800; color:#38bdf8; line-height:1.2;">{total_p} People</div>
                </div>
                <div>
                    <span style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Avg Service Wait</span>
                    <div style="font-size:2.3rem; font-weight:800; color:#34d399; line-height:1.2;">~{res.get('average_wait_time', 0)} Mins</div>
                </div>
                <div>
                    <span style="color:#64748b; font-size:0.8rem; text-transform:uppercase;">Space Occupancy</span>
                    <div style="font-size:1.3rem; font-weight:700; color:{space_color}; margin-top:5px;">{space_status} ({space_percent}%)</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.success(f"📌 **Easiest Fast-track:** Route to **Counter {res.get('best_counter_for_new_customer', 1)}** for the shortest waiting time.")
        st.markdown("#### 📱 Counter-by-Counter Live Feeds")
        cols = st.columns(min(len(counters), 4))
        for i, c in enumerate(counters):
            with cols[i % 4]:
                c_people = c.get('people', 0)
                c_wait = c.get('wait_time', 0)
                c_status = "NORMAL" if c_people <= 6 else ("MODERATE" if c_people <= 10 else "CRITICAL")
                st.markdown(f"""
                <div class="counter-card" style="animation-delay: {i * 0.1}s;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#e2e8f0; font-size:0.85rem;">Counter {c.get('counter_id')}</span>
                        <span class="badge {'badge-normal' if c_status == 'NORMAL' else ('badge-moderate' if c_status == 'MODERATE' else 'badge-critical')}">{c_status}</span>
                    </div>
                    <div style="font-size:1.8rem; font-weight:800; margin:10px 0; color:#f1f5f9;">{c_people} <span style="font-size:0.9rem; color:#64748b; font-weight:normal;">ppl</span></div>
                    <div style="display:flex; justify-content:space-between; font-size:0.78rem;">
                        <span style="color:#64748b;">Est. Wait Time:</span>
                        <span style="font-weight:600; color:#e2e8f0;">{c_wait} mins</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("""
        <div style="text-align:center; margin: 10px 0;" class="animate-slide-up">
            <h3 style="margin:0; color:#c7d2fe;">🎫 Reserve Your Spot via Token</h3>
            <p style="color:#64748b; font-size:0.85rem;">Can't stand around? Click below to generate an official digital ticket number.</p>
        </div>
        """, unsafe_allow_html=True)

        # Initialize session states for scanner
        if "scanner_token" not in st.session_state:
            st.session_state.scanner_token = None
        if "show_guest_popup" not in st.session_state:
            st.session_state.show_guest_popup = False

        # Determine user status
        is_authenticated = st.session_state.get("authenticated", False)
        current_user = st.session_state.get("user_info", {}) or {}
        is_guest = current_user.get("email") == "guest@qadapt.ai" or current_user.get("name") == "Guest Customer"

        # Token generate button - handles guest restriction
        if st.button("🎫 Generate My Digital Token", use_container_width=True, type="primary"):
            if not is_authenticated or is_guest:
                # Guest user or unauthenticated - show popup
                st.session_state.show_guest_popup = True
                st.session_state.scanner_token = None
            else:
                # Logged-in non-guest user - generate token
                new_token = generate_new_token(fac_name, counters, res)
                st.session_state.scanner_token = new_token
                st.session_state.show_guest_popup = False
            st.rerun()

        # Show restriction popup for guest users
        if st.session_state.show_guest_popup:
            st.markdown("""
            <div class="guest-popup-overlay">
                <div class="guest-popup-icon">🔒</div>
                <div class="guest-popup-title">Login Required to Generate Token</div>
                <div class="guest-popup-message">
                    Sorry! Guest users are not permitted to generate digital tokens.<br>
                    Please <b>login with a registered account</b> to reserve your spot in the queue.
                </div>
                <div class="guest-popup-hint">
                    💡 Register a free customer account to unlock token generation, priority routing, and personalized queue tracking!
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            pop_col1, pop_col2 = st.columns(2)
            with pop_col1:
                if st.button("🔐 Go to Login Page", use_container_width=True, type="primary"):
                    st.session_state.authenticated = False
                    st.session_state.user_info = None
                    st.session_state.show_guest_popup = False
                    clear_active_session()
                    st.query_params.clear()
                    st.rerun()
            with pop_col2:
                if st.button("❌ Dismiss This Alert", use_container_width=True):
                    st.session_state.show_guest_popup = False
                    st.rerun()

        # Display token if generated (only for non-guest logged-in users)
        if st.session_state.scanner_token and not st.session_state.show_guest_popup:
            tkn = st.session_state.scanner_token
            st.markdown(f"""
            <div class="token-receipt">
                <div style="color:#64748b; font-size:0.8rem; text-transform:uppercase; letter-spacing:2px; margin-bottom:5px;">🏢 {tkn['facility']}</div>
                <div style="color:#94a3b8; font-size:0.75rem; letter-spacing:1.5px;">OFFICIAL ENTRY RECEIPT</div>
                <div class="token-number">{tkn['token_id']}</div>
                <div style="color:#34d399; font-size:0.85rem; font-weight:600; margin-bottom:18px;">✅ Position Secured Successfully</div>
                <div style="background:rgba(0,0,0,0.25); border-radius:12px; padding:16px; text-align:left;">
                    <div class="token-detail-row"><span class="token-label">📍 Target Station</span><span class="token-value">Counter {tkn['assigned_counter']}</span></div>
                    <div class="token-detail-row"><span class="token-label">👥 Clients Ahead Of You</span><span class="token-value">{tkn['position_in_queue'] - 1} People</span></div>
                    <div class="token-detail-row"><span class="token-label">⏱️ Expected Wait Time</span><span class="token-value">~{tkn['estimated_wait_min']} minutes</span></div>
                    <div class="token-detail-row"><span class="token-label">🕐 Timestamp Issued</span><span class="token-value">{tkn['generated_at']}</span></div>
                    <div class="token-detail-row"><span class="token-label">📋 Booking Status</span><span class="token-value" style="color:#fbbf24;">⏳ WAITING IN LINE</span></div>
                </div>
                <div style="margin-top:15px; color:#64748b; font-size:0.75rem;">🔔 An administrator will announce your token ID when your station is ready.</div>
            </div>
            """, unsafe_allow_html=True)
            st.info(f"📢 **Hold onto this screen:** Your assigned counter is **Counter {tkn['assigned_counter']}**. Proceed there when called!")
    else:
        st.warning("⚠️ Waiting for active station queue updates... Please refresh after some time.")
    if st.button("🔄 Refresh Live Status", use_container_width=True, type="primary"):
        st.rerun()
    st.markdown("<p style='text-align:center; color:#475569; font-size:0.8rem; margin-top:40px;'>QAdapt Scanner Engine · Dynamic Offline Syncing</p>", unsafe_allow_html=True)
    st.stop()

# ═══════════════════════════════════════════════════════════
#  USER DATABASE (JSON-based persistent storage)
# ═══════════════════════════════════════════════════════════
USER_DB_PATH = os.path.join(ROOT_DIR, "data", "users.json")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USER_DB_PATH):
        try:
            with open(USER_DB_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"admin": {"password": hash_password("admin123"), "name": "System Administrator", "email": "admin@queueintel.ai", "role": "admin"}}

def save_users(users):
    os.makedirs(os.path.dirname(USER_DB_PATH), exist_ok=True)
    with open(USER_DB_PATH, "w") as f:
        json.dump(users, f, indent=2)

def register_user(username, password, name, email, role="customer"):
    users = load_users()
    if username.lower() in [u.lower() for u in users]:
        return False, "Username already registered!"
    if any(u.get('email', '').lower() == email.lower() for u in users.values()):
        return False, "Email already registered!"
    users[username] = {
        "password": hash_password(password),
        "name": name, "email": email, "role": role,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users(users)
    return True, "Registration successful! Please login below."

def authenticate_user(username, password):
    users = load_users()
    if username in users and users[username]["password"] == hash_password(password):
        return True, users[username]
    return False, None

if not os.path.exists(USER_DB_PATH):
    save_users({"admin": {"password": hash_password("admin123"), "name": "System Administrator", "email": "admin@queueintel.ai", "role": "admin"}})

FACILITY_OPTIONS = [
    "Bank Branch", "Hospital OPD", "Government Office",
    "Railway Station", "College Admin", "Service Center"
]

# ═══════════════════════════════════════════════════════════
#  AUTHENTICATION INTERFACE (GATEKEEPER)
# ═══════════════════════════════════════════════════════════
if not st.session_state.authenticated:
    st.markdown('<div class="auth-bg-container">', unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 2.2, 1])
    with col_l2:
        st.markdown("""
        <div class="login-container-premium animate-fade-scale">
            <div class="auth-glowing-glow">🚶‍♂️‍➡️</div>
            <h1 style="margin:0; font-size:2.4rem;" class="shimmer-text">QAdapt</h1>
            <p style="color:#64748b; margin-top:6px; font-size:0.85rem; letter-spacing: 2px; text-transform: uppercase;">
                Queue Intelligence & Optimization Portal
            </p>
            <hr style="margin:20px 0;">
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="login-facility-selector">
            <span style="color:#818cf8; font-size:0.78rem; font-weight:700; letter-spacing:1.5px; text-transform:uppercase;">
                🏢 Select Facility to Monitor
            </span>
        </div>
        """, unsafe_allow_html=True)

        login_facility = st.selectbox(
            "Facility",
            FACILITY_OPTIONS,
            index=FACILITY_OPTIONS.index(st.session_state.get("selected_facility", "Bank Branch")) if st.session_state.get("selected_facility", "Bank Branch") in FACILITY_OPTIONS else 0,
            label_visibility="collapsed",
            key="login_facility_widget"
        )
        st.session_state.selected_facility = login_facility

        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

        auth_tab = st.radio("Select Portal Mode:", ["👥 Customer Portal", "🔑 Staff & Manager Portal"], horizontal=True)

        st.session_state.remember_me = st.checkbox(
            "🔒 Remember Me (Keep me securely signed in)",
            value=st.session_state.remember_me
        )

        if auth_tab == "👥 Customer Portal":
            st.markdown("<p style='color:#cbd5e1; margin-bottom: 15px; font-size:0.9rem;'>⚡ Track live queues, instant wait estimates, and station occupancy in real-time.</p>", unsafe_allow_html=True)

            if st.button("🚀 Quick Instant Access as Guest (No Login)", use_container_width=True, type="primary"):
                st.session_state.selected_facility = st.session_state.get("login_facility_widget", "Bank Branch")
                st.session_state.authenticated = True
                st.session_state.user_info = {"name": "Guest Customer", "role": "customer", "email": "guest@qadapt.ai"}
                save_active_session(st.session_state.user_info, st.session_state.remember_me, st.session_state.selected_facility)
                st.success(f"🎉 Access Granted! Loading {st.session_state.selected_facility} dashboard...")
                time.sleep(0.8)
                st.rerun()

            st.markdown("<p style='color:#475569; margin: 15px 0; text-align:center; font-weight:bold;'>─── OR LOGIN WITH ACCOUNT ───</p>", unsafe_allow_html=True)

            with st.form("customer_login"):
                cust_user = st.text_input("Customer Username", placeholder="e.g. xyz")
                cust_pass = st.text_input("Customer Password", type="password", placeholder="••••••••")
                cust_submit = st.form_submit_button("Sign In to My Account", use_container_width=True)
                if cust_submit:
                    status, user_details = authenticate_user(cust_user, cust_pass)
                    if status and user_details.get('role') == 'customer':
                        st.session_state.selected_facility = st.session_state.get("login_facility_widget", "Bank Branch")
                        st.session_state.authenticated = True
                        st.session_state.user_info = user_details
                        save_active_session(user_details, st.session_state.remember_me, st.session_state.selected_facility)
                        st.success(f"✨ Welcome back, {user_details['name']}! Loading {st.session_state.selected_facility}...")
                        time.sleep(0.9)
                        st.rerun()
                    elif status:
                        st.error("⚠️ This is an authorized manager profile. Switch to Staff Portal tab.")
                    else:
                        st.error("❌ Invalid credentials. Please try again.")

            if st.button("✨ New Customer? Create Free Account", use_container_width=True):
                st.session_state.auth_page = "register"
                st.rerun()

        else:  # Manager/Admin Portal
            if st.session_state.auth_page == "login":
                with st.form("login_form"):
                    st.markdown("<h4 style='text-align: left; margin-bottom: 12px; color:#c7d2fe;'>🔐 Authorized Staff Gateway</h4>", unsafe_allow_html=True)
                    username_input = st.text_input("Staff Username / Email", placeholder="admin")
                    password_input = st.text_input("Password", type="password", placeholder="••••••••")
                    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                    login_submitted = st.form_submit_button("Access Management Panel", use_container_width=True, type="primary")
                    if login_submitted:
                        status, user_details = authenticate_user(username_input, password_input)
                        if status:
                            if user_details.get('role') in ['admin', 'manager']:
                                st.session_state.selected_facility = st.session_state.get("login_facility_widget", "Bank Branch")
                                st.session_state.authenticated = True
                                st.session_state.user_info = user_details
                                save_active_session(user_details, st.session_state.remember_me, st.session_state.selected_facility)
                                st.success(f"🔓 Access Granted! Welcome {user_details['name']} — Monitoring {st.session_state.selected_facility}")
                                time.sleep(0.9)
                                st.rerun()
                            else:
                                st.error("❌ Access denied. Customer accounts cannot access the admin panel.")
                        else:
                            st.error("❌ Invalid credentials. (Hint: admin / admin123)")

                if st.button("🛡️ Onboard New Manager Account", use_container_width=True):
                    st.session_state.auth_page = "register_manager"
                    st.rerun()

        if st.session_state.auth_page in ["register", "register_manager"]:
            role_to_reg = "manager" if st.session_state.auth_page == "register_manager" else "customer"
            role_label = "Admin/Manager" if role_to_reg == "manager" else "Customer"
            with st.form("register_form"):
                st.markdown(f"<h4 style='text-align: left; margin-bottom: 12px; color:#818cf8;'>📝 New {role_label} Registration</h4>", unsafe_allow_html=True)
                reg_name = st.text_input("Full Name", placeholder="XYZ")
                reg_email = st.text_input("Email ID", placeholder="xyz@company.com")
                reg_username = st.text_input("Choose Username", placeholder="xyz123")
                reg_pass = st.text_input("Password Secure", type="password", placeholder="••••••••")
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                reg_submitted = st.form_submit_button("Register & Create Profile", use_container_width=True, type="primary")
                if reg_submitted:
                    if not (reg_name and reg_email and reg_username and reg_pass):
                        st.error("⚠️ All registration fields are mandatory.")
                    else:
                        success, message = register_user(reg_username, reg_pass, reg_name, reg_email, role=role_to_reg)
                        if success:
                            st.success(f"🎉 {message}")
                            time.sleep(1.2)
                            st.session_state.auth_page = "login"
                            st.rerun()
                        else:
                            st.error(message)
            if st.button("⬅️ Return to Portal Login", use_container_width=True):
                st.session_state.auth_page = "login"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ═══════════════════════════════════════════════════════════
#  ROLE DEFINITIONS
# ═══════════════════════════════════════════════════════════
user_info = st.session_state.user_info
is_admin = user_info.get('role', 'customer') in ['admin', 'manager']

# ═══════════════════════════════════════════════════════════
#  FACILITY LAYOUT LABELS
# ═══════════════════════════════════════════════════════════
FACILITY_COUNTERS = {
    "Bank Branch":       ["Cash Counter", "Accounts", "Loan Desk", "Forex", "FD/RD", "Clearing", "Service", "Digital"],
    "Hospital OPD":      ["Registration", "Pharmacy", "Billing", "Triage", "Lab Reports", "Specialist", "Emergency", "Follow-up"],
    "Government Office": ["Application", "Verification", "Certificate", "Aadhaar", "PAN", "Revenue", "Grievance", "Dispatch"],
    "Railway Station":   ["Ticket", "Tatkal", "Reservation", "Refund", "Enquiry", "Platform", "Luggage", "VIP"],
    "College Admin":     ["Admission", "Fees", "Examination", "Library", "Scholarship", "ID Card", "Transcript", "Placement"],
    "Service Center":    ["Reception", "Technical", "Billing", "Returns", "Warranty", "Installation", "Complaints", "Pickup"],
}

STATUS_COLORS = {'NORMAL': '#10b981', 'MODERATE': '#f59e0b', 'HIGH': '#f97316', 'CRITICAL': '#ef4444'}
STATUS_BADGE = {'NORMAL': 'badge-normal', 'MODERATE': 'badge-moderate', 'HIGH': 'badge-high', 'CRITICAL': 'badge-critical'}

# ═══════════════════════════════════════════════════════════
#  DATA INTERPOLATION & HELPER MATH
# ═══════════════════════════════════════════════════════════
def compute_risk_score(result, counter_data):
    if not counter_data or result.get('total_people', 0) == 0:
        return 0
    score = 0.0
    util = result.get('utilization_pct', 0)
    score += min(35, util / 100 * 35)
    max_p = max(c['people'] for c in counter_data)
    score += min(25, (max_p / 20) * 25)
    avg_w = result.get('average_wait_time', 0)
    score += min(20, (avg_w / 30) * 20)
    overloaded = sum(1 for c in counter_data if c['people'] > 12)
    score += min(20, (overloaded / max(1, len(counter_data))) * 20)
    return min(100, max(0, round(score)))

def risk_label(score):
    if score >= 75: return "CRITICAL", "🔴"
    if score >= 50: return "HIGH", "🟠"
    if score >= 25: return "MODERATE", "🟡"
    return "NORMAL", "🟢"

def counter_status(people):
    if people > 15: return "CRITICAL"
    if people > 10: return "HIGH"
    if people > 6:  return "MODERATE"
    return "NORMAL"

def generate_alerts(counter_data, result, risk_sc):
    alerts = []
    for c in counter_data:
        if c['people'] > 15:
            alerts.append(('CRITICAL', f"Counter {c['counter_id']} overloaded — {c['people']} people, {c['wait_time']} min wait"))
        elif c['people'] > 10:
            alerts.append(('WARNING', f"Counter {c['counter_id']} approaching capacity — {c['people']} people"))
    if result.get('average_wait_time', 0) > 25:
        alerts.append(('CRITICAL', f"Average wait {result['average_wait_time']} min exceeds 25 min threshold"))
    elif result.get('average_wait_time', 0) > 15:
        alerts.append(('WARNING', f"Average wait rising: {result['average_wait_time']} min"))
    if result.get('utilization_pct', 0) > 90:
        alerts.append(('CRITICAL', f"System utilization at {result['utilization_pct']}%"))
    if risk_sc >= 75:
        alerts.append(('CRITICAL', f"Overall risk score {risk_sc}% — immediate action recommended"))
    if not alerts:
        alerts.append(('OK', 'All counters operating smoothly within normal parameters'))
    return alerts[:5]

def generate_nl_prediction(predictor, current_hour, day_num, is_month_start, num_counters):
    for m in [5, 10, 15, 20, 25, 30]:
        future = predictor.predict_future(current_hour, day_num, is_month_start, m, num_counters)
        if future['total_predicted_people'] >= 30:
            return f"Queue is likely to exceed 30 people within the next {m} minutes.", m
    return "Queue is expected to remain below 30 people for the next 30 minutes.", None

def forecast_reliability(minutes_ahead):
    return max(55, min(95, round(95 - minutes_ahead * 0.8)))

def counter_card_html(cid, name, people, wait, cap_pct, status):
    color = STATUS_COLORS.get(status, '#6b7280')
    badge = STATUS_BADGE.get(status, 'badge-normal')
    return f"""
    <div class="counter-card animate-slide-up">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <span style="color:#94a3b8; font-size:0.78em; font-weight:700; letter-spacing:0.5px;">STATION {cid:02d}</span>
            <span class="badge {badge}">{status}</span>
        </div>
        <div style="color:#64748b; font-size:0.75em; font-weight:600; text-transform:uppercase; margin-bottom:8px;">{name}</div>
        <div style="font-size:2.8em; font-weight:800; color:#f8fafc; line-height:1; margin-bottom:2px;">{people}</div>
        <div style="color:#64748b; font-size:0.82em; margin-bottom:14px;">people waiting in line</div>
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
            <span style="color:#94a3b8; font-size:0.78em; font-weight:600;">EST. SERVICE WAIT</span>
            <span style="color:{color}; font-weight:700; font-size:0.95em;">{wait} min</span>
        </div>
        <div style="background:rgba(255,255,255,0.06); border-radius:10px; height:6px; overflow:hidden; position:relative;">
            <div style="background:linear-gradient(90deg, {color}, #818cf8); height:100%; border-radius:10px; width:{min(cap_pct,100)}%; transition:width 0.8s cubic-bezier(0.16, 1, 0.3, 1);"></div>
        </div>
        <div style="color:#64748b; font-size:0.72em; margin-top:5px; text-align:right; font-weight:600;">{cap_pct}% active load</div>
    </div>
    """

# ═══════════════════════════════════════════════════════════
#  REAL-TIME HEADER WITH DATE & TIME
# ═══════════════════════════════════════════════════════════
formatted_date = datetime.now().strftime('%A, %d %B %Y')
formatted_time = datetime.now().strftime('%I:%M:%S %p')

st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;" class="animate-slide-up">
    <div>
        <h1 style="margin:0; font-size:2.2rem;" class="shimmer-text">
            🚶‍♂️‍➡️ QAdapt Intelligence Suite
        </h1>
        <p style="color:#94a3b8; margin:4px 0 0 0; font-size:0.95em;">
            Dynamic Queue Forecasting & Automated Resource Optimization Engine
        </p>
    </div>
    <div class="corner-widget">
        <span style="color: #34d399; font-weight: bold; font-size: 0.78rem;">
            <span class="live-dot"></span> NEURAL ENGINE LIVE
        </span>
        <div style="color: #f1f5f9; font-weight: 700; font-size: 1.08rem; margin-top: 3px; font-family: 'Space Grotesk', monospace;">
            ⏱️ {formatted_time}
        </div>
        <div style="color: #64748b; font-size: 0.72rem; letter-spacing: 0.5px; margin-top: 2px; text-transform: uppercase;">
            📅 {formatted_date}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ═══════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 👤 User Workspace")
    current_user_name = user_info.get('name', 'Operator')
    current_user_role = user_info.get('role', 'customer')
    
    st.markdown(f"""
    <div class="glass-panel" style="padding:14px; margin-bottom:14px; border: 1px solid rgba(99,102,241,0.25);">
        <span style="color:#64748b; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px;">Active Session:</span>
        <div style="color:#f1f5f9; font-weight:700; font-size:1.1rem; margin:2px 0;">{current_user_name}</div>
        <span class="badge {'badge-normal' if current_user_role == 'admin' else 'badge-moderate'}">
            ⚡ {current_user_role.upper()} PORTAL
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Terminate Session
    if st.button("🚪 Logout / Terminate Session", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        clear_active_session()
        st.rerun()

    st.markdown("---")
    st.markdown("## ⚙️ Environment Control")

    # ★ Automatically get active facility set during login process (Dropdown removed from Sidebar)
    facility = st.session_state.get("selected_facility", "Bank Branch")

    # Context values
    day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    current_day = st.selectbox("📅 Day of Week:", day_names, index=datetime.now().weekday())
    day_num = day_names.index(current_day)
    current_hour = st.slider("⏰ Operating Hour Slot:", 9, 17, min(17, max(9, datetime.now().hour)))
    is_month_start = st.checkbox("📈 Peak Cycle / Month-Start Surge?", value=datetime.now().day <= 5)

    # RESTRICTED ADMINISTRATIVE SETTINGS (Only for Manager/Admin)
    if is_admin:
        st.markdown("---")
        st.markdown("### 🔐 Live Feed & Station Control")
        feed_mode = st.radio(
            "📥 Feed Telemetry Mode:",
            ["📷 CCTV Camera Feed (Live / Simulated)", "🎛️ Manual Input"],
            index=0
        )
        num_counters = st.slider("🔢 Active Operational Counters:", 2, 8, 4)
    else:
        feed_mode = "📷 CCTV Camera Feed (Live / Simulated)"
        num_counters = 4

    st.markdown("---")

    # ── AI EXPLANATION PANEL ──
    with st.expander("🚶‍♂️‍➡️ Deep Learning Telemetry Architecture"):
        st.markdown("""
        <div style="font-size:0.85em; line-height:1.7;">
        <b style="color:#818cf8;">📥 INPUT SIGNALS</b><br>
        • Live arrival stream · Service queue length<br>
        • Active station throughput · Temporal patterns<br>
        • Historical surge indices · Shift operator count
        <br><br>
        <b style="color:#06b6d4;">⚙️ MACHINE LEARNING PIPELINE</b><br>
        <code>GradientBoostingRegressor</code> → Density forecast<br>
        <code>RandomForestRegressor</code> → Latency / wait estimation
        </div>
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    #  DYNAMIC BOTTOM QR CODE GENERATOR
    # ═══════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📱 Mobile Passenger Portal")
    
    server_ip = get_local_ip()
    target_link = f"http://{server_ip}:8501/?share=true"
    encoded_link = urllib.parse.quote_plus(target_link)
    qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&color=818cf8&bgcolor=080f25&data={encoded_link}"
    
    st.markdown(f"""
    <div class="qr-container">
        <p style="color:#c7d2fe; font-size:0.85rem; font-weight:700; margin-bottom:10px;">📲 Scan for Live Status & Token</p>
        <img src="{qr_api_url}" alt="QR Status Link" style="border: 2px solid rgba(129, 140, 248, 0.3); border-radius: 12px; width: 135px; height: 135px; box-shadow: 0 4px 15px rgba(99,102,241,0.2);" />
        <p style="color:#64748b; font-size:0.72rem; margin-top:10px;">Scan using any phone camera to check station wait times and generate tokens seamlessly.</p>
    </div>
    """, unsafe_allow_html=True)

    if is_admin:
        st.markdown("---")
        st.markdown("### 🎫 Token Ticket Dispatch Log")
        todays_tokens = get_todays_tokens()
        st.markdown(f"**Total Registered Today:** `{len(todays_tokens)}` tickets")
        if todays_tokens:
            with st.expander(f"📋 Live Token Stream ({len(todays_tokens)})"):
                for tkn in reversed(todays_tokens[-20:]):
                    st.markdown(f"🎟️ **{tkn['token_id']}** → Station **{tkn['assigned_counter']}** (`#{tkn['position_in_queue']}` in queue) · <small>{tkn['generated_at']}</small>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  ROLE-BASED VIEW CONTROL (RBAC MULTI-TAB)
# ═══════════════════════════════════════════════════════════

if not is_admin:
    # ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    #  CUSTOMER / PUBLIC USER VIEW
    # ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    
    cust_tab1, cust_tab2, cust_tab3 = st.tabs([
        "📍 Live Queue Tracker", 
        "🔮 Peak-Hour Predictions (Forecast)", 
        "💬 Ask AI Queue Bot"
    ])
    
    counter_names = FACILITY_COUNTERS.get(facility, [f"Counter {i+1}" for i in range(8)])
    
    # Simulated Live values generation for customers
    counter_data = []
    for i in range(num_counters):
        pred_p, _ = predictor.predict_queue(
            current_hour, day_num, i+1,
            int(is_month_start), 1 if 12 <= current_hour <= 14 else 0
        )
        sim_p = max(1, pred_p + np.random.randint(-2, 3))
        sim_w = max(2, int((sim_p * 5.0) / num_counters))
        counter_data.append({'counter_id': i+1, 'people': sim_p, 'wait_time': sim_w})

    result = engine.analyze_and_recommend(counter_data)
    chatbot.update_data(counter_data, result)
    st.session_state['live_counter_data'] = counter_data
    st.session_state['live_result'] = result
    
    save_live_status_to_disk(facility, counter_data, result)

    # ━━ CUST TAB 1: LIVE QUEUE TRACKER ━━
    with cust_tab1:
        st.markdown(f"### 📍 Current Live Facility Feed: <span style='color:#38bdf8;'>{facility}</span>", unsafe_allow_html=True)
        
        risk_sc = compute_risk_score(result, counter_data)
        r_label, r_emoji = risk_label(risk_sc)
        
        st.markdown(f"""
        <div class="customer-info-box">
            <h4 style="margin:0; color:#c7d2fe; font-size:1.15rem;">📊 Real-Time Facility Intelligence</h4>
            <div style="display: flex; gap: 40px; margin-top: 18px; flex-wrap: wrap;">
                <div>
                    <span style="color:#64748b; font-size:0.8rem; font-weight:700; text-transform:uppercase;">Total Waiting In Facility</span>
                    <div style="font-size:2.5rem; font-weight:800; color:#38bdf8; line-height:1.1;">{result['total_people']} People</div>
                </div>
                <div>
                    <span style="color:#64748b; font-size:0.8rem; font-weight:700; text-transform:uppercase;">Estimated Service Wait</span>
                    <div style="font-size:2.5rem; font-weight:800; color:#34d399; line-height:1.1;">~{result['average_wait_time']} Mins</div>
                </div>
                <div>
                    <span style="color:#64748b; font-size:0.8rem; font-weight:700; text-transform:uppercase;">Facility Congestion Status</span>
                    <div style="font-size:2.5rem; font-weight:800; color:#fbbf24; line-height:1.1;">{r_emoji} {r_label}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.success(f"💡 **Smart Fast-Track Route:** Head over to **Counter {result['best_counter_for_new_customer']}** ({counter_names[result['best_counter_for_new_customer'] - 1]}) for the fastest processing!")

        st.markdown("#### 🖥️ Station-by-Station Occupancy Levels")
        cc_cols = st.columns(num_counters)
        for i, c in enumerate(counter_data):
            with cc_cols[i]:
                cs = counter_status(c['people'])
                cap_pct = round(c['people'] / 15 * 100)
                cname = counter_names[i]
                st.markdown(counter_card_html(c['counter_id'], cname, c['people'], c['wait_time'], cap_pct, cs), unsafe_allow_html=True)

        st.markdown("---")
        fig_bar = go.Figure(go.Bar(
            x=[f"C-{c['counter_id']} ({counter_names[c['counter_id']-1]})" for c in counter_data],
            y=[c['people'] for c in counter_data],
            marker=dict(
                color=[STATUS_COLORS.get(counter_status(c['people']), '#6b7280') for c in counter_data],
                line=dict(color='rgba(255,255,255,0.2)', width=1.5)
            ),
            text=[f"{c['people']} awaiting" for c in counter_data], 
            textposition='auto'
        ))
        fig_bar.update_layout(
            title="Station Queue Density Overview", 
            template="plotly_dark", 
            height=340, 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ━━ CUST TAB 2: AI FORECAST FOR VISITORS ━━
    with cust_tab2:
        st.markdown("### 🔮 AI Predictive Travel & Visit Advisory")
        st.markdown("Get neural predictions on peak arrival surges to plan your visit efficiently.")
        
        mins = st.slider("Select Horizon Time (Minutes):", 10, 120, 30, step=10, key="cust_slider")
        future = predictor.predict_future(current_hour, day_num, int(is_month_start), mins, num_counters)
        
        st.markdown(f"""
        <div class="prediction-callout">
            🔮 <b>AI Predictive Telemetry ({mins} mins from now):</b> Total facility queue is projected at 
            <b style="color:#38bdf8;">{future['total_predicted_people']} visitors</b> with an estimated queue turnaround delay of 
            <b style="color:#34d399;">~{round(future['total_predicted_people'] * 1.5)} minutes</b>.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)

        timeline = []
        for m in range(0, 130, 15):
            r = predictor.predict_future(current_hour, day_num, int(is_month_start), m, num_counters)
            timeline.append({'Minutes': m, 'Total Customers': r['total_predicted_people']})
            
        tdf = pd.DataFrame(timeline)
        fig_line = px.area(tdf, x='Minutes', y='Total Customers', markers=True, title="Projected Visitor Surge Trajectory", template="plotly_dark")
        fig_line.update_traces(
            line_color="#06b6d4", 
            line_width=3,
            fillcolor='rgba(6,182,212,0.12)',
            marker=dict(size=8, color='#818cf8', line=dict(color='#ffffff', width=1.5))
        )
        fig_line.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # ━━ CUST TAB 3: FAQ CHATBOT ━━
    with cust_tab3:
        st.markdown("### 💬 Real-Time Smart Assistant")
        st.markdown("Ask natural language queries regarding station workloads, quick fast-tracks, and optimal arrival times.")
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        st.markdown("**⚡ Instant Quick Questions:**")
        qc1, qc2 = st.columns(2)
        quick_query = None
        with qc1:
            if st.button("🔴 Which counter has the shortest waiting line?", use_container_width=True):
                quick_query = "Where is the queue shortest?"
        with qc2:
            if st.button("⏱️ What are the current average wait times?", use_container_width=True):
                quick_query = "What are the wait times?"

        if quick_query:
            st.session_state.chat_history.append({"role": "user", "content": quick_query})
            response = chatbot.respond(quick_query)
            st.session_state.chat_history.append({"role": "assistant", "content": response})

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ask a question about current status...")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"): st.markdown(user_input)
            ai_response = chatbot.respond(user_input)
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"): st.markdown(ai_response)

else:
    # ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    #  STAFF & MANAGER ADMIN VIEW (FULL ACCESS)
    # ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Live Dashboard",
        "🔮 AI Forecast",
        "📈 Historical Analytics",
        "🎮 What-If Simulator",
        "💬 AI Assistant"
    ])

    # ==================== TAB 1: LIVE DASHBOARD ====================
    with tab1:
        run_camera = False
        counter_data = []
        counter_names = FACILITY_COUNTERS.get(facility, [f"Counter {i+1}" for i in range(8)])

        st.markdown(f"#### 📡 {facility} — Real-Time Facility Intelligence Matrix")

        if feed_mode == "📷 CCTV Camera Feed (Live / Simulated)":
            st.markdown("##### 📹 Live CCTV Video Feeds (YOLOv8 Edge Vision)")
            run_camera = st.toggle(
                "🔴 Activate Station 1 Edge Webcam Telemetry",
                value=False,
                key="camera_enabled"
            )

            if not HAS_CV2:
                st.error("Camera telemetry is unavailable: OpenCV is not installed in the active Python environment.")
            elif detector is None:
                st.error(f"Camera telemetry is unavailable: YOLO detector could not initialize. Details: {_detector_error}")

            cam_container = st.empty()
            analytics_container = st.empty()

            if run_camera and detector is not None and HAS_CV2:
                @st.fragment(run_every="500ms")
                def refresh_camera_frame():
                    cap = st.session_state.get("camera_capture")
                    if cap is None or not cap.isOpened():
                        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                        st.session_state["camera_capture"] = cap

                    if not cap.isOpened():
                        st.error("❌ Unable to establish link with primary camera stream.")
                        return

                    ret, frame = cap.read()
                    if not ret:
                        st.error("❌ CCTV video feed disconnected!")
                        return

                    people_count, frame_to_show = detector.process_frame(frame)
                    wait_time = max(1, int((people_count * 4.5) / num_counters))
                    counter_data = [{'counter_id': 1, 'people': people_count, 'wait_time': wait_time}]
                    for counter_index in range(1, num_counters):
                        predicted_people, _ = predictor.predict_queue(
                            current_hour, day_num, counter_index + 1,
                            int(is_month_start),
                            1 if 12 <= current_hour <= 14 else 0
                        )
                        simulated_people = max(0, predicted_people + np.random.randint(-2, 3))
                        simulated_wait = max(1, int((simulated_people * 4.5) / num_counters))
                        counter_data.append({
                            'counter_id': counter_index + 1,
                            'people': simulated_people,
                            'wait_time': simulated_wait
                        })

                    result = engine.analyze_and_recommend(counter_data)
                    chatbot.update_data(counter_data, result)
                    st.session_state['live_counter_data'] = counter_data
                    st.session_state['live_result'] = result
                    save_live_status_to_disk(facility, counter_data, result)

                    with st.container():
                        camera_columns = st.columns(num_counters)
                        with camera_columns[0]:
                            st.markdown("**Counter 1 — 🔴 LIVE VISION STREAM**")
                            st.image(frame_to_show, channels="RGB", use_container_width=True)
                            st.metric("Counter 1", f"{people_count} people", f"~{wait_time} min wait")
                        for counter_index in range(1, num_counters):
                            with camera_columns[counter_index]:
                                st.markdown(f"**Counter {counter_index + 1} — CCTV Feed**")
                                st.markdown(
                                    '<div class="camera-box"><span class="rec">● LIVE STREAM</span> '
                                    f'CAM-{counter_index + 1}<br><span style="font-size:2.5em;">👥</span>'
                                    '<br><span style="color:#06b6d4; font-weight:600;">Neural Processing...</span></div>',
                                    unsafe_allow_html=True
                                )
                                st.metric(
                                    f"Counter {counter_index + 1}",
                                    f"{counter_data[counter_index]['people']} people",
                                    f"~{counter_data[counter_index]['wait_time']} min wait"
                                )

                    risk_score = compute_risk_score(result, counter_data)
                    risk_label_text, risk_emoji = risk_label(risk_score)
                    with st.container():
                        metrics = st.columns(5)
                        metrics[0].metric("👥 Total Queue", result['total_people'])
                        metrics[1].metric("⏱️ Avg Wait", f"{result['average_wait_time']} min")
                        metrics[2].metric("🏢 Active Stations", num_counters)
                        metrics[3].metric("⚠️ Queue Risk", f"{risk_score}%")
                        metrics[4].metric("System Health", f"{risk_emoji} {risk_label_text}")

                        chart_columns = st.columns(3)
                        with chart_columns[0]:
                            load_chart = go.Figure(go.Bar(
                                x=[f"C-{counter['counter_id']}" for counter in counter_data],
                                y=[counter['people'] for counter in counter_data],
                                marker_color=[STATUS_COLORS.get(counter_status(counter['people']), '#6b7280') for counter in counter_data],
                                text=[f"{counter['people']} ({counter['wait_time']}m)" for counter in counter_data],
                                textposition='auto'
                            ))
                            load_chart.add_hline(y=12, line_dash="dash", line_color="#ef4444", annotation_text="Overload Bound")
                            load_chart.update_layout(title="Live Station Load Distribution", template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                            st.plotly_chart(load_chart, use_container_width=True, key="camera_load_chart")
                        with chart_columns[1]:
                            utilization_chart = go.Figure(go.Indicator(
                                mode="gauge+number", value=min(result.get('utilization_pct', 0), 100),
                                title={'text': "Facility Utilization"},
                                gauge={'axis': {'range': [0, 100]}, 'bar': {'color': '#6366f1'}}
                            ))
                            utilization_chart.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)')
                            st.plotly_chart(utilization_chart, use_container_width=True, key="camera_utilization_chart")
                        with chart_columns[2]:
                            risk_chart = go.Figure(go.Indicator(
                                mode="gauge+number", value=risk_score,
                                title={'text': "Real-Time Risk Monitor"},
                                gauge={'axis': {'range': [0, 100]}, 'bar': {'color': STATUS_COLORS.get(risk_label_text, '#6b7280')}}
                            ))
                            risk_chart.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)')
                            st.plotly_chart(risk_chart, use_container_width=True, key="camera_risk_chart")

                        st.markdown("### 💡 AI Real-Time Dispatch Recommendations")
                        for warning in result['warnings']:
                            st.error(warning)
                        for recommendation in result['recommendations']:
                            st.info(recommendation)
                        st.success(f"📍 Route new arrivals → **Counter {result['best_counter_for_new_customer']}**")

                        st.markdown("##### 🖥️ Counter-Wise Queue Status")
                        queue_columns = st.columns(min(num_counters, 4))
                        for counter_index, counter in enumerate(counter_data):
                            with queue_columns[counter_index % min(num_counters, 4)]:
                                st.markdown(
                                    counter_card_html(
                                        counter['counter_id'], counter_names[counter_index],
                                        counter['people'], counter['wait_time'],
                                        round(counter['people'] / 12 * 100),
                                        counter_status(counter['people'])
                                    ),
                                    unsafe_allow_html=True
                                )

                        report = pd.DataFrame(counter_data)
                        report['facility'] = facility
                        report['status'] = result['status']
                        report['risk_score'] = risk_score
                        report['recommendation'] = "; ".join(result['recommendations'])
                        st.download_button(
                            "📥 Download Queue Report (CSV)", report.to_csv(index=False),
                            f"queue_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            "text/csv", key="live_camera_export"
                        )

                refresh_camera_frame()

            if False and run_camera and detector is not None and HAS_CV2:
                cap = st.session_state.get("camera_capture")
                if cap is None or not cap.isOpened():
                    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    st.session_state["camera_capture"] = cap
                if not cap.isOpened():
                    st.error("❌ Unable to establish link with primary camera stream.")
                    cap.release()
                    st.session_state.pop("camera_capture", None)
                else:
                    stop_signal = False
                    frame_count = 0
                    frame_processed = False
                    try:
                        if run_camera and not stop_signal:
                            ret, frame = cap.read()
                            if not ret:
                                st.error("❌ CCTV video feed disconnected!")
                            else:
                                frame_processed = True
                                live_p1, frame_to_show = detector.process_frame(frame)
                                wait_c1 = max(1, int((live_p1 * 4.5) / num_counters))
                                counter_data = [{'counter_id': 1, 'people': live_p1, 'wait_time': wait_c1}]
                                for i in range(1, num_counters):
                                    pred_p, _ = predictor.predict_queue(
                                        current_hour, day_num, i+1,
                                        int(is_month_start), 1 if 12 <= current_hour <= 14 else 0
                                    )
                                    sim_p = max(0, pred_p + np.random.randint(-2, 3))
                                    sim_w = max(1, int((sim_p * 4.5) / num_counters))
                                    counter_data.append({'counter_id': i+1, 'people': sim_p, 'wait_time': sim_w})

                                with cam_container.container():
                                    cols = st.columns(num_counters)
                                    with cols[0]:
                                        st.markdown("**Counter 1 — 🔴 LIVE VISION STREAM**")
                                        if frame_to_show is not None:
                                            st.image(frame_to_show, channels="RGB", use_container_width=True)
                                        st.metric("Counter 1", f"{live_p1} people", f"~{wait_c1} min wait", delta_color="inverse")
                                    for idx in range(1, num_counters):
                                        with cols[idx]:
                                            st.markdown(f"**Counter {idx+1} — CCTV Feed**")
                                            st.markdown(f'<div class="camera-box"><span class="rec">● LIVE STREAM</span> CAM-{idx+1}<br><span style="font-size:2.5em;">👥</span><br><span style="color:#06b6d4; font-weight:600;">Neural Processing...</span></div>', unsafe_allow_html=True)
                                            st.metric(f"Counter {idx+1}", f"{counter_data[idx]['people']} people", f"~{counter_data[idx]['wait_time']} min wait", delta_color="inverse")

                                result = engine.analyze_and_recommend(counter_data)
                                chatbot.update_data(counter_data, result)
                                st.session_state['live_counter_data'] = counter_data
                                st.session_state['live_result'] = result
                                
                                save_live_status_to_disk(facility, counter_data, result)

                                risk_sc = compute_risk_score(result, counter_data)
                                alerts = generate_alerts(counter_data, result, risk_sc)
                                k1,k2,k3,k4,k5 = st.columns(5)
                                k1.metric("👥 Total Queue", result['total_people'])
                                k2.metric("⏱️ Avg Wait", f"{result['average_wait_time']} min")
                                k3.metric("🏢 Active Stations", f"{num_counters}")
                                k4.metric("⚠️ Queue Risk", f"{risk_sc}%")
                                r_label, r_emoji = risk_label(risk_sc)
                                k5.metric("System Health", f"{r_emoji} {r_label}")
                                c1, c2, c3 = st.columns(3)
                                with c1:
                                    fig_bar = go.Figure(go.Bar(
                                        x=[f"C-{c['counter_id']}" for c in counter_data],
                                        y=[c['people'] for c in counter_data],
                                        marker=dict(
                                            color=[STATUS_COLORS.get(counter_status(c['people']), '#6b7280') for c in counter_data],
                                            line=dict(color='rgba(255,255,255,0.2)', width=1.5)
                                        ),
                                        text=[f"{c['people']} ({c['wait_time']}m)" for c in counter_data], textposition='auto'
                                    ))
                                    fig_bar.add_hline(y=12, line_dash="dash", line_color="#ef4444", annotation_text="Overload Bound")
                                    fig_bar.update_layout(
                                        title="Live Station Load Distribution", 
                                        template="plotly_dark", 
                                        height=300, 
                                        paper_bgcolor='rgba(0,0,0,0)', 
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                                        yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
                                    )
                                    st.plotly_chart(fig_bar, use_container_width=True, key=f"bar_{frame_count}")
                                with c2:
                                    util = min(result.get('utilization_pct', 0), 100)
                                    fig_g = go.Figure(go.Indicator(mode="gauge+number", value=util, title={'text': "Total Facility Utilization"},
                                        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#6366f1"},
                                        'steps': [{'range': [0, 50], 'color': "rgba(34,197,94,0.15)"}, {'range': [50, 80], 'color': "rgba(245,158,11,0.15)"}, {'range': [80, 100], 'color': "rgba(239,68,68,0.15)"}]}))
                                    fig_g.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)')
                                    st.plotly_chart(fig_g, use_container_width=True, key=f"gauge_{frame_count}")
                                with c3:
                                    fig_live_risk = go.Figure(go.Indicator(
                                        mode="gauge+number",
                                        value=risk_sc,
                                        title={'text': "Real-Time Risk Monitor"},
                                        gauge={
                                            'axis': {'range': [0, 100]},
                                            'bar': {'color': STATUS_COLORS.get(r_label, '#6b7280')},
                                            'steps': [
                                                {'range': [0, 25], 'color': "rgba(16, 185, 129, 0.12)"},
                                                {'range': [25, 50], 'color': "rgba(245, 158, 11, 0.12)"},
                                                {'range': [50, 75], 'color': "rgba(249, 115, 22, 0.12)"},
                                                {'range': [75, 100], 'color': "rgba(239, 68, 68, 0.12)"}
                                            ]
                                        }
                                    ))
                                    fig_live_risk.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)')
                                    st.plotly_chart(fig_live_risk, use_container_width=True, key=f"risk_{frame_count}")
                                st.markdown("### 💡 AI Recommendations")
                                for w in result['warnings']: st.error(w)
                                for r in result['recommendations']: st.info(r)
                                st.success(f"📍 Route new arrivals → **Counter {result['best_counter_for_new_customer']}**")

                                st.markdown("##### 🖥️ Counter-Wise Queue Status")
                                live_cols = st.columns(min(num_counters, 4))
                                for idx, counter in enumerate(counter_data):
                                    with live_cols[idx % min(num_counters, 4)]:
                                        counter_state = counter_status(counter['people'])
                                        capacity_pct = round(counter['people'] / 12 * 100)
                                        station_name = counter_names[idx] if idx < len(counter_names) else f"Counter {counter['counter_id']}"
                                        st.markdown(
                                            counter_card_html(
                                                counter['counter_id'], station_name,
                                                counter['people'], counter['wait_time'],
                                                capacity_pct, counter_state
                                            ),
                                            unsafe_allow_html=True
                                        )

                                st.markdown("##### 📥 Export Live Telemetry")
                                live_report = pd.DataFrame(counter_data)
                                live_report['facility'] = facility
                                live_report['status'] = result['status']
                                live_report['risk_score'] = risk_sc
                                live_report['recommendation'] = "; ".join(result['recommendations'])
                                st.download_button(
                                    "📥 Download Queue Report (CSV)",
                                    live_report.to_csv(index=False),
                                    f"queue_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                    "text/csv",
                                    key="live_camera_export"
                                )
                                frame_count += 1
                    finally:
                        pass
                    if frame_processed and st.session_state.get("camera_enabled", False):
                        time.sleep(0.5)
                        st.rerun()
            elif not run_camera:
                cap = st.session_state.pop("camera_capture", None)
                if cap is not None:
                    cap.release()
                cam_cols = st.columns(num_counters)
                for i in range(num_counters):
                    with cam_cols[i]:
                        pred_p, _ = predictor.predict_queue(current_hour, day_num, i+1, int(is_month_start), 1 if 12 <= current_hour <= 14 else 0)
                        live_p = max(0, pred_p + np.random.randint(-2, 3))
                        live_w = max(1, int((live_p * 4.5) / num_counters))
                        st.markdown(f'<div class="camera-box"><span style="color:#64748b; font-weight:700;">CAM-{i+1} STANDBY</span><br><span style="font-size:2.2em;">⏸️</span><br><span style="color:#94a3b8; font-weight:600;">{counter_names[i]}</span></div>', unsafe_allow_html=True)
                        counter_data.append({'counter_id': i+1, 'people': live_p, 'wait_time': live_w})
                        st.metric(f"Counter {i+1}", f"{live_p} people", f"~{live_w} min wait", delta_color="inverse")
                st.info("ℹ️ Toggle ON the webcam telemetry switch above to initiate YOLOv8 person detection.")
        else:
            man_cols = st.columns(num_counters)
            for i in range(num_counters):
                with man_cols[i]:
                    st.markdown(f"#### {counter_names[i]}")
                    pred_p, pred_w = predictor.predict_queue(current_hour, day_num, i+1, int(is_month_start), 1 if 12 <= current_hour <= 14 else 0)
                    p = st.number_input("People", 0, 80, pred_p, key=f"mp_{i}")
                    w = st.number_input("Wait (min)", 0, 120, int(pred_w), key=f"mw_{i}")
                    counter_data.append({'counter_id': i+1, 'people': p, 'wait_time': w})
                    cs = counter_status(p)
                    st.markdown(f'<span class="badge {STATUS_BADGE[cs]}">{cs}</span>', unsafe_allow_html=True)

        # Camera mode renders its live feed and analytics above. Keep the
        # shared dashboard below for manual input only to avoid duplicate UI.
        if feed_mode != "📷 CCTV Camera Feed (Live / Simulated)":
            if counter_data:
                st.markdown("---")
                result = engine.analyze_and_recommend(counter_data)
                chatbot.update_data(counter_data, result)
                st.session_state['live_counter_data'] = counter_data
                st.session_state['live_result'] = result
                
                save_live_status_to_disk(facility, counter_data, result)

                risk_sc = compute_risk_score(result, counter_data)
                r_label, r_emoji = risk_label(risk_sc)
                alerts = generate_alerts(counter_data, result, risk_sc)

                st.markdown("##### 🔔 Real-Time Anomaly & Threshold Alerts")
                for a_type, a_msg in alerts:
                    if a_type == 'CRITICAL':
                        st.markdown(f'<div class="alert-critical">🔴 <b>CRITICAL DISPATCH</b> — {a_msg}</div>', unsafe_allow_html=True)
                    elif a_type == 'WARNING':
                        st.markdown(f'<div class="alert-warning">🟡 <b>CAPACITY ADVISORY</b> — {a_msg}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="alert-ok">🟢 <b>OPTIMAL FLOW</b> — {a_msg}</div>', unsafe_allow_html=True)

                st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
                st.markdown("##### 📊 Operational Metrics & Facility KPIs")
                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("👥 Total Waiting", result['total_people'])
                k2.metric("⏱️ Avg Wait Latency", f"{result['average_wait_time']} min")
                k3.metric("🏢 Active Stations", f"{num_counters}")
                k4.metric("⚠️ Queue Risk Index", f"{risk_sc}%")
                k5.metric("Facility Health", f"{r_emoji} {r_label}")

                st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
                st.markdown("##### 🖥️ Operational Station Status Matrix")
                cc_cols = st.columns(min(num_counters, 4))
                for i, c in enumerate(counter_data):
                    with cc_cols[i % min(num_counters, 4)]:
                        cs = counter_status(c['people'])
                        cap_pct = round(c['people'] / 12 * 100)
                        cname = counter_names[i] if i < len(counter_names) else f"Counter {c['counter_id']}"
                        st.markdown(counter_card_html(c['counter_id'], cname, c['people'], c['wait_time'], cap_pct, cs), unsafe_allow_html=True)

                if num_counters > 4:
                    cc_cols2 = st.columns(num_counters - 4)
                    for i in range(4, num_counters):
                        c = counter_data[i]
                        with cc_cols2[i - 4]:
                            cs = counter_status(c['people'])
                            cap_pct = round(c['people'] / 12 * 100)
                            cname = counter_names[i] if i < len(counter_names) else f"Counter {c['counter_id']}"
                            st.markdown(counter_card_html(c['counter_id'], cname, c['people'], c['wait_time'], cap_pct, cs), unsafe_allow_html=True)

                st.markdown("---")
                chart_col1, chart_col2, chart_col3 = st.columns([1.2, 1, 1])

                with chart_col1:
                    fig_bar = go.Figure(go.Bar(
                        x=[f"C-{c['counter_id']}" for c in counter_data],
                        y=[c['people'] for c in counter_data],
                        marker=dict(
                            color=[STATUS_COLORS.get(counter_status(c['people']), '#6b7280') for c in counter_data],
                            line=dict(color='rgba(255,255,255,0.2)', width=1.5)
                        ),
                        text=[f"{c['people']} ({c['wait_time']}m)" for c in counter_data], 
                        textposition='auto'
                    ))
                    fig_bar.add_hline(y=12, line_dash="dash", line_color="#ef4444", annotation_text="Capacity Ceiling")
                    fig_bar.update_layout(
                        title="Queue Density Breakdown", 
                        template="plotly_dark", 
                        height=320, 
                        yaxis_title="Occupants",
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                        yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                with chart_col2:
                    util = min(result.get('utilization_pct', 0), 100)
                    fig_g = go.Figure(go.Indicator(
                        mode="gauge+number+delta", 
                        value=util,
                        title={'text': "Facility Capacity %"}, 
                        delta={'reference': 80, 'increasing': {'color': "#ef4444"}},
                        gauge={
                            'axis': {'range': [0, 100]}, 
                            'bar': {'color': "#6366f1"},
                            'steps': [
                                {'range': [0, 50], 'color': "rgba(34,197,94,0.12)"}, 
                                {'range': [50, 80], 'color': "rgba(245,158,11,0.12)"}, 
                                {'range': [80, 100], 'color': "rgba(239,68,68,0.12)"}
                            ],
                            'threshold': {'line': {'color': "#ef4444", 'width': 3}, 'thickness': 0.75, 'value': 90}
                        }
                    ))
                    fig_g.update_layout(template="plotly_dark", height=320, paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_g, use_container_width=True)

                with chart_col3:
                    fig_risk = go.Figure(go.Indicator(
                        mode="gauge+number", 
                        value=risk_sc,
                        title={'text': "Real-Time Risk Index"},
                        gauge={
                            'axis': {'range': [0, 100]}, 
                            'bar': {'color': STATUS_COLORS.get(r_label, '#6b7280')},
                            'steps': [
                                {'range': [0, 25], 'color': "rgba(16, 185, 129, 0.12)"}, 
                                {'range': [25, 50], 'color': "rgba(245, 158, 11, 0.12)"},
                                {'range': [50, 75], 'color': "rgba(249, 115, 22, 0.12)"}, 
                                {'range': [75, 100], 'color': "rgba(239, 68, 68, 0.12)"}
                            ]
                        }
                    ))
                    fig_risk.update_layout(template="plotly_dark", height=320, paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_risk, use_container_width=True)

                

                st.markdown("---")
                st.markdown("##### 💡 AI Real-Time Dispatch Recommendations")
                rec_col1, rec_col2 = st.columns([1.5, 1])

                with rec_col1:
                    for w in result['warnings']:
                        st.markdown(f'<div class="alert-critical">{w}</div>', unsafe_allow_html=True)
                    for r in result['recommendations']:
                        st.markdown(f'<div class="alert-ok">{r}</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="prediction-callout" style="margin-top:12px;">
                        📍 <b>Dynamic Ingestion Routing → Direct arrivals to Station {result['best_counter_for_new_customer']}</b>
                        <span style="color:#94a3b8; font-size:0.85em;"> (Lowest queue load)</span>
                    </div>
                    """, unsafe_allow_html=True)

                with rec_col2:
                    st.markdown("**🚶‍♂️‍➡️ Decision Tree Attribution:**")
                    reasons = []
                    busiest = result.get('busiest_counter', '-')
                    least = result.get('least_busy_counter', '-')
                    if busiest != least:
                        reasons.append(f"Station {busiest} exceeds balanced load baseline")
                        reasons.append(f"Station {least} has available servicing capacity")
                    if result.get('utilization_pct', 0) > 80:
                        reasons.append("Overall system utilization crossed 80% ceiling")
                    if result.get('average_wait_time', 0) > 15:
                        reasons.append("Average servicing delay above 15 min tolerance")
                    if not reasons:
                        reasons.append("Station loads are harmoniously balanced")
                    for reason in reasons:
                        st.markdown(f"• <span style='color:#c7d2fe;'>{reason}</span>", unsafe_allow_html=True)

                st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
                report_df = pd.DataFrame(counter_data)
                report_df['facility'] = facility
                report_df['status'] = result['status']
                report_df['risk_score'] = risk_sc
                report_df['recommendation'] = "; ".join(result['recommendations'])
                st.download_button("📥 Export Live Telemetry Report (CSV)", report_df.to_csv(index=False),
                                   f"queue_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")

    # ==================== TAB 2: AI FORECAST ====================
    with tab2:
        st.markdown("#### 🔮 Predictive Queue Forecasting & Surge Early Warning")
        st.markdown("ML-driven forward simulation to preempt bottlenecks before they occur.")

        nl_text, nl_minutes = generate_nl_prediction(predictor, current_hour, day_num, int(is_month_start), num_counters)
        nl_color = "#f87171" if nl_minutes else "#34d399"
        nl_icon = "⚠️" if nl_minutes else "✅"
        st.markdown(f"""
        <div class="prediction-callout" style="border-color:{nl_color}40; background:linear-gradient(135deg, {nl_color}14, {nl_color}05);">
            <span style="font-size:1.4em;">{nl_icon}</span>
            <span style="font-size:1.1em; color:{nl_color}; font-weight:700;"> {nl_text}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        mins = st.slider("⏰ Forward Prediction Horizon (Minutes):", 10, 120, 20, step=10)
        confidence = forecast_reliability(mins)

        future = predictor.predict_future(current_hour, day_num, int(is_month_start), mins, num_counters)

        st.markdown("##### 🚨 Neural Early Warning System")
        if 'CRITICAL' in future['alert_message']:
            st.markdown(f'<div class="alert-critical">{future["alert_message"]}</div>', unsafe_allow_html=True)
        elif 'WARNING' in future['alert_message']:
            st.markdown(f'<div class="alert-warning">{future["alert_message"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-ok">{future["alert_message"]}</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div style="text-align:right; margin-top:-10px; margin-bottom:10px;">
            <span style="color:#64748b; font-size:0.82em; font-weight:600;">Model Confidence: </span>
            <span style="color:#818cf8; font-weight:700; font-size:0.95em;">{confidence}%</span>
            <span style="color:#475569; font-size:0.75em;"> (Calculated across {mins}-min horizon)</span>
        </div>
        """, unsafe_allow_html=True)

        if future['predictions']:
            fdf = pd.DataFrame(future['predictions'])
            fc1, fc2 = st.columns(2)
            with fc1:
                fig1 = px.bar(fdf, x='counter', y='predicted_people',
                              title=f"Predicted Headcount ({mins} min ahead)",
                              color='predicted_people', color_continuous_scale='Reds', template='plotly_dark')
                fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig1, use_container_width=True)
            with fc2:
                fig2 = px.bar(fdf, x='counter', y='predicted_wait_min',
                              title=f"Predicted Wait Time ({mins} min ahead)",
                              color='predicted_wait_min', color_continuous_scale='Oranges', template='plotly_dark')
                fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig2, use_container_width=True)

        st.markdown("##### 📈 2-Hour Continuous Surge Curve")
        timeline = []
        for m in range(0, 130, 10):
            r = predictor.predict_future(current_hour, day_num, int(is_month_start), m, num_counters)
            if r['predictions']:
                timeline.append({'Minutes Ahead': m, 'Total People': r['total_predicted_people']})

        if timeline:
            tdf = pd.DataFrame(timeline)
            fig_tl = go.Figure()
            fig_tl.add_trace(go.Scatter(x=tdf['Minutes Ahead'], y=tdf['Total People'],
                                         mode='lines+markers', fill='tozeroy',
                                         fillcolor='rgba(99,102,241,0.12)',
                                         line=dict(color='#818cf8', width=3.5),
                                         marker=dict(size=8, color='#06b6d4', line=dict(color='#ffffff', width=1.5))))
            fig_tl.add_hline(y=12*num_counters, line_dash="dash", line_color="#ef4444",
                             annotation_text=f"⚠️ Maximum Capacity ({12*num_counters})")
            fig_tl.add_hline(y=30, line_dash="dot", line_color="#f59e0b",
                             annotation_text="🎯 Comfort Threshold (30 people)")
            fig_tl.update_layout(title="Continuous Queue Accumulation Trajectory", template="plotly_dark",
                                 xaxis_title="Minutes Ahead", yaxis_title="Predicted People",
                                 paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=380,
                                 xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                                 yaxis=dict(gridcolor='rgba(255,255,255,0.05)'))
            st.plotly_chart(fig_tl, use_container_width=True)

    # ==================== TAB 3: HISTORICAL ANALYTICS ====================
    with tab3:
        st.markdown("#### 📈 Historical Queue Analytics & Temporal Trends")

        csv_path = os.path.join(ROOT_DIR, 'data', 'historical_queue_data.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)

            day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
            day_avg = df.groupby('day_name')['people_in_queue'].mean().reset_index()
            day_avg['day_name'] = pd.Categorical(day_avg['day_name'], categories=day_order, ordered=True)
            day_avg = day_avg.sort_values('day_name')

            hour_avg = df.groupby('hour')['people_in_queue'].mean().reset_index()
            peak_hour = int(hour_avg.loc[hour_avg['people_in_queue'].idxmax(), 'hour'])
            peak_day = day_avg.loc[day_avg['people_in_queue'].idxmax(), 'day_name']
            busiest_counter = int(df.groupby('counter_id')['people_in_queue'].mean().idxmax())

            st.markdown(f"""
            <div class="prediction-callout">
                📊 <b>Temporal Pattern Insight:</b> Historical logs show maximum load surges occur at
                <span style="color:#f59e0b; font-weight:700;">{peak_hour}:00 on {peak_day}s</span>,
                with Station {busiest_counter} recording highest historical bottlenecks.
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")

            hc1, hc2 = st.columns(2)
            with hc1:
                fig_d = px.bar(day_avg, x='day_name', y='people_in_queue',
                               title="Average Queue Density by Weekday", color='people_in_queue',
                               color_continuous_scale='Purples', template='plotly_dark')
                fig_d.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_d, use_container_width=True)
            with hc2:
                fig_h = px.line(hour_avg, x='hour', y='people_in_queue',
                                title="Hourly Arrival Density Curve", markers=True, template='plotly_dark')
                fig_h.update_traces(line_color="#a78bfa", line_width=3)
                fig_h.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_h, use_container_width=True)

            st.markdown("##### 🗓️ Surge Heatmap: Weekday × Hour Matrix")
            pivot = df.pivot_table(values='people_in_queue', index='day_name',
                                   columns='hour', aggfunc='mean').reindex(day_order)
            fig_heat = px.imshow(pivot, title="Historical Congestion Intensity",
                                 color_continuous_scale='RdYlGn_r', template='plotly_dark')
            fig_heat.update_layout(paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_heat, use_container_width=True)

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Peak Weekday", peak_day)
            sc2.metric("Peak Rush Hour", f"{peak_hour}:00")
            sc3.metric("Historical Mean", f"{df['people_in_queue'].mean():.1f} ppl")
            sc4.metric("Max Surge Recorded", f"{df['people_in_queue'].max()} ppl")

            st.markdown("##### 🏢 Station Performance Metrics")
            counter_perf = df.groupby('counter_id').agg(
                avg_people=('people_in_queue', 'mean'),
                avg_wait=('estimated_wait_time_min', 'mean'),
                max_people=('people_in_queue', 'max')
            ).reset_index()
            cp1, cp2 = st.columns(2)
            with cp1:
                fig_cp = px.bar(counter_perf, x='counter_id', y='avg_people',
                                title="Average Occupancy per Counter", template='plotly_dark',
                                color='avg_people', color_continuous_scale='Blues')
                fig_cp.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_cp, use_container_width=True)
            with cp2:
                fig_cw = px.bar(counter_perf, x='counter_id', y='avg_wait',
                                title="Average Wait Duration per Counter (min)", template='plotly_dark',
                                color='avg_wait', color_continuous_scale='Oranges')
                fig_cw.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_cw, use_container_width=True)
        else:
            st.warning("⚠️ Historical training database not detected. Run simulated_data.py to generate telemetry records.")

    # ==================== TAB 4: WHAT-IF SIMULATOR ====================
    with tab4:
        st.markdown("#### 🎮 What-If Resource Allocation Sandbox")
        st.markdown("Simulate surge stress-tests and optimize counter staffing allocations dynamically.")

        if 'scenario' not in st.session_state:
            st.session_state.scenario = "normal"

        st.markdown("##### ⚡ Preconfigured Stress Scenarios")
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            if st.button("🍔 Peak Lunch Rush", use_container_width=True, type="primary"):
                st.session_state.scenario = "lunch"
        with sc2:
            if st.button("🚨 Emergency Crowd Surge", use_container_width=True, type="primary"):
                st.session_state.scenario = "server"
        with sc3:
            if st.button("👤 50% Staff Shortage", use_container_width=True, type="primary"):
                st.session_state.scenario = "staff"
        with sc4:
            if st.button("✅ Standard Operations", use_container_width=True):
                st.session_state.scenario = "normal"

        scenario = st.session_state.scenario
        scenario_config = {
            'lunch':  {'base': 25, 'label': '🍔 Peak Hour Rush (12-2 PM)', 'color': 'orange'},
            'server': {'base': 35, 'label': '🚨 Sudden Crowd Surge', 'color': 'red'},
            'staff':  {'base': 20, 'label': '👤 50% Staff Shortage', 'color': 'yellow'},
            'normal': {'base': 8,  'label': '✅ Standard Baseline Operations', 'color': 'green'}
        }
        cfg = scenario_config[scenario]
        st.info(f"**Current Sandbox Preset:** {cfg['label']}")

        st.markdown("---")
        st.markdown("##### 🎛️ Dynamic Parameter Calibration")

        sim_col1, sim_col2 = st.columns(2)
        with sim_col1:
            sim_counters = st.slider("Active Station Count", 1, 8, num_counters, key="sim_c")
            sim_speed = st.slider("Service Processing Speed Multiplier", 0.5, 2.0, 1.0, 0.1, key="sim_sp")
        with sim_col2:
            sim_staff = st.slider("Personnel per Station", 1, 5, 1, key="sim_st")
            sim_arrival = st.slider("Arrival Stream Multiplier", 0.5, 2.5, 1.0, 0.1, key="sim_ar")

        current_total = st.session_state.get('live_result', {}).get('total_people', cfg['base'] * num_counters)
        current_wait = st.session_state.get('live_result', {}).get('average_wait_time', cfg['base'] * 2)

        effective_capacity = sim_counters * 12 * sim_staff * sim_speed
        new_wait = max(1, round(current_wait * sim_arrival / max(0.5, sim_counters * sim_speed * sim_staff / num_counters), 1))
        new_queue = max(0, int(current_total * sim_arrival * num_counters / max(1, sim_counters * sim_staff * sim_speed)))
        wait_improvement = max(0, round((1 - new_wait / max(1, current_wait)) * 100))
        queue_improvement = max(0, round((1 - new_queue / max(1, current_total)) * 100))

        st.markdown("##### 📊 Projected Optimization Impact")
        ba1, ba2, ba3 = st.columns([1, 0.5, 1])

        with ba1:
            st.markdown(f"""
            <div class="impact-before">
                <div style="color:#f87171; font-size:0.82em; font-weight:700; letter-spacing:1px;">❌ CURRENT BOTTLENECK</div>
                <div style="font-size:2.5em; font-weight:800; color:#fca5a5; margin:8px 0;">{current_total}</div>
                <div style="color:#94a3b8; font-size:0.85em;">waiting in queue</div>
                <div style="font-size:1.6em; font-weight:700; color:#fca5a5; margin-top:10px;">{current_wait} min</div>
                <div style="color:#94a3b8; font-size:0.85em;">average service latency</div>
            </div>
            """, unsafe_allow_html=True)

        with ba2:
            st.markdown(f"""
            <div style="text-align:center; padding-top:35px;">
                <div style="font-size:2.5em; color:#818cf8;">➜</div>
                <div style="color:#34d399; font-weight:800; font-size:1.4em;">↓ {wait_improvement}%</div>
                <div style="color:#64748b; font-size:0.78em;">Latency Saved</div>
            </div>
            """, unsafe_allow_html=True)

        with ba3:
            st.markdown(f"""
            <div class="impact-after">
                <div style="color:#34d399; font-size:0.82em; font-weight:700; letter-spacing:1px;">✅ WITH OPTIMIZED DISPATCH</div>
                <div style="font-size:2.5em; font-weight:800; color:#6ee7b7; margin:8px 0;">{new_queue}</div>
                <div style="color:#94a3b8; font-size:0.85em;">waiting in queue</div>
                <div style="font-size:1.6em; font-weight:700; color:#6ee7b7; margin-top:10px;">{new_wait} min</div>
                <div style="color:#94a3b8; font-size:0.85em;">optimized turnaround</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("⚡ Execute Live 10-Minute Stress Test Simulation", type="primary"):
            prog = st.progress(0)
            status = st.empty()
            metrics_ph = st.empty()
            chart_ph = st.empty()
            rec_ph = st.empty()
            history = []
            initial_total = 0

            for step in range(1, 11):
                prog.progress(step * 10)
                status.text(f"Computing minute {step}/10 simulation step...")

                sim_data = []
                active_c = max(2, num_counters - (1 if scenario == 'staff' else 0))
                for c in range(1, active_c + 1):
                    base = cfg['base']
                    if scenario == 'server': base += step * 2
                    elif scenario == 'lunch': base += np.random.randint(0, 5)
                    p = max(0, int(np.random.poisson(base)))
                    w = max(1, int(p * np.random.uniform(1.5, 3.0)))
                    sim_data.append({'counter_id': c, 'people': p, 'wait_time': w})

                total = sum(c['people'] for c in sim_data)
                if step == 1: initial_total = total
                history.append({'Minute': step, 'Total People': total})

                with metrics_ph.container():
                    mc = st.columns(active_c)
                    for idx, cd in enumerate(sim_data):
                        cs = counter_status(cd['people'])
                        mc[idx].metric(f"Counter {cd['counter_id']}", f"{cd['people']} ppl", f"{cd['wait_time']}m")

                hdf = pd.DataFrame(history)
                fig_s = go.Figure()
                fig_s.add_trace(go.Scatter(x=hdf['Minute'], y=hdf['Total People'],
                                            mode='lines+markers', fill='tozeroy',
                                            fillcolor='rgba(239, 68, 68, 0.12)',
                                            line=dict(color='#f87171', width=3)))
                fig_s.add_hline(y=12*active_c, line_dash="dash", line_color="#ef4444", annotation_text="Threshold Bound")
                fig_s.update_layout(
                    title="Real-Time Stress Evolution", 
                    template="plotly_dark", 
                    height=300,
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                chart_ph.plotly_chart(fig_s, use_container_width=True)

                sim_result = engine.analyze_and_recommend(sim_data)
                with rec_ph.container():
                    for r in sim_result['recommendations'][:2]:
                        st.info(r)
                time.sleep(0.6)

            final_total = history[-1]['Total People'] if history else 0
            st.success(f"🎉 Stress Simulation Completed! Final stabilization level: {final_total} waiting visitors")
            st.balloons()

    # ==================== TAB 5: AI CHATBOT ====================
    with tab5:
        st.markdown("#### 💬 QAdapt Neural Operations Assistant")
        st.markdown("Real-time telemetry queries and dispatch optimization assistant.")

        if 'live_counter_data' in st.session_state and 'live_result' in st.session_state:
            chatbot.update_data(st.session_state['live_counter_data'], st.session_state['live_result'])

        st.markdown("---")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        st.markdown("##### ⚡ Rapid Diagnostic Inquiries:")
        qc1, qc2, qc3, qc4 = st.columns(4)
        quick_query = None
        with qc1:
            if st.button("🟢 Lowest queue load?", use_container_width=True): quick_query = "Where is the queue shortest?"
        with qc2:
            if st.button("⏱️ Current wait times?", use_container_width=True): quick_query = "What are the wait times?"
        with qc3:
            if st.button("📊 Facility overall health?", use_container_width=True): quick_query = "What is the overall status?"
        with qc4:
            if st.button("💡 Optimal station route?", use_container_width=True): quick_query = "Which is the best counter right now?"

        if quick_query:
            st.session_state.chat_history.append({"role": "user", "content": quick_query})
            response = chatbot.respond(quick_query)
            st.session_state.chat_history.append({"role": "assistant", "content": response})

        st.markdown("---")

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("💬 Type your question here...")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"): st.markdown(user_input)
            ai_response = chatbot.respond(user_input)
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"): st.markdown(ai_response)

        if st.session_state.chat_history:
            if st.button("🗑️ Clear Diagnostic History"):
                st.session_state.chat_history = []
                st.rerun()

# --- FOOTER ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align:center; padding: 15px 0;'>
        <p style='color:#64748b; font-size:0.85rem; margin:0;' class='shimmer-text'>
            🚶‍♂️‍➡️ QAdapt v3.5 · Advanced Neural Queue Intelligence & Automated Flow Balancing System
        </p>
        <p style='color:#475569; font-size:0.75rem; margin-top:4px;'>
            Python • Scikit-Learn • YOLOv8 • Streamlit • Plotly Engine • Built for Production Excellence 🏆
        </p>
    </div>
    """,
    unsafe_allow_html=True
)