# ML Model Training Guide

**For Team Member 2: ML Models & Training Pipeline**

This guide explains how to train the ML models for FocusVault.

## 📊 Overview

You need to train 3 models:

1. **Activity Classifier** - Classifies browsing activity (learning/work/entertainment)
2. **Topic Clusterer** - Groups learning content by topic (DSA, Web Dev, ML, etc.)
3. **Flashcard Quality Scorer** - Rates flashcard quality (optional, can use rule-based)

## 🎯 Target Metrics

- Activity Classifier: ≥85% accuracy
- Topic Clusterer: Silhouette score ≥0.4
- Flashcard Scorer: ≥75% accuracy

## 📝 Step 1: Data Collection

### Using the Extension

1. Install the extension in Chrome
2. Browse normally for 1-2 weeks
3. Visit diverse content:
   - Learning sites (GeeksforGeeks, MDN, tutorials)
   - Work sites (GitHub, Jira, Slack)
   - Entertainment (YouTube, Reddit, social media)

### Export Data from Database

```python
import psycopg2
import pandas as pd

# Connect to database
conn = psycopg2.connect(
    host="localhost",
    database="focusvault_db",
    user="focusvault",
    password="password"
)

# Export events
query = """
SELECT 
    url, title, domain, duration_seconds, 
    hour_of_day, created_at
FROM browser_events
"""

df = pd.read_sql(query, conn)
df.to_csv('browsing_data.csv', index=False)
print(f"Exported {len(df)} events")
```

### Manual Labeling

Create `labeled_data.csv` with these columns:

```csv
url,title,domain,duration_seconds,hour_of_day,activity_label,topic_label
https://www.geeksforgeeks.org/binary-search-tree,Binary Search Tree,geeksforgeeks.org,180,14,learning,dsa
https://github.com/myproject,My Project,github.com,300,10,work,programming
https://www.youtube.com/watch?v=xyz,Funny Video,youtube.com,600,20,entertainment,other
```

**Target:** 500-1000 labeled samples (more is better)

**Activity Labels:**
- `learning` - Educational content
- `work` - Professional/project work
- `entertainment` - Leisure browsing

**Topic Labels:**
- `dsa` - Data Structures & Algorithms
- `webdev` - Web Development
- `ml` - Machine Learning
- `sysdesign` - System Design
- `programming` - Programming Languages
- `other` - Everything else

## 🔧 Step 2: Feature Engineering

```python
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Load data
df = pd.read_csv('labeled_data.csv')

# Feature 1: Duration (normalized)
df['duration_norm'] = (df['duration_seconds'] - df['duration_seconds'].mean()) / df['duration_seconds'].std()

# Feature 2: Hour of day (cyclical encoding)
df['hour_sin'] = np.sin(2 * np.pi * df['hour_of_day'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour_of_day'] / 24)

# Feature 3: Title length
df['title_length'] = df['title'].str.len()

# Feature 4: Domain features
df['is_edu'] = df['domain'].str.contains('edu|tutorial|learn|course', case=False).astype(int)
df['is_social'] = df['domain'].str.contains('facebook|twitter|instagram|reddit', case=False).astype(int)

# Feature 5: Text features (for topic clustering)
vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
title_vectors = vectorizer.fit_transform(df['title'].fillna(''))

print("Features prepared!")
```

## 🤖 Step 3: Train Activity Classifier

```python
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import pickle

# Prepare features
X = df[['duration_norm', 'hour_sin', 'hour_cos', 'title_length', 'is_edu', 'is_social']]
y = df['activity_label']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Activity Classifier Accuracy: {accuracy:.2%}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# Save model
with open('../models/activity_classifier.pkl', 'wb') as f:
    pickle.dump(model, f)

print("✅ Activity classifier saved!")
```

### Alternative: LightGBM (Better Performance)

```python
import lightgbm as lgb

# Train LightGBM
model = lgb.LGBMClassifier(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5,
    random_state=42
)

model.fit(X_train, y_train)

# Evaluate and save (same as above)
```

## 🎯 Step 4: Train Topic Clusterer

```python
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# Use TF-IDF vectors from earlier
X_text = title_vectors.toarray()

# Determine optimal clusters (elbow method)
inertias = []
silhouettes = []

for k in range(3, 10):
    kmeans = KMeans(n_clusters=k, random_state=42)
    labels = kmeans.fit_predict(X_text)
    inertias.append(kmeans.inertia_)
    silhouettes.append(silhouette_score(X_text, labels))

# Choose k=6 (based on your topics)
kmeans = KMeans(n_clusters=6, random_state=42)
kmeans.fit(X_text)

# Evaluate
labels = kmeans.predict(X_text)
score = silhouette_score(X_text, labels)
print(f"Silhouette Score: {score:.3f}")

# Save model
with open('../models/topic_clusterer.pkl', 'wb') as f:
    pickle.dump(kmeans, f)

# Save vectorizer
with open('../models/vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)

print("✅ Topic clusterer saved!")
```

## 📊 Step 5: Evaluate Models

