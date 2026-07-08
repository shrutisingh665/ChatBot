# train.py
# This script trains a deep learning model to classify user intents for a retrieval chatbot.
# It reads patterns from intents.json, processes text using NLTK lemmatization,
# creates a bag-of-words representation, and trains a TensorFlow Keras model.
# The vocabulary, intent classes, and trained model are saved for chatbot.py to use.

import json
import pickle
import random
import numpy as np
import os
import nltk
from nltk.stem import WordNetLemmatizer

# Automatically download required NLTK resources
# 'punkt' is used for tokenizing sentences into individual words.
# 'wordnet' is used for lemmatization (reducing words to their base form).
print("Downloading NLTK resources...")
nltk.download('punkt', quiet=True)
nltk.download('wordnet', quiet=True)

# Import TensorFlow Keras components for building the neural network
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import SGD

# Initialize the lemmatizer
lemmatizer = WordNetLemmatizer()

# Resolve directories relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
TRAINING_DIR = os.path.join(BASE_DIR, 'training')

INTENTS_PATH = os.path.join(ASSETS_DIR, 'intents.json')
WORDS_PATH = os.path.join(ASSETS_DIR, 'words.pkl')
CLASSES_PATH = os.path.join(ASSETS_DIR, 'classes.pkl')
KERAS_MODEL_PATH = os.path.join(TRAINING_DIR, 'chatbot_model.keras')

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
    cleaned = clean_and_preprocess(sentence)
    sentence_words = nltk.word_tokenize(cleaned)
    sentence_words = [lemmatizer.lemmatize(word) for word in sentence_words]
    return sentence_words

# Load the training data from intents.json
print("Loading intents.json dataset...")
with open(INTENTS_PATH, 'r', encoding='utf-8') as file:
    intents_data = json.load(file)

# Initialize structures to hold processed vocabulary, class tags, and document patterns
words = []
classes = []
documents = []

# Process each intent and its corresponding patterns in the dataset
for intent in intents_data['intents']:
    tag = intent['tag']
    # Keep track of all unique intent tags
    if tag not in classes:
        classes.append(tag)
        
    for pattern in intent['patterns']:
        # Tokenize and lemmatize each word in the pattern sentence
        word_list = clean_up_sentence(pattern)
        # Store words in the global word list
        words.extend(word_list)
        # Pair the tokenized sentence pattern with its intent tag
        documents.append((word_list, tag))

# Remove duplicates and sort the words and classes alphabetically
words = sorted(list(set(words)))
classes = sorted(list(set(classes)))

print(f"Total vocabulary size: {len(words)} unique words.")
print(f"Total classes (tags): {len(classes)} classes.")
print(f"Total pattern documents: {len(documents)} patterns.")

# Save the words list and classes list as pickle files for prediction reference
print("Saving vocabulary and classes to pkl files...")
pickle.dump(words, open(WORDS_PATH, 'wb'))
pickle.dump(classes, open(CLASSES_PATH, 'wb'))

# Create training data list
training_data = []
# Create an empty template list for one-hot output vectors
output_empty = [0] * len(classes)

# Create bag-of-words dataset for training
for doc in documents:
    bag = []
    pattern_words = doc[0]
    # Lemmatize and lowercase the words in the current document pattern
    pattern_words = [lemmatizer.lemmatize(word.lower()) for word in pattern_words]
    
    # Generate the bag-of-words array (1 if word is present, 0 otherwise)
    for w in words:
        bag.append(1 if w in pattern_words else 0)
        
    # Create the target one-hot output vector for this document's tag
    output_row = list(output_empty)
    output_row[classes.index(doc[1])] = 1
    
    # Append the input bag and target vector to our training list
    training_data.append((bag, output_row))

# Shuffle the training data to ensure unbiased training
random.shuffle(training_data)

# Split features (X) and labels (y) and convert them to numpy arrays
train_x = np.array([item[0] for item in training_data])
train_y = np.array([item[1] for item in training_data])

print("Building the neural network model...")

# Define the neural network topology using TensorFlow Sequential API
model = Sequential()
# Input layer with 128 neurons, receiving the length of the vocabulary bag-of-words
model.add(Dense(128, input_shape=(len(train_x[0]),), activation='relu'))
# Dropout layer to mitigate overfitting (randomly disables neurons during training)
model.add(Dropout(0.5))
# Hidden layer with 64 neurons
model.add(Dense(64, activation='relu'))
# Dropout layer
model.add(Dropout(0.5))
# Output layer with neurons matching the number of target intent classes (softmax activation for probabilities)
model.add(Dense(len(train_y[0]), activation='softmax'))

# Configure the Stochastic Gradient Descent (SGD) optimizer
# The learning rate and momentum are optimized for stable gradient updates.
sgd = SGD(learning_rate=0.01, momentum=0.9, nesterov=True)

# Compile the model using categorical crossentropy loss since we classification intents
model.compile(loss='categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])

# Fit (train) the model on our bag of words dataset
print("Starting training...")
model.fit(train_x, train_y, epochs=200, batch_size=5, verbose=1)

# Save the fully trained model to a .keras file
print("Saving trained model to chatbot_model.keras...")
model.save(KERAS_MODEL_PATH)
print("Model training successfully completed!")
