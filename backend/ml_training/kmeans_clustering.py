import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import silhouette_score
import joblib
import json
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================
DATA_DIR = Path(__file__).parent.parent / 'Data'
OUTPUT_DIR = Path(__file__).parent.parent / 'Models'
RAW_DATA_FILE = DATA_DIR / 'focus-vault-data (1).csv'
CLEANED_DATA_FILE = OUTPUT_DIR / 'combined_clean.csv'
VECTORIZER_FILE = OUTPUT_DIR / 'tfidf_vectorizer.pkl'
KMEANS_MODEL_FILE = OUTPUT_DIR / 'kmeans_model.pkl'
LABEL_ENCODER_FILE = OUTPUT_DIR / 'label_encoder.pkl'
CLUSTER_MAP_FILE = OUTPUT_DIR / 'cluster_map.json'
ELBOW_CURVE_FILE = OUTPUT_DIR / 'elbow_curve.png'
HEATMAP_FILE = OUTPUT_DIR / 'cluster_keywords_heatmap.png'
VISUALIZATION_FILE = OUTPUT_DIR / 'cluster_visualization.png'
DISTRIBUTION_FILE = OUTPUT_DIR / 'topic_distribution.png'

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Blocklisted domains and titles
BLOCKLISTED_DOMAINS = {'newtab', 'chrome://', 'about:', 'edge://', 'data:'}
BLOCKLISTED_TITLES = {'new tab', 'new window', 'youtube', 'blank page', 'home'}

print("=" * 80)
print("STEP 0: CLEAN RAW DATA")
print("=" * 80)

# Read raw data
print(f"Reading {RAW_DATA_FILE}...")
try:
    df_raw = pd.read_csv(RAW_DATA_FILE, encoding='utf-8')
except UnicodeDecodeError:
    print("  UTF-8 encoding failed, trying latin-1...")
    df_raw = pd.read_csv(RAW_DATA_FILE, encoding='latin-1')
print(f"  Total rows: {len(df_raw)}")
print(f"  Columns: {df_raw.columns.tolist()}")

# Filter only learning rows
df_clean = df_raw[df_raw['is_learning'] == True].copy()
print(f"  After filtering is_learning==True: {len(df_clean)} rows")

# Remove null/empty titles and domains
df_clean = df_clean.dropna(subset=['title', 'Domain'])
df_clean = df_clean[(df_clean['title'].str.strip() != '') & (df_clean['Domain'].str.strip() != '')]
print(f"  After removing null/empty: {len(df_clean)} rows")

# Remove blocklisted domains
df_clean = df_clean[~df_clean['Domain'].str.lower().isin(BLOCKLISTED_DOMAINS)]
print(f"  After removing blocklisted domains: {len(df_clean)} rows")

# Remove blocklisted titles
blocklist_pattern = '|'.join(BLOCKLISTED_TITLES)
df_clean = df_clean[~df_clean['title'].str.lower().str.contains(blocklist_pattern, na=False)]
print(f"  After removing blocklisted titles: {len(df_clean)} rows")

# Cap overrepresented domains at 5 rows per unique title
print("  Capping overrepresented domains to 5 rows per unique title...")
df_clean = df_clean.groupby(['Domain', 'title']).head(5).reset_index(drop=True)
print(f"  After capping: {len(df_clean)} rows")

# Save cleaned data
df_clean.to_csv(CLEANED_DATA_FILE, index=False)
print(f"  Saved to {CLEANED_DATA_FILE}")

print("\n" + "=" * 80)
print("STEP 1: LOAD & PREPARE DATA")
print("=" * 80)

# Reload cleaned data
df = pd.read_csv(CLEANED_DATA_FILE, encoding='latin-1')
print(f"Loaded {len(df)} rows from {CLEANED_DATA_FILE}")

# Create combined_text: title + domain + category (lowercased)
df['combined_text'] = (
    df['title'].str.lower() + ' ' + 
    df['Domain'].str.lower() + ' ' + 
    df['category'].str.lower()
).str.strip()

print(f"Created combined_text feature (title + domain + category)")
print(f"Sample combined_text entries:")
for i in range(min(5, len(df))):
    print(f"  {df['combined_text'].iloc[i]}")

print("\n" + "=" * 80)
print("STEP 2: TF-IDF VECTORIZATION")
print("=" * 80)

