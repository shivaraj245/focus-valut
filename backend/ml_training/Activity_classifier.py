import os
import re
import numpy as np
import pandas as pd
import joblib
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except:
    XGBOOST_AVAILABLE = False
    print("⚠️  XGBoost not installed. Will use LogisticRegression instead.")

# ==========================================================
# CONFIG
# ==========================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(os.path.dirname(SCRIPT_DIR), 'Data')
MODELS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'Models')
os.makedirs(MODELS_DIR, exist_ok=True)

CSV_PATH = os.path.join(DATA_DIR, 'focus-vault-data (1).csv')

print("🚀 FocusVault: FIXED Activity Classifier Training\n")

# ==========================================================
# 1️⃣  LOAD DATA
# ==========================================================
df = pd.read_csv(CSV_PATH, encoding='latin-1')
print(f"✅ Loaded {len(df)} rows")
print(f"\n📊 Dataset Shape: {df.shape}")
print(f"\n🔍 Missing Values:\n{df.isnull().sum()}")

df = df.dropna(subset=['title'])
print(f"✅ After dropping missing titles: {len(df)}")

df['Domain']           = df['Domain'].fillna('').str.lower()
df['duration_seconds'] = pd.to_numeric(df['duration_seconds'], errors='coerce').fillna(300)

print(f"\n📈 Class Distribution:")
print(df['is_learning'].value_counts())
print(f"Class Balance: {df['is_learning'].value_counts(normalize=True)}")

# ==========================================================
# 2️⃣  CLEAN TITLE
# ==========================================================
def clean_title(text):
    text = str(text).lower()
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+',     '', text)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+',         ' ', text)
    return text.strip()

df['title'] = df['title'].apply(clean_title)

# ==========================================================
# 3️⃣  TIME FEATURES
# ==========================================================
df['start_time']  = pd.to_datetime(df['start_time'], errors='coerce')
df['hour_of_day'] = df['start_time'].dt.hour.fillna(12)
df['hour_sin']    = np.sin(2 * np.pi * df['hour_of_day'] / 24)
df['hour_cos']    = np.cos(2 * np.pi * df['hour_of_day'] / 24)

# ==========================================================
# 4️⃣  DURATION FEATURE
# ==========================================================
df['is_very_short_session'] = (df['duration_seconds'] < 60).astype(int)

# ==========================================================
# 5️⃣  KEYWORD LISTS
# ==========================================================
learning_keywords = [
    'tutorial', 'course', 'problem', 'leetcode', 'interview',
    'algorithm', 'data structure', 'guide', 'documentation',
    'learn', 'lesson', 'training', 'class', 'education',
    'practice', 'exercise', 'solution', 'code', 'programming',
    'python', 'javascript', 'java', 'database', 'sql',
    'lecture', 'workshop', 'seminar', 'conference', 'webinar',
    'book', 'manual', 'reference', 'academic', 'research',
    'aptitude', 'preparation', 'placement', 'campus', 'quantitative',
    'reasoning', 'ability', 'test', 'exam', 'quiz', 'assessment',
    'skill', 'certification', 'project', 'assignment', 'homework',
    'study', 'notes', 'revision', 'subject', 'chapter'
]

non_learning_keywords = [
    'music', 'song', 'playlist', 'movie', 'film', 'watch',
    'entertainment', 'game', 'gaming', 'streaming', 'social',
    'meme', 'funny', 'comedy', 'news', 'sport', 'cricket',
    'instagram', 'facebook', 'twitter', 'tiktok', 'shorts',
    'viral', 'trending', 'celebrity', 'gossip',
    'drama', 'prank', 'challenge', 'react', 'reaction'
]

# ==========================================================
# ✅ FIX 1 — WHOLE-WORD KEYWORD MATCHING
#    Prevents 'java' matching inside 'javascript',
#    'game' inside 'engagement', 'react' inside 'reaction', etc.
# ==========================================================
def count_keywords_whole_word(text, keywords):
    """Count keyword matches using whole-word boundary matching."""
    text = str(text).lower()
    count = 0
    for kw in keywords:
        # Use word boundary (\b) so 'java' won't match 'javascript'
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text):
            count += 1
    return count

df['learning_keyword_count']     = df['title'].apply(
    lambda x: count_keywords_whole_word(x, learning_keywords))
df['non_learning_keyword_count'] = df['title'].apply(
    lambda x: count_keywords_whole_word(x, non_learning_keywords))

# ==========================================================
# 6️⃣  DOMAIN FLAGS
# ==========================================================
# ✅ FIX 2 — youtube.com REMOVED from learning_domains
#    YouTube hosts both learning and entertainment equally.
#    Keeping it caused all YouTube URLs to bias toward LEARNING
#    regardless of content (e.g. "funny cat compilation" → LEARNING ❌)
learning_domains = [
    # 'youtube.com'  ← REMOVED (ambiguous domain)
    'geeksforgeeks.org', 'github.com',
    'stackoverflow.com', 'leetcode.com', 'hackerrank.com',
    'w3schools.com',     'mdn.mozilla.org', 'coursera.org',
    'udemy.com',         'edx.org',         'kdnuggets.com',
    'dev.to',            'freecodecamp.org', 'tutorialspoint.com',
    'medium.com'         # Keep medium — majority of Medium posts are technical
]

