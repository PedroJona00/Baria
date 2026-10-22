from dataclasses import dataclass
from .normalizer import normalize

@dataclass(frozen=True)
class Rule:
    name: str
    priority: int
    requires: frozenset
    concludes: str

# Encadeamento determinístico até ponto fixo, sem executar texto do usuário.
INFERENCE_RULES = (
    Rule('restricao_alcool', 100, frozenset({'wants_no_alcohol'}), 'exclude_alcohol'),
    Rule('restricao_ingredientes', 100, frozenset({'has_exclusions'}), 'filter_ingredients'),
    Rule('perfil_sem_alcool', 70, frozenset({'exclude_alcohol', 'wants_refreshing'}), 'prefer_refreshing_non_alcoholic'),
)

class RuleEngine:
    def infer(self, prefs):
        facts, trace = set(), []
        if prefs.get('alcool') == 'nao': facts.add('wants_no_alcohol')
        if prefs.get('sabor') == 'refrescante': facts.add('wants_refreshing')
        if prefs.get('evitar'): facts.add('has_exclusions')
        for _ in range(len(INFERENCE_RULES) + 1):
            changed = False
            for rule in sorted(INFERENCE_RULES, key=lambda r: -r.priority):
                if rule.requires <= facts and rule.concludes not in facts:
                    facts.add(rule.concludes)
                    trace.append(rule.name)
                    changed = True
            if not changed: break
        return facts, trace

    def conflicts(self, entities):
        if len(entities['alcohol']) > 1: return 'alcool'
        if set(entities['flavors']) & set(entities['avoid_flavors']): return 'sabor'
        return None

    def rank(self, kb, state, exclude_recent=False):
        prefs = state['prefs']
        facts, trace = self.infer(prefs)
        avoid = [normalize(x.strip()) for x in prefs.get('evitar', '').split(',') if x.strip()]
        available = [normalize(x.strip()) for x in prefs.get('ingredientes', '').split(',') if x.strip()]
        ranked = []
        for drink in kb.drinks:
            names = [normalize(i['nome']) for i in drink['ingredientes']]
            if 'exclude_alcohol' in facts and drink['alcool']: continue
            if prefs.get('alcool') == 'sim' and not drink['alcool']: continue
            if any(x in name for x in avoid for name in names): continue
            if set(drink['tags']) & set(state['avoid_flavors']): continue
            if exclude_recent and drink['id'] in state['recent_drinks']: continue
            score, reasons = 0, []
            if prefs.get('alcool'): reasons.append('respeita sua escolha ' + ('sem álcool' if prefs['alcool'] == 'nao' else 'com álcool'))
            if prefs.get('sabor') in drink['tags']:
                score += 5
                reasons.append('combina com o perfil ' + prefs['sabor'])
            matching = [x for x in available if any(x in name for name in names)]
            if matching:
                score += len(matching) * 2
                reasons.append('usa ingredientes que você informou: ' + ', '.join(matching))
            if 'prefer_refreshing_non_alcoholic' in facts and not drink['alcool'] and 'refrescante' in drink['tags']: score += 1
            if avoid: reasons.append('não inclui os nomes de ingredientes que você pediu para evitar')
            if state['avoid_flavors']: reasons.append('respeita os perfis de sabor que você excluiu')
            ranked.append({'drink': drink, 'score': score, 'reasons': reasons, 'trace': trace})
        return sorted(ranked, key=lambda r: (-r['score'], r['drink']['id']))
