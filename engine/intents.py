import re

class IntentClassifier:
    def classify(self, text, entities, rules, action='chat', preferences=None):
        if action != 'chat': return {'name': action, 'confidence': 1.0, 'candidates': []}
        matches = []
        for rule in rules:
            count = sum(bool(re.search(pattern, text)) for pattern in rule['patterns'])
            if count:
                matches.append({'name': rule['name'], 'confidence': min(.98, rule['confidence'] + .02 * (count-1)), 'priority': rule['priority']})
        if entities['drinks']: matches.append({'name': 'describe', 'confidence': .9, 'priority': 20})
        if any(entities[k] for k in ('flavors', 'avoid_flavors', 'alcohol', 'available', 'avoid')) or preferences:
            matches.append({'name': 'recommend', 'confidence': .85, 'priority': 10})
        matches.sort(key=lambda x: (-x['priority'], -x['confidence']))
        return {**(matches[0] if matches else {'name': 'unknown', 'confidence': .0}), 'candidates': matches[:4]}
