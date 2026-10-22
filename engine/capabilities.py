"""Capacidades práticas por regras; nenhuma alteração automática de receitas."""
import copy
import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from .normalizer import normalize
from .rules import RuleEngine
from .generator import LanguageGenerator
from .online import search_drink

FOOD_SOURCE = 'https://www.fda.gov/food/buy-store-serve-safe-food/refrigerator-thermometers-cold-facts-about-food-safety'
NUMBERS = {'um':1,'uma':1,'dois':2,'duas':2,'tres':3,'quatro':4,'cinco':5,
           'seis':6,'sete':7,'oito':8,'nove':9,'dez':10,'onze':11,'doze':12,
           'quinze':15,'vinte':20}
OCCASIONS = {
    'churrasco': ('citrico', 'um perfil cítrico pode contrastar com pratos de sabor intenso'),
    'praia': ('refrescante', 'um perfil refrescante combina com a proposta da ocasião'),
    'piscina': ('refrescante', 'priorizei um perfil refrescante'),
    'festa': ('frutado', 'um perfil frutado é uma opção para explorar em uma festa'),
    'aniversario': ('frutado', 'priorizei um perfil frutado para a ocasião'),
    'jantar': ('citrico', 'um perfil cítrico é um ponto de partida; a combinação depende do prato'),
    'pizza': ('refrescante', 'priorizei um perfil refrescante para acompanhar a refeição'),
    'sobremesa': ('amargo', 'um perfil amargo pode contrastar com a doçura da sobremesa'),
    'cafe da manha': ('quente', 'priorizei uma opção quente'),
    'dia frio': ('quente', 'priorizei uma bebida quente'),
}
SUBSTITUTIONS = {
    ('cachaca','vodka'): 'É uma adaptação possível; na caipirinha, a versão com vodka é chamada caipiroska. O sabor muda. Use o mesmo volume como ponto de partida.',
    ('vodka','cachaca'): 'É uma adaptação possível, com mudança no sabor do destilado. Use o mesmo volume como ponto de partida.',
    ('rum branco','vodka'): 'A vodka muda o perfil aromático da receita. Use o mesmo volume como ponto de partida para uma adaptação.',
    ('leite','bebida de aveia'): 'Pode usar o mesmo volume como ponto de partida. A textura e a espuma dependem da bebida vegetal; confira os ingredientes no rótulo.',
    ('leite','leite de coco'): 'Pode adaptar, mas o coco muda bastante o sabor e pode engrossar a bebida. Comece com uma parte e ajuste a consistência.',
    ('acucar','mel'): 'É uma adaptação de doçura, sem equivalência exata por colher. Dissolva uma pequena quantidade de mel antes de misturar e ajuste aos poucos.',
    ('agua com gas','agua'): 'Pode trocar pelo mesmo volume, mas a bebida ficará sem efervescência.',
    ('agua tonica','agua com gas'): 'Pode usar o mesmo volume, mas perderá o amargor e a doçura da tônica.',
}
ALCOHOL_INGREDIENTS = ('vodka','cachaca','gin','rum','tequila','whisky','vinho','espumante','licor','campari','aperol','vermut','limoncello','cerveja','sidra')

def number(text):
    if text in NUMBERS: return NUMBERS[text]
    try: return int(text)
    except (ValueError, TypeError): return None

def quantity(text, multiplier):
    match = re.match(r'^(\d+(?:/\d+|[.,]\d+)?)\s*(.*)$', text)
    if not match: return text + ' (ajuste ao servir)'
    value = Fraction(match[1].replace(',', '.')) * multiplier
    if value.denominator == 1: formatted = str(value.numerator)
    else: formatted = f'{float(value):.2f}'.rstrip('0').rstrip('.').replace('.', ',')
    unit=match[2]
    if value != 1:
        plurals={'unidade':'unidades','colher':'colheres','xícara':'xícaras','fatia':'fatias','bola':'bolas','gota':'gotas','rodela':'rodelas','folha':'folhas'}
        word=unit.split(' ',1)[0]
        if word in plurals: unit=plurals[word]+unit[len(word):]
    return formatted + (' ' + unit if unit else '')

