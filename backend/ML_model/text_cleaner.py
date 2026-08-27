# Cleaning of raw text extracted from pdf_reader.py file

import spacy    # NLP library
import re       # regular expression library

# ----- load spaCy model ------------

# Internal/private function used in this module
def _load_model():
    try:
        # "en_core_web_sm" : pre-trained English NLP model by spaCy
        return spacy.load("en_core_web_sem" , disable=["parser"])
    
    except OSError:
        print("text_cleaner WARNING : NLP model not found"
              "RUN : python -m spacy download en_core_web_sm ")

        return spacy.blank("en") # "en" : empty English NLP model pipeline

    # _NLP : internal / private variable
    _NLP = _load_model()


# --------- STEP 1 : Words to keep after spaCy analyze the text

# spaCy provides POS(Parts Of Speech) tag to each token
_KEEP_POS = {"NOUN" , "PRON" , "VERB" , "ADJ"}


# user defined stopward list : words useless for NLP task in this module
_EXTRA_STOPS = {
    "experience", "experienced", "work", "worked", "working",
    "year", "years", "month", "use", "used", "using", "good",
    "strong", "knowledge", "understanding", "ability", "skill",
    "skills", "include", "including", "role", "team", "project",
    "projects", "company", "position", "candidate", "require",
    "required", "requirement", "plus", "preferred", "nice",
    "responsible", "responsibility", "looking", "seek", "hire",
    "join", "lead", "senior", "junior", "intern"
}


# ---------- STEP 2 : takes raw text and return clean list  of tokens/words
def clean_text(text: str) -> list[str]:

    # Pre-cleaning : remove mostly noise before NLP 
    text = re.sub(r"\S+@\S+\.\S+", " ", text)                # email
    text = re.sub(r"\b\d[\d\s\-\+\(\)]{7,}\d\b", " ", text)  # phone number
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)       # URL
    text = re.sub(r"\|", " ", text)                          # pipe/pdf formatting

    doc = _NLP(text)

    tokens = []
    for token in doc:
        #remove punctuation , white spaces and single character
        if token.is_punct or token.is_space:
            continue

        if len(token.text) <= 2:
            continue

        # Lemmatization
        lemma = (token.lemma_ if token.lemma_ else token.text).lower().strip()

        # 1 : empty/short lemma 
        if not lemma or len(lemma) <= 2:
            continue

        # 2 : stopword filtering
        if token.is_stop or lemma in _EXTRA_STOPS: # spaCy built-in stopword list : token.is_stop
            continue

        # 3 : POS filtering
        if token.pop_ != "" and token.pos_ not in _KEEP_POS:
            continue

        # 4 : Removing numbers
        if token.like_num or lemma.isdigit():
            continue

        tokens.append(lemma)

    return tokens


# ------ STEP 3 : Named Entity Recoginization
def extract_named_entities(text:str) -> dict[str,list[str]]:

    #giving text to spaCy model
    doc = _NLP(text) 

    #result dictionary
    entities : dict[str,list[str]] = {
        "persons"    : [],
        "orgs"       : [],
        "dates"      : [],
        "products"   : []
    }

    #dedublication
    seen = set()

    for ent in doc.ents:

        val = ent.text.strip()
        key = val.lower()

        #check dublicates
        if key in seen:
            continue
        else:
            seen.add(key)

        if ent.label_ == "PERSON":
            entities["persons"].append(val)
        elif ent.label_ == "ORG":
            entities["orgs"].append(val)
        elif ent.label_ == "DATE":
            entities["dates"].append(val)
        elif ent.label_ == "PRODUCT":
            entities["products"].append(val)


    return entities


# -------- STEP 4 : return unique tokens
def get_unique_tokens(tokens: list[str]) -> set[str]:
    #no dublicates
    return set(tokens)










    

