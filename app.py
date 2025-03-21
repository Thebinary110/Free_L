from flask import Flask, render_template, request, jsonify
import os
import json
import pandas as pd
import numpy as np

app = Flask(__name__)

data_dir = "data"  # Folder containing JSON state files
rank_file = "Corrected_Marks_vs_Rank.xlsx"  # Corrected rank prediction file

def load_state_data(state_name):
    """Load JSON data for a specific state."""
    filename = f"state={state_name.lower().replace(' ', '_')}.json"
    filepath = os.path.join(data_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"⚠️ State data file not found: {filepath}")
    return None

# Load the corrected rank dataset
df_rank = pd.read_excel(rank_file)
df_rank = df_rank.sort_values(by="Marks").reset_index(drop=True)

def predict_rank(marks, category):
    """Predicts NEET rank based on marks & category adjustments."""
    if marks < 0 or marks > 720:
        return 2000000  # Default worst rank for out-of-range marks

    # Interpolate rank based on marks
    predicted_rank = np.interp(marks, df_rank["Marks"], df_rank["Predicted Rank"])

    # Adjust rank based on category
    category_adjustment = {
        "open": 1.0,
        "ews": 1.1,
        "obc-ncl": 1.3,
        "sc": 1.6,
        "st": 1.9
    }
    predicted_rank *= category_adjustment.get(category, 1.0)
    
    print(f"✅ Marks: {marks}, Category: {category}, Predicted Rank: {int(predicted_rank)}")
    return int(predicted_rank)

@app.route('/')
def index():
    """Render the index.html page (Rank Predictor)."""
    return render_template('index.html')

@app.route('/colleges')
def colleges():
    """Render the colleges.html page (College Predictor)."""
    return render_template('colleges.html')

@app.route('/predict', methods=['POST'])
def predict():
    """Predict rank based on marks and category."""
    data = request.json
    print("Received Data:", data)  # Debugging

    marks = int(data.get("marks"))
    category = data.get("category").lower()

    predicted_rank = predict_rank(marks, category)
    print(f"Predicted Rank: {predicted_rank}")

    return jsonify({"predicted_rank": predicted_rank})

@app.route('/find_colleges', methods=['POST'])
def find_colleges():
    """Find matching colleges based on predicted rank and filters."""
    data = request.json
    print("🟡 DEBUG: Received Data for College Search ->", data)  # Debugging Output

    # Ensure required fields exist in the request
    required_fields = ["rank", "category", "quota", "state", "round"]
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    try:
        rank = int(data["rank"])
        category = data["category"].lower()
        quota = data["quota"].lower()
        state = data["state"].lower()
        round_num = str(data["round"])  # Ensure it's a string for matching JSON keys
    except Exception as e:
        return jsonify({"error": f"Invalid input data: {str(e)}"}), 400

    state_data = load_state_data(state)
    if not state_data:
        return jsonify({"error": f"State data not found for {state}"}), 400

    matching_colleges = []
    for record in state_data.get("records", []):
        if record.get("category", "").lower() == category and record.get("quota", "").lower() == quota:
            round_key = f"cr_2024_round{round_num}"
            if round_key in record:
                closing_rank = record[round_key].get("closing_rank", None)
                if closing_rank is not None and rank <= closing_rank:
                    matching_colleges.append({
                        "name": record["institute"]["name"],
                        "location": record["institute"].get("location", "Unknown"),
                        "closing_rank": closing_rank,
                        "quota": quota,
                        "round": round_num
                    })

    matching_colleges.sort(key=lambda x: x["closing_rank"])
    print("🟢 DEBUG: Matching Colleges Found ->", matching_colleges[:10])  

    return jsonify({"colleges": matching_colleges[:10]})



if __name__ == '__main__':
    print("🚀 Flask server is running! Open http://127.0.0.1:5000 in your browser.")
    app.run(debug=True)