def taste_adjustment(text, state):
    """Identifica direção do ajuste sem confundir elogios, negações e preferências."""
    q = normalize(text)
    # Correção local e conservadora: preserva o texto e o catálogo originais.
    q = re.sub(r'\bsuavis', 'suaviz', q)

    def negated(position):
        clause = re.split(r'[,;.!?]|\b(?:mas|porem|e)\b', q[:position])[-1]
        return bool(re.search(r'\b(?:nao|nunca|nem)\b', ' '.join(clause.split()[-5:])))

    desired = (
        ('soften', r'\b(?:suaviz\w*|ameniz\w*|diluir|dilua|diluindo)\b|\b(?:menos\s+(?:forte|intens[oa])|mais\s+(?:suave|leve|frac[oa])|nao\s+tao\s+forte)\b'),
        ('strengthen', r'\b(?:mais\s+(?:forte|intens[oa]|encorpad[oa])|menos\s+(?:frac[oa]|aguad[oa]|ral[oa]))\b'),
        ('less_sweet', r'\bmenos\s+(?:doce|adocicad[oa])\b'),
        ('more_sweet', r'\bmais\s+(?:doce|adocicad[oa])\b|\b(?:adocar|adoce)\b'),
        ('less_bitter', r'\bmenos\s+amarg[oa]\b|\b(?:reduzir|diminuir|tirar|amenizar)\s+(?:o\s+)?amargor\b'),
        ('less_sour', r'\bmenos\s+(?:azed[oa]|acid[oa])\b|\b(?:reduzir|diminuir|tirar|amenizar)\s+(?:a\s+)?acidez\b'),
    )
    requests = []
    rejected = set()
    for kind, pattern in desired:
        for match in re.finditer(pattern, q):
            if not negated(match.start()):
                requests.append(kind)
            else:
                rejected.add(kind)
    # “Quero suave” e “deixar a bebida fraca” também expressam um objetivo.
    adjective = r'forte|intens[oa]|pesad[oa]|suave|leve|frac[oa]|aguad[oa]|ral[oa]|doce|amarg[oa]|azed[oa]|acid[oa]|sem\s+(?:sabor|gosto)'
    goals = re.finditer(r'\b(?:quero|prefiro|deixe|deixar|torne|tornar)\b(?:\s+\w+){0,4}?\s+(?P<quality>' + adjective + r')\b', q)
    for match in goals:
        if re.search(r'\b(?:mais|menos)\b', match.group()):
            continue
        if match.group().split()[0] in ('quero', 'prefiro') and not (state.get('last') or state.get('cap_pending', {}).get('kind') == 'taste'):
            continue
        if not negated(match.start()):
            quality = match['quality']
            if re.fullmatch(r'suave|leve|frac[oa]', quality):
                requests.append('soften')
    specific = set(requests) - {'soften'}
    if specific and specific <= {'less_bitter', 'less_sour'}:
        requests = list(specific)
    elif specific and 'soften' in requests and specific <= {'less_sweet'}:
        requests = list(specific)
    if requests:
        kinds = set(requests)
        return next(iter(kinds)) if len(kinds) == 1 else 'clarify'

    observed = re.finditer(
        r'\b(?:ficou|ficaram|esta|estava|ta|achei|senti|parece|pareceu)\b'
        r'(?:\s+\w+){0,5}?\s+(?P<quality>' + adjective + r')\b', q,
    )
    problems = []
    for match in observed:
        if not negated(match.start()):
            quality = match['quality']
            if re.fullmatch(r'forte|intens[oa]|pesad[oa]', quality):
                problems.append('soften')
            elif re.fullmatch(r'frac[oa]|aguad[oa]|ral[oa]|sem\s+(?:sabor|gosto)', quality):
                problems.append('strengthen')
            elif quality == 'doce':
                problems.append('less_sweet')
            elif re.fullmatch(r'amarg[oa]', quality):
                problems.append('less_bitter')
            elif re.fullmatch(r'azed[oa]|acid[oa]', quality):
                problems.append('less_sour')
    if problems:
        return problems[-1] if problems[-1] not in rejected else None

    brief = re.fullmatch(
        r'(?:(?:a|o|minha|meu|essa|esse)\s+)?(?:(?:bebida|drink|cafe|cha)\s+)?'
        r'(?:muito\s+)?(?P<quality>' + adjective + r')(?:\s+demais)?[.!?]*', q,
    )
    if brief:
        quality = brief['quality']
        if quality in ('suave', 'leve') and (state.get('last') or state.get('cap_pending', {}).get('kind') == 'taste'):
            return 'soften'
        if re.fullmatch(r'forte|intens[oa]|pesad[oa]', quality):
            return 'soften'
        if re.fullmatch(r'frac[oa]|aguad[oa]|ral[oa]|sem\s+(?:sabor|gosto)', quality):
            return 'strengthen'
        # Sabores isolados continuam sendo preferências fora de uma tarefa de ajuste.
        if state.get('cap_pending', {}).get('kind') == 'taste':
            if quality == 'doce':
                return 'less_sweet'
            if re.fullmatch(r'amarg[oa]', quality):
                return 'less_bitter'
            if re.fullmatch(r'azed[oa]|acid[oa]', quality):
                return 'less_sour'
    if re.search(r'\b(?:corrigir|ajustar|mudar)\s+(?:o\s+)?sabor\b', q):
        return 'clarify'
    return None


