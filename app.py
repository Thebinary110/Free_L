from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import numpy as np

app = Flask(__name__)

# Define separate paths for rank prediction and state datasets
rank_file_path = "./Corrected_Marks_vs_Rank.xlsx"  # Rank vs Marks file
state_data_path = "./cleaned_data"  # Folder where all state Excel files are stored

# Load the rank vs marks dataset
df_rank = pd.read_excel(rank_file_path)
df_rank = df_rank.sort_values(by="Marks").reset_index(drop=True)

# List of all Indian states
STATES_LIST = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"]

def predict_rank(marks, category):
    """Predicts NEET rank based on marks & category adjustments."""
    if marks < 0 or marks > 720:
        return 2000000  # Default worst rank for out-of-range marks

    predicted_rank = np.interp(marks, df_rank["Marks"], df_rank["Predicted Rank"])

    category_adjustment = {
        "open": 1.0,
        "ews": 1.1,
        "obc-ncl": 1.3,
        "sc": 1.6,
        "st": 1.9
    }
    predicted_rank *= category_adjustment.get(category, 1.0)
    return int(predicted_rank)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/colleges')
def colleges():
    return render_template('colleges.html')

@app.route('/predict', methods=['POST'])
def predict():
    """Predict rank based on marks and category."""
    data = request.json
    marks = int(data.get("marks"))
    category = data.get("category").lower()
    predicted_rank = predict_rank(marks, category)
    return jsonify({"predicted_rank": predicted_rank})

@app.route('/get_states', methods=['GET'])
def get_states():
    """Returns the list of Indian states."""
    return jsonify({"states": STATES_LIST})

@app.route('/get_categories', methods=['POST'])
def get_categories():
    """Returns unique categories based on selected state dataset."""
    data = request.json
    state = data.get("state")
    
    file_name = "./cleaned_data/all_india.xlsx" if state == "All India" else f"{state.replace(' ', '_').lower()}.xlsx"
    file_path = os.path.join(state_data_path, file_name)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "Dataset not found for selected state."}), 400
    
    df = pd.read_excel(file_path)
    unique_categories = df["category"].dropna().unique().tolist()
    return jsonify({"categories": unique_categories})

@app.route('/find_colleges', methods=['POST'])
def find_colleges():
    """Returns college names, states, and closing ranks based on user selection."""
    data = request.json
    state = data.get("state")
    category = data.get("category")
    round_num = data.get("round")
    rank = int(data.get("rank"))
    
    file_name = "all_india.xlsx" if state == "All India" else f"{state.replace(' ', '_').lower()}.xlsx"
    file_path = os.path.join(state_data_path, file_name)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "Dataset not found for selected state."}), 400
    
    df = pd.read_excel(file_path)
    round_column = f"cr_{round_num}"
    
    if round_column not in df.columns:
        return jsonify({"error": f"Column {round_column} not found in dataset."}), 400
    
    # Filtering the dataset based on rank, category, and round
    filtered_df = df[(df["category"].str.lower() == category) & (df[round_column] >= rank)]
    filtered_df = filtered_df.sort_values(by=round_column)
    
    result = filtered_df[["college_name", "state", round_column]].rename(columns={round_column: "closing_rank"}).to_dict(orient="records")
    return jsonify({"colleges": result})

if __name__ == '__main__':
    app.run(debug=True)
