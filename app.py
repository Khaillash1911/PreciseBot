import os
import subprocess
import sys
import io
import json

def install_packages():
    packages = [
        "groq",
        "faiss-cpu",
        "PyPDF2",
        "sentence-transformers",
        "flask",
        "flask_cors"
    ]
    for pkg in packages:
        try:
            __import__(pkg.split("==")[0].replace('-', '_'))
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_packages()

from groq import Groq
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

os.environ["GROQ_API_KEY"] = "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"  # Add your key here
client = Groq(api_key=os.environ["GROQ_API_KEY"])

def extract_text_from_pdf_stream(pdf_file_stream):
    reader = PdfReader(pdf_file_stream)
    return "\n".join([p.extract_text() or "" for p in reader.pages])

def chunk_text(text, chunk_size=500):
    words = text.split()
    return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

embedder = SentenceTransformer("all-MiniLM-L6-v2")

def create_faiss_index(chunks):
    if not chunks:
        return None, []
    embeddings = embedder.encode(chunks)
    dimension = embeddings[0].shape[0]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype('float32'))
    return index, embeddings

def ask_question_rag(query, chunks, index):
    if not index or not chunks:
        return "⚠️ I need a processed PDF to answer questions. Please upload one first."

    question_embedding = embedder.encode([query])
    D, I = index.search(np.array(question_embedding).astype('float32'), 5)
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
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred with the AI model: {str(e)}"

app = Flask(__name__)
CORS(app)

pdf_chunks = []
pdf_index = None
is_pdf_processed = False

@app.route('/')
def serve_index():
    return send_from_directory(os.path.abspath(os.path.dirname(__file__)), 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    allowed_files = ['style.css', 'script.js', 'contact_us.html']
    if filename in allowed_files:
        return send_from_directory(os.path.abspath(os.path.dirname(__file__)), filename)
    return "File not found", 404

@app.route('/api/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded."}), 400

    file = request.files['file']
    if file and file.filename.endswith('.pdf'):
        try:
            pdf_stream = io.BytesIO(file.read())
            text = extract_text_from_pdf_stream(pdf_stream)
            pdf_chunks = chunk_text(text)
            # Optionally, you can also return embeddings, but it's usually enough to return chunks
            return jsonify({"status": "success", "chunks": pdf_chunks})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "Only PDF files are supported."}), 400

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_question = data.get('message')
    pdf_chunks = data.get('chunks')
    if not user_question or not pdf_chunks:
        return jsonify({"response": "No question or chunks provided."}), 400

    try:
        pdf_index, _ = create_faiss_index(pdf_chunks)
        bot_response = ask_question_rag(user_question, pdf_chunks, pdf_index)
        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)