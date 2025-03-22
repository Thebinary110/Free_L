# app.py - Main FastAPI application
import os
import pandas as pd
from fastapi import FastAPI, Query, HTTPException
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import json
from pathlib import Path
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
import streamlit as st

app = FastAPI(title="NEET Counseling Data API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to data files
DATA_DIR = Path("cleaned-data 2")
METADATA_FILE = Path("metadata.json")

# Models
class FileMetadata(BaseModel):
    filename: str
    state: str
    columns: List[str]
    rounds: List[str]
    quotas: List[str]
    categories: List[str]

class CounselingQuery(BaseModel):
    state: str
    quota: Optional[str] = None
    category: Optional[str] = None
    round: Optional[str] = None
    rank: Optional[int] = None

# Cache for DataFrames
df_cache = {}

def extract_state_name(filename: str) -> str:
    """Extract state name from filename."""
    parts = filename.split('_')
    if len(parts) >= 4:
        return parts[3].replace('.xlsx', '')
    return "unknown"

def identify_college_name_column(df: pd.DataFrame) -> str:
    """Identify the column that contains college names."""
    possible_columns = ['college_name', 'name', 'institute', 'college', 'institution']
    for col in possible_columns:
        if col in df.columns:
            return col
    
    # If none of the expected columns are found, use the first column
    # that's not a round, quota, or category
    for col in df.columns:
        if not col.startswith('cr_') and col not in ['quota', 'category', 'state']:
            return col
    
    # Fallback to the first column
    return df.columns[0] if not df.empty else None

def load_and_analyze_file(file_path: Path) -> Dict:
    """Load Excel file and analyze its structure."""
    # Read first row to get column structure
    df_head = pd.read_excel(file_path, nrows=1)
    columns = df_head.columns.tolist()
    
    # Load full data for quota and category extraction
    df = pd.read_excel(file_path)
    
    # Extract rounds (columns starting with 'cr_')
    rounds = [col for col in columns if col.startswith('cr_')]
    
    # Extract quotas and categories (assuming these columns exist)
    quotas = []
    categories = []
    
    if 'quota' in columns:
        quotas = df['quota'].dropna().unique().tolist()
    
    if 'category' in columns:
        categories = df['category'].dropna().unique().tolist()
    
    state = extract_state_name(file_path.name)
    
    # Identify college name column
    college_name_col = identify_college_name_column(df)
    
    # Store dataframe in cache
    df_cache[file_path.name] = df
    
    return {
        "filename": file_path.name,
        "state": state,
        "columns": columns,
        "rounds": rounds,
        "quotas": quotas,
        "categories": categories,
        "college_name_column": college_name_col
    }

def analyze_all_files() -> List[Dict]:
    """Analyze all Excel files in the data directory."""
    metadata = []
    for file in DATA_DIR.glob("*.xlsx"):
        try:
            file_metadata = load_and_analyze_file(file)
            metadata.append(file_metadata)
        except Exception as e:
            print(f"Error analyzing {file}: {e}")
    
    # Save metadata to file for faster startup
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)
    
    return metadata

def get_metadata() -> List[Dict]:
    """Get or create metadata for all files."""
    if METADATA_FILE.exists():
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    else:
        return analyze_all_files()

# Initialize metadata on startup
@app.on_event("startup")
async def startup_event():
    global file_metadata
    file_metadata = get_metadata()

# API Endpoints
@app.get("/states", response_model=List[str])
def get_states():
    """Get all available states."""
    return sorted(list(set(meta["state"] for meta in file_metadata)))

@app.get("/state/{state}/metadata")
def get_state_metadata(state: str):
    """Get metadata for a specific state."""
    for meta in file_metadata:
        if meta["state"] == state:
            return meta
    raise HTTPException(status_code=404, detail=f"State {state} not found")

@app.get("/state/{state}/quotas")
def get_quotas(state: str):
    """Get available quotas for a state."""
    for meta in file_metadata:
        if meta["state"] == state:
            return meta["quotas"]
    raise HTTPException(status_code=404, detail=f"State {state} not found")

