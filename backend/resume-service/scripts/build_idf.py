"""
Build data/idf_corpus.json from a folder of .txt files (job descriptions and/or resumes).

    python -m scripts.build_idf path/to/folder_of_txt_files

More documents = better IDF. Aim for 200+ job descriptions across roles.
Without this file the service falls back to pair-only IDF (the v1 behaviour).
"""
import sys
from pathlib import Path

from app.config import settings
from app.core.text_cleaner import preprocess
from app.core.tfidf import CorpusIdf


def main(folder: str) -> None:
    files = sorted(Path(folder).glob("*.txt"))
    if not files:
        sys.exit(f"No .txt files found in {folder}")
    docs = [preprocess(f.read_text(encoding="utf-8", errors="ignore")) for f in files]
    corpus = CorpusIdf.from_documents(docs)
    corpus.save(Path(settings.idf_path))
    print(f"Built IDF from {corpus.n_docs} documents, {len(corpus.df)} terms -> {settings.idf_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
