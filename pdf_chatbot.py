# pdf_chatbot.py

import os
import subprocess
import sys

# -------- Install Required Packages --------
def install_packages():
    packages = [
        "groq",
        "faiss-cpu",
        "PyPDF2",
        "sentence-transformers",
        "gradio"
    ]
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)

install_packages()

# -------- Imports --------
from groq import Groq
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import gradio as gr

# -------- API Key --------
os.environ["GROQ_API_KEY"] = "" #<------- Insert your API Key here
client = Groq(api_key=os.environ["GROQ_API_KEY"])

# -------- PDF Text Extraction --------
def extract_text_from_pdf(path):
    reader = PdfReader(path)
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

# -------- Ask Question --------
def ask_question(query, chunks, index):
    question_embedding = embedder.encode([query])
    D, I = index.search(np.array(question_embedding), 5)
    context = "\n\n".join([chunks[i] for i in I[0]])

    prompt = f"""Answer the question using ONLY the context below.

Context:
{context}

Question: {query}
Answer:"""

    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that only answers using the given context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )

    return response.choices[0].message.content.strip()

# -------- Gradio Interface --------
pdf_chunks = []
pdf_index = None

def process_pdf(file):
    global pdf_chunks, pdf_index

    text = extract_text_from_pdf(file.name)
    pdf_chunks = chunk_text(text)
    pdf_index, _ = create_faiss_index(pdf_chunks)

    return "✅ PDF uploaded and processed. You can now ask questions."

def query_pdf(question):
    if not pdf_chunks or not pdf_index:
        return "⚠️ Please upload a PDF first."

    return ask_question(question, pdf_chunks, pdf_index)

def run_gradio():
    with gr.Blocks() as demo:
        gr.Markdown("## 🧠 PDF Chatbot — Powered by Groq + LLaMA 3\nUpload a PDF and ask questions based on it.")

        with gr.Row():
            pdf_upload = gr.File(label="Upload your PDF", file_types=[".pdf"])
            upload_status = gr.Textbox(label="Status", interactive=False)

        upload_btn = gr.Button("Process PDF")
        upload_btn.click(process_pdf, inputs=[pdf_upload], outputs=[upload_status])

        question_input = gr.Textbox(label="Ask a question")
        answer_output = gr.Textbox(label="Answer", lines=5)
        question_input.submit(query_pdf, inputs=[question_input], outputs=[answer_output])

    demo.launch(share=True)

# -------- CLI Mode (Optional) --------
def run_cli():
    pdf_path = input("📄 Enter path to your PDF file: ")
    if not os.path.exists(pdf_path):
        print("❌ File not found.")
        return

    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text)
    index, _ = create_faiss_index(chunks)

    print("✅ PDF loaded and indexed.")
    while True:
        q = input("\n❓ Ask a question (or 'exit'): ")
        if q.lower() == "exit":
            break
        print("\n🧠 Answer:\n", ask_question(q, chunks, index))

# -------- Entry Point --------
if __name__ == "__main__":
    mode = input("Choose mode: [1] CLI  [2] Gradio Web App: ").strip()
    if mode == "1":
        run_cli()
    else:
        run_gradio()
