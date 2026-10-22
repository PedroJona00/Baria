class ResponsePlanner:
    """Árvore de decisão: referências explícitas > último assunto > esclarecimento."""
    def plan(self, intent, entities, state, kb):
        name = intent['name']
        targets = entities['drinks']
        if name == 'compare':
            if len(targets) == 1 and state.get('last') and state['last'] != targets[0]: targets = [state['last'], targets[0]]
            if len(targets) != 2: return {'kind': 'clarify', 'message': 'Quais duas bebidas você quer comparar? Escreva os dois nomes.', 'pending': 'compare'}
            return {'kind': 'compare', 'targets': targets}
        if name in ('recipe', 'ingredients', 'fact', 'alcohol_check', 'describe', 'explain'):
            if len(targets) > 1: return {'kind': 'clarify', 'message': 'Você citou mais de uma bebida. Qual delas deseja consultar?'}
            target = targets[0] if targets else state.get('last')
            if not target: return {'kind': 'clarify', 'message': 'Sobre qual bebida? Diga o nome para eu consultar a memória.', 'pending': name}
            return {'kind': name, 'target': target}
        if intent['confidence'] < .6: return {'kind': 'unknown'}
        return {'kind': name}
