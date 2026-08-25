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






    


    
