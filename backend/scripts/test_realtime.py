import pandas as pd
import numpy as np
import joblib
import os
import re
from urllib.parse import urlparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ==========================================================
# PATH SETUP
# ==========================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, 'Models')

print("🚀 Loading trained models...")

pipeline = joblib.load(os.path.join(MODELS_DIR, 'activity_classifier_pipeline.pkl'))
le       = joblib.load(os.path.join(MODELS_DIR, 'activity_label_encoder.pkl'))

try:
    metadata              = joblib.load(os.path.join(MODELS_DIR, 'model_metadata.pkl'))
    learning_keywords     = metadata.get('learning_keywords',     [])
    non_learning_keywords = metadata.get('non_learning_keywords', [])
    learning_domains      = metadata.get('learning_domains',      [])
    model_type            = metadata.get('model_type',            'Unknown')
    test_f1               = metadata.get('test_f1_score',         0)
except Exception as e:
    print(f"⚠️  Could not load metadata: {e}")
    learning_keywords     = []
    non_learning_keywords = []
    learning_domains      = []
    model_type            = "Unknown"
    test_f1               = 0

print("✅ Models loaded successfully!")
print(f"   Model Type : {model_type}")
print(f"   Test F1    : {test_f1:.4f}\n")
print("=" * 75)
print("        FocusVault — Intelligent Activity Classifier")
print("=" * 75)
print("\n  LEARNING     → tutorials, courses, documentation, coding practice …")
print("  NOT_LEARNING → entertainment, social media, news, gaming …")
print("\nType 'quit' to exit.\n")

# ==========================================================
# UTILITY FUNCTIONS
# ==========================================================

def is_url(text: str) -> bool:
    """Return True if the input looks like a URL."""
    return (
        text.startswith(('http://', 'https://', 'www.')) or
        ('.' in text and ' ' not in text.split('.')[0])
    )

def extract_domain(url: str) -> str:
    """
    Extract and normalise domain from URL.
    Keeps 'www.' prefix to match training data format.
    """
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        parsed = urlparse(url)
        domain = parsed.netloc or url
        return domain.lower()       # keep www. — matches training data
    except Exception:
        return url.lower()

def clean_title(text: str) -> str:
    """Mirrors the exact preprocessing used during training."""
    text = str(text).lower()
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+',     '', text)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+',         ' ', text)
    return text.strip()

# ✅ FIX 1 — WHOLE-WORD KEYWORD MATCHING
# Prevents false matches like:
#   'java'  inside 'javascript'
#   'game'  inside 'engagement'
#   'react' inside 'reaction'
def count_keywords_whole_word(text: str, keywords: list) -> int:
    """Count keyword matches using whole-word boundary regex."""
    text  = str(text).lower()
    count = 0
    for kw in keywords:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text):
            count += 1
    return count

def get_matched_keywords(text: str, keywords: list) -> list:
    """Return list of matched keywords (whole-word only)."""
    text    = str(text).lower()
    matched = []
    for kw in keywords:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text):
            matched.append(kw)
    return matched

# Domains that are ambiguous — need content title to classify accurately
# ✅ FIX 2 — youtube.com kept ONLY here (not in learning_domains)
AMBIGUOUS_DOMAINS = {
    'youtube.com',    'www.youtube.com',
    'medium.com',     'www.medium.com',
    'twitter.com',    'www.twitter.com',
    'x.com',
    'facebook.com',   'www.facebook.com',
    'instagram.com',  'www.instagram.com',
    'reddit.com',     'www.reddit.com',
    'netflix.com',    'www.netflix.com',
    'twitch.tv',      'www.twitch.tv',
}

def domain_is_ambiguous(domain: str) -> bool:
    return any(amb in domain for amb in AMBIGUOUS_DOMAINS)

# ==========================================================
# MAIN PREDICTION LOOP
# ==========================================================

while True:
    print("-" * 75)
    user_input = input("🔗 Enter URL or plain title (or 'quit'): ").strip()

    if user_input.lower() == 'quit':
        print("\n👋 Exiting — goodbye!\n")
        break

    if not user_input:
        print("❌ Input cannot be empty.\n")
        continue

    # ----------------------------------------------------------
    # STEP 1 — Separate domain from title
    # ----------------------------------------------------------
    if is_url(user_input):
        domain    = extract_domain(user_input)
        raw_title = ""          # Don't use URL string as title — adds noise
    else:
        domain    = ""
        raw_title = user_input

    # ----------------------------------------------------------
    # STEP 2 — Collect title / content description
    # ----------------------------------------------------------
    if domain_is_ambiguous(domain):
        # Always ask — these domains host mixed content
        print(f"\n📌  '{domain}' hosts both learning and entertainment content.")
        print("    Please describe what you were watching / reading.\n")
        while True:
            content_desc = input("📝  Content title (e.g. 'Python async tutorial'): ").strip()
            if len(content_desc) > 2:
                raw_title = content_desc
                print(f"   ✅  Using: '{raw_title}'")
                break
            print("   ❌  Please provide at least 3 characters.")

    elif domain and not raw_title:
        # Non-ambiguous URL — ask for page title to improve accuracy
        print(f"\n📌  Domain detected: {domain}")
        content_desc = input("📝  Page title (press Enter to skip): ").strip()
        if content_desc:
            raw_title = content_desc

    elif not domain:
        # ✅ FIX 3 — Ask for website when only plain text is given
        # Fixes: "Python Django REST API tutorial" → NOT_LEARNING
        # because model had no domain signal at all
        print(f"\n📌  No URL detected.")
        site_input = input("🌐  Which website was this on? (press Enter to skip): ").strip()
        if site_input:
            domain = extract_domain(site_input) if is_url(site_input) else site_input.lower()
            print(f"   ✅  Domain set to: '{domain}'")

    # Handle very short plain text with no domain
    if not domain and len(raw_title.strip()) < 3:
        print("📌  Title too short. Please provide more context:")
        extra = input("📝  Activity description: ").strip()
        if extra:
            raw_title = extra

    # Clean title using same logic as training
    title = clean_title(raw_title)

    # ----------------------------------------------------------
    # STEP 3 — Duration
    # ----------------------------------------------------------
    duration_input = input("⏱  Duration in seconds (press Enter for 300): ").strip()
    try:
        duration = float(duration_input) if duration_input else 300.0
    except ValueError:
        print("⚠️  Invalid duration — using 300 s.")
        duration = 300.0

    # ----------------------------------------------------------
    # STEP 4 — Derived features  (must EXACTLY mirror training)
    # ----------------------------------------------------------
    is_very_short_session      = int(duration < 60)

    # ✅ FIX 1 applied here — whole-word matching
    learning_keyword_count     = count_keywords_whole_word(title, learning_keywords)
    non_learning_keyword_count = count_keywords_whole_word(title, non_learning_keywords)

    is_learning_domain         = int(any(dom in domain for dom in learning_domains))
    keyword_balance            = learning_keyword_count - (3 * non_learning_keyword_count)
    has_non_learning_marker    = int(non_learning_keyword_count > 0)

    # ----------------------------------------------------------
    # STEP 5 — Build DataFrame with exact column names from training
    # ----------------------------------------------------------
    input_df = pd.DataFrame([{
        "title"                     : title,
        "Domain"                    : domain,
        "duration_seconds"          : duration,
        "is_very_short_session"     : is_very_short_session,
        "learning_keyword_count"    : learning_keyword_count,
        "non_learning_keyword_count": non_learning_keyword_count,
        "is_learning_domain"        : is_learning_domain,
        "keyword_balance"           : keyword_balance,
        "has_non_learning_marker"   : has_non_learning_marker,
    }])

    # ----------------------------------------------------------
    # STEP 6 — Predict
    # ----------------------------------------------------------
    try:
        probs      = pipeline.predict_proba(input_df)[0]
        pred_idx   = pipeline.predict(input_df)[0]
        pred_label = le.inverse_transform([pred_idx])[0]
        confidence = probs.max()
    except Exception as e:
        print(f"\n❌ Prediction failed: {e}\n")
        continue

    # ----------------------------------------------------------
    # STEP 7 — Display results
    # ----------------------------------------------------------
    print("\n" + " ✨ PREDICTION RESULT ✨ ".center(75, "="))
    print(f"  🌐 Domain        : {domain if domain else '(none)'}")
    print(f"  📄 Cleaned Title : '{title if title else '(none)'}'")
    print(f"  ⏱  Duration      : {duration:.0f} s")
    print()

    print("  📊 FEATURE ANALYSIS")
    if learning_keyword_count > 0:
        found = get_matched_keywords(title, learning_keywords)
        print(f"     🟢 Learning keywords     : {learning_keyword_count} → {found}")
    if non_learning_keyword_count > 0:
        found = get_matched_keywords(title, non_learning_keywords)
        print(f"     🔴 Non-learning keywords : {non_learning_keyword_count} (×3 penalty) → {found}")
    if learning_keyword_count == 0 and non_learning_keyword_count == 0:
        print("     ℹ️  No keywords matched — relying on domain & TF-IDF")
    print(f"     📊 Keyword balance   : {keyword_balance:+d}")
    print(f"     🏢 Learning domain   : {'✅ Yes' if is_learning_domain else '❌ No'}")
    print()

    emoji = "🎓" if pred_label == "learning" else "🎮"
    print(f"  {emoji} RESULT     : {pred_label.upper()}")
    print(f"  🔒 Confidence  : {confidence:.1%}")
    print()
    print("  Probability Distribution:")
    for cls in le.classes_:
        prob       = probs[le.transform([cls])[0]]
        bar_filled = int(prob * 40)
        bar        = "█" * bar_filled + "░" * (40 - bar_filled)
        print(f"    {cls:15} │ {bar} {prob:.1%}")

    print("=" * 75 + "\n")

print("=" * 75)
print("       Thank you for using FocusVault Activity Classifier!")
print("=" * 75)