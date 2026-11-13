import json
import logging
import os
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import chromadb
from flask import Flask, jsonify, request
from sentence_transformers import SentenceTransformer

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

CHUNK_SIZE = 40
CHUNK_OVERLAP = 8
RESULT_COUNT = 3
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_TIMEOUT = 120

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="documents")
model = None
model_lock = Lock()
collection_lock = Lock()


def get_model():
    global model
    if model is None:
        with model_lock:
            if model is None:
                model = SentenceTransformer("all-MiniLM-L6-v2")
    return model


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    step = chunk_size - overlap
    return [
        " ".join(words[start : start + chunk_size])
        for start in range(0, len(words), step)
    ]


def generate_answer(question, context):
    ollama_request = Request(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        data=json.dumps(
            {
                "model": OLLAMA_MODEL,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Answer the user's question using only the provided "
                            "document excerpts. If the excerpts do not contain "
                            "the answer, say that the document does not provide "
                            "enough information. Do not invent facts."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Document excerpts:\n{context}\n\n"
                            f"Question: {question}"
                        ),
                    },
                ],
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(ollama_request, timeout=OLLAMA_TIMEOUT) as response:
        ollama_result = json.loads(response.read().decode("utf-8"))

    answer = ollama_result.get("message", {}).get("content")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Ollama returned an empty or invalid response.")
    return answer.strip()


@app.post("/upload_file")
def upload_file():
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify(error="Upload a .txt file using the 'file' field."), 400

    if not uploaded_file.filename.lower().endswith(".txt"):
        return jsonify(error="Only .txt files are supported."), 400

    try:
        content = uploaded_file.read().decode("utf-8").strip()
    except UnicodeDecodeError:
        return jsonify(error="The uploaded file must be UTF-8 encoded text."), 400

    if not content:
        return jsonify(error="The uploaded file is empty."), 400

    chunks = chunk_text(content)
    try:
        embeddings = get_model().encode(
            chunks,
            convert_to_numpy=True,
        ).tolist()

        with collection_lock:
            existing_ids = collection.get(include=[])["ids"]
            if existing_ids:
                collection.delete(ids=existing_ids)
            collection.add(
                ids=[f"chunk_{index}" for index in range(len(chunks))],
                documents=chunks,
                embeddings=embeddings,
                metadatas=[
                    {"filename": uploaded_file.filename} for _ in chunks
                ],
            )
    except Exception:
        app.logger.exception("Failed to index uploaded text file")
        return jsonify(error="Failed to process the uploaded file."), 500

    return jsonify(
        message="File uploaded and indexed successfully.",
        filename=uploaded_file.filename,
        chunks=len(chunks),
    ), 200


@app.post("/ask")
def ask():
    payload = request.get_json(silent=True)
    question = payload.get("question") if isinstance(payload, dict) else None
    if not isinstance(question, str) or not question.strip():
        return jsonify(error="Provide a non-empty 'question' in the JSON body."), 400

    try:
        query_embedding = get_model().encode(question.strip()).tolist()
        with collection_lock:
            document_count = collection.count()
            if document_count == 0:
                return jsonify(error="Upload a .txt file before asking a question."), 409

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(RESULT_COUNT, document_count),
                include=["documents", "distances", "metadatas"],
            )
    except Exception:
        app.logger.exception("Failed to retrieve relevant text")
        return jsonify(error="Failed to search the uploaded document."), 500

    documents = results["documents"][0]
    context = "\n\n---\n\n".join(documents)
    try:
        answer = generate_answer(question.strip(), context)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        app.logger.exception("Failed to generate an answer with Ollama")
        return jsonify(
            error=(
                "Could not get a response from Ollama. Make sure Ollama is running "
                f"and the {OLLAMA_MODEL} model is available."
            )
        ), 502

    return jsonify(question=question.strip(), answer=answer), 200


if __name__ == "__main__":
    app.run()
