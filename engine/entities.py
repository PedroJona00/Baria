import re
from datetime import datetime

FLAVORS = ('doce', 'citrico', 'amargo', 'frutado', 'cremoso', 'refrescante', 'quente')

def negated(text, start):
    # Escopo local: não propaga uma negação através de outra oração.
    before = re.split(r'[,;.!?]|\b(?:mas|porem|prefiro|quero|gosto de)\b', text[:start])[-1]
    local = text[max(0, start - 40):start]
    return bool(re.search(r'(?:nao (?:gosto|quero|prefiro)(?: de)?|sem|evit[oa]|nada de|menos|pouco)\s+(?:muito\s+|algo\s+)?$', local) or re.search(r'\b(?:sem|evito|nada de)\b[^.;!?]*$', before))

class EntityExtractor:
    def extract(self, text, kb):
        entities = {'drinks': kb.mentioned(text), 'flavors': [], 'avoid_flavors': [], 'avoid': [], 'available': [], 'alcohol': [], 'numbers': [], 'dates': [], 'invalid_dates': []}
        alcohol_patterns = [
            ('nao', r'\b(?:sem alcool|zero alcool|nao alcoolico|mocktail|nao (?:quero|bebo|gosto de) (?:algo |bebida |bebidas |com )?(?:alcool|alcoolico))\b'),
            ('sim', r'\b(?:com alcool|quero alcool|alcoolico)\b'),
        ]
        for value, pattern in alcohol_patterns:
            for match in re.finditer(pattern, text):
                if value == 'sim' and (text[max(0, match.start()-4):match.start()].strip() == 'nao' or negated(text, match.start())): continue
                entities['alcohol'].append(value)
        entities['alcohol'] = list(dict.fromkeys(entities['alcohol']))
        flavor_text = re.sub(r'\b(?:sem alcool|zero alcool|nao alcoolico)\b', lambda m: ' ' * len(m.group()), text)
        for flavor in FLAVORS:
            for m in re.finditer(r'\b' + flavor + r'\b', text):
                entities['avoid_flavors' if negated(flavor_text, m.start()) else 'flavors'].append(flavor)
        for ingredient in kb.ingredients:
            for m in re.finditer(r'\b' + re.escape(ingredient) + r'\b', text):
                if negated(text, m.start()): entities['avoid'].append(ingredient)
                elif re.search(r'\b(?:tenho|disponivel|usar|com)\b', text[:m.start()]): entities['available'].append(ingredient)
        # Termos genéricos úteis que não são nomes exatos no catálogo.
        for ingredient in ('leite', 'cafe', 'gin', 'rum', 'alcool'):
            if ingredient == 'alcool': continue
            for m in re.finditer(r'\b'+ingredient+r'\b', text):
                if negated(text, m.start()): entities['avoid'].append(ingredient)
        entities['avoid'] = list(dict.fromkeys(entities['avoid']))
        entities['available'] = list(dict.fromkeys(entities['available']))
        for match in re.finditer(r'\b\d{1,2}/\d{1,2}/\d{4}\b', text):
            try: entities['dates'].append(datetime.strptime(match.group(), '%d/%m/%Y').date().isoformat())
            except ValueError: entities['invalid_dates'].append(match.group())
        without_dates = re.sub(r'\b\d{1,2}/\d{1,2}/\d{4}\b', '', text)
        for m in re.finditer(r'\b(\d+(?:[.,]\d+)?)\s*(ml|litros?|l|g|pessoas?|porcoes|copos?)?\b', without_dates):
            entities['numbers'].append({'value': float(m[1].replace(',', '.')), 'unit': m[2] or ''})
        entities['reference'] = bool(re.search(r'\b(?:ele|ela|dele|dela|esse|essa|isso|o anterior|a anterior)\b', text))
        entities['detail'] = 'short' if re.search(r'\b(?:resuma|resumo|curto|curta|breve)\b', text) else 'long' if re.search(r'\b(?:detalh\w*|passo a passo|completo)\b', text) else None
        entities['correction'] = bool(re.search(r'\b(?:na verdade|corrigindo|mudei de ideia|agora prefiro)\b', text))
        return entities
