# export_weights.py
# This script loads the trained Keras model and exports its weight matrices and biases
# to a lightweight JSON file (model_weights.json) so the chatbot can run predictions
# on Android (using pure NumPy) without needing the massive 500MB TensorFlow library.

import json
import os
import tensorflow as tf
from tensorflow.keras.models import load_model

def export():
    # Resolve directories relative to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, 'assets')
    training_dir = os.path.join(base_dir, 'training')

    model_file = os.path.join(training_dir, 'chatbot_model.keras')
    if not os.path.exists(model_file):
        print(f"Error: {model_file} not found. Please train the model first.")
        return
        
    print(f"Loading {model_file}...")
    model = load_model(model_file)
    
    exported_layers = []
    for layer in model.layers:
        # Check if the layer contains weights (like Dense layers)
        if hasattr(layer, 'get_weights') and len(layer.get_weights()) > 0:
            w, b = layer.get_weights()
            exported_layers.append({
                'name': layer.name,
                'w': w.tolist(),
                'b': b.tolist()
            })
            print(f"Exported layer: {layer.name} | shape: {w.shape}")

    output_file = os.path.join(assets_dir, 'model_weights.json')
    with open(output_file, 'w') as f:
        json.dump(exported_layers, f)
        
    print(f"Weights successfully saved to {output_file}! ✅")

if __name__ == "__main__":
    export()
