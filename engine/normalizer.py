import re
import unicodedata
from difflib import get_close_matches

ALIASES = {
    'docinho': 'doce', 'docinha': 'doce', 'adocicado': 'doce',
    'azedo': 'citrico', 'azedinho': 'citrico', 'citrica': 'citrico',
    'amarguinho': 'amargo', 'amarga': 'amargo', 'cremosa': 'cremoso',
    'frutada': 'frutado', 'geladinho': 'refrescante', 'gelada': 'refrescante',
    'alcoolica': 'alcoolico', 'alcoolicas': 'alcoolico', 'alcoolicos': 'alcoolico',
    'vc': 'voce', 'pq': 'por que', 'pfv': 'por favor', 'naum': 'nao',
}

def normalize(text):
    text = ''.join(c for c in unicodedata.normalize('NFD', text.casefold()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', text).strip()

class Normalizer:
    def __init__(self, vocabulary):
        self.vocabulary = sorted(set(vocabulary) | set(ALIASES) | {'alcool', 'recomende', 'receita', 'ingredientes', 'curiosidade', 'doce', 'citrico', 'amargo', 'cremoso', 'frutado', 'refrescante'})

    def process(self, text):
        changes = []
        def word(match):
            token = match.group()
            if token in ALIASES:
                return ALIASES[token]
            # Apenas palavras longas e próximas do vocabulário do domínio.
            if len(token) >= 5 and token not in self.vocabulary:
                matches = get_close_matches(token, self.vocabulary, n=2, cutoff=.86)
                if len(matches) == 1:
                    changes.append({'de': token, 'para': matches[0]})
                    return ALIASES.get(matches[0], matches[0])
            return token
        return re.sub(r'\b[a-z]+\b', word, normalize(text)), changes
