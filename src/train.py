import pandas as pd
import joblib
from sklearn.linear_model import SGDClassifier # Optimized for streaming/low RAM
import gc
import os

def train_model(file_path: str, model_save_path: str):
    try:
        print(f"📦 8GB RAM MODE: Loading {file_path} in chunks...")
        
        # We use SGDClassifier because it has a 'partial_fit' method
        # This allows training on 100 rows at a time instead of 1,000,000
        clf = SGDClassifier(loss='log_loss') 
        
        # Read JSON in chunks of 500 rows to save RAM
        reader = pd.read_json(file_path, lines=True, chunksize=500)
        
        first_chunk = True
        for chunk in reader:
            # Clean numeric data only
            chunk = chunk.select_dtypes(include=['number']).dropna()
            if chunk.empty: continue
            
            target = chunk.columns[-1]
            X = chunk.drop(columns=[target])
            y = chunk[target]
            
            # Identify all possible classes in the first chunk
            if first_chunk:
                all_classes = y.unique()
                clf.partial_fit(X, y, classes=all_classes)
                print(f"🎯 Target: {target} | Features: {list(X.columns)}")
                first_chunk = False
            else:
                clf.partial_fit(X, y)
            
            del chunk, X, y
            gc.collect()

        # Save the "Brain"
        os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
        joblib.dump(clf, model_save_path)
        print("💾 SUCCESS: Model saved to disk!")
        return True

    except Exception as e:
        print(f"❌ TRAINING CRASHED: {str(e)}")
        return False
