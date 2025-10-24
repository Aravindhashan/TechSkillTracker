import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib
import os

MODEL_PATH = "models/job_classifier_model.pkl"

def train_job_classifier(df):
    """Trains a job role classifier and saves the model."""
    # For simplicity, let's assume 'Job Title' is our target variable
    # and we'll use 'Job Title' itself as features for now, or a combination
    # In a real scenario, you'd use job descriptions.
    
    # Create a simplified 'Job Role' for classification
    # This is a placeholder for more sophisticated NLP-based classification
    def categorize_job_title(title):
        title = str(title).lower()
        if "data scientist" in title or "ml engineer" in title or "machine learning" in title:
            return "Data Science/ML"
        elif "full stack" in title or "backend" in title or "frontend" in title or "developer" in title or "engineer" in title:
            return "Software Development"
        elif "devops" in title or "cloud" in title:
            return "DevOps/Cloud"
        elif "qa" in title or "tester" in title:
            return "QA/Testing"
        elif "manager" in title or "lead" in title:
            return "Management"
        else:
            return "Other"

    df["Job Role Category"] = df["Job Title"].apply(categorize_job_title)
    
    # Filter out 'Other' if it's not a significant category or if we want to focus
    df_filtered = df[df["Job Role Category"] != "Other"].copy()

    if df_filtered.empty:
        print("Not enough data to train the job classifier after filtering.")
        return None

    X = df_filtered["Job Title"]
    y = df_filtered["Job Role Category"]

    if len(y.unique()) < 2:
        print("Not enough unique job role categories to train a classifier.")
        return None

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Create a pipeline with TF-IDF and Logistic Regression
    model_pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(stop_words="english", max_features=5000)),
        ("classifier", LogisticRegression(max_iter=1000))
    ])

    model_pipeline.fit(X_train, y_train)

    # Evaluate (optional)
    accuracy = model_pipeline.score(X_test, y_test)
    print(f"Job Classifier Accuracy: {accuracy:.2f}")

    # Save the model
    joblib.dump(model_pipeline, MODEL_PATH)
    print(f"Job classifier model saved to {MODEL_PATH}")
    return model_pipeline

def load_job_classifier():
    """Loads the pre-trained job role classifier."""
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

def predict_job_role(model, job_title):
    """Predicts the job role for a given job title."""
    if model:
        return model.predict([job_title])[0]
    return "Unknown"

if __name__ == "__main__":
    # This block is for testing the model training independently
    # In the main app, you'd call train_job_classifier and load_job_classifier
    sample_data = {
        "Job Title": [
            "Senior Data Scientist", "Junior Backend Developer", "DevOps Engineer L3",
            "Machine Learning Engineer", "Frontend Web Developer", "QA Tester",
            "Project Manager", "Cloud Architect", "Data Analyst", "Software Engineer"
        ]
    }
    sample_df = pd.DataFrame(sample_data)
    trained_model = train_job_classifier(sample_df)
    if trained_model:
        print(f"Predicted role for 'Lead Data Scientist': {predict_job_role(trained_model, 'Lead Data Scientist')}")
        print(f"Predicted role for 'Full Stack Engineer': {predict_job_role(trained_model, 'Full Stack Engineer')}")
        print(f"Predicted role for 'Manual QA': {predict_job_role(trained_model, 'Manual QA')}")
        print(f"Predicted role for 'HR Manager': {predict_job_role(trained_model, 'HR Manager')}")


