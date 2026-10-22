import re

class InputProcessor:
    def process(self, text, preferences, action):
        if not isinstance(text, str) or not 0 <= len(text) <= 2000:
            raise ValueError('Mensagem inválida')
        if not isinstance(preferences, dict):
            raise ValueError('Preferências inválidas')
        if action not in ('chat', 'reset', 'finish', 'feedback'):
            raise ValueError('Ação inválida')
        clean = {}
        for key, value in preferences.items():
            if key not in ('alcool', 'sabor', 'ingredientes', 'evitar'): continue
            if not isinstance(value, str) or len(value) > 300: raise ValueError('Filtro inválido')
            if key == 'alcool' and value not in ('', 'sim', 'nao'): raise ValueError('Álcool inválido')
            if key == 'sabor' and value not in ('', 'doce', 'citrico', 'amargo', 'frutado', 'cremoso', 'refrescante', 'quente'): raise ValueError('Sabor inválido')
            clean[key] = value.strip()
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text).strip()
        form = 'pergunta' if '?' in text else 'afirmacao'
        if re.match(r'(?i)^(quero|gostaria|pode|preciso)', text): form = 'solicitacao'
        elif re.match(r'(?i)^(indique|recomende|mostre|explique|encerre)', text): form = 'comando'
        return text, clean, form
