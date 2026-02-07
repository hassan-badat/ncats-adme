"""
DNN architecture for cytosol stability models (HLC, MLC, RLC).

This module provides the build_dnn function required by scikeras-wrapped
Keras models that were pickled with a reference to this function.

The architecture was extracted from the pickle file headers.
"""
from tensorflow import keras
from tensorflow.keras import layers


def build_dnn(input_dim=6532, output_dim=1, hidden_units=(64, 32), dropout_rate=0.2, learning_rate=0.001):
    """
    Build a DNN model for cytosol stability prediction.
    
    Parameters:
        input_dim: Number of input features (Morgan fingerprint size)
        output_dim: Number of output classes (1 for binary)
        hidden_units: Tuple of hidden layer sizes
        dropout_rate: Dropout rate between layers
        learning_rate: Learning rate for RMSprop optimizer
    
    Returns:
        Compiled Keras Sequential model
    """
    model = keras.Sequential()
    model.add(layers.Input(shape=(input_dim,)))
    
    for units in hidden_units:
        model.add(layers.Dense(units, activation='relu'))
        model.add(layers.Dropout(dropout_rate))
    
    model.add(layers.Dense(output_dim, activation='sigmoid'))
    
    model.compile(
        optimizer=keras.optimizers.RMSprop(learning_rate=learning_rate),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model

