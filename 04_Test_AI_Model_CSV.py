#!/usr/bin/env python3
import pandas as pd
import numpy as np
import tensorflow as tf
from tqdm import tqdm

# -------------------------
# 1. Load your saved model
# -------------------------
model = tf.keras.models.load_model("trained_model.h5")
print("Model loaded.")

# -------------------------
# 2. Load the data to predict on (features only)
# -------------------------
df_to_predict = pd.read_csv("training_data/x_data.csv")

# If your y data had columns like 'sell_signal'/'buy_signal' or 'datetime', remove them from X
y_columns = ['sell_signal', 'buy_signal']  
columns_to_remove = y_columns + ['datetime']  
X_predict_df = df_to_predict.drop(columns=columns_to_remove, errors='ignore')

print(f"Features for prediction: {X_predict_df.shape[1]} columns.")
# Convert numeric columns to float32
X_predict = X_predict_df.select_dtypes(include=[np.number]).values.astype(np.float32)

# Drop rows with NaNs
valid_mask = ~np.isnan(X_predict).any(axis=1)
X_predict = X_predict[valid_mask]

# -------------------------
# 3. Predict in batches with progress bar
# -------------------------
batch_size = 512
num_samples = X_predict.shape[0]
all_predictions = []

for start_idx in tqdm(range(0, num_samples, batch_size), desc="Predicting"):
    end_idx = start_idx + batch_size
    batch_X = X_predict[start_idx:end_idx]
    
    # Model now outputs a single value per row
    batch_pred = model.predict(batch_X, verbose=0)  # shape: (batch_size, 1)
    all_predictions.append(batch_pred)

predictions = np.concatenate(all_predictions, axis=0)  # shape: (num_samples, 1)

# -------------------------
# 4. Merge predictions back
# -------------------------
# Create a DataFrame with a single column named 'pred_value'
pred_df = pd.DataFrame(predictions, columns=['pred_value'])

# Match up the valid rows
final_df = df_to_predict.loc[valid_mask].reset_index(drop=True).copy()
pred_df = pred_df.reset_index(drop=True)

# Concatenate side by side
final_df = pd.concat([final_df, pred_df], axis=1)

# -------------------------
# 5. Save to CSV
# -------------------------
final_df.to_csv("predictions.csv", index=False)
print("Predictions saved to predictions.csv")
