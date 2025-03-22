from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import os
from enum import Enum

app = FastAPI(
    title="NEET College Explorer API",
    description="API for exploring NEET college cutoff data",
    version="1.0.0"
)

# Add CORS middleware to allow Streamlit to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Define path resolution function
def resolve_path(path):
    # Try current directory first
    if os.path.exists(path):
        return path
    
    # Try parent directory
    parent_path = os.path.join("..", path)
    if os.path.exists(parent_path):
        return parent_path
    
    # Try absolute path as last resort
    abs_path = os.path.abspath(path)
    if os.path.exists(abs_path):
        return abs_path
    
    # Return original path if all else fails
    return path

# Define data directory with resolution
data_dir_options = ["./cleaned_data", "cleaned-data", "."]
for dir_option in data_dir_options:
    resolved_dir = resolve_path(dir_option)
    if os.path.exists(resolved_dir) and any(f.endswith('.xlsx') for f in os.listdir(resolved_dir)):
        DATA_DIR = resolved_dir
        break
else:
    # Default to the first option if nothing found
    DATA_DIR = data_dir_options[0]

# Cache for loaded dataframes
dataframe_cache = {}

def load_data(filename):
    """Load Excel data with caching"""
    if filename in dataframe_cache:
        return dataframe_cache[filename]
    
    try:
        file_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(file_path):
            return None
        
        df = pd.read_excel(file_path)
        dataframe_cache[filename] = df
        return df
    except Exception as e:
        print(f"Error loading {filename}: {str(e)}")
        return None

# Models
class FileInfo(BaseModel):
    filename: str
    columns: List[str]

class DataResponse(BaseModel):
    data: List[Dict[str, Any]]
    total_count: int

class StatisticsResponse(BaseModel):
    count: int
    average_cutoff: Optional[float] = None
    lowest_cutoff: Optional[float] = None
    distribution: Dict[str, int]
    top_entries: List[Dict[str, Any]]

# Routes
@app.get("/")
async def root():
    return {"message": "Welcome to NEET College Explorer API"}

@app.get("/files", response_model=List[str])
async def get_files():
    """Get list of available Excel files"""
    try:
        excel_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.xlsx')]
        return excel_files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accessing directory: {str(e)}")

@app.get("/files/{filename}/info", response_model=FileInfo)
async def get_file_info(filename: str):
    """Get information about a specific Excel file"""
    df = load_data(filename)
    if df is None:
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    
    return {
        "filename": filename,
        "columns": df.columns.tolist()
    }

@app.get("/files/{filename}/categories")
async def get_categories(filename: str):
    """Get unique categories from a file"""
    df = load_data(filename)
    if df is None:
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    
    # Look for possible category columns
    category_col = None
    for col in df.columns:
        if 'categ' in str(col).lower():
            category_col = col
            break
    
    if category_col:
        categories = sorted(df[category_col].dropna().unique().tolist())
        return {
            "category_column": category_col,
            "categories": categories
        }
    else:
        return {
            "category_column": None,
            "categories": []
        }

@app.get("/files/{filename}/rounds")
async def get_rounds(filename: str):
    """Get available rounds from a file"""
    df = load_data(filename)
    if df is None:
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    
    # Find round columns (columns that start with 'cr_')
    round_cols = [col for col in df.columns if str(col).startswith('cr_')]
    
    round_display_names = {
        col: col.replace('cr_', 'Round ').replace('_', ' ') 
        for col in round_cols
    }
    
    return {
        "round_columns": round_cols,
        "display_names": round_display_names
    }

