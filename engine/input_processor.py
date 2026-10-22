import re
from config import ACTIONS, FLAVORS, MAX_MESSAGE_CHARS, MAX_PREFERENCE_CHARS

class InputProcessor:
    def process(self, text, preferences, action):
        if not isinstance(text, str) or not 0 <= len(text) <= MAX_MESSAGE_CHARS:
            raise ValueError('Mensagem inválida')
        if not isinstance(preferences, dict):
            raise ValueError('Preferências inválidas')
        if action not in ACTIONS:
            raise ValueError('Ação inválida')
        clean = {}
        for key, value in preferences.items():
            if key not in ('alcool', 'sabor', 'ingredientes', 'evitar'): continue
            if not isinstance(value, str) or len(value) > MAX_PREFERENCE_CHARS: raise ValueError('Filtro inválido')
            if key == 'alcool' and value not in ('', 'sim', 'nao'): raise ValueError('Álcool inválido')
            if key == 'sabor' and value not in ('', *FLAVORS): raise ValueError('Sabor inválido')
            clean[key] = value.strip()
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text).strip()
        form = 'pergunta' if '?' in text else 'afirmacao'
        if re.match(r'(?i)^(quero|gostaria|pode|preciso)', text): form = 'solicitacao'
        elif re.match(r'(?i)^(indique|recomende|mostre|explique|encerre)', text): form = 'comando'
        return text, clean, form
