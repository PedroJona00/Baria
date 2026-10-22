"""Gera exemplos reais sem alterar a memória ou o feedback de uso."""
import tempfile
from pathlib import Path
from unittest.mock import patch
import app

SCENARIOS = [
    ('Conversa simples e contextual', [
        'Olá!', 'Quero algo cítrico sem álcool', 'Como preparar ela?', 'Por que escolheu essa?', 'Outra opção', 'O que eu pedi?'
    ]),
    ('Negação, erro de digitação e mudança de preferência', [
        'Não gosto de doce, quero algo refescante sem álcool', 'Na verdade, agora prefiro com álcool e amargo', 'Receita curta'
    ]),
    ('Contradição e esclarecimento', [
        'Quero algo cítrico com álcool e sem álcool', 'Sem álcool', 'Compare Mojito e Mojito sem álcool'
    ]),
    ('Limite da base e feedback', [
        'Quantas calorias tem a Caipirinha?', 'florb zzz blarg', 'Não foi isso que eu pedi', 'Sugiro uma regra: reconhecer aromas florais'
    ]),
    ('Contribuição persistente', [
        'Limonada', 'encerrar', 'sim', 'Eu prefiro servir a limonada com bastante gelo.'
    ]),
]

def generate():
    output = ['# Exemplos executados pelo BARIA', '', 'Transcrições geradas por `python demo.py`, usando a mesma função chamada pela interface web e uma cópia temporária do catálogo.', '']
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
        root = Path(folder)
        (root/'data').mkdir()
        for name in ('memoria.json', 'regras.json'):
            (root/'data'/name).write_bytes((app.ROOT/'data'/name).read_bytes())
        with patch.object(app, 'ROOT', root):
            for title, messages in SCENARIOS:
                output += ['## ' + title, '']
                state = {}
                for text in messages:
                    result = app.reply(state, text, {})
                    output += ['**Usuário:** ' + text, '', '**BARIA:** ' + result['message'], '']
    return '\n'.join(output)

if __name__ == '__main__':
    target = Path(__file__).with_name('EXEMPLOS.md')
    target.write_text(generate(), encoding='utf-8')
    print('Exemplos gravados em EXEMPLOS.md')
