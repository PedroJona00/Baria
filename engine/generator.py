class LanguageGenerator:
    TEMPLATES = {
        'recommend': ('Minha sugestão é {name}.', 'Para essas preferências, sugiro {name}.', 'Uma opção que combina com seu pedido é {name}.'),
        'greet': ('Olá! Vamos encontrar sua bebida? Você prefere com ou sem álcool, e qual sabor?', 'Boas-vindas ao balcão! Conte seu gosto ou diga o nome de uma bebida.'),
        'unknown': ('Não consegui identificar seu pedido com segurança. Posso recomendar bebidas, mostrar receitas ou comparar duas opções. Por exemplo: “algo cítrico sem álcool”.', 'Esse pedido ficou fora das regras que conheço. Você quer uma recomendação ou informações sobre uma bebida?'),
    }

    def template(self, template_key, state, **values):
        choices = self.TEMPLATES[template_key]
        counts = state['template_counts']
        index = counts.get(template_key, 0)
        counts[template_key] = index + 1
        return choices[index % len(choices)].format(**values)

    def recommendation(self, item, state):
        drink = item['drink']
        text = self.template('recommend', state, name=drink['nome'])
        reasons = item['reasons'] or ['é uma opção disponível na minha base; ainda faltam preferências para personalizar melhor']
        text += ' ' + reasons[0][0].upper() + reasons[0][1:] + '.'
        if state.get('detail') != 'short':
            if len(reasons) > 1: text += '\nTambém ' + '; '.join(reasons[1:]) + '.'
            if state['prefs'].get('sabor') and state['prefs']['sabor'] not in drink['tags']: text += '\nNão encontrei correspondência exata com o sabor pedido entre as opções priorizadas.'
            if state['prefs'].get('ingredientes'): text += '\nConfira a lista completa: você pode precisar de ingredientes adicionais.'
            text += '\nA receita está no painel. Ao encerrar a conversa, você poderá adicionar uma curiosidade.'
        text += '\n\nIngredientes:\n' + '\n'.join('• ' + i['nome'] + ': ' + i['quantidade'] for i in drink['ingredientes'])
        return text

    def information(self, kind, drink, state):
        name = drink['nome']
        if kind == 'recipe':
            ingredients = '; '.join(i['nome'] + ': ' + i['quantidade'] for i in drink['ingredientes'])
            return f'{name} — preparo: {drink["preparo"]}' if state.get('detail') == 'short' else f'Para preparar {name}:\n1. Separe: {ingredients}.\n2. {drink["preparo"]}\nAs quantidades são da receita de referência cadastrada.'
        if kind == 'ingredients': return name + ' leva: ' + '; '.join(i['nome'] + ' (' + i['quantidade'] + ')' for i in drink['ingredientes']) + '.'
        if kind == 'alcohol_check': return name + (' contém álcool.' if drink['alcool'] else ' não leva bebida alcoólica na receita cadastrada.')
        if kind == 'fact':
            text = f'Sobre {name}, minha base registra: {drink["curiosidade"]}'
            if drink['contribuicoes'] and state.get('detail') != 'short': text += '\nContribuições não verificadas: ' + ' | '.join(c['texto'] for c in drink['contribuicoes'][-3:])
            return text
        return f'{name} é uma bebida da categoria {drink["categoria"]}, ' + ('com álcool' if drink['alcool'] else 'sem álcool') + '. Perfis cadastrados: ' + ', '.join(drink['tags']) + '. ' + drink['curiosidade']
