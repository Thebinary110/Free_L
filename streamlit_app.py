import streamlit as st
import pandas as pd
import json
import os

# Set page config
st.set_page_config(
    page_title="NEET College Explorer",
    page_icon="🏥",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 1.5rem;
    }
    .stSelectbox label, .stNumberInput label {
        font-weight: 500;
    }
    .stDataFrame {
        margin-top: 1rem;
    }
    .app-header {
        color: #3366cc;
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1.5rem;
        border-left: 4px solid #3366cc;
    }
    .filter-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .college-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .highlight {
        color: #3366cc;
        font-weight: bold;
    }
    .error-box {
        background-color: #ffe6e6;
        border-left: 4px solid #ff3333;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .debug-box {
        background-color: #f5f5f5;
        border: 1px solid #ddd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        font-family: monospace;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

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
data_dir_options = ["cleaned-data 2", "cleaned-data", "."]
for dir_option in data_dir_options:
    resolved_dir = resolve_path(dir_option)
    if os.path.exists(resolved_dir) and any(f.endswith('.xlsx') for f in os.listdir(resolved_dir)):
        DATA_DIR = resolved_dir
        break
else:
    # Default to the first option if nothing found
    DATA_DIR = data_dir_options[0]

st.sidebar.info(f"Using data from: {DATA_DIR}")

# Debug mode toggle
enable_debug = st.sidebar.checkbox("Enable Debug Mode", value=False)

# Function to load Excel data with error handling
@st.cache_data
def load_data(filename):
    try:
        file_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(file_path):
            if enable_debug:
                st.error(f"File not found: {file_path}")
            return pd.DataFrame()
        
        df = pd.read_excel(file_path)
        
        # Show column names in debug mode
        if enable_debug:
            st.write(f"Original columns in {filename}:", df.columns.tolist())
        
        return df
    except Exception as e:
        if enable_debug:
            st.error(f"Error loading {filename}: {str(e)}")
        return pd.DataFrame()

# Get list of Excel files in the directory
try:
    excel_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.xlsx')]
    if not excel_files:
        st.error(f"No Excel files found in {DATA_DIR}")
except Exception as e:
    st.error(f"Error accessing directory {DATA_DIR}: {str(e)}")
    excel_files = []

# App title and description
st.markdown('<div class="app-header">NEET College Data Explorer</div>', unsafe_allow_html=True)

st.markdown("""
<div class="info-box">
Explore NEET college cutoff data across different states and categories. Select a file to begin exploring the data.
</div>
""", unsafe_allow_html=True)

# Create a sidebar for file selection
st.sidebar.title("Select Data File")

# File selection
selected_file = st.sidebar.selectbox(
    "Choose Excel File",
    options=excel_files,
    index=0 if excel_files else None
)

if not selected_file:
    st.error(f"No Excel files found in {DATA_DIR}. Please check your data directory.")
    st.stop()

# Load the selected file
df = load_data(selected_file)

if df.empty:
    st.error(f"Could not load data from {selected_file}.")
    st.stop()

# Display column names for debugging
if enable_debug:
    st.markdown('<div class="debug-box">', unsafe_allow_html=True)
    st.write("Available columns:", df.columns.tolist())
    st.markdown('</div>', unsafe_allow_html=True)

# Create main filter container
st.sidebar.title("Filter Data")

# Get unique categories if the column exists
category_col = None
category_options = []

# Look for possible category columns
for col in df.columns:
    if 'categ' in str(col).lower():
        category_col = col
        category_options = sorted(df[col].dropna().unique().tolist())
        break

# Category selection
if category_col and category_options:
    all_categories_option = "All Categories"
    selected_category = st.sidebar.selectbox(
        f"Select {category_col}",
        options=[all_categories_option] + category_options,
        index=0
    )
else:
    selected_category = None
    if enable_debug:
        st.sidebar.warning("No category column found in the data.")

# Find round columns (columns that start with 'cr_')
round_cols = [col for col in df.columns if str(col).startswith('cr_')]

# Round selection
if round_cols:
    round_display_names = {
        col: col.replace('cr_', 'Round ').replace('_', ' ') 
        for col in round_cols
    }
    
    selected_round = st.sidebar.selectbox(
        "Select Round",
        options=round_cols,
        format_func=lambda x: round_display_names.get(x, x),
        index=len(round_cols)-1
    )
else:
    selected_round = None
    if enable_debug:
        st.sidebar.warning("No round columns found in the data.")

# Rank range filter only if we have a selected round
if selected_round and selected_round in df.columns:
    # Get min and max values in the column
    min_val = int(df[selected_round].min())
    max_val = int(df[selected_round].max())
    
    rank_range = st.sidebar.slider(
        "Cutoff Rank Range",
        min_value=min_val,
        max_value=max_val,
        value=(min_val, min(min_val + 5000, max_val))
    )
else:
    rank_range = (0, 100000)  # Default values

# College name search
college_name_cols = [col for col in df.columns if 'name' in str(col).lower() or 'college' in str(col).lower()]
if college_name_cols:
    college_name_col = college_name_cols[0]
    college_search = st.sidebar.text_input(f"Search by {college_name_col}")
else:
    college_name_col = None
    college_search = None
    if enable_debug:
        st.sidebar.warning("No college name column found in the data.")

# Apply filters
filtered_df = df.copy()

# Apply category filter if applicable
if selected_category and selected_category != "All Categories" and category_col:
    filtered_df = filtered_df[filtered_df[category_col] == selected_category]

# Apply round filter if applicable
if selected_round and selected_round in filtered_df.columns:
    # Filter by rank range
    filtered_df = filtered_df[(filtered_df[selected_round] >= rank_range[0]) & 
                              (filtered_df[selected_round] <= rank_range[1])]
    
    # Remove rows with empty values in the selected round
    filtered_df = filtered_df[filtered_df[selected_round].notna()]

# Apply college name search if applicable
if college_search and college_name_col:
    filtered_df = filtered_df[filtered_df[college_name_col].astype(str).str.contains(college_search, case=False)]

# Main content area with tabs
tab1, tab2 = st.tabs(["Data View", "Statistics"])

# Show data in the first tab
with tab1:
    # Show count of entries
    entries_count = len(filtered_df)
    st.markdown(f"### Found {entries_count} entries matching your criteria")
    
    # Display the data table
    if not filtered_df.empty:
        st.dataframe(filtered_df, use_container_width=True)
        
        # Download option
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"neet_data_{selected_file.replace('.xlsx', '')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No data found matching your criteria. Try adjusting the filters.")

