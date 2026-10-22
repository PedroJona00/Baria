from datetime import datetime, timezone

class ContextManager:
    def __init__(self, session):
        self.state = session
        session.setdefault('prefs', {})
        session.setdefault('history', [])
        session.setdefault('avoid_flavors', [])
        session.setdefault('recent_drinks', [])
        session.setdefault('template_counts', {})
        session.setdefault('task', 'idle')

    def remember(self, role, text, **metadata):
        history = self.state['history']
        history.append({'role': role, 'text': text, 'at': datetime.now(timezone.utc).isoformat(), **metadata})
        del history[:-60]

    def merge(self, ui, entities):
        state, prefs = self.state, self.state['prefs']
        changes = []
        patch = dict(ui)
        if entities['alcohol']: patch['alcool'] = entities['alcohol'][-1]
        if entities['flavors']: patch['sabor'] = entities['flavors'][-1]
        if entities['available']: patch['ingredientes'] = ', '.join(entities['available'])
        if entities['avoid']:
            patch['evitar'] = ', '.join(dict.fromkeys([x.strip() for x in patch.get('evitar', prefs.get('evitar', '')).split(',') if x.strip()] + entities['avoid']))
        for key, value in patch.items():
            if key in prefs and prefs[key] and prefs[key] != value:
                changes.append({'field': key, 'before': prefs[key], 'after': value})
            prefs[key] = value
        for flavor in entities['avoid_flavors']:
            if flavor not in state['avoid_flavors']: state['avoid_flavors'].append(flavor)
            if prefs.get('sabor') == flavor: prefs['sabor'] = ''
        # Uma preferência positiva mais recente substitui sua negação anterior.
        state['avoid_flavors'] = [f for f in state['avoid_flavors'] if f not in entities['flavors'] and f != ui.get('sabor')]
        if entities['detail']: state['detail'] = entities['detail']
        state['changes'] = changes
        state['entities'] = entities
        return changes
