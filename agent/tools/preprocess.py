import spacy 

class Preprocessor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
    
    def preprocess(self, text):
        doc = self.nlp(text)
        # Example preprocessing: lemmatization and stop word removal
        processed_tokens = [token.lemma_ for token in doc if not token.is_stop]
        return " ".join(processed_tokens)