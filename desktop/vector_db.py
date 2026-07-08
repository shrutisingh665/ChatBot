# vector_db.py
# This module implements the local PDF vector database using pypdf and FAISS.
# Features:
# 1. Scans the 'documents' folder for PDF files.
# 2. Extracts page-by-page text.
# 3. Splits texts into chunks with character boundaries and overlaps.
# 4. Generates embeddings using a lightweight local Transformer ('all-MiniLM-L6-v2').
# 5. Saves and loads the flat L2 FAISS index alongside chunks metadata.
# 6. Performs high-speed similarity search using L2 distances.

import os
import pickle
import numpy as np
import faiss
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

class VectorDB:
    def __init__(self, doc_dir="documents", index_path="vector_index.faiss", chunks_path="chunks.pkl"):
        self.doc_dir = doc_dir
        self.index_path = index_path
        self.chunks_path = chunks_path
        self.model = None
        self.index = None
        self.chunks = []
        
        # Enforce target documents folder existence
        if not os.path.exists(self.doc_dir):
            os.makedirs(self.doc_dir)

    def lazy_load_model(self):
        """
        Loads the SentenceTransformer model on demand to minimize startup delays.
        """
        if self.model is None:
            print("Loading sentence-transformers embedding model ('all-MiniLM-L6-v2')...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def load_index(self):
        """
        Loads the saved FAISS index and chunk metadata from disk.
        """
        if os.path.exists(self.index_path) and os.path.exists(self.chunks_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.chunks_path, "rb") as f:
                    self.chunks = pickle.load(f)
                print(f"Successfully loaded vector index containing {len(self.chunks)} chunks.")
                return True
            except Exception as e:
                print(f"Error loading FAISS index files: {e}")
        return False

    def build_index(self):
        """
        Parses all PDFs inside doc_dir, chunks content, creates L2 FAISS index, and writes to disk.
        """
        self.lazy_load_model()
        
        # Read text from all PDFs
        raw_text = []
        if not os.path.exists(self.doc_dir):
            os.makedirs(self.doc_dir)
            
        pdf_files = [f for f in os.listdir(self.doc_dir) if f.lower().endswith(".pdf")]
        
        if not pdf_files:
            print("Indexing aborted: No PDF files found in documents directory.")
            self.index = None
            self.chunks = []
            # Clean obsolete index files if any
            if os.path.exists(self.index_path):
                os.remove(self.index_path)
            if os.path.exists(self.chunks_path):
                os.remove(self.chunks_path)
            return False
            
        print(f"Processing {len(pdf_files)} PDF files...")
        for pdf_file in pdf_files:
            pdf_path = os.path.join(self.doc_dir, pdf_file)
            try:
                reader = PdfReader(pdf_path)
                for page_idx, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        raw_text.append((text, pdf_file, page_idx + 1))
            except Exception as e:
                print(f"Failed to read PDF file {pdf_file}: {e}")

        # Split text into chunks (500 chars with 100 chars overlap)
        chunks = []
        chunk_size = 500
        overlap = 100
        
        for text, source_file, page_num in raw_text:
            text = " ".join(text.split()) # clean whitespaces
            i = 0
            while i < len(text):
                chunk = text[i:i + chunk_size]
                chunks.append({
                    "text": chunk,
                    "source": f"{source_file} (Page {page_num})"
                })
                i += (chunk_size - overlap)

        if not chunks:
            print("No text chunks could be extracted from the documents.")
            return False

        self.chunks = chunks
        print(f"Extracted {len(self.chunks)} chunks. Generating embeddings...")

        # Generate embeddings
        texts = [c["text"] for c in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Convert embeddings to standard float32 numpy array
        embeddings = np.array(embeddings).astype("float32")
        dimension = embeddings.shape[1]

        # Initialize and populate flat L2 index
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

        # Persist vectors and metadata to disk
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.chunks_path, "wb") as f:
                pickle.dump(self.chunks, f)
            print("Vector database build successful and saved to disk.")
            return True
        except Exception as e:
            print(f"Failed to write index to disk: {e}")
            return False

    def search(self, query, top_k=2, similarity_threshold=1.2):
        """
        Queries the vector index for nearby text chunks.
        L2 distance index matches are closer if L2 distance is smaller.
        """
        # Load from disk if index is not loaded in memory
        if self.index is None or not self.chunks:
            if not self.load_index():
                return []

        self.lazy_load_model()
        
        try:
            query_embedding = np.array([self.model.encode(query)]).astype("float32")
            distances, indices = self.index.search(query_embedding, top_k)
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx != -1 and dist <= similarity_threshold:
                    chunk = self.chunks[idx]
                    results.append({
                        "text": chunk["text"],
                        "source": chunk["source"],
                        "distance": float(dist)
                    })
            return results
        except Exception as e:
            print(f"Vector search failed: {e}")
            return []