@app.get("/state/{state}/categories")
def get_categories(state: str):
    """Get available categories for a state."""
    for meta in file_metadata:
        if meta["state"] == state:
            return meta["categories"]
    raise HTTPException(status_code=404, detail=f"State {state} not found")

@app.get("/state/{state}/rounds")
def get_rounds(state: str):
    """Get available rounds for a state."""
    for meta in file_metadata:
        if meta["state"] == state:
            return meta["rounds"]
    raise HTTPException(status_code=404, detail=f"State {state} not found")

@app.post("/query")
def query_colleges(query: CounselingQuery):
    """Query colleges based on dynamic parameters."""
    # Find the right file
    filename = None
    college_name_col = None
    
    for meta in file_metadata:
        if meta["state"] == query.state:
            filename = meta["filename"]
            college_name_col = meta.get("college_name_column")
            break
    
    if not filename:
        raise HTTPException(status_code=404, detail=f"State {query.state} not found")
    
    # Get DataFrame from cache or load it
    if filename not in df_cache:
        file_path = DATA_DIR / filename
        df_cache[filename] = pd.read_excel(file_path)
    
    df = df_cache[filename].copy()
    
    # If college_name_col is not in metadata, identify it
    if not college_name_col:
        college_name_col = identify_college_name_column(df)
    
    # Apply filters based on query parameters
    if query.quota:
        df = df[df['quota'] == query.quota]
    
    if query.category:
        df = df[df['category'] == query.category]
    
    if query.round and query.round in df.columns:
        # Filter out rows where the round column is null
        df = df[df[query.round].notna()]
        
        # If rank is provided, filter colleges where rank is higher than the cutoff
        if query.rank:
            df = df[df[query.round] >= query.rank]
    
    # Rename college name column for consistency in the API response
    if college_name_col and college_name_col != 'college_name' and college_name_col in df.columns:
        df = df.rename(columns={college_name_col: 'college_name'})
    
    # Return results
    return {
        "total": len(df),
        "colleges": df.to_dict(orient='records')
    }

# Endpoint to force refresh metadata
@app.post("/refresh-metadata")
def refresh_metadata():
    """Force refresh of file metadata."""
    global file_metadata
    file_metadata = analyze_all_files()
    # Clear cache
    df_cache.clear()
    return {"status": "success", "message": "Metadata refreshed"}

