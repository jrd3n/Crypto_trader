import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import tensorflow as tf
import matplotlib.pyplot as plt

# -------------------------
# 1. Load X and Y CSV
# -------------------------
x_data = pd.read_csv("training_data/x_data.csv")
y_data = pd.read_csv("training_data/y_data.csv") 
#   ^-- Contains columns: ['datetime', 'close', 'sell_signal', 'buy_signal'] (for example)

# Merge on 'datetime' so X and Y line up
merged_data = pd.merge(x_data, y_data, on='datetime', how='inner')

# -------------------------
# 2. Define which columns are Y (targets)
#    We now have two signals: sell_signal and buy_signal
# -------------------------
# Merge on 'datetime'
merged_data = pd.merge(x_data, y_data, on='datetime', how='inner')

# For example, if you only want the 'close' from the X side:
if 'close_y' in merged_data.columns:
    merged_data.drop('close_y', axis=1, inplace=True)

# Define which columns are your targets
y_columns = ['sma_diff_percent']  # for example

# Create X by dropping 'datetime' and the y_columns
X = merged_data.drop(columns=y_columns + ['datetime', 'sma_current', 'sma_future'], errors='ignore')

X.head()

y = merged_data[y_columns]

# 1) Print all columns in merged_data:
print("All merged_data columns:", merged_data.columns.tolist())

# 2) Drop the columns you *intend* to remove and check what's left:
temp_X = merged_data.drop(columns=y_columns + ['datetime', 'sma_current', 'sma_future'], errors='ignore')
print("Columns after drop:", temp_X.columns.tolist())

# 3) Check the dtypes (sometimes 'datetime' might have become numeric or object):
print("Dtypes in temp_X:\n", temp_X.dtypes)

# 4) Print shape before numeric-only filtering:
print("Shape before numeric filtering:", temp_X.shape)

# 5) Now pick only numeric columns:
temp_X_numeric = temp_X.select_dtypes(include=[np.number])
print("Columns kept as numeric:", temp_X_numeric.columns.tolist())
print("Shape of numeric-only temp_X:", temp_X_numeric.shape)

# 6) If everything looks correct, assign back to X:
X = temp_X_numeric.values.astype(np.float32)

# Convert to float32
# X = X.select_dtypes(include=[np.number]).values.astype(np.float32)
y = y.select_dtypes(include=[np.number]).values.astype(np.float32)

# Drop rows where X or y has NaN
valid_mask = (~np.isnan(X).any(axis=1)) & (~np.isnan(y).any(axis=1))
X = X[valid_mask]
y = y[valid_mask]

# -------------------------
# 3. Train/Test Split
# -------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42
)

# -------------------------
# 4. Build Model
#    2 outputs = [sell_signal, buy_signal]
#    Use sigmoid activation + binary crossentropy for binary classification
# -------------------------
input_dim = X_train.shape[1]   # Number of features

print(f"Input Dimension: {input_dim}")

output_dim = y_train.shape[1]  # Should be 2 (sell, buy)

model = tf.keras.Sequential([
    tf.keras.layers.InputLayer(input_shape=(input_dim,)),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(output_dim)  # no activation => outputs can be any real number (negative or positive)
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
    loss='mean_squared_error',  # suitable for multi-label binary classification
    metrics=['mean_squared_error']         # track accuracy; can add others
)

model.summary()

# -------------------------
# 5. Train the Model
# -------------------------
history = model.fit(
    X_train, y_train,
    epochs=600,
    batch_size=300000,
    validation_split=0.2,
    verbose=1,
    shuffle=True
)

# -------------------------
# 6. Evaluate
# -------------------------
test_loss, test_accuracy = model.evaluate(X_test, y_test)
print(f"Test Loss: {test_loss:.4f}, Test Accuracy: {test_accuracy:.4f}")

# -------------------------
# 7. Save the Model
# -------------------------
model.save("trained_model.h5")
print("Model saved as 'trained_model.h5'")

# -------------------------
# 8. Plot Training History
# -------------------------
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('Training and Validation Loss Over Time')
plt.legend()
plt.show()
