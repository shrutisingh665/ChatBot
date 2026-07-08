# chatbot.py
# This script handles the runtime classification logic for the chatbot.
# It supports loading weights dynamically into a pure-NumPy inference pipeline (if model_weights.json exists)
# or falling back to Keras (if chatbot_model.keras is present).

import json
import pickle
import random
import numpy as np
import os
import nltk
from nltk.stem import WordNetLemmatizer

# Automatically download NLTK data if it wasn't downloaded during training
nltk.download('punkt', quiet=True)
nltk.download('wordnet', quiet=True)

# Initialize the lemmatizer
lemmatizer = WordNetLemmatizer()

# Resolve directories relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
TRAINING_DIR = os.path.join(BASE_DIR, 'training')

WORDS_PATH = os.path.join(ASSETS_DIR, 'words.pkl')
CLASSES_PATH = os.path.join(ASSETS_DIR, 'classes.pkl')
INTENTS_PATH = os.path.join(ASSETS_DIR, 'intents.json')
WEIGHTS_PATH = os.path.join(ASSETS_DIR, 'model_weights.json')
KERAS_MODEL_PATH = os.path.join(TRAINING_DIR, 'chatbot_model.keras')

# Load the saved helper files
print("Loading chatbot artifacts...")
words = pickle.load(open(WORDS_PATH, 'rb'))
classes = pickle.load(open(CLASSES_PATH, 'rb'))

# Load the intents.json mapping responses
with open(INTENTS_PATH, 'r', encoding='utf-8') as file:
    intents = json.load(file)

# Attempt to load model weights for pure NumPy execution
numpy_model_weights = None
model = None

if os.path.exists(WEIGHTS_PATH):
    try:
        with open(WEIGHTS_PATH, 'r') as f:
            numpy_model_weights = json.load(f)
        print("Loaded lightweight NumPy model weights successfully!")
    except Exception as e:
        print(f"Failed to load NumPy weights: {e}")

if numpy_model_weights is None:
    print("Loading TensorFlow Keras model...")
    try:
        from tensorflow.keras.models import load_model
        model = load_model(KERAS_MODEL_PATH)
        print("Loaded Keras model successfully!")
    except Exception as e:
        print(f"Failed to load Keras model: {e}")


import string

CONTRACTIONS = {
    "what's": "what is",
    "how's": "how is",
    "who's": "who is",
    "it's": "it is",
    "you're": "you are",
    "don't": "do not",
    "can't": "cannot",
    "won't": "will not",
    "i'm": "i am"
}

def clean_and_preprocess(sentence):
    sentence = sentence.lower().strip()
    for contraction, expansion in CONTRACTIONS.items():
        sentence = sentence.replace(contraction, expansion)
    # Remove punctuation
    sentence = "".join([c for c in sentence if c not in string.punctuation])
    return sentence

def clean_up_sentence(sentence):
    """
    Tokenizes, cleans contractions, removes punctuation, and lemmatizes words.
    """
    cleaned = clean_and_preprocess(sentence)
    sentence_words = nltk.word_tokenize(cleaned)
    sentence_words = [lemmatizer.lemmatize(word) for word in sentence_words]
    return sentence_words

def bag_of_words(sentence, words_vocab):
    """
    Creates a bag-of-words array representation of the sentence based on the loaded vocabulary.
    """
    # Tokenize and lemmatize the sentence
    sentence_words = clean_up_sentence(sentence)
    # Initialize the bag-of-words list with zeros
    bag = [0] * len(words_vocab)
    
    # Set the index value to 1 if a vocabulary word is present in the sentence words list
    for s_word in sentence_words:
        for i, word in enumerate(words_vocab):
            if word == s_word:
                bag[i] = 1
                
    return np.array(bag)

def relu(x):
    return np.maximum(0, x)

def softmax(x):
    # Avoid overflow
    exp_x = np.exp(x - np.max(x))
    return exp_x / exp_x.sum(axis=0)

def predict_numpy(bow_array):
    """
    Executes feedforward prediction using weight matrices via pure NumPy.
    """
    x = bow_array
    for idx, layer in enumerate(numpy_model_weights):
        w = np.array(layer['w'])
        b = np.array(layer['b'])
        x = np.dot(x, w) + b
        
        # Apply activation functions
        if idx == len(numpy_model_weights) - 1:
            x = softmax(x)
        else:
            x = relu(x)
    return x

def predict_class(sentence):
    """
    Predicts the intent class of the input sentence using loaded model weights.
    """
    # Convert input sentence to its bag of words array
    bow_array = bag_of_words(sentence, words)
    
    # Run prediction using NumPy or Keras model
    if numpy_model_weights is not None:
        predictions = predict_numpy(bow_array)
    elif model is not None:
        predictions = model.predict(np.array([bow_array]))[0]
    else:
        # Emergency fallback if both are missing
        predictions = np.zeros(len(classes))
        predictions[0] = 1.0
    
    # Filter out predictions below a probability threshold of 0.50 for high accuracy
    threshold = 0.50
    results = [[i, r] for i, r in enumerate(predictions) if r > threshold]
    
    # Sort predictions by probability in descending order
    results.sort(key=lambda x: x[1], reverse=True)
    
    # Construct a structured list of intents and their probabilities
    return_list = []
    for r in results:
        return_list.append({
            "intent": classes[r[0]],
            "probability": str(r[1])
        })
        
    return return_list

def get_response(intents_list, intents_json):
    """
    Selects a random response from the matched intent tag inside intents.json.
    """
    # If no intent is predicted above the threshold, default to 'noanswer'
    if not intents_list:
        tag_to_find = "noanswer"
    else:
        tag_to_find = intents_list[0]['intent']
        
    # Search for the matched tag in our intents JSON structure
    list_of_intents = intents_json['intents']
    for intent in list_of_intents:
        if intent['tag'] == tag_to_find:
            # Pick a random response from the matches
            return random.choice(intent['responses'])
            
    # Fallback response in case tag is not found in json
    return "I'm sorry, I don't know how to respond to that."

def chatbot_response(text):
    """
    Helper function that wraps predict_class and get_response to return response and matched tag.
    """
    ints = predict_class(text)
    if not ints:
        tag = "noanswer"
    else:
        tag = ints[0]['intent']
    res = get_response(ints, intents)
    return res, tag

# Simple terminal interface test block to run chatbot.py directly
if __name__ == "__main__":
    print("Chatbot logic initialized. Type 'quit' to exit.")
    while True:
        message = input("You: ")
        if message.lower() == 'quit':
            break
        response, tag = chatbot_response(message)
        print(f"Bot: {response} [Intent: {tag}]")
