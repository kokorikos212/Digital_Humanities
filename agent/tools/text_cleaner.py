import spacy
import re

def preprocess_for_ner(text, model="en_core_web_sm"):
    """
    Cleans and tokenizes text specifically for Entity Detection.
    Preserves casing (critical for NER) while removing noise.
    """
    # 1. Load model (disable unnecessary components for speed)
    nlp = spacy.load(model, disable=["ner", "parser"])
    
    # 2. Normalize whitespace and remove non-printable characters
    # We keep punctuation as it provides context for entity boundaries
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 3. Process text
    doc = nlp(text)
    
    # 4. Filter tokens: Keep alphanumeric and relevant punctuation
    # We avoid lowercasing because 'Apple' (company) != 'apple' (fruit)
    cleaned_tokens = [
        token.text for token in doc 
        if not token.is_space and not token.is_bracket
    ]
    
    return " ".join(cleaned_tokens)

# Example Usage:
raw_input = """  ## The Dialogue :

**Patrick:** Hello, Maya!

**Maya:** Good evening, Patrick. I hope you managed to study after we split up yesterday. I had some hangups again—political-economic stuff and whatnot. Where is Souzi? I thought you’d come together!

**Patrick:** She’s on her way. Generally, I hear you regarding the concerns you texted me the other day... but I don’t think I can put them into words to ask Vergis about them!

**Maya:** Better that way! Forget it; politics is nothing but trouble. Nothing they teach us in theory actually constitutes the foundations of practice for the “big players.”

**Souzi (Interjecting):** But wait!

**Patrick:** Here comes Souzi to solve our problems... Hello, baby. *(Kiss)*.

**Maya:** Are we changing [the subject]?

**Patrick:** Yes.

**Souzi:** Impossible! I have my own things to contribute to the tank: [HOW DO PEOPLE DRIVE LIKE THAT, MAN!] **Event:** I was coming by bike and this guy cut in front of me turning without a blinker! You know? -> EVEN THOUGH HE HAD JUST OVERTAKEN ME!

**Patrick:** Uh-oh. Let’s solve this first, guys, or we won’t live long enough to see the “end of politics.” Come here, my sweaty one *(Affiliation: Close friend)*, let me give you a hug...
print(preprocess_for_ner(raw_input)) 
# Output: Patrick & Souzi went to ... Paris ! Yesterday 
"""

print(preprocess_for_ner(raw_input))

