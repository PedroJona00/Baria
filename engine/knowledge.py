import json
import re
from .normalizer import normalize

class KnowledgeBase:
    def __init__(self, memory, rules_path):
        self.drinks = memory['bebidas']
        self.by_id = {d['id']: d for d in self.drinks}
        if len(self.by_id) != len(self.drinks): raise ValueError('IDs de bebidas duplicados')
        self.ingredients = sorted({normalize(i['nome']) for d in self.drinks for i in d['ingredientes']}, key=len, reverse=True)
        self.vocabulary = set(re.findall(r'[a-z]+', normalize(' '.join(d['nome'] for d in self.drinks) + ' ' + ' '.join(self.ingredients))))
        self.intent_rules = json.loads(rules_path.read_text(encoding='utf-8'))['intencoes']
        for rule in self.intent_rules:
            for pattern in rule['patterns']: re.compile(pattern)

    def mentioned(self, text):
        found = []
        occupied = []
        for drink in sorted(self.drinks, key=lambda d: -len(d['nome'])):
            for match in re.finditer(r'\b' + re.escape(normalize(drink['nome'])) + r'\b', text):
                if not any(start <= match.start() < end for start, end in occupied):
                    found.append((match.start(), drink['id']))
                    occupied.append(match.span())
        return list(dict.fromkeys(drink_id for _, drink_id in sorted(found)))
