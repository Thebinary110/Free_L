import json
import pandas as pd
import os


json_file = "./data/state=bihar.json"
save_path = r"C:\Users\Dell\Desktop\data_company\NEET_College_Data1.xlsx"

with open(json_file, "r", encoding="utf-8") as file:
    data = json.load(file)


records = data.get("records") or data.get("colleges") or data.get("data")


if records and isinstance(records, list) and len(records) > 0:
    df = pd.DataFrame(records)
    
  
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

   
    df.to_excel(save_path, index=False, engine="openpyxl")
    print(f"Excel file saved successfully at: {save_path}")
else:
    print("No valid records found in the JSON file.")