df['is_learning_domain'] = df['Domain'].apply(
    lambda x: 1 if any(dom in str(x) for dom in learning_domains) else 0
)

print(f"\n🎯 Feature Engineering Complete!")
print(f"   ✅ Whole-word keyword matching enabled")
print(f"   ✅ youtube.com removed from learning_domains")
print(f"   - Learning keywords  : {len(learning_keywords)}")
print(f"   - Learning domains   : {len(learning_domains)}")

# ==========================================================
# 7️⃣  FEATURE DEFINITIONS
# ==========================================================
TEXT_FEATURES = ['title', 'Domain']
NUM_FEATURES  = [
    'duration_seconds', 'is_very_short_session',
    'learning_keyword_count', 'non_learning_keyword_count',
    'is_learning_domain'
]

df['keyword_balance']          = df['learning_keyword_count'] - (3 * df['non_learning_keyword_count'])
df['has_non_learning_marker']  = (df['non_learning_keyword_count'] > 0).astype(int)
NUM_FEATURES.extend(['keyword_balance', 'has_non_learning_marker'])

# TF-IDF Vectorizers
title_tfidf = TfidfVectorizer(
    max_features=10000,
    ngram_range=(1, 2),
    stop_words='english',
    min_df=2
)
domain_tfidf = TfidfVectorizer(
    max_features=15,
    ngram_range=(1, 1)
)

preprocessor = ColumnTransformer(
    transformers=[
        ('title_tfidf',  title_tfidf,  'title'),
        ('domain_tfidf', domain_tfidf, 'Domain'),
        ('num_scaler',   StandardScaler(), NUM_FEATURES)
    ]
)

# ==========================================================
# 8️⃣  TRAIN / TEST SPLIT
# ==========================================================
df['learning_label'] = df['is_learning'].map({True: 'learning', False: 'not_learning'})

le = LabelEncoder()
y  = le.fit_transform(df['learning_label'])

X_train, X_test, y_train, y_test = train_test_split(
    df, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n✅ Train size: {len(X_train)} | Test size: {len(X_test)}")

# ==========================================================
# 9️⃣  MODEL
# ==========================================================
print("\n🤖 Training model...")

if XGBOOST_AVAILABLE:
    try:
        pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', XGBClassifier(
                max_depth=6,
                learning_rate=0.1,
                n_estimators=200,
                scale_pos_weight=len(y_train[y_train == 0]) / len(y_train[y_train == 1]),
                random_state=42,
                use_label_encoder=False,
                eval_metric='logloss'
            ))
        ])
        print("   Using XGBoost")
    except Exception as e:
        print(f"   XGBoost failed: {e} → falling back to LogisticRegression")
        XGBOOST_AVAILABLE = False

if not XGBOOST_AVAILABLE:
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(
            max_iter=5000,
            class_weight='balanced',
            random_state=42
        ))
    ])
    print("   Using LogisticRegression")

pipeline.fit(X_train, y_train)

# ==========================================================
# 🔟  EVALUATION
# ==========================================================
y_pred     = pipeline.predict(X_test)
train_acc  = pipeline.score(X_train, y_train)
test_acc   = pipeline.score(X_test,  y_test)
test_f1    = f1_score(y_test, y_pred)

print("\n📈 RESULTS")
print(f"Train Accuracy : {train_acc:.4f}")
print(f"Test Accuracy  : {test_acc:.4f}")
print(f"Test F1 Score  : {test_f1:.4f} ⭐")

print("\n📊 Classification Report:")
print(classification_report(y_test, y_pred, target_names=le.classes_))

print("\n📉 Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# ==========================================================
# 1️⃣1️⃣  FEATURE IMPORTANCE
# ==========================================================
print("\n🔍 Top Features:")
try:
    feature_names = pipeline.named_steps['preprocessor'].get_feature_names_out()
    coefs         = pipeline.named_steps['classifier'].coef_[0]

    top_learning = sorted(zip(coefs, feature_names), reverse=True)[:15]
    top_not      = sorted(zip(coefs, feature_names))[:15]

    print("\n🎓 Top Learning Indicators:")
    for weight, feat in top_learning:
        print(f"   {feat} → {weight:.3f}")

    print("\n❌ Top Non-Learning Indicators:")
    for weight, feat in top_not:
        print(f"   {feat} → {weight:.3f}")
except Exception:
    print("   Feature importance not available for this model type")

# ==========================================================
# 1️⃣2️⃣  SAVE
# ==========================================================
joblib.dump(pipeline, os.path.join(MODELS_DIR, 'activity_classifier_pipeline.pkl'))
joblib.dump(le,       os.path.join(MODELS_DIR, 'activity_label_encoder.pkl'))

metadata = {
    'learning_keywords'    : learning_keywords,
    'non_learning_keywords': non_learning_keywords,
    'learning_domains'     : learning_domains,
    'test_f1_score'        : float(test_f1),
    'test_accuracy'        : float(test_acc),
    'model_type'           : 'XGBoost' if XGBOOST_AVAILABLE else 'LogisticRegression'
}
joblib.dump(metadata, os.path.join(MODELS_DIR, 'model_metadata.pkl'))

print("\n💾 Saved:")
print("   ✅ activity_classifier_pipeline.pkl")
print("   ✅ activity_label_encoder.pkl")
print("   ✅ model_metadata.pkl")
print("\n🎉 FIXED Model Training Complete!")
print("=" * 75)