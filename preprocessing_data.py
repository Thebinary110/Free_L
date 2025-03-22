import pandas as pd
import ast


file_path = "./data_company/NEET_College_Data_gujrat.xlsx" 


def extract_name(value):
    if isinstance(value, str):
        try:
            value_dict = ast.literal_eval(value)
            return value_dict.get("name", value)
        except (SyntaxError, ValueError):
            return value
    return value


df["college_name"] = df["institute"].apply(extract_name)
df["quota_name"] = df["quota"].apply(extract_name)

def extract_closing_rank(value):
    if isinstance(value, str):
        try:
            value_dict = ast.literal_eval(value)
            return value_dict.get("closing_rank", None)
        except (SyntaxError, ValueError):
            return None
    return None


round_columns = ["cr_2022_1", "cr_2022_2", "cr_2023_1", "cr_2023_2", "cr_2023_3", "cr_2023_4"]
for col in round_columns:
    df[col] = df[col].apply(extract_closing_rank)


df_cleaned = df[["college_name", "state", "quota_name", "category"] + round_columns]


for col in round_columns:
    df_cleaned[col].fillna(df_cleaned[col].mean(), inplace=True)  

df_cleaned["quota_name"].fillna(df_cleaned["quota_name"].mode()[0], inplace=True) 
df_cleaned["category"].fillna(df_cleaned["category"].mode()[0], inplace=True) 


save_path = "./cleaned_data/cleaned_data_gujrat.xlsx" 
df_cleaned.to_excel(save_path, index=False)

print(f"Data cleaning complete. File saved at: {save_path}")