# TF-IDF Vectorization
print("Performing TF-IDF vectorization...")
vectorizer = TfidfVectorizer(
    max_features=3000,
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    stop_words='english'
)
tfidf_matrix = vectorizer.fit_transform(df['combined_text'])
print(f"  TF-IDF matrix shape: {tfidf_matrix.shape}")
print(f"  Features (vocabulary size): {len(vectorizer.get_feature_names_out())}")

# Save vectorizer
joblib.dump(vectorizer, VECTORIZER_FILE)
print(f"  Saved vectorizer to {VECTORIZER_FILE}")

print("\n" + "=" * 80)
print("STEP 3: FIND OPTIMAL K (ELBOW METHOD)")
print("=" * 80)

# Find optimal K using elbow method and silhouette score
k_range = range(2, 14)
inertias = []
silhouette_scores = []

print("Evaluating K values...")
for k in k_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
    km.fit(tfidf_matrix)
    inertias.append(km.inertia_)
    sil_score = silhouette_score(tfidf_matrix, km.labels_)
    silhouette_scores.append(sil_score)
    print(f"  K={k}: Inertia={km.inertia_:.2f}, Silhouette={sil_score:.4f}")

# Plot elbow curve and silhouette scores
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Elbow curve
axes[0].plot(k_range, inertias, 'bo-', linewidth=2, markersize=8)
axes[0].set_xlabel('K (Number of Clusters)', fontsize=12)
axes[0].set_ylabel('Inertia', fontsize=12)
axes[0].set_title('Elbow Method: Finding Optimal K', fontsize=14, fontweight='bold')
axes[0].grid(True, alpha=0.3)

# Silhouette scores
axes[1].plot(k_range, silhouette_scores, 'ro-', linewidth=2, markersize=8)
axes[1].set_xlabel('K (Number of Clusters)', fontsize=12)
axes[1].set_ylabel('Silhouette Score', fontsize=12)
axes[1].set_title('Silhouette Score: Finding Optimal K', fontsize=14, fontweight='bold')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(ELBOW_CURVE_FILE, dpi=150, bbox_inches='tight')
print(f"  Saved elbow curve to {ELBOW_CURVE_FILE}")
plt.close()

# Pick K with highest silhouette score
optimal_k = k_range[np.argmax(silhouette_scores)]
print(f"\nOptimal K (highest silhouette): {optimal_k}")
print(f"Silhouette Score: {max(silhouette_scores):.4f}")

print("\n" + "=" * 80)
print("STEP 4: TRAIN FINAL MODEL")
print("=" * 80)

# Train KMeans with optimal K
final_k = optimal_k  # Use optimal K found
print(f"Training K-Means with K={final_k}...")
km = KMeans(n_clusters=final_k, random_state=42, n_init=10, max_iter=300)
df['cluster_id'] = km.fit_predict(tfidf_matrix)
print(f"  Model trained successfully")
print(f"  Cluster distribution:")
print(df['cluster_id'].value_counts().sort_index())

# Save model
joblib.dump(km, KMEANS_MODEL_FILE)
print(f"  Saved model to {KMEANS_MODEL_FILE}")

print("\n" + "=" * 80)
print("STEP 5: INSPECT CLUSTERS")
print("=" * 80)

# Get top keywords per cluster
feature_names = vectorizer.get_feature_names_out()
print("Top 12 keywords per cluster:\n")

cluster_keywords_dict = {}
for cluster_id in range(final_k):
    center = km.cluster_centers_[cluster_id]
    top_indices = center.argsort()[-12:][::-1]
    top_keywords = [feature_names[i] for i in top_indices]
    cluster_keywords_dict[cluster_id] = top_keywords
    print(f"Cluster {cluster_id}: {', '.join(top_keywords)}")
    
    # Print sample titles
    cluster_titles = df[df['cluster_id'] == cluster_id]['title'].head(5).tolist()
    print(f"  Sample titles: {cluster_titles}\n")

# Generate keyword heatmap
cluster_keywords_matrix = np.zeros((final_k, 20))
for cluster_id in range(final_k):
    center = km.cluster_centers_[cluster_id]
    top_indices = center.argsort()[-20:][::-1]
    cluster_keywords_matrix[cluster_id] = center[top_indices]

plt.figure(figsize=(14, 8))
sns.heatmap(cluster_keywords_matrix, cmap='YlOrRd', cbar_kws={'label': 'TF-IDF Score'})
plt.xlabel('Top 20 Keywords per Cluster', fontsize=12)
plt.ylabel('Cluster ID', fontsize=12)
plt.title('Cluster Keywords Heatmap', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(HEATMAP_FILE, dpi=150, bbox_inches='tight')
print(f"Saved keyword heatmap to {HEATMAP_FILE}")
plt.close()

print("\n" + "=" * 80)
print("STEP 6: CREATE CLUSTER MAP")
print("=" * 80)

# Auto-name clusters using the DOMINANT category + top content keyword in each cluster
# This produces meaningful names like "DSA", "AI Tools", "SQL" instead of keyword noise

# Normalize category names for cleanliness
CATEGORY_DISPLAY = {
    'dsa': 'DSA',
    'ai_tool': 'AI Tools',
    'learning': 'General Learning',
    'other': 'Other',
    'search': 'Web Search',
    'career': 'Career',
    'docs': 'Documentation',
    'sql': 'SQL',
    'aptitude': 'Aptitude',
    'entertainment': 'Entertainment',
    'articles': 'Articles',
    'ai/ml': 'AI/ML',
}

cluster_map = {}
for cid in range(final_k):
    cluster_rows = df[df['cluster_id'] == cid]
    
    # Get dominant category in this cluster
    top_category = cluster_rows['category'].str.lower().value_counts()
    if len(top_category) == 0:
        cluster_map[cid] = f"Cluster_{cid}"
        continue
    
    primary_cat = top_category.index[0]
    display_name = CATEGORY_DISPLAY.get(primary_cat, primary_cat.title())
    
    # If multiple clusters share the same dominant category, 
    # differentiate using top domain
    top_domain = cluster_rows['Domain'].value_counts().index[0]
    domain_short = top_domain.replace('.com', '').replace('.org', '').replace('.ai', '').title()
    
    # Check if this name is already used
    if display_name in cluster_map.values():
        display_name = f"{display_name} ({domain_short})"
    
    cluster_map[cid] = display_name

print(f"Cluster to Topic Mapping (based on dominant category):")
for cid, topic in sorted(cluster_map.items()):
    # Also show cluster size
    size = len(df[df['cluster_id'] == cid])
    print(f"  Cluster {cid}: {topic} ({size} rows)")

# Save cluster map
with open(CLUSTER_MAP_FILE, 'w') as f:
    json.dump(cluster_map, f, indent=2)
print(f"Saved cluster map to {CLUSTER_MAP_FILE}")

# Fit and save LabelEncoder for topic names
le = LabelEncoder()
topic_names = [cluster_map.get(i, f"Cluster_{i}") for i in range(final_k)]
le.fit(topic_names)
joblib.dump(le, LABEL_ENCODER_FILE)
print(f"Saved label encoder to {LABEL_ENCODER_FILE}")

print("\n" + "=" * 80)
print("STEP 7: EVALUATE QUALITY")
print("=" * 80)

# Map cluster IDs to topic names
df['topic'] = df['cluster_id'].map(cluster_map)
print("Topic distribution:")
print(df['topic'].value_counts())

# PCA visualization
print("\nPerforming PCA for 2D visualization...")
pca = PCA(n_components=2, random_state=42)
tfidf_2d = pca.fit_transform(tfidf_matrix.toarray())

# Create visualization
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Scatter plot
colors = plt.cm.tab20(np.linspace(0, 1, final_k))
for cluster_id in range(final_k):
    mask = df['cluster_id'] == cluster_id
    axes[0].scatter(
        tfidf_2d[mask, 0], tfidf_2d[mask, 1],
        label=cluster_map.get(cluster_id, f"Cluster_{cluster_id}"),
        alpha=0.6, s=50, color=colors[cluster_id]
    )

axes[0].set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)', fontsize=12)
axes[0].set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)', fontsize=12)
axes[0].set_title('Cluster Visualization (PCA)', fontsize=14, fontweight='bold')
axes[0].legend(loc='best', fontsize=9)
axes[0].grid(True, alpha=0.3)

