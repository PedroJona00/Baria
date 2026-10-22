"""Consulta enciclopédica opcional. Sem geração de texto ou gravação no catálogo."""
import json
import re
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from .normalizer import normalize

ENDPOINTS = [('pt','https://pt.wikipedia.org/w/api.php'),('en','https://en.wikipedia.org/w/api.php')]

def search_drink(term, opener=None):
    term = re.sub(r'[^\w\s()-]', ' ', term).strip()[:100]
    if not term:
        return {'message': 'Qual bebida você quer pesquisar? Escreva “pesquise na internet sobre Nome da bebida”.'}
    try:
        results = []
        for lang, endpoint in ENDPOINTS:
            params = {'action':'query', 'format':'json', 'formatversion':2,
                      'generator':'search', 'gsrsearch':'"'+term+'" '+('bebida' if lang=='pt' else 'drink'),
                      'gsrnamespace':0, 'gsrlimit':5, 'prop':'extracts', 'exintro':1, 'explaintext':1, 'exchars':600}
            request = Request(endpoint + '?' + urlencode(params),
                              headers={'User-Agent':'BARIA/2.0 (local beverage reference app)', 'Accept':'application/json'})
            with (opener or urlopen)(request, timeout=6) as response:
                raw = response.read(250001)
            if len(raw) > 250000: raise ValueError('Resposta muito grande')
            payload = json.loads(raw)
            pages = payload.get('query', {}).get('pages', [])
            if not isinstance(pages, list): raise ValueError('Resposta inesperada')
            words=set(re.findall(r'\w+',normalize(term)))
            for page in sorted(pages, key=lambda p:p.get('index', 999)):
                title, excerpt = page.get('title'), page.get('extract')
                if not isinstance(title, str) or not isinstance(excerpt, str) or not excerpt.strip(): continue
                # Nome no título E indicação de bebida na introdução.
                if not words <= set(re.findall(r'\w+',normalize(title))): continue
                if not re.search(r'\b(coquetel|cocktail|bebida|drink|beverage|liqueur|licor|juice|suco|wine|vinho|beer|cerveja|tea|cha|coffee|cafe)\b',normalize(excerpt[:350])): continue
                results.append({'title':title[:200], 'excerpt':excerpt[:600], 'lang':lang,
                                'url':f'https://{lang}.wikipedia.org/wiki/' + quote(title.replace(' ', '_'), safe='')})
            if results: break
        results=results[:3]
        if not results:
            return {'message': f'Não encontrei resultados com resumo para “{term}”. Tente o nome completo ou outra grafia. Nada foi cadastrado.'}
        text = 'Resultados externos da Wikipédia — confira as fontes; podem tratar de bebidas com nomes semelhantes. Estes trechos não são receitas validadas pelo BARIA.\n\n'
        text += '\n\n'.join(r['title'] + (' (fonte em inglês)' if r['lang']=='en' else '') + '\n' + r['excerpt'] for r in results)
        return {'message':text + '\n\nNada foi adicionado à memória de bebidas.', 'sources': [{'title':r['title'], 'url':r['url']} for r in results]}
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {'message': 'Não consegui consultar a Wikipédia agora. Verifique a conexão e tente novamente. O catálogo local continua disponível; nada foi cadastrado.'}
