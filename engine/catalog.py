"""Validação estrutural e cache limitado a uma versão ativa do catálogo."""
import copy
import json
import logging
import re
import threading

from .knowledge import KnowledgeBase


class KnowledgeError(ValueError):
    """Catálogo ou regras inválidos: falha de configuração, não do visitante."""


def normalize_empty_contributions(memory):
    """Remove apenas espaços vazios conhecidos da cópia carregada em memória."""
    removed = 0
    if not isinstance(memory, dict) or not isinstance(memory.get('bebidas'), list):
        return removed
    metadata = {'texto', 'origem', 'verificada', 'data'}
    for drink in memory['bebidas']:
        if not isinstance(drink, dict) or not isinstance(drink.get('contribuicoes'), list):
            continue
        kept = []
        for fact in drink['contribuicoes']:
            empty = isinstance(fact, dict) and (
                not fact or (
                    isinstance(fact.get('texto'), str)
                    and not fact['texto'].strip()
                    and set(fact) <= metadata
                )
            )
            if empty:
                removed += 1
            else:
                kept.append(fact)
        drink['contribuicoes'] = kept
    return removed


def validate_catalog(memory):
    if not isinstance(memory, dict) or not isinstance(memory.get('bebidas'), list) or not memory['bebidas']:
        raise KnowledgeError('O catálogo precisa de uma lista não vazia de bebidas.')
    ids = set()
    for index, drink in enumerate(memory['bebidas'], 1):
        prefix = f'Bebida {index}'
        if not isinstance(drink, dict):
            raise KnowledgeError(f'{prefix}: registro inválido.')
        for field in ('id', 'nome', 'categoria', 'preparo', 'curiosidade'):
            if not isinstance(drink.get(field), str) or not drink[field].strip():
                raise KnowledgeError(f'{prefix}: campo {field} ausente ou vazio.')
        if drink['id'] in ids:
            raise KnowledgeError(f'{prefix}: ID duplicado {drink["id"]}.')
        ids.add(drink['id'])
        if type(drink.get('alcool')) is not bool:
            raise KnowledgeError(f'{prefix}: alcool precisa ser booleano.')
        if not isinstance(drink.get('tags'), list) or not all(isinstance(tag, str) and tag.strip() for tag in drink['tags']):
            raise KnowledgeError(f'{prefix}: tags inválidas.')
        ingredients = drink.get('ingredientes')
        if not isinstance(ingredients, list) or not ingredients:
            raise KnowledgeError(f'{prefix}: ingredientes ausentes.')
        for ingredient in ingredients:
            if not isinstance(ingredient, dict) or not all(isinstance(ingredient.get(key), str) and ingredient[key].strip() for key in ('nome', 'quantidade')):
                raise KnowledgeError(f'{prefix}: ingrediente sem nome ou quantidade.')
            amount = re.match(r'^\s*(-?\d+(?:[.,]\d+)?)', ingredient['quantidade'])
            if amount and float(amount[1].replace(',', '.')) <= 0:
                raise KnowledgeError(f'{prefix}: quantidade precisa ser positiva.')
        if not isinstance(drink.get('contribuicoes'), list):
            raise KnowledgeError(f'{prefix}: contribuições inválidas.')
        for fact in drink['contribuicoes']:
            if not isinstance(fact, dict) or not isinstance(fact.get('texto'), str) or not fact['texto'].strip():
                raise KnowledgeError(f'{prefix}: contribuição sem texto.')


class CatalogCache:
    def __init__(self):
        self.lock = threading.RLock()
        self.invalidate()

    def invalidate(self):
        with self.lock:
            self._memory_key = self._knowledge_key = None
            self._memory = self._knowledge = None

    @staticmethod
    def signature(path):
        stat = path.stat()
        return str(path.resolve()), stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino

    def _load(self, path):
        key = self.signature(path)
        if key != self._memory_key:
            try:
                memory = json.loads(path.read_text(encoding='utf-8'))
            except (ValueError, UnicodeError) as error:
                raise KnowledgeError('Não foi possível interpretar o catálogo JSON.') from error
            removed = normalize_empty_contributions(memory)
            validate_catalog(memory)
            if removed:
                logging.getLogger(__name__).warning(
                    '%d contribuição(ões) vazia(s) ignorada(s) na leitura. O JSON original não foi alterado.',
                    removed,
                )
            self._memory, self._memory_key = memory, key
            self._knowledge_key = None
        return self._memory

    def snapshot(self, path):
        with self.lock:
            return copy.deepcopy(self._load(path))

    def knowledge(self, memory_path, rules_path):
        with self.lock:
            memory = self._load(memory_path)
            key = self._memory_key, self.signature(rules_path)
            if key != self._knowledge_key:
                try:
                    knowledge = KnowledgeBase(memory, rules_path)
                except (ValueError, TypeError, KeyError, re.error) as error:
                    raise KnowledgeError(f'Regras inválidas: {error}') from error
                self._knowledge, self._knowledge_key = knowledge, key
            return self._knowledge
