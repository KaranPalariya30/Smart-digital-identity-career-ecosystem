"""spaCy-based preprocessing (unchanged logic from v1, model now loaded lazily)."""
import re
from functools import lru_cache

import spacy

_KEEP_POS = {"NOUN", "PROPN", "VERB", "ADJ"}

_EXTRA_STOPS = {
    "experience", "experienced", "work", "worked", "working",
    "year", "years", "month", "use", "used", "using", "good",
    "strong", "knowledge", "understanding", "ability", "skill",
    "skills", "include", "including", "role", "team", "project",
    "projects", "company", "position", "candidate", "require",
    "required", "requirement", "plus", "preferred", "nice",
    "responsible", "responsibility", "looking", "seek", "hire",
    "join", "lead", "senior", "junior", "intern",
}


@lru_cache(maxsize=1)
def _nlp():
    try:
        return spacy.load("en_core_web_sm", disable=["parser"])
    except OSError:
        print("[text_cleaner] WARNING: en_core_web_sm missing - using blank model. "
              "Run: python -m spacy download en_core_web_sm")
        return spacy.blank("en")


def clean_text(text: str) -> list[str]:
    text = re.sub(r"\S+@\S+\.\S+", " ", text)                       # emails
    text = re.sub(r"\b\d[\d\s\-\+\(\)]{7,}\d\b", " ", text)         # phone numbers
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)              # URLs
    text = re.sub(r"\|", " ", text)                                 # pipes from PDFs

    tokens = []
    for token in _nlp()(text):
        if token.is_punct or token.is_space or len(token.text) <= 2:
            continue
        lemma = (token.lemma_ if token.lemma_ else token.text).lower().strip()
        if not lemma or len(lemma) <= 2:
            continue
        if token.is_stop or lemma in _EXTRA_STOPS:
            continue
        if token.pos_ != "" and token.pos_ not in _KEEP_POS:
            continue
        if token.like_num or lemma.isdigit():
            continue
        tokens.append(lemma)
    return tokens


def extract_bigrams(tokens: list[str]) -> list[str]:
    return [tokens[i] + "_" + tokens[i + 1] for i in range(len(tokens) - 1)]


def preprocess(text: str, include_bigrams: bool = True) -> list[str]:
    tokens = clean_text(text)
    return tokens + extract_bigrams(tokens) if include_bigrams else tokens


def extract_named_entities(text: str) -> dict[str, list[str]]:
    """Kept for the future profile agent (orgs, dates, people in a resume)."""
    ents: dict[str, list[str]] = {"persons": [], "orgs": [], "dates": [], "products": []}
    label_map = {"PERSON": "persons", "ORG": "orgs", "DATE": "dates", "PRODUCT": "products"}
    seen = set()
    for ent in _nlp()(text).ents:
        key = ent.text.strip().lower()
        if key in seen or ent.label_ not in label_map:
            continue
        seen.add(key)
        ents[label_map[ent.label_]].append(ent.text.strip())
    return ents
