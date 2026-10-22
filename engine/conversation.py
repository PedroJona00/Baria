import re
from .input_processor import InputProcessor
from .normalizer import Normalizer, normalize
from .knowledge import KnowledgeBase
from .entities import EntityExtractor
from .intents import IntentClassifier
from .context import ContextManager
from .rules import RuleEngine
from .planner import ResponsePlanner
from .generator import LanguageGenerator
from .validator import ResponseValidator
from .feedback import FeedbackRecorder
from .capabilities import Capabilities, detect

class ConversationEngine:
    def __init__(self, root, read_memory, save_fact, feedback_path=None, knowledge_provider=None):
        self.root, self.read_memory, self.save_fact = root, read_memory, save_fact
        self.feedback_path = feedback_path or root / 'data/feedback.jsonl'
        self.knowledge_provider = knowledge_provider

    def reply(self, session, text, preferences, action='chat'):
        text, ui, form = InputProcessor().process(text, preferences, action)
        if action == 'reset':
            session.clear()
            return {'message': 'Vamos começar de novo! Você prefere uma bebida com ou sem álcool? E qual sabor combina com você?', 'preferences': {'alcool':'','sabor':'','ingredientes':'','evitar':''}, 'diagnostics': {'intent':'reset','confidence':1.0}}
        kb = self.knowledge_provider() if self.knowledge_provider else KnowledgeBase(self.read_memory(), self.root / 'data/regras.json')
        context = ContextManager(session)
        q, corrections = Normalizer(kb.vocabulary).process(text)
        entities = EntityExtractor().extract(q, kb)
        intent = IntentClassifier().classify(q, entities, kb.intent_rules, action, ui)
        generator, rules = LanguageGenerator(), RuleEngine()
        previous = session.get('last_turn')
        context.remember('user', text, form=form)
        diagnostics = {'intent': intent['name'], 'confidence': intent['confidence'], 'form': form, 'corrections': corrections, 'entities': entities, 'candidates': intent['candidates']}

        def log(category):
            try:
                FeedbackRecorder(self.feedback_path).record(category, text, diagnostics, previous)
                return True
            except OSError:
                return False

        def finish(message, **extras):
            result = {'message': message, 'preferences': dict(session['prefs']), 'diagnostics': diagnostics, **extras}
            ResponseValidator().validate(result, kb, extras.pop('allowed_ids', None))
            result.pop('allowed_ids', None)
            context.remember('assistant', result['message'], intent=diagnostics['intent'])
            session['last_turn'] = {'user':text, 'response':result['message'], 'intent':diagnostics['intent'], 'confidence':diagnostics['confidence']}
            return result

        # Estado de contribuição tem prioridade e nunca interpreta seu texto como regra.
        if session.get('adding') and intent['name'] not in ('finish', 'feedback', 'rule_suggestion'):
            if q in ('nao', 'nao obrigado', 'nao obrigada', 'cancelar'):
                session.update(adding=False, task='idle')
                return finish('Tudo certo! Conversa encerrada. Quando quiser, podemos descobrir outra bebida.')
            if q in ('sim', 'quero', 'sim quero'):
                return finish('Conte a informação ou curiosidade que deseja salvar.', adding=True)
            if form == 'pergunta' or detect(text, session) or intent['name'] in ('recipe', 'ingredients', 'compare', 'alcohol_check'):
                return finish('Estou aguardando uma curiosidade para salvar. Escreva sua contribuição ou diga “cancelar” para voltar às perguntas.', adding=True)
            if len(text) < 8:
                return finish('Escreva uma informação um pouco mais completa (pelo menos 8 caracteres).', adding=True)
            saved = self.save_fact(session['last'], text)
            session.update(adding=False, task='idle')
            return finish('Curiosidade salva na memória JSON como contribuição do usuário, ainda não verificada. Até a próxima!' if saved else 'Essa curiosidade já está na memória. Até a próxima!')

        if intent['name'] == 'finish':
            if not session.get('last'): return finish('Até a próxima! Ainda não escolhemos uma bebida para registrar uma curiosidade.')
            session.update(adding=True, task='awaiting_contribution')
            return finish(f'Deseja adicionar alguma informação ou curiosidade sobre {kb.by_id[session["last"]]["nome"]}? Escreva sua contribuição ou responda “não”.', adding=True)

        if intent['name'] in ('feedback', 'rule_suggestion'):
            category = 'rule_suggestion' if intent['name'] == 'rule_suggestion' else 'misclassified_intent' if re.search(r'nao foi isso|entendeu errado', q) else 'low_performance' if re.search(r'errada|ruim|nao ajudou', q) else 'explicit_feedback'
            recorded = log(category)
            return finish(('Registrei seu comentário para revisão manual. As regras não são alteradas automaticamente.' if recorded else 'Não consegui gravar o feedback. Verifique a permissão da pasta data.') + (' O que você queria saber? Pode reformular seu pedido.' if category in ('misclassified_intent','low_performance') else ''))

        capability = detect(text, session)
        if not capability and session.get('cap_pending') and entities['drinks'] and intent['name'] in ('describe', 'unknown'):
            capability = session['cap_pending']['kind']
        if capability:
            diagnostics.update(intent=capability, confidence=.95)
            if capability in ('occasion', 'budget'):
                if rules.conflicts(entities):
                    return finish('Encontrei preferências contraditórias. Diga se deseja com ou sem álcool e repita o pedido.')
                context.merge(ui, entities)
            elif capability != 'online':
                # “Não quero mais doce; quero menos doce” descreve um ajuste,
                # não duas preferências sensoriais contraditórias.
                checked_entities = {**entities, 'flavors': [], 'avoid_flavors': []} if capability == 'taste' else entities
                if rules.conflicts(checked_entities):
                    return finish('Encontrei preferências contraditórias. Esclareça se deseja com ou sem álcool antes de continuar.')
                context.merge(ui, {**entities, 'flavors':[], 'avoid_flavors':[], 'available':[]})
            # Pedido prático explicitamente novo encerra uma clarificação antiga.
            session.pop('pending', None)
            result = Capabilities(kb, session).handle(capability, text)
            diagnostics['rule_trace'] = ['capacidade_' + capability]
            return finish(**result)
        if session.get('cap_pending') and intent['name'] not in ('unknown', 'greet', 'thanks'):
            session.pop('cap_pending', None)

        # Não transforma perguntas sobre dados ausentes em recomendações.
        unsupported = re.search(r'\b(calorias|calorico|preco|custa|teor|porcentagem|abv|saudavel|cura|diabetes|gravidez|gestante)\b', q)
        if unsupported:
            diagnostics.update(intent='unsupported', confidence=1.0)
            log('knowledge_gap')
            return finish('Minha base não contém dados confiáveis para responder a essa pergunta. Posso consultar os ingredientes, o preparo e as curiosidades cadastradas, sem estimar essa informação.')

        conflict = rules.conflicts(entities)
        if conflict:
            session['pending'] = {'kind':'conflict', 'field':conflict, 'entities':entities, 'ui':ui}
            session['task'] = 'awaiting_clarification'
            diagnostics['rule_trace'] = ['contradicao_na_mesma_mensagem']
            return finish('Encontrei preferências contraditórias na mesma mensagem. Você quer com ou sem álcool?' if conflict == 'alcool' else 'Você pediu e rejeitou o mesmo sabor. Qual perfil devo considerar?')

        pending = session.get('pending')
        if pending and pending['kind'] == 'conflict':
            field = pending['field']
            resolved = bool(entities['alcohol'] or ui.get('alcool')) if field == 'alcool' else bool(entities['flavors'] or entities['avoid_flavors'] or ui.get('sabor'))
            if not resolved:
                return finish('Ainda preciso resolver a preferência anterior: com ou sem álcool?' if field == 'alcool' else 'Qual sabor você deseja incluir ou evitar?')
            retained = pending['entities']
            for key in ('flavors', 'avoid_flavors', 'alcohol', 'available', 'avoid'):
                if key in (('alcohol',) if field == 'alcool' else ('flavors', 'avoid_flavors')): continue
                if not entities[key]: entities[key] = retained[key]
            ui = {**pending['ui'], **ui}
            session.pop('pending', None)
            session['task'] = 'idle'
            intent.update(name='recommend', confidence=.95)
        elif pending and pending['kind'] == 'target' and entities['drinks'] and intent['name'] in ('describe', 'recommend'):
            intent.update(name=pending['intent'], confidence=.95)
            session.pop('pending', None)
            session['task'] = 'idle'
        elif pending and pending['kind'] == 'target' and intent['name'] not in ('unknown', 'greet', 'thanks'):
            session.pop('pending', None)
            session['task'] = 'idle'
        # Pedidos de detalhe sem nome retomam o assunto atual.
        if intent['name'] == 'unknown' and entities['detail'] and session.get('last'):
            intent.update(name=session.get('last_information', 'describe'), confidence=.85)
        diagnostics.update(intent=intent['name'], confidence=intent['confidence'])
        if entities['invalid_dates']:
            return finish('A data informada não é válida: ' + ', '.join(entities['invalid_dates']) + '. Use dia/mês/ano.')

        # Informações sobre uma bebida não viram preferências implícitas do usuário.
        personal_intents = ('recommend', 'alternative', 'greet', 'unknown')
        if intent['name'] in personal_intents:
            context.merge(ui, entities)
        else:
            if ui: context.merge(ui, {**entities, 'alcohol':[], 'flavors':[], 'avoid_flavors':[], 'avoid':[], 'available':[]})
            if entities['detail']: session['detail'] = entities['detail']
            session['entities'] = entities
        if entities['dates']: session['event_dates'] = entities['dates']
        if entities['numbers']: session['quantities'] = entities['numbers']
        plan = ResponsePlanner().plan(intent, entities, session, kb)
        kind = plan['kind']
        if kind == 'clarify':
            session['task'] = 'awaiting_clarification'
            if plan.get('pending'): session['pending'] = {'kind':'target','intent':plan['pending']}
            return finish(plan['message'])
        if kind == 'greet': return finish(generator.template('greet', session))
        if kind == 'thanks': return finish('De nada! Se terminou, clique em “Encerrar conversa” para decidir se quer adicionar uma curiosidade.')
        if kind == 'unknown':
            log('unrecognized')
            return finish(generator.template('unknown', session))
        if kind == 'context':
            prefs = session['prefs']
            parts = []
            if prefs.get('alcool'): parts.append('bebidas ' + ('sem álcool' if prefs['alcool'] == 'nao' else 'com álcool'))
            if prefs.get('sabor'): parts.append('perfil ' + prefs['sabor'])
            if prefs.get('ingredientes'): parts.append('ingredientes disponíveis: ' + prefs['ingredientes'])
            if prefs.get('evitar'): parts.append('evitar: ' + prefs['evitar'])
            if session['avoid_flavors']: parts.append('perfis excluídos: ' + ', '.join(session['avoid_flavors']))
            if session.get('event_dates'): parts.append('datas mencionadas: ' + ', '.join(session['event_dates']))
            if session.get('last'): parts.append('última bebida: ' + kb.by_id[session['last']]['nome'])
            return finish('Nesta conversa, lembro: ' + '; '.join(parts) + '.' if parts else 'Você ainda não informou preferências nesta conversa.')
        if kind == 'compare':
            a, b = [kb.by_id[x] for x in plan['targets']]
            def summary(d): return d['nome'] + ': ' + ('com álcool' if d['alcool'] else 'sem álcool') + '; sabores: ' + ', '.join(d['tags']) + '.'
            message = summary(a) + '\n' + summary(b)
            if session.get('detail') != 'short': message += '\nIngredientes de ' + a['nome'] + ': ' + ', '.join(i['nome'] for i in a['ingredientes']) + '.\nIngredientes de ' + b['nome'] + ': ' + ', '.join(i['nome'] for i in b['ingredientes']) + '.'
            session['comparison'] = plan['targets']
            session['last'] = b['id']
            return finish(message + '\nPara uma pergunta sobre apenas uma delas, use o nome da bebida.')
        if kind == 'explain':
            choice = session.get('decision')
            if not choice or choice['id'] != plan['target']: return finish('Ainda não fiz uma recomendação dessa bebida com base nas suas preferências. Peça uma sugestão para eu explicar os critérios.')
            message = 'Escolhi ' + kb.by_id[choice['id']]['nome'] + ' porque ' + '; '.join(choice['reasons'] or ['é uma opção cadastrada, mas você ainda não definiu preferências suficientes']) + '.'
            if session.get('detail') != 'short': message += '\nPrimeiro apliquei as restrições de álcool, ingredientes e sabores excluídos. Depois ordenei as opções por afinidade de sabor e ingredientes disponíveis. Empates usam a ordem do catálogo.'
            diagnostics['rule_trace'] = choice['trace']
            return finish(message)
        ranked = rules.rank(kb, session, exclude_recent=kind == 'alternative')
        allowed = {item['drink']['id'] for item in rules.rank(kb, session)}
        if kind in ('recipe', 'ingredients', 'fact', 'alcohol_check', 'describe'):
            drink = kb.by_id[plan['target']]
            if kind == 'describe' and drink['id'] not in allowed:
                return finish(drink['nome'] + ' não atende aos filtros atuais. Posso mostrar a receita para consulta, ou você pode ajustar os filtros para receber uma recomendação.')
            session['last'] = drink['id']
            session['last_information'] = kind
            message = generator.information(kind, drink, session)
            if drink['id'] not in allowed: message += '\nEsta é uma consulta: a bebida não atende às suas restrições atuais.'
            # Não escala quantidades vagas ("a gosto", "unidade") automaticamente.
            if any(n['unit'] in ('pessoa', 'pessoas', 'porcoes', 'copos', 'copo') for n in entities['numbers']): message += '\nA receita exibida mantém as quantidades cadastradas; não fiz conversão automática de porções.'
            return finish(message, drink=drink)
        if kind in ('recommend', 'alternative'):
            if not any(session['prefs'].values()) and not session['avoid_flavors'] and not entities['drinks']:
                session['task'] = 'awaiting_preferences'
                return finish('Para recomendar melhor, você prefere com ou sem álcool? E qual sabor: doce, cítrico, amargo ou cremoso?')
            if entities['drinks']:
                ranked = [item for item in ranked if item['drink']['id'] == entities['drinks'][0]]
            if not ranked:
                return finish('Não encontrei outra opção ainda não sugerida dentro dos filtros.' if kind == 'alternative' else 'Não encontrei uma bebida que respeite essas restrições. Você pode revisar os filtros; não vou ignorá-los automaticamente.')
            best = ranked[0]
            session['last'] = best['drink']['id']
            session['last_information'] = 'describe'
            session['recent_drinks'] = list(dict.fromkeys(session['recent_drinks'] + [session['last']]))[-32:]
            session['decision'] = {'id':session['last'], 'reasons':best['reasons'], 'trace':best['trace'], 'score':best['score']}
            session['task'] = 'idle'
            diagnostics.update(rule_trace=best['trace'], score=best['score'])
            message = generator.recommendation(best, session)
            if session.get('changes'): message = 'Atualizei suas preferências conforme o pedido mais recente.\n' + message
            if corrections: message += '\nInterpretei: ' + ', '.join(c['de'] + ' → ' + c['para'] for c in corrections) + '.'
            return finish(message, drink=best['drink'], alternatives=[item['drink']['nome'] for item in ranked[1:4]], alternative_details=[{'id': item['drink']['id'], 'nome': item['drink']['nome'], 'ingredientes': item['drink']['ingredientes']} for item in ranked[1:4]], allowed_ids=allowed)
        return finish(generator.template('unknown', session))
