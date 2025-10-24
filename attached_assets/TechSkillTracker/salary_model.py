import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import joblib
import os

MODEL_PATH = "models/salary_predictor_model.pkl"

def train_salary_predictor(df):
    """Trains a salary prediction model and saves it."""
    # Prepare data: Drop rows with missing salary or experience
    df_cleaned = df.dropna(subset=["Salary (in LPA)", "Experience Required (in years)", "Location", "Tech Skill"]).copy()

    if df_cleaned.empty:
        print("Not enough data to train salary predictor after cleaning.")
        return None

    # Feature Engineering (simplified for demonstration)
    # Encode categorical features
    for col in ["Location", "Tech Skill", "Job Title"]:
        if col in df_cleaned.columns:
            df_cleaned[col] = df_cleaned[col].astype(str) # Ensure string type
            le = LabelEncoder()
            df_cleaned[f"{col}_encoded"] = le.fit_transform(df_cleaned[col])
            joblib.dump(le, f"models/{col}_label_encoder.pkl") # Save encoder

    features = ["Experience Required (in years)", "Location_encoded", "Tech Skill_encoded"]
    # Add Job Title if it was encoded
    if "Job Title_encoded" in df_cleaned.columns:
        features.append("Job Title_encoded")

    # Ensure all features exist in the dataframe
    for feature in features:
        if feature not in df_cleaned.columns:
            print(f"Missing feature for training: {feature}")
            return None

    X = df_cleaned[features]
    y = df_cleaned["Salary (in LPA)"]

    if len(X) < 2 or len(y.unique()) < 2: # Need at least 2 samples and 2 unique target values
        print("Not enough diverse data to train salary predictor.")
        return None

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate (optional)
    score = model.score(X_test, y_test)
    print(f"Salary Predictor R^2 Score: {score:.2f}")

    joblib.dump(model, MODEL_PATH)
    print(f"Salary predictor model saved to {MODEL_PATH}")
    return model

def load_salary_predictor():
    """Loads the pre-trained salary prediction model."""
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

def predict_salary(model, data):
    """Predicts salary based on input data."""
    if model:
        # Load encoders
        encoded_data = {}
        for col in ["Location", "Tech Skill", "Job Title"]:
            encoder_path = f"models/{col}_label_encoder.pkl"
            if os.path.exists(encoder_path):
                le = joblib.load(encoder_path)
                # Handle unseen labels by mapping to a default or ignoring
                try:
                    encoded_data[f"{col}_encoded"] = le.transform([data[col]])[0]
                except ValueError:
                    encoded_data[f"{col}_encoded"] = -1 # Or some other default for unseen
            else:
                print(f"Warning: Label encoder for {col} not found.")
                encoded_data[f"{col}_encoded"] = 0 # Default if encoder missing

        input_df = pd.DataFrame([{
            "Experience Required (in years)": data["Experience Required (in years)"],
            "Location_encoded": encoded_data["Location_encoded"],
            "Tech Skill_encoded": encoded_data["Tech Skill_encoded"],
            "Job Title_encoded": encoded_data.get("Job Title_encoded", 0) # Use .get for optional
        }])
        
        # Ensure columns match training data
        # This is a simplified check; a robust solution would handle missing features
        expected_features = model.feature_names_in_ if hasattr(model, 'feature_names_in_') else []
        for feature in expected_features:
            if feature not in input_df.columns:
                input_df[feature] = 0 # Add missing features with default value
        input_df = input_df[expected_features] # Reorder columns

        return model.predict(input_df)[0]
    return None

if __name__ == "__main__":
    # Example usage for testing
    sample_data = {
        "Job Title": ["Data Scientist", "Software Engineer", "DevOps Engineer", "Data Analyst"],
        "Tech Skill": ["Python", "Java", "AWS", "SQL"],
        "Location": ["Bengaluru", "Hyderabad", "Mumbai", "Chennai"],
        "Salary (in LPA)": [15, 12, 10, 8],
        "Experience Required (in years)": [3, 2, 4, 1]
    }
    sample_df = pd.DataFrame(sample_data)
    
    trained_model = train_salary_predictor(sample_df)
    
    if trained_model:
        test_data = {
            "Job Title": "Data Scientist",
            "Tech Skill": "Python",
            "Location": "Bengaluru",
            "Experience Required (in years)": 4
        }
        predicted_salary = predict_salary(trained_model, test_data)
        print(f"Predicted Salary for Data Scientist in Bengaluru with 4 years experience: {predicted_salary:.2f} LPA")

        test_data_unseen = {
            "Job Title": "New Role", # Unseen job title
            "Tech Skill": "Rust", # Unseen tech skill
            "Location": "Delhi", # Unseen location
            "Experience Required (in years)": 5
        }
        predicted_salary_unseen = predict_salary(trained_model, test_data_unseen)
        print(f"Predicted Salary for unseen data: {predicted_salary_unseen:.2f} LPA")


