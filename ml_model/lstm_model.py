"""
LSTM Deep Learning Model for Stock Price Prediction
====================================================
Uses TensorFlow/Keras to build an LSTM-based sequence model.
Takes the last N days of technical indicators to predict next-day close.

Architecture:
    Input (sequence_length × num_features)
    → LSTM(128, return_sequences=True)
    → Dropout(0.2)
    → LSTM(64)
    → Dropout(0.2)
    → Dense(32, relu)
    → Dense(1)

Training:
    - Adam optimizer with learning rate scheduling
    - Early stopping with patience=10
    - Huber loss (robust to outliers)
"""

import numpy as np
import os

# Lazy imports to avoid TensorFlow overhead when not needed
_tf = None
_keras = None


def _import_tf():
    """Lazy import TensorFlow to avoid startup overhead."""
    global _tf, _keras
    if _tf is None:
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TF info logs
        import tensorflow as tf
        _tf = tf
        _keras = tf.keras
    return _tf, _keras


def create_sequences(X: np.ndarray, y: np.ndarray, sequence_length: int = 60):
    """
    Create sliding window sequences for LSTM input.

    Parameters
    ----------
    X : np.ndarray of shape (n_samples, n_features)
    y : np.ndarray of shape (n_samples,)
    sequence_length : int
        Number of time steps in each sequence.

    Returns
    -------
    X_seq : np.ndarray of shape (n_sequences, sequence_length, n_features)
    y_seq : np.ndarray of shape (n_sequences,)
    """
    X_seq, y_seq = [], []
    for i in range(sequence_length, len(X)):
        X_seq.append(X[i - sequence_length:i])
        y_seq.append(y[i])
    return np.array(X_seq), np.array(y_seq)


def build_lstm_model(input_shape: tuple, learning_rate: float = 0.001):
    """
    Build and compile the LSTM model.

    Parameters
    ----------
    input_shape : tuple
        (sequence_length, num_features)
    learning_rate : float

    Returns
    -------
    Compiled Keras model
    """
    tf, keras = _import_tf()

    model = keras.Sequential([
        keras.layers.Input(shape=input_shape),
        keras.layers.LSTM(128, return_sequences=True),
        keras.layers.Dropout(0.2),
        keras.layers.LSTM(64, return_sequences=False),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(32, activation='relu'),
        keras.layers.Dense(1)
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss=keras.losses.Huber(delta=1.0),
        metrics=['mae']
    )

    return model


def train_lstm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    sequence_length: int = 60,
    epochs: int = 100,
    batch_size: int = 32,
    verbose: int = 1
):
    """
    Train an LSTM model on the provided data.

    Parameters
    ----------
    X_train, y_train : Training features and targets (already scaled)
    X_val, y_val : Validation features and targets (already scaled)
    sequence_length : int
        Number of time steps per sequence
    epochs : int
    batch_size : int
    verbose : int

    Returns
    -------
    model : Trained Keras model
    history : Training history object
    """
    tf, keras = _import_tf()

    # Create sequences
    X_train_seq, y_train_seq = create_sequences(X_train, y_train, sequence_length)
    X_val_seq, y_val_seq = create_sequences(X_val, y_val, sequence_length)

    if len(X_train_seq) == 0 or len(X_val_seq) == 0:
        raise ValueError(
            f"Not enough data for sequence_length={sequence_length}. "
            f"Train samples: {len(X_train)}, Val samples: {len(X_val)}"
        )

    print(f"  LSTM Training shapes: X={X_train_seq.shape}, y={y_train_seq.shape}")
    print(f"  LSTM Validation shapes: X={X_val_seq.shape}, y={y_val_seq.shape}")

    # Build model
    input_shape = (sequence_length, X_train_seq.shape[2])
    model = build_lstm_model(input_shape)

    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True,
            verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1
        ),
    ]

    # Train
    history = model.fit(
        X_train_seq, y_train_seq,
        validation_data=(X_val_seq, y_val_seq),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=verbose
    )

    return model, history


def predict_lstm(
    model,
    X: np.ndarray,
    sequence_length: int = 60
) -> np.ndarray:
    """
    Make predictions using a trained LSTM model.

    Parameters
    ----------
    model : Trained Keras model
    X : np.ndarray of shape (n_samples, n_features) — already scaled
    sequence_length : int

    Returns
    -------
    predictions : np.ndarray of shape (n_predictions,)
    """
    X_seq, _ = create_sequences(X, np.zeros(len(X)), sequence_length)
    if len(X_seq) == 0:
        return np.array([])
    preds = model.predict(X_seq, verbose=0)
    return preds.flatten()


def save_lstm_model(model, path: str):
    """Save LSTM model to disk."""
    model.save(path)
    print(f"  LSTM model saved to {path}")


def load_lstm_model(path: str):
    """Load LSTM model from disk."""
    tf, keras = _import_tf()
    model = keras.models.load_model(path)
    return model


if __name__ == "__main__":
    # Quick smoke test with random data
    print("Testing LSTM model module...")
    np.random.seed(42)

    n_samples = 500
    n_features = 10
    seq_len = 60

    X = np.random.randn(n_samples, n_features)
    y = np.random.randn(n_samples)

    split = 400
    X_train, y_train = X[:split], y[:split]
    X_val, y_val = X[split:], y[split:]

    model, history = train_lstm(
        X_train, y_train, X_val, y_val,
        sequence_length=seq_len, epochs=5, verbose=0
    )
    preds = predict_lstm(model, X_val, seq_len)
    print(f"✅ Predictions shape: {preds.shape}")
    print("✅ LSTM module working correctly!")