@app.get("/files/{filename}/data", response_model=DataResponse)
async def get_data(
    filename: str,
    category: Optional[str] = None,
    round_col: Optional[str] = None,
    min_rank: Optional[int] = None,
    max_rank: Optional[int] = None,
    college_search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000)
):
    """Get filtered data from a file"""
    df = load_data(filename)
    if df is None:
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    
    filtered_df = df.copy()
    
    # Apply category filter if applicable
    if category and category != "All Categories":
        # Find category column
        category_col = None
        for col in df.columns:
            if 'categ' in str(col).lower():
                category_col = col
                break
        
        if category_col:
            filtered_df = filtered_df[filtered_df[category_col] == category]
    
    # Apply round filter if applicable
    if round_col and round_col in filtered_df.columns:
        # Filter by rank range
        if min_rank is not None:
            filtered_df = filtered_df[filtered_df[round_col] >= min_rank]
        
        if max_rank is not None:
            filtered_df = filtered_df[filtered_df[round_col] <= max_rank]
        
        # Remove rows with empty values in the selected round
        filtered_df = filtered_df[filtered_df[round_col].notna()]
    
    # Apply college name search if applicable
    if college_search:
        # Find college name column
        college_name_cols = [col for col in df.columns if 'name' in str(col).lower() or 'college' in str(col).lower()]
        if college_name_cols:
            college_name_col = college_name_cols[0]
            filtered_df = filtered_df[filtered_df[college_name_col].astype(str).str.contains(college_search, case=False)]
    
    # Calculate total count before pagination
    total_count = len(filtered_df)
    
    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_df = filtered_df.iloc[start_idx:end_idx]
    
    # Convert to list of dictionaries
    data = paginated_df.fillna("").to_dict(orient="records")
    
    return {
        "data": data,
        "total_count": total_count
    }

@app.get("/files/{filename}/statistics", response_model=StatisticsResponse)
async def get_statistics(
    filename: str,
    category: Optional[str] = None,
    round_col: Optional[str] = None,
    min_rank: Optional[int] = None,
    max_rank: Optional[int] = None,
    college_search: Optional[str] = None
):
    """Get statistics for filtered data"""
    df = load_data(filename)
    if df is None:
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    
    filtered_df = df.copy()
    
    # Apply category filter if applicable
    if category and category != "All Categories":
        # Find category column
        category_col = None
        for col in df.columns:
            if 'categ' in str(col).lower():
                category_col = col
                break
        
        if category_col:
            filtered_df = filtered_df[filtered_df[category_col] == category]
    
    # Apply round filter if applicable
    if round_col and round_col in filtered_df.columns:
        # Filter by rank range
        if min_rank is not None:
            filtered_df = filtered_df[filtered_df[round_col] >= min_rank]
        
        if max_rank is not None:
            filtered_df = filtered_df[filtered_df[round_col] <= max_rank]
        
        # Remove rows with empty values in the selected round
        filtered_df = filtered_df[filtered_df[round_col].notna()]
    
    # Apply college name search if applicable
    if college_search:
        # Find college name column
        college_name_cols = [col for col in df.columns if 'name' in str(col).lower() or 'college' in str(col).lower()]
        if college_name_cols:
            college_name_col = college_name_cols[0]
            filtered_df = filtered_df[filtered_df[college_name_col].astype(str).str.contains(college_search, case=False)]
    
    # Calculate statistics
    count = len(filtered_df)
    average_cutoff = None
    lowest_cutoff = None
    distribution = {}
    top_entries = []
    
    if count > 0 and round_col and round_col in filtered_df.columns:
        # Calculate average and lowest cutoff
        average_cutoff = float(filtered_df[round_col].mean())
        lowest_cutoff = float(filtered_df[round_col].min())
        
        # Calculate distribution
        hist_values = filtered_df[round_col].value_counts().sort_index()
        distribution = {str(k): int(v) for k, v in hist_values.items()}
        
        # Get top 10 entries with lowest cutoffs
        top_df = filtered_df.sort_values(by=round_col).head(10)
        
        # Find college name column
        college_name_col = None
        college_name_cols = [col for col in df.columns if 'name' in str(col).lower() or 'college' in str(col).lower()]
        if college_name_cols:
            college_name_col = college_name_cols[0]
        
        if college_name_col:
            top_entries = top_df[[college_name_col, round_col]].fillna("").to_dict(orient="records")
        else:
            top_entries = top_df[[round_col]].fillna("").to_dict(orient="records")
    
    return {
        "count": count,
        "average_cutoff": average_cutoff,
        "lowest_cutoff": lowest_cutoff,
        "distribution": distribution,
        "top_entries": top_entries
    }

@app.get("/files/{filename}/range/{round_col}")
async def get_rank_range(filename: str, round_col: str):
    """Get min and max rank values for a specific round"""
    df = load_data(filename)
    if df is None:
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    
    if round_col not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column {round_col} not found in file")
    
    # Get min and max values
    min_val = int(df[round_col].min())
    max_val = int(df[round_col].max())
    
    return {
        "min_rank": min_val,
        "max_rank": max_val
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
