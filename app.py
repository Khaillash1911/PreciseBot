import os
import subprocess
import sys
import io # Import io for BytesIO

# -------- Install Required Packages --------
# This function will ensure all necessary packages are installed
def install_packages():
    packages = [
        "groq",
        "faiss-cpu",
        "PyPDF2",
        "sentence-transformers",
        "flask",
        "flask_cors"
    ]
    print("Checking and installing required packages...")
    for pkg in packages:
        try:
            # Attempt to import to check if installed
            __import__(pkg.split("==")[0].replace('-', '_'))
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
    print("Package installation complete.")

# Call install_packages() at the very beginning
install_packages()

# -------- Imports (after ensuring packages are installed) --------
from groq import Groq
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# -------- API Key --------
# For local development, keeping it here. For production, use environment variables.
os.environ["GROQ_API_KEY"] = "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"
client = Groq(api_key=os.environ["GROQ_API_KEY"])

# -------- PDF Text Extraction --------
def extract_text_from_pdf_stream(pdf_file_stream):
    """
    Extracts text from a PDF file stream (BytesIO object).
    """
    reader = PdfReader(pdf_file_stream)
    return "\n".join([p.extract_text() or "" for p in reader.pages])

# -------- Text Chunking --------
def chunk_text(text, chunk_size=500):
    words = text.split()
    return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

# -------- Embedding & Indexing --------
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def create_faiss_index(chunks):
    embeddings = embedder.encode(chunks)
    dimension = embeddings[0].shape[0]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))
    return index, embeddings

# -------- Ask Question (RAG - Retrieval Augmented Generation) --------
def ask_question_rag(query, chunks, index):
    question_embedding = embedder.encode([query])
    D, I = index.search(np.array(question_embedding), 5) # Retrieve top 5 relevant chunks
    context = "\n\n".join([chunks[i] for i in I[0]])

    prompt = f"""Answer the question using ONLY the context below.
If the answer is not in the context, clearly state that you don't have enough information.

Context:
{context}

Question: {query}
Answer:"""

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions accurately based on the provided context. If the answer is not in the context, state that you don't have enough information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling Groq API: {e}") # Log the specific API error
        return f"An error occurred with the AI model: {str(e)}. Please try again."

# -------- Flask App Setup --------
app = Flask(__name__, static_folder='.') # Serve static files from the current directory
CORS(app) # Enable CORS for all routes (important for frontend development)

# Global variables to store PDF data for the current session
# NOTE: For a multi-user production environment, this global state
# would need to be managed per-user (e.g., using sessions or a database).
pdf_chunks = []
pdf_index = None
is_pdf_processed = False # Flag to track if a PDF has been successfully processed

# -------- Flask Routes --------

# Route to serve the main HTML file
@app.route('/')
def serve_index():
    return send_from_directory('.', 'static/index.html')

# Route to serve static assets like CSS and JS
@app.route('/<path:filename>')
def serve_static(filename):
    # Basic security: only serve files we expect
    if filename in ['static/style.css', 'static/script.js']:
        return send_from_directory('.', filename)
    return "File not found", 404

# API endpoint for PDF upload
@app.route('/api/upload_pdf', methods=['POST'])
def upload_pdf():
    global pdf_chunks, pdf_index, is_pdf_processed

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part in the request."}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file."}), 400

    if file and file.filename.endswith('.pdf'):
        try:
            # Read the file stream directly into memory
            pdf_stream = io.BytesIO(file.read())
            text = extract_text_from_pdf_stream(pdf_stream)
            pdf_chunks = chunk_text(text)
            pdf_index, _ = create_faiss_index(pdf_chunks)
            is_pdf_processed = True
            return jsonify({"status": "success", "message": "PDF uploaded and processed. You can now ask questions."})
        except Exception as e:
            print(f"Error processing PDF: {e}") # Log detailed error for debugging
            return jsonify({"status": "error", "message": f"Error processing PDF: {str(e)}. Please try another file."}), 500
    else:
        return jsonify({"status": "error", "message": "Invalid file type. Please upload a PDF."}), 400

# API endpoint for chatbot interaction
@app.route('/api/chat', methods=['POST'])
def chat():
    global is_pdf_processed

    if not is_pdf_processed:
        return jsonify({"response": "⚠️ Please upload and process a PDF first."}), 200

    data = request.json
    user_question = data.get('message')

    if not user_question:
        return jsonify({"response": "No question provided."}), 400

    try:
        bot_response = ask_question_rag(user_question, pdf_chunks, pdf_index)
        return jsonify({"response": bot_response})
    except Exception as e:
        print(f"Error during chat: {e}") # Log detailed error for debugging
        return jsonify({"response": f"An error occurred during chat: {str(e)}. Please try again."}), 500

# -------- Entry Point --------
if __name__ == "__main__":
    print("Starting Flask application (app.py)...")
    print("Navigate to http://127.0.0.1:5000 in your browser to access the chatbot UI.")
    app.run(debug=True, port=5000) # Run Flask app on port 5000