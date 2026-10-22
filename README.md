# BARIA 🍋

**Seu bartender digital em português.** Receba sugestões conforme seu paladar, com ingredientes, quantidades, preparo e curiosidades.

Sistema especialista em Python com **102 bebidas alcoólicas e não alcoólicas** e memória JSON. Usa regras, contexto, processamento de texto e templates. **Não utiliza IA generativa, redes neurais ou APIs de LLM.**

## Conversas possíveis

| Você diz | O BARIA faz |
| --- | --- |
| Quero algo cítrico e sem álcool | Recomenda bebidas, com ingredientes e quantidades. |
| Como eu faço uma caipirinha? | Recupera a receita e o modo de preparo. |
| E os ingredientes dela? | Usa a última bebida como contexto. |
| Outra opção / Por que escolheu essa? | Troca a sugestão ou explica sua decisão. |
| Compare Mojito e Mojito sem álcool | Compara itens do catálogo. |
| Caipirinha para 4 pessoas | Ajusta quantidades para servir um grupo. |
| Não tenho coqueteleira | Orienta sobre utensílios alternativos. |
| Encerrar | Pergunta se deseja acrescentar uma curiosidade. |

Também oferece substituições previstas em regras, sugestões por ocasião, conservação e estimativas de custo a partir dos preços informados pelo usuário. A pesquisa opcional na Wikipédia precisa de internet; o motor principal funciona offline.

## Executar localmente

Requer **Python 3.10+**. Na pasta do projeto:

```sh
python app.py
```

Abra [localhost:8000](http://127.0.0.1:8000). No Windows, também pode abrir `iniciar.bat`. Para outra porta: `python app.py --port 8080`. Esse modo usa apenas a biblioteca padrão do Python.

## Servidor para hospedagem

```sh
python -m pip install -r requirements.txt
python serve.py
```

Usa Waitress, com um adaptador WSGI para o mesmo motor. Configure `HOST=0.0.0.0`, `PORT` e as variáveis descritas em [HOSPEDAGEM.md](HOSPEDAGEM.md). Em desenvolvimento, o padrão é `127.0.0.1:8000`. Recomendamos instalar dependências em um ambiente virtual (`python -m venv .venv`).

**GitHub Pages não executa Python.** `render.yaml` prepara uma demonstração no Render Free; o Dockerfile oferece outra forma de implantação. O plano gratuito tem armazenamento temporário, indicado na página e ao salvar curiosidades. Hospedagem com JSON persistente requer um volume apropriado.

## Memória e privacidade

- O catálogo de distribuição não inclui contribuições anteriores nem logs locais.
- No modo local, curiosidades são gravadas em `data/memoria.json`. Com `BARIA_DATA_DIR`, uma cópia inicial é criada nessa pasta, sem sobrescrever dados nas próximas execuções.
- Contribuições são **não verificadas** e podem aparecer para outros visitantes. Não envie dados pessoais ou confidenciais.
- Histórico e preferências ficam na memória do processo e somem ao reiniciar. No WSGI, sessões expiram após uma hora de inatividade; abas do mesmo navegador compartilham sessão.
- Feedback e mensagens não reconhecidas podem ser gravados em `feedback.jsonl`, com rotação limitada, para revisão humana. Não são publicados no GitHub.
- Render Free perde alterações em arquivos ao reiniciar. Disco persistente é necessário para preservar curiosidades e feedback.

## Testes e exemplos

```sh
python -m unittest -v
python demo.py
```

A suíte cobre preferências, contexto, negações, receitas, capacidades adicionais, persistência, HTTP e implantação. O GitHub Actions executa os testes em Python 3.10 e 3.13. `demo.py` gera transcrições usando uma cópia temporária do catálogo.

## Organização

| Arquivo/pasta | Responsabilidade |
| --- | --- |
| `app.py` | Servidor local e persistência JSON. |
| `serve.py`, `web.py` | Servidor Waitress e interface WSGI. |
| `engine/` | Interpretação, entidades, intenções, contexto, regras e respostas. |
| `data/regras.json` | Padrões e prioridades configuráveis. |
| `data/memoria.json` | Catálogo inicial. |
| `static/` | Interface HTML, CSS e JavaScript responsiva. |
| `test_*.py` | Testes automatizados. |

## Documentação

- [Arquitetura e extensão](ARQUITETURA.md)
- [Capacidades e limitações](NOVAS_CAPACIDADES.md)
- [Exemplos reais de conversa](EXEMPLOS.md)
- [Hospedagem e operação](HOSPEDAGEM.md)
- [Como contribuir](CONTRIBUTING.md)
- [Segurança e dados](SECURITY.md)

## Limites

O entendimento depende das regras cadastradas. Confiança é uma pontuação heurística, não uma probabilidade. Não há aprendizado automático nem cadastro de receitas completas pelo chat. Ingredientes a evitar são comparados por texto, sem garantia de detecção de alérgenos. Receitas são referências culinárias.

A implantação utiliza **um processo e uma instância**. Escalar exige migrar sessões e gravações para armazenamento compartilhado. Não há autenticação nem moderação prévia das curiosidades.

Nenhuma licença de código aberto foi atribuída; o titular pode escolhê-la posteriormente. Dependências mantêm suas próprias licenças.

Se beber, não dirija. Bebidas alcoólicas são destinadas a maiores de idade.
