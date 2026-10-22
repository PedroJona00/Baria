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
        if not isinstance(self.intent_rules, list):
            raise ValueError('Intenções precisam ser uma lista.')
        for rule in self.intent_rules:
            if not isinstance(rule, dict) or not isinstance(rule.get('name'), str) or not rule['name']:
                raise ValueError('Intenção sem nome.')
            if type(rule.get('priority')) is not int or type(rule.get('confidence')) not in (int, float) or not 0 <= rule['confidence'] <= 1:
                raise ValueError('Prioridade ou confiança inválida.')
            if not isinstance(rule.get('patterns'), list) or not rule['patterns'] or not all(isinstance(pattern, str) for pattern in rule['patterns']):
                raise ValueError('Padrões de intenção inválidos.')
            rule['patterns'] = [re.compile(pattern) for pattern in rule['patterns']]
        self.name_patterns = [
            (drink['id'], re.compile(r'\b' + re.escape(normalize(drink['nome'])) + r'\b'))
            for drink in sorted(self.drinks, key=lambda drink: -len(drink['nome']))
        ]

    def mentioned(self, text):
        found = []
        occupied = []
        for drink_id, pattern in self.name_patterns:
            for match in pattern.finditer(text):
                if not any(start <= match.start() < end for start, end in occupied):
                    found.append((match.start(), drink_id))
                    occupied.append(match.span())
        return list(dict.fromkeys(drink_id for _, drink_id in sorted(found)))