def detect(text, state):
    q = normalize(text)
    if re.search(r'\b(pesquis[ae]|busque|buscar|procure)\b.*\b(internet|web|wikipedia|fora do catalogo)\b', q) or re.search(r'\b(pesquis[ae]|busque|procure)\s+(?:sobre\s+)?',q):
        return 'online'
    if re.search(r'\b(trocar|substituir|substituo|troco|substituicao)\b',q): return 'substitute'
    if re.search(r'\b(sem|nao tenho)\s+(?:uma? |o |a )?(coqueteleira|liquidificador|coador|dosador|macerador)\b',q): return 'equipment'
    if taste_adjustment(text, state):
        return 'taste'
    if re.search(r'\b(conservar|conservacao|guardar|armazenar|geladeira|dura|estraga)\b|hoje.*amanha|amanha.*servir',q): return 'storage'
    if re.search(r'\b(orcamento|gastar|gastando|custo|custos|preco|precos|custa|barato|barata|reais)\b|r\$',q): return 'budget'
    if re.search(r'\b(?:para|rende|render|quantidade para)\s+[-\w.,]+\s+(pessoas?|porcoes|copos?|doses?)\b|\b(?:porcoes|dobrar|triplicar)\b',q): return 'scale'
    if any(re.search(r'\b'+re.escape(x)+r'\b',q) for x in OCCASIONS): return 'occasion'
    pending = state.get('cap_pending')
    if pending and (q in ('cancelar','cancela','deixa pra la') or q in NUMBERS or q.isdigit() or '=' in q): return pending['kind']
    if pending:
        if pending['kind']=='taste' and re.fullmatch(r'(?:muito )?(?:doce|amargo|azedo|forte|aguado)',q): return 'taste'
        if pending['kind']=='equipment' and q in ('coqueteleira','liquidificador','coador','dosador','macerador'): return 'equipment'
        if pending['kind']=='substitute' and re.fullmatch(r'[\w ]+ por [\w ]+',q): return 'substitute'
        if pending['kind']=='online' and re.fullmatch(r'[\w ()-]{1,80}',q): return 'online'
    return None

