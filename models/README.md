# ML Models Directory

Place your trained ML models here:

## Required Models

1. **activity_classifier.pkl** - Classifies browsing activity
   - Input: Features from page visit (title, duration, hour)
   - Output: Probabilities for learning/work/entertainment
   - Target accuracy: ≥85%

2. **topic_clusterer.pkl** - Clusters learning content by topic
   - Input: Vectorized page title
   - Output: Topic ID (0-5)
   - Method: K-Means or similar

3. **vectorizer.pkl** - Text vectorizer (TF-IDF or similar)
   - Used to convert page titles to vectors
   - Should match the vectorizer used during training

## Model Training

Your teammate should train these models using:

1. **Data Collection**: Use the extension to collect browsing data
2. **Labeling**: Manually label a dataset of ~500-1000 pages
3. **Feature Engineering**: Extract relevant features
4. **Training**: Train classifiers using scikit-learn or LightGBM
5. **Evaluation**: Validate accuracy meets targets
6. **Export**: Save models as .pkl files using pickle

## Fallback Behavior

If models are not found, the backend will use rule-based classification:
- Keyword matching for activity detection
- Domain-based topic classification
- This works but is less accurate than trained models

## Model Format

Models should be saved using pickle:

```python
import pickle

# Save model
with open('activity_classifier.pkl', 'wb') as f:
    pickle.dump(model, f)

# Load model
with open('activity_classifier.pkl', 'rb') as f:
    model = pickle.load(f)
```

## Integration

Once models are trained and placed here:
1. Restart the backend: `docker-compose restart backend`
2. Check logs: `docker-compose logs backend`
3. Look for "✅ Activity classifier loaded" messages
4. Test with extension to verify predictions