# Topic distribution bar + pie
topic_counts = df['topic'].value_counts()
axes[1].bar(range(len(topic_counts)), topic_counts.values, color=colors[:len(topic_counts)])
axes[1].set_xticks(range(len(topic_counts)))
axes[1].set_xticklabels(topic_counts.index, rotation=45, ha='right')
axes[1].set_ylabel('Number of Pages', fontsize=12)
axes[1].set_title('Topic Distribution (Bar Chart)', fontsize=14, fontweight='bold')
axes[1].grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(VISUALIZATION_FILE, dpi=150, bbox_inches='tight')
print(f"Saved visualizations to {VISUALIZATION_FILE}")
plt.close()

# Distribution pie chart
fig, ax = plt.subplots(figsize=(10, 8))
ax.pie(topic_counts.values, labels=topic_counts.index, autopct='%1.1f%%', startangle=90)
ax.set_title('Topic Distribution (Pie Chart)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(DISTRIBUTION_FILE, dpi=150, bbox_inches='tight')
print(f"Saved distribution chart to {DISTRIBUTION_FILE}")
plt.close()

print("\n" + "=" * 80)
print("STEP 8: PREDICTION FUNCTION & TEST")
print("=" * 80)

def predict_topic(title, domain, category='general'):
    """
    Predict topic for a given title and domain
    
    Args:
        title (str): Webpage title
        domain (str): Domain name
        category (str): Activity category (default: 'general')
    
    Returns:
        dict: {
            'topic': predicted topic name,
            'cluster_id': cluster ID,
            'confidence': confidence score (0-1)
        }
    """
    # Combine text
    combined = (title.lower() + ' ' + domain.lower() + ' ' + category.lower()).strip()
    
    # Vectorize
    combined_vec = vectorizer.transform([combined])
    
    # Predict cluster
    cluster_id = km.predict(combined_vec)[0]
    
    # Calculate confidence from distances to all cluster centers
    distances = np.linalg.norm(
        km.cluster_centers_ - combined_vec.toarray(), 
        axis=1
    )
    confidence = 1.0 / (1.0 + distances[cluster_id])  # Sigmoid-like confidence
    
    topic = cluster_map.get(cluster_id, f"Cluster_{cluster_id}")
    
    return {
        'topic': topic,
        'cluster_id': int(cluster_id),
        'confidence': float(confidence)
    }

# Test predictions
print("Testing predictions on sample pages:\n")
test_samples = [
    ('Python Tutorial', 'python.org', 'learning'),
    ('LinkedIn Feed', 'linkedin.com', 'career'),
    ('GitHub Repository', 'github.com', 'learning'),
    ('YouTube Video', 'youtube.com', 'learning'),
    ('Stack Overflow', 'stackoverflow.com', 'learning'),
    ('CSS Reference', 'developer.mozilla.org', 'learning'),
    ('Design Inspiration', 'dribbble.com', 'design'),
    ('Data Analysis', 'kaggle.com', 'learning'),
    ('News Article', 'news.ycombinator.com', 'learning'),
    ('Project Management', 'notion.so', 'productivity'),
]

for title, domain, category in test_samples:
    prediction = predict_topic(title, domain, category)
    print(f"Title: {title}")
    print(f"Domain: {domain}")
    print(f"  → Topic: {prediction['topic']}, Confidence: {prediction['confidence']:.3f}\n")

print("\n" + "=" * 80)
print("STEP 9: SAVE ALL ARTIFACTS")
print("=" * 80)

# Re-save all artifacts
joblib.dump(km, KMEANS_MODEL_FILE)
joblib.dump(vectorizer, VECTORIZER_FILE)
joblib.dump(le, LABEL_ENCODER_FILE)

print(f"Saved artifacts:")
print(f"  {KMEANS_MODEL_FILE}: {os.path.getsize(KMEANS_MODEL_FILE) / 1024:.2f} KB")
print(f"  {VECTORIZER_FILE}: {os.path.getsize(VECTORIZER_FILE) / 1024:.2f} KB")
print(f"  {LABEL_ENCODER_FILE}: {os.path.getsize(LABEL_ENCODER_FILE) / 1024:.2f} KB")
print(f"  {CLUSTER_MAP_FILE}: {os.path.getsize(CLUSTER_MAP_FILE) / 1024:.2f} KB")

print("\n" + "=" * 80)
print("✅ KMEANS CLUSTERING PIPELINE COMPLETE")
print("=" * 80)
print(f"\nAll outputs saved to: {OUTPUT_DIR}")
print(f"Ready for prediction phase!")