class Capabilities:
    def __init__(self, kb, state):
        self.kb, self.state = kb, state

    def ask(self, kind, message, **saved):
        self.state['cap_pending'] = {'kind':kind, **saved}
        self.state['task'] = 'awaiting_clarification'
        return {'message':message}

    def target(self, text):
        names = self.kb.mentioned(normalize(text))
        if len(names) > 1: return None
        target = names[0] if names else self.state.get('last')
        return self.kb.by_id.get(target)

    def handle(self, kind, text):
        q = normalize(text)
        if q in ('cancelar','cancela','deixa pra la'):
            self.state.pop('cap_pending',None)
            self.state['task']='idle'
            return {'message':'Pedido cancelado. Você pode perguntar por outra bebida.'}
        pending = self.state.pop('cap_pending', {})
        self.state['task']='idle'
        if pending.get('kind') == kind:
            # Mescla somente dados de uma tarefa do mesmo tipo.
            text = pending.get('original','') + '\n' + text
            q = normalize(text)
        return getattr(self, kind)(text, q, pending)

    def scale(self, text, q, pending):
        drink = self.target(text)
        if not drink:
            return self.ask('scale','Qual bebida e quantas porções? Exemplo: “Caipirinha para 10 pessoas”.', original=text)
        self.state['last']=drink['id']
        if re.search(r'(?<!\w)(?:-\d+|\d+[.,]\d+)\s+(?:pessoas?|porcoes|copos?|doses?)',q):
            return self.ask('scale','Informe um número inteiro positivo de porções, de 1 a 200.',original='Porções de '+drink['nome'])
        matches = re.findall(r'\b(?:para\s+)?(\d+|\w+)\s+(?:pessoas?|porcoes|copos?|doses?)\b',q)
        count = number(matches[-1]) if matches else None
        if count is None and 'dobrar' in q: count=2
        if count is None and 'triplicar' in q: count=3
        if count is None:
            count=number(q.split()[-1]) if q.split() else None
        if count is None:
            return self.ask('scale', f'Quantas porções de {drink["nome"]}? Vou considerar uma receita cadastrada por pessoa.', original='Porções de '+drink['nome'])
        if not 1 <= count <= 200:
            return self.ask('scale','Informe um número inteiro de 1 a 200 porções.',original='Porções de '+drink['nome'])
        ingredients = [{'nome':i['nome'],'quantidade':quantity(i['quantidade'],count)} for i in drink['ingredientes']]
        message=f'{drink["nome"]} para {count} porções — considerei a receita cadastrada como 1 porção e uma por pessoa:\n'
        message+='\n'.join('• '+i['nome']+': '+i['quantidade'] for i in ingredients)
        message+='\n\nPreparo: '+drink['preparo']+'\nPrepare em lotes se necessário. Gelo e itens “a gosto” são ajustados ao servir. O painel lateral mantém a receita-base.'
        return {'message':message,'scaled_recipe':{'id':drink['id'],'portions':count,'ingredientes':ingredients}}

    def substitute(self,text,q,pending):
        if pending.get('kind')=='substitute' and ' por ' in q and not re.search(r'\b(?:trocar|troco|substituir|substituo)\b',q):
            q='trocar '+q
        match=re.search(r'\b(?:trocar|troco|substituir|substituo)\s+(?:o |a )?(.+?)\s+(?:por|pelo|pela)\s+(.+?)(?:[?.!;\n]|$)',q)
        if not match:
            return self.ask('substitute','Qual ingrediente deseja substituir e por qual? Exemplo: “trocar cachaça por vodka na caipirinha”.')
        source, replacement = match[1].strip(),re.split(r'\s+(?:na|no|em)\s+',match[2])[0].strip()
        source=source.removeprefix('a ').removeprefix('o ')
        replacement=replacement.removeprefix('a ').removeprefix('o ')
        drink=self.target(text)
        if drink and not any(source in normalize(i['nome']) for i in drink['ingredientes']):
            return {'message':f'Não encontrei {source} na receita de {drink["nome"]}. Diga o ingrediente e a bebida que deseja adaptar.'}
        avoid=[normalize(x.strip()) for x in self.state['prefs'].get('evitar','').split(',') if x.strip()]
        if any(x in replacement for x in avoid):
            return {'message':'O ingrediente proposto está entre os que você pediu para evitar. Não vou sugerir essa troca.'}
        if self.state['prefs'].get('alcool')=='nao' and any(x in replacement for x in ALCOHOL_INGREDIENTS):
            return {'message':'Essa troca acrescenta bebida alcoólica e conflita com sua preferência sem álcool. Escolha outra substituição ou altere sua preferência.'}
        advice=SUBSTITUTIONS.get((source,replacement))
        if not advice:
            return {'message':f'Não tenho uma regra validada para trocar {source} por {replacement}. Não vou afirmar que os ingredientes são equivalentes.'}
        if drink: self.state['last']=drink['id']
        return {'message':advice+'\nEsta é uma sugestão de adaptação; a receita original no catálogo permanece igual.'}

    def equipment(self,text,q,pending):
        tool=next((x for x in ('coqueteleira','liquidificador','coador','dosador','macerador') if x in q),None)
        tips={
            'coqueteleira':'Para líquidos frios e sem gás, use um pote próprio para alimentos com tampa firme, limpo e em boas condições. Misturar com colher também é uma alternativa, com textura diferente. Nunca agite líquidos quentes ou gaseificados em recipiente fechado; acrescente os gaseificados depois.',
            'liquidificador':'Para frutas macias, amasse com garfo e misture com colher ou batedor. Não terá a mesma textura lisa. Frutas congeladas, gelo e ingredientes duros não devem ser triturados à mão; use componentes já descongelados ou uma receita que não dependa de trituração.',
            'coador':'Use uma peneira culinária limpa. A malha muda a quantidade de polpa que passa; não é uma equivalência exata ao coador de bar.',
            'dosador':'Use um copo ou jarra graduada em mililitros. Colheres domésticas variam de tamanho; evite tratá-las como medida exata.',
            'macerador':'Use as costas de uma colher resistente e utensílios próprios para alimentos. Pressione delicadamente frutas e ervas, sem golpear o copo.',
        }
        if not tool: return self.ask('equipment','Qual utensílio está faltando: coqueteleira, liquidificador, coador, dosador ou macerador?')
        drink=self.target(text)
        prefix=f'Para adaptar o preparo de {drink["nome"]}: ' if drink else ''
        return {'message':prefix+tips[tool]}

    def taste(self,text,q,pending):
        context = {**self.state, 'cap_pending': pending} if pending.get('kind') == 'taste' else self.state
        adjustment = taste_adjustment(text, context)
        tips = {
            'soften': 'Para suavizar, dilua uma pequena amostra com água e prove antes de ajustar o restante. Se o incômodo for o sabor alcoólico, reduza o destilado na próxima preparação ou use um misturador sem álcool compatível. Se for café, amargor ou acidez, diga qual aspecto está intenso para eu orientar melhor. Diluir não remove o álcool já presente nem reduz a quantidade total ingerida se beber tudo.',
            'strengthen': 'Para uma bebida fraca, aguada ou sem sabor, teste uma pequena quantidade do ingrediente principal em uma amostra, respeitando as restrições. Na próxima vez, resfrie os ingredientes antes e evite excesso de água ou gelo derretido. Isso é um ajuste de sabor; não vou aumentar o álcool automaticamente.',
            'less_sweet': 'Para deixar menos doce, dilua uma pequena amostra com água e prove. Se combinar com a receita e suas restrições, acrescente algumas gotas de limão à amostra. Só ajuste o restante depois.',
            'more_sweet': 'Para deixar mais doce, teste uma pequena quantidade de açúcar já dissolvido em uma amostra, apenas se puder e desejar usá-lo. Prove antes de ajustar o restante; não há proporção universal.',
            'less_bitter': 'Para reduzir o amargor, dilua uma pequena amostra com água e prove. Se você puder e desejar adicionar açúcar, teste uma pequena quantidade já dissolvida. Não há proporção universal para corrigir o sabor.',
            'less_sour': 'Para reduzir a acidez ou o azedo, dilua uma pequena amostra com água e prove. Se você puder e desejar adicionar açúcar, teste uma pequena quantidade já dissolvida. Não há proporção universal para corrigir o sabor.',
        }
        if adjustment not in tips:
            return self.ask('taste','Você quer suavizar ou intensificar? A bebida ficou forte, fraca, aguada, doce, amarga ou ácida? Diga o que deseja mudar.')
        drink = self.target(text)
        if drink:
            self.state['last'] = drink['id']
        prefix = f'Para ajustar {drink["nome"]}:\n' if drink else ''
        tip = tips[adjustment]
        if self.state['prefs'].get('evitar') or self.state['avoid_flavors']:
            tip = ('Como você informou restrições, não vou indicar um ingrediente adicional automaticamente. '
                   'Diga quais ingredientes pode usar e se quer suavizar ou intensificar. '
                   'Teste qualquer ajuste em uma pequena amostra antes de mudar o restante.')
        result = {'message': prefix + tip + '\nSão ajustes de paladar; a receita original permanece no catálogo.'}
        if drink:
            result['drink'] = drink
        return result

    def occasion(self,text,q,pending):
        occasion=next((x for x in OCCASIONS if re.search(r'\b'+re.escape(x)+r'\b',q)),None)
        if not occasion: return self.ask('occasion','Qual ocasião ou comida? Por exemplo: churrasco, jantar, pizza, sobremesa, praia ou dia frio.')
        flavor,reason=OCCASIONS[occasion]
        local=copy.deepcopy(self.state)
        if not local['prefs'].get('sabor'): local['prefs']['sabor']=flavor
        ranked=RuleEngine().rank(self.kb,local)
        if not ranked: return {'message':'Não encontrei uma opção para a ocasião que respeite suas restrições. Não vou removê-las automaticamente.'}
        best=ranked[0]
        # Só atribui a justificativa sensorial se o sabor de fato está presente.
        if flavor in best['drink']['tags']: best['reasons'].append(reason)
        self.state['last']=best['drink']['id']
        self.state['decision']={'id':best['drink']['id'],'reasons':best['reasons'],'trace':best['trace'],'score':best['score']}
        self.state['recent_drinks']=list(dict.fromkeys(self.state['recent_drinks']+[best['drink']['id']]))
        msg=f'Para {occasion}, esta é uma sugestão de combinação, não uma regra de gosto.\n'
        msg+=LanguageGenerator().recommendation(best,self.state)
        return {'message':msg,'drink':best['drink'],
                'alternatives':[r['drink']['nome'] for r in ranked[1:4]],
                'alternative_details':[{'id':r['drink']['id'],'nome':r['drink']['nome'],'ingredientes':r['drink']['ingredientes']} for r in ranked[1:4]]}

    def storage(self,text,q,pending):
        drink=self.target(text)
        if drink and drink['categoria'] in ('Cerveja','Vinho','Destilado','Licor','Sidra'):
            return {'message':f'Para {drink["nome"]}, siga as instruções do rótulo antes e depois de abrir. Guarde a embalagem bem fechada, protegida de calor e luz. Não tenho um prazo validado para esse produto específico. Se misturar com suco, frutas ou laticínios, trate a mistura como perecível; o álcool não garante sua conservação.',
                    'sources':[{'title':'FDA — armazenamento de alimentos perecíveis','url':FOOD_SOURCE}]}
        title=drink['nome'] if drink else 'bebidas preparadas com ingredientes perecíveis'
        msg=f'Conservação de {title}:\n'
        msg+='• Use recipiente limpo e fechado e mantenha sob refrigeração a 4 °C ou menos.\n'
        msg+='• Perecíveis não devem ficar fora de refrigeração por mais de 2 horas, ou 1 hora quando o ambiente estiver acima de 32 °C. Se esse limite foi ultrapassado, descarte.\n'
        if drink:
            ingredients=' '.join(normalize(i['nome']) for i in drink['ingredientes'])
            if re.search(r'leite|iogurte|sorvete|fruta|polpa|suco|morango|banana',ingredients):
                msg+='• Para esta receita com ingredientes perecíveis, prefira preparar perto de servir e siga também os prazos dos rótulos.\n'
            if re.search(r'gas|tonica|espumante|refrigerante',ingredients):
                msg+='• Acrescente os ingredientes gaseificados ao servir para preservar a efervescência.\n'
        msg+='Não tenho uma validade específica validada para essa mistura e não posso garantir que uma bebida preparada hoje estará segura amanhã sem conhecer as condições de preparo e armazenamento. Para produtos prontos, siga o rótulo.'
        return {'message':msg,'sources':[{'title':'FDA — armazenamento refrigerado e regra de 2 horas','url':FOOD_SOURCE}]}

    def budget(self,text,q,pending):
        costs=self.state.setdefault('ingredient_costs',{})
        # Valores representam o custo usado em UMA receita, não preço de embalagem.
        for name,value in re.findall(r'(?:^|[;\n])\s*([^=;\n]{1,70})\s*=\s*(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?=;|\n|$)',q):
            try:
                amount=Decimal(value.replace(',','.'))
                if amount <= 100000: costs[normalize(name.strip())]=str(amount)
            except InvalidOperation: pass
        budget_match=re.search(r'(?:ate|limite|orcamento(?: de)?|tenho|gastar|gastando)\s*(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)',q)
        if not budget_match and '=' not in q: budget_match=re.search(r'r\$\s*(\d+(?:[.,]\d{1,2})?)',q)
        limit=Decimal(budget_match[1].replace(',','.')) if budget_match else Decimal(pending['limit']) if pending.get('limit') else None
        if limit is not None and not 0 < limit <= 100000:
            return self.ask('budget','Informe um orçamento positivo, em reais, de até R$ 100.000.')
        self.state['budget_limit']=str(limit) if limit is not None else self.state.get('budget_limit')
        if limit is None and self.state.get('budget_limit'): limit=Decimal(self.state['budget_limit'])
        ranked=RuleEngine().rank(self.kb,self.state)
        names=self.kb.mentioned(q)
        target=names[0] if len(names)==1 else pending.get('target')
        if not target and re.search(r'\b(?:essa|esse|esta|este|dessa|desse|quanto custa)\b',q): target=self.state.get('last')
        if target: ranked=[r for r in ranked if r['drink']['id']==target]
        if not ranked: return {'message':'Não encontrei uma opção compatível com suas restrições para calcular o custo.'}
        complete=[]
        for item in ranked:
            drink=item['drink']
            missing=[i['nome'] for i in drink['ingredientes'] if normalize(i['nome']) not in costs]
            if not missing:
                total=sum((Decimal(costs[normalize(i['nome'])]) for i in drink['ingredientes']),Decimal('0'))
                complete.append((total,drink))
        eligible=sorted([(cost,drink) for cost,drink in complete if limit is None or cost<=limit],key=lambda x:x[0])
        if eligible:
            cost,drink=eligible[0]
            self.state['last']=drink['id']
            money=f'{cost:.2f}'.replace('.',',')
            message=f'{drink["nome"]}: custo estimado de R$ {money} para uma receita, usando somente os custos que você informou.'
            message+='\nIngredientes:\n'+'\n'.join('• '+i['nome']+': '+i['quantidade'] for i in drink['ingredientes'])
            message+='\nA estimativa considera o custo consumido, não o valor para comprar embalagens inteiras, transporte ou utensílios.'
            return {'message':message,'drink':drink,'estimated_cost':str(cost)}
        if complete and target:
            cost=complete[0][0]
            return {'message':f'O custo informado dessa receita é R$ {cost:.2f}, acima do limite de R$ {limit:.2f}. Não vou reduzir quantidades sem combinar uma adaptação.'}
        drink=ranked[0]['drink']
        missing=[i['nome'] for i in drink['ingredientes'] if normalize(i['nome']) not in costs]
        message='Não tenho preços locais atualizados. '
        if complete: message+='As opções com custos completos ultrapassam o limite. '
        message+=f'Para avaliar {drink["nome"]}, informe o custo da quantidade usada em UMA receita para: '+', '.join(missing)+'.'
        message+='\nFormato: ingrediente = valor; ingrediente = valor. Exemplo: limão = 1,50; açúcar = 0,20. Para itens que já tem e não geram gasto agora, pode informar 0. Não use preços de embalagens nesse formato.'
        return self.ask('budget',message,target=drink['id'],limit=str(limit) if limit is not None else None)

    def online(self,text,q,pending):
        term=re.sub(r'^.*?\b(?:pesquise|pesquisa|busque|procure|buscar)\b','',text,flags=re.I).strip()
        term=re.sub(r'\b(?:na internet|na web|na wikipedia|fora do catalogo|sobre|por favor)\b','',normalize(term)).strip(' :?.!')
        term=re.sub(r'^(?:a bebida|o drink|bebida|drink)\s+','',term)
        if not term: return self.ask('online','Qual bebida você quer pesquisar? Escreva “pesquise sobre Nome da bebida”.')
        return search_drink(term)