# Set page config
st.set_page_config(
    page_title="NEET College Data Explorer",
    page_icon="🏥",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stSelectbox label, .stSlider label {
        font-weight: bold;
    }
    .stDataFrame {
        margin-top: 1rem;
    }
    .st-emotion-cache-16txtl3 h1 {
        margin-bottom: 1.5rem;
    }
    .info-box {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Load metadata
with open("metadata.json", "r") as f:
    metadata = json.load(f)

# Title and description
st.title("NEET College Data Explorer")
st.markdown("""
<div class="info-box">
Explore NEET cutoff ranks across different medical colleges in India. Use the filters below to select your preferred state, category, and admission round.
</div>
""", unsafe_allow_html=True)

# Create columns for the main filters
col1, col2, col3 = st.columns(3)

# Get unique states from metadata
states = [item["state"] for item in metadata]
states = sorted(list(set(states)))
state_display = {state: state.replace("_", " ").title() for state in states}

# State selection
with col1:
    selected_state = st.selectbox(
        "Select State",
        options=["All States"] + states,
        index=0,
        format_func=lambda x: "All States" if x == "All States" else state_display.get(x, x)
    )

# Find the selected state metadata
if selected_state == "All States":
    selected_metadata = next((item for item in metadata if item["state"] == "all"), metadata[0])
else:
    selected_metadata = next((item for item in metadata if item["state"] == selected_state), None)

# Get categories for the selected state
categories = selected_metadata["categories"]

# Category selection
with col2:
    selected_category = st.selectbox(
        "Select Category",
        options=["All Categories"] + categories,
        index=0
    )

# Get rounds for the selected state
rounds = selected_metadata["rounds"]
round_display_names = {
    "cr_2022_1": "2022 Round 1",
    "cr_2022_2": "2022 Round 2",
    "cr_2023_1": "2023 Round 1",
    "cr_2023_2": "2023 Round 2",
    "cr_2023_3": "2023 Round 3",
    "cr_2023_4": "2023 Round 4"
}

# Round selection
with col3:
    selected_round = st.selectbox(
        "Select Round",
        options=rounds,
        format_func=lambda x: round_display_names.get(x, x),
        index=len(rounds)-1  # Select the latest round by default
    )

# Function to load Excel data
@st.cache_data
def load_data(filename):
    try:
        return pd.read_excel(filename)
    except FileNotFoundError:
        st.error(f"File not found: {filename}")
        return pd.DataFrame()

# Additional filters in an expander
with st.expander("Advanced Filters"):
    # Rank range filter
    min_rank, max_rank = 1, 100000
    rank_range = st.slider(
        "Cutoff Rank Range",
        min_value=min_rank,
        max_value=max_rank,
        value=(min_rank, max_rank)
    )
    
    # Search by college name
    college_search = st.text_input("Search by College Name")

# Load and display data
try:
    filename = selected_metadata["filename"]
    df = load_data(filename)
    
    # Apply basic filters
    if selected_category != "All Categories":
        df = df[df["category"] == selected_category]
    
    # Filter by rank range
    df = df[(df[selected_round] >= rank_range[0]) & (df[selected_round] <= rank_range[1])]
    
    # Filter by college name search
    if college_search:
        df = df[df["college_name"].str.contains(college_search, case=False)]
    
    # Select columns to display
    display_columns = ["college_name", "state", "quota_name", "category", selected_round]
    
    # Filter out rows with empty selected_round values
    df_filtered = df[df[selected_round].notna()]
    
    # Sort by selected round (ascending)
    df_filtered = df_filtered.sort_values(by=selected_round)
    
    # Show the data
    if not df_filtered.empty:
        # Stats
        st.subheader("Statistics")
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        with stat_col1:
            st.metric("Number of Colleges", df_filtered["college_name"].nunique())
        with stat_col2:
            if not df_filtered[selected_round].empty:
                st.metric("Average Cutoff Rank", int(df_filtered[selected_round].mean()))
        with stat_col3:
            if not df_filtered[selected_round].empty:
                st.metric("Lowest Cutoff Rank", int(df_filtered[selected_round].min()))
        
        # Table
        st.subheader(f"Cutoff Data for {state_display.get(selected_state, selected_state)} - {round_display_names.get(selected_round, selected_round)}")
        
        # Format the dataframe for display
        display_df = df_filtered[display_columns].copy()
        display_df = display_df.rename(columns={
            "college_name": "College Name",
            "state": "State",
            "quota_name": "Quota",
            "category": "Category",
            selected_round: f"Cutoff Rank ({round_display_names.get(selected_round, selected_round)})"
        })
        
        st.dataframe(display_df, use_container_width=True)
        
    else:
        st.info("No data available for the selected filters. Please adjust your selection.")
except Exception as e:
    st.error(f"Error loading data: {e}")

# Download section
st.sidebar.title("Download Options")

if 'df_filtered' in locals() and not df_filtered.empty:
    csv = df_filtered.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name=f"neet_data_{selected_state}_{selected_round}.csv",
        mime="text/csv",
    )

# Information section in sidebar
st.sidebar.title("About")
st.sidebar.info("""
This app provides data for NEET college cutoffs across different states in India.

**Data includes:**
- College names
- Categories (Open, SC, ST, OBC, etc.)
- Cutoff ranks for different rounds

**Note:** Cutoff ranks are from official counseling data from 2022-2023 sessions.
""")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
NEET College Data Explorer | Made with Streamlit | © 2023
</div>
""", unsafe_allow_html=True)

# Run with: uvicorn app:app --reload 