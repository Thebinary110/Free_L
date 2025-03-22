import streamlit as st
import pandas as pd
import ast
import os

# Function to extract 'name' from JSON-like structures
def extract_name(value):
    if isinstance(value, str):
        try:
            value_dict = ast.literal_eval(value)
            return value_dict.get("name", value)
        except (SyntaxError, ValueError):
            return value
    return value

# Function to extract closing rank from JSON-like structures
def extract_closing_rank(value):
    if isinstance(value, str):
        try:
            value_dict = ast.literal_eval(value)
            return value_dict.get("closing_rank", None)
        except (SyntaxError, ValueError):
            return None
    return None

# Streamlit UI
st.title("NEET College Data Preprocessor")
st.write("Upload your NEET College Dataset (Excel) and get the cleaned file.")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    original_filename = uploaded_file.name  # Get the original filename with extension
    
    # Check if required columns exist
    if "institute" in df.columns:
        df["college_name"] = df["institute"].apply(extract_name)
    else:
        st.error("❌ Column 'institute' not found in the dataset!")
        st.stop()
    
    if "quota" in df.columns:
        df["quota_name"] = df["quota"].apply(extract_name)
    else:
        st.error("❌ Column 'quota' not found in the dataset!")
        st.stop()
    
    # Define round columns
    round_columns = ["cr_2022_1", "cr_2022_2", "cr_2023_1", "cr_2023_2", "cr_2023_3", "cr_2023_4"]
    
    for col in round_columns:
        if col in df.columns:
            df[col] = df[col].apply(extract_closing_rank)
        else:
            df[col] = None  # Create column if missing
    
    # Select relevant columns
    df_cleaned = df[["college_name", "state", "quota_name", "category"] + round_columns]
    
    # Handle missing values
    for col in round_columns:
        df_cleaned[col].fillna(df_cleaned[col].mean(), inplace=True)  # Fill missing ranks with mean
    df_cleaned["quota_name"].fillna(df_cleaned["quota_name"].mode()[0], inplace=True)  # Fill missing quota with mode
    df_cleaned["category"].fillna(df_cleaned["category"].mode()[0], inplace=True)  # Fill missing category with mode
    

    df_cleaned.to_excel(original_filename, index=False)
    
    st.success("✅ Data preprocessing complete!")
    st.download_button(label="Download Cleaned File", data=open(original_filename, "rb"), file_name=original_filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")