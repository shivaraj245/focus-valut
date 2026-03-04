import os
import time
import pandas as pd
import tldextract
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
script_dir = os.path.dirname(__file__)
env_path = os.path.join(script_dir, '.env')
print(f"🔍 Looking for .env at: {env_path}")
print(f"✓ .env exists: {os.path.exists(env_path)}")
load_dotenv(env_path)

# =========================
# CONFIG
# =========================
INPUT_CSV = os.path.join(script_dir, "real_history_raw.csv")
OUTPUT_CSV = os.path.join(script_dir, "activity_dataset_labeled.csv")
BATCH_SIZE = 5
MODEL_NAME = "llama-3.3-70b-versatile"  # Latest stable Groq model
VALID_LABELS = {"work", "learning", "entertainment"}

print(f"📁 Input CSV: {INPUT_CSV}")
print(f"📁 Input exists: {os.path.exists(INPUT_CSV)}\n")

# =========================
# GROQ SETUP
# =========================
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print(f"❌ GROQ_API_KEY not found. Please set it in .env or as environment variable")
    raise ValueError("❌ GROQ_API_KEY not found")

# Strip whitespace from API key
api_key = api_key.strip()
print(f"✅ Groq API Key found: {api_key[:20]}...")  # Show first 20 chars

# Initialize Groq client
client = Groq(api_key=api_key)
print(f"✅ Groq client configured successfully\n")

# =========================
# HELPERS
# =========================

def extract_domain(url: str) -> str:
    ext = tldextract.extract(url)
    if ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return ext.domain

def extract_hour(ts) -> int:
    try:
        return datetime.fromisoformat(str(ts)).hour
    except Exception:
        return 12  # safe default

def classify_with_groq(rows):
    """
    rows: list of dicts
    returns: list[str] labels
    """

    prompt = """Classify each browser activity into ONE label.

Labels:
- learning: coding, tutorials, documentation, studying
- work: emails, documents, meetings, github, project tools
- entertainment: movies, music, social media, random videos

Rules:
- Return ONLY labels
- One label per line
- Same order as input
- Allowed labels: work, learning, entertainment

Activities:
"""

    for i, r in enumerate(rows, start=1):
        prompt += (
            f"{i}. Title: {r['title']}\n"
            f"   Domain: {r['domain']}\n"
            f"   Duration: {r['duration_seconds']} seconds\n"
            f"   Hour: {r['hour_of_day']}\n\n"
        )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that classifies web activities."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=100
    )

    raw_lines = response.choices[0].message.content.strip().splitlines()

    labels = []
    for line in raw_lines:
        label = line.strip().lower()
        labels.append(label if label in VALID_LABELS else "work")

    return labels

# =========================
# MAIN PIPELINE
# =========================

df = pd.read_csv(INPUT_CSV)
print(f"📊 CSV Columns: {list(df.columns)}\n")

# ---- normalize schema ----
# Check if columns already exist
if "domain" not in df.columns and "url" in df.columns:
    df["domain"] = df["url"].apply(extract_domain)

if "duration_seconds" not in df.columns and "duration" in df.columns:
    df["duration_seconds"] = df["duration"]
elif "duration_seconds" not in df.columns:
    df["duration_seconds"] = 300  # Default

if "hour_of_day" not in df.columns and "visit_time" in df.columns:
    df["hour_of_day"] = df["visit_time"].apply(extract_hour)
elif "hour_of_day" not in df.columns:
    df["hour_of_day"] = 12  # Default

# Keep only needed columns
needed_cols = ["url", "title", "domain", "duration_seconds", "hour_of_day"]
available_cols = [col for col in needed_cols if col in df.columns]
df = df[available_cols]

print(f"✅ Ready to label {len(df)} rows\n")

all_labels = []

for start in range(0, len(df), BATCH_SIZE):
    batch = df.iloc[start:start + BATCH_SIZE]
    records = batch.to_dict(orient="records")

    print(f"Labeling rows {start} → {start + len(batch) - 1}")

    try:
        labels = classify_with_groq(records)
        if len(labels) != len(batch):
            raise ValueError("Label count mismatch")
    except Exception as e:
        print("⚠️ Error, defaulting batch to 'work':", e)
        labels = ["work"] * len(batch)

    all_labels.extend(labels)
    time.sleep(1)  # rate-limit safety

df["label"] = all_labels

df.to_csv(OUTPUT_CSV, index=False)

print("✅ Labeling complete. Output saved to:", OUTPUT_CSV)