```python
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
import seaborn as sns

# Confusion Matrix for Activity Classifier
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Entertainment', 'Learning', 'Work'],
            yticklabels=['Entertainment', 'Learning', 'Work'])
plt.title('Activity Classifier Confusion Matrix')
plt.ylabel('True Label')
plt.xlabel('Predicted Label')
plt.savefig('confusion_matrix.png')
plt.show()

# Feature Importance
feature_names = ['duration', 'hour_sin', 'hour_cos', 'title_len', 'is_edu', 'is_social']
importances = model.feature_importances_

plt.figure(figsize=(10, 6))
plt.barh(feature_names, importances)
plt.xlabel('Importance')
plt.title('Feature Importance')
plt.savefig('feature_importance.png')
plt.show()
```

## 🔄 Step 6: Integrate Models

1. Place trained models in `models/` directory:
   ```
   models/
   ├── activity_classifier.pkl
   ├── topic_clusterer.pkl
   └── vectorizer.pkl
   ```

2. Restart the backend:
   ```bash
   docker-compose restart backend
   ```

3. Check logs:
   ```bash
   docker-compose logs backend | grep "classifier"
   ```

   You should see:
   ```
   ✅ Activity classifier loaded
   ✅ Topic clusterer loaded
   ✅ Vectorizer loaded
   ```

## 🧪 Step 7: Test Models

```python
# Test script
import pickle
import numpy as np

# Load models
with open('../models/activity_classifier.pkl', 'rb') as f:
    activity_model = pickle.load(f)

with open('../models/topic_clusterer.pkl', 'rb') as f:
    topic_model = pickle.load(f)

with open('../models/vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)

# Test case 1: Learning page
test_features = np.array([[0.5, 0.7, 0.3, 50, 1, 0]])  # duration, hour_sin, hour_cos, title_len, is_edu, is_social
prediction = activity_model.predict(test_features)
probs = activity_model.predict_proba(test_features)
print(f"Test 1 - Predicted: {prediction[0]}, Probabilities: {probs[0]}")

# Test case 2: Topic clustering
test_title = "Binary Search Tree Implementation in Python"
test_vector = vectorizer.transform([test_title])
topic = topic_model.predict(test_vector)
print(f"Test 2 - Topic ID: {topic[0]}")
```

## 📈 Model Improvement Tips

### If Accuracy is Low (<85%)

1. **Collect More Data**
   - Need at least 500 samples per class
   - Ensure balanced dataset

2. **Feature Engineering**
   - Add domain-specific features
   - Try word embeddings (Word2Vec, BERT)
   - Add URL path features

3. **Try Different Models**
   - XGBoost
   - Neural Networks
   - Ensemble methods

4. **Hyperparameter Tuning**
   ```python
   from sklearn.model_selection import GridSearchCV
   
   param_grid = {
       'n_estimators': [50, 100, 200],
       'max_depth': [5, 10, 15],
       'min_samples_split': [2, 5, 10]
   }
   
   grid_search = GridSearchCV(RandomForestClassifier(), param_grid, cv=5)
   grid_search.fit(X_train, y_train)
   print(f"Best params: {grid_search.best_params_}")
   ```

### If Topics Don't Make Sense

1. **Manual Topic Assignment**
   - Use supervised learning instead of clustering
   - Label topics manually
   - Train a classifier

2. **Better Text Features**
   - Use BERT embeddings
   - Include page content (not just title)
   - Add domain knowledge

## 📦 Complete Training Script

Save as `train_models.py`:

```python
import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, silhouette_score

def train_activity_classifier(df):
    print("Training Activity Classifier...")
    
    # Features
    X = df[['duration_seconds', 'hour_of_day', 'title_length']]
    y = df['activity_label']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {accuracy:.2%}")
    print(classification_report(y_test, y_pred))
    
    # Save
    with open('../models/activity_classifier.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    return model

def train_topic_clusterer(df):
    print("\nTraining Topic Clusterer...")
    
    # Vectorize
    vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
    X = vectorizer.fit_transform(df['title'].fillna(''))
    
    # Cluster
    kmeans = KMeans(n_clusters=6, random_state=42)
    kmeans.fit(X)
    
    # Evaluate
    labels = kmeans.predict(X)
    score = silhouette_score(X, labels)
    print(f"Silhouette Score: {score:.3f}")
    
    # Save
    with open('../models/topic_clusterer.pkl', 'wb') as f:
        pickle.dump(kmeans, f)
    
    with open('../models/vectorizer.pkl', 'wb') as f:
        pickle.dump(vectorizer, f)
    
    return kmeans, vectorizer

if __name__ == "__main__":
    # Load data
    df = pd.read_csv('labeled_data.csv')
    df['title_length'] = df['title'].str.len()
    
    # Train models
    activity_model = train_activity_classifier(df)
    topic_model, vectorizer = train_topic_clusterer(df)
    
    print("\n✅ All models trained and saved!")
```

Run with:
```bash
python train_models.py
```

## 📚 Resources

- [scikit-learn Documentation](https://scikit-learn.org/)
- [LightGBM Guide](https://lightgbm.readthedocs.io/)
- [Feature Engineering Book](https://www.oreilly.com/library/view/feature-engineering-for/9781491953235/)

## ✅ Checklist

- [ ] Collected 500+ labeled samples
- [ ] Balanced dataset across classes
- [ ] Trained activity classifier (≥85% accuracy)
- [ ] Trained topic clusterer (silhouette ≥0.4)
- [ ] Saved models as .pkl files
- [ ] Tested models with sample data
- [ ] Integrated with backend
- [ ] Verified predictions in dashboard

Good luck with model training! 🚀
