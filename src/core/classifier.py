# src/core/classifier.py
# Handles text preprocessing, vocabulary bag-of-words mapping, 
# and intent classification using lightweight NumPy weight inference.

import os
import json
import pickle
import numpy as np
import string
import random
import nltk
from nltk.stem import WordNetLemmatizer

# Setup local NLTK data directory path dynamically
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
nltk_data_dir = os.path.join(BASE_DIR, 'nltk_data')
if nltk_data_dir not in nltk.data.path:
    nltk.data.path.append(nltk_data_dir)

# Ensure NLTK packages are present locally
try:
    nltk.download('punkt', download_dir=nltk_data_dir, quiet=True)
    nltk.download('wordnet', download_dir=nltk_data_dir, quiet=True)
except Exception as e:
    print(f"NLTK data download skipped or failed: {e}")

lemmatizer = WordNetLemmatizer()

ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
WORDS_PATH = os.path.join(ASSETS_DIR, 'words.pkl')
CLASSES_PATH = os.path.join(ASSETS_DIR, 'classes.pkl')
INTENTS_PATH = os.path.join(ASSETS_DIR, 'intents.json')
WEIGHTS_PATH = os.path.join(ASSETS_DIR, 'model_weights.json')

# Load the saved helper files
print("Loading chatbot artifacts from assets...")
try:
    words = pickle.load(open(WORDS_PATH, 'rb'))
    classes = pickle.load(open(CLASSES_PATH, 'rb'))
except Exception as e:
    print(f"Failed to load pkl files: {e}")
    words = []
    classes = []

try:
    with open(INTENTS_PATH, 'r', encoding='utf-8') as file:
        intents = json.load(file)
except Exception as e:
    print(f"Failed to load intents.json: {e}")
    intents = {"intents": []}

numpy_model_weights = None
if os.path.exists(WEIGHTS_PATH):
    try:
        with open(WEIGHTS_PATH, 'r') as f:
            numpy_model_weights = json.load(f)
        print("Loaded lightweight NumPy model weights successfully!")
    except Exception as e:
        print(f"Failed to load NumPy weights: {e}")

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
    sentence = "".join([c for c in sentence if c not in string.punctuation])
    return sentence

def clean_up_sentence(sentence):
    cleaned = clean_and_preprocess(sentence)
    sentence_words = nltk.word_tokenize(cleaned)
    sentence_words = [lemmatizer.lemmatize(word) for word in sentence_words]
    return sentence_words

def bag_of_words(sentence, words_vocab):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words_vocab)
    for s_word in sentence_words:
        for i, word in enumerate(words_vocab):
            if word == s_word:
                bag[i] = 1
    return np.array(bag)

def relu(x):
    return np.maximum(0, x)

def softmax(x):
    exp_x = np.exp(x - np.max(x))
    return exp_x / exp_x.sum(axis=0)

def predict_numpy(bow_array):
    x = bow_array
    for idx, layer in enumerate(numpy_model_weights):
        w = np.array(layer['w'])
        b = np.array(layer['b'])
        x = np.dot(x, w) + b
        
        if idx == len(numpy_model_weights) - 1:
            x = softmax(x)
        else:
            x = relu(x)
    return x

def predict_class(sentence):
    if not words or not classes:
        return []
        
    bow_array = bag_of_words(sentence, words)
    
    if numpy_model_weights is not None:
        predictions = predict_numpy(bow_array)
    else:
        # Fallback if weights file is missing
        predictions = np.zeros(len(classes))
        predictions[0] = 1.0
    
    threshold = 0.50
    results = [[i, r] for i, r in enumerate(predictions) if r > threshold]
    results.sort(key=lambda x: x[1], reverse=True)
    
    return_list = []
    for r in results:
        return_list.append({
            "intent": classes[r[0]],
            "probability": str(r[1])
        })
    return return_list

def get_response(intents_list, intents_json):
    if not intents_list:
        tag_to_find = "noanswer"
    else:
        tag_to_find = intents_list[0]['intent']
        
    list_of_intents = intents_json.get('intents', [])
    for intent in list_of_intents:
        if intent['tag'] == tag_to_find:
            return random.choice(intent['responses'])
            
    return "I'm sorry, I don't know how to respond to that."

def chatbot_response(text):
    ints = predict_class(text)
    if not ints:
        tag = "noanswer"
    else:
        tag = ints[0]['intent']
    res = get_response(ints, intents)
    return res, tag
