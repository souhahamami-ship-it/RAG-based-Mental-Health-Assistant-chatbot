"""

"""

import os


def load_documents(data_dir: str) -> list[dict]:
    documents = []

    files = sorted(os.listdir(data_dir))  # deterministic order, not OS-dependent

    for file in files:
        if file.endswith(".txt"):
            path = os.path.join(data_dir, file)

            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

            documents.append({
                "text": text,
                "source": file
            })

    return documents


def chunk_text(text, chunk_size=1000):
    paragraphs = text.split("\n\n")

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        if len(current_chunk) + len(paragraph) <= chunk_size:
            current_chunk += paragraph + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())

            current_chunk = paragraph + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def load_chunks(data_dir: str) -> list[dict]:
    documents = load_documents(data_dir)

    chunks = []

    for document in documents:
        document_chunks = chunk_text(document["text"])

        for chunk in document_chunks:
            chunks.append({
                "text": chunk,
                "source": document["source"]
            })

    return chunks