# Show statistics in the second tab
with tab2:
    if not filtered_df.empty and selected_round and selected_round in filtered_df.columns:
        st.subheader("Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Number of Entries", len(filtered_df))
        with col2:
            if not filtered_df[selected_round].empty:
                st.metric("Average Cutoff Rank", int(filtered_df[selected_round].mean()))
        with col3:
            if not filtered_df[selected_round].empty:
                st.metric("Lowest Cutoff Rank", int(filtered_df[selected_round].min()))
        
        # Distribution of cutoff ranks
        st.subheader("Cutoff Rank Distribution")
        
        # Create histogram of cutoff ranks
        hist_values = filtered_df[selected_round].value_counts().sort_index()
        st.bar_chart(hist_values)
        
        # Top 10 colleges with lowest cutoffs
        st.subheader("Top 10 Entries (Lowest Cutoffs)")
        top_colleges = filtered_df.sort_values(by=selected_round).head(10)
        
        if college_name_col:
            st.table(top_colleges[[college_name_col, selected_round]])
        else:
            st.table(top_colleges[selected_round])
    else:
        st.info("No data available for statistics with the current filters.")

# Help guide at the bottom
with st.expander("How to use this app"):
    st.markdown("""
    ### Quick Guide:
    
    1. **Select a File**: Choose an Excel file from the dropdown menu
    2. **Apply Filters**: Use the sidebar filters to narrow down the data
    3. **View Data**: Browse the filtered data in the Data View tab
    4. **View Statistics**: Check the Statistics tab for insights
    5. **Download**: Use the download button to save the filtered data as CSV
    
    ### Troubleshooting:
    
    If you encounter issues:
    - Enable Debug Mode to see detailed information
    - Try selecting a different file
    - Check if the selected file has the expected columns
    - Reset your filters if you get no results
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
NEET College Data Explorer | Made with Streamlit | © 2023
</div>
""", unsafe_allow_html=True) 