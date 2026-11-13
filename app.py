from flask import Flask
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

app = Flask(__name__)

content = ""

try:
    # 1. Load text file
    file_path = Path("static/files/engineering_policy.txt")
    content = file_path.read_text(encoding="utf-8")
except FileNotFoundError:
    print("File not found!")

# 2. Split text into chunks
def chunk_text(text, chunk_size=40, overlap=8):
    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks

chunks = chunk_text(content)

# 3. Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# 4. Generate embeddings
embeddings = model.encode(
    chunks,
    convert_to_numpy=True
).tolist()

# 5. Initialize ChromaDB
client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_or_create_collection(
    name="documents"
)

# 6. Store embeddings and text
collection.add(
    ids=[f"chunk_{i}" for i in range(len(chunks))],
    documents=chunks,
    embeddings=embeddings
)

print(f"Successfully stored {len(chunks)} chunks!")

# User question
query = "What is the Architecture?"

# Convert question into embedding
query_embedding = model.encode(query).tolist()

# Search vector database
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3
)

print("rrr")
# Display relevant chunks
for document in results["documents"][0]:
    print(document)
    print("-" * 50)

@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


if __name__ == '__main__':
    app.run()
