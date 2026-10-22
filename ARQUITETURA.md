# BARIA — motor conversacional por regras

## Análise do código anterior

O servidor, a recomendação e o diálogo estavam concentrados em `app.py`. A extração usava expressões regulares simples, não distinguia “doce” de “não gosto de doce” e não tinha histórico, classificação de intenção ou respostas próprias para perguntas de acompanhamento. Os campos da interface eram enviados em todas as mensagens, podendo substituir preferências já expressas na conversa. O estado de contribuição aceitava perguntas como se fossem curiosidades.

A evolução preserva o servidor da biblioteca padrão, o catálogo JSON, as receitas, o isolamento por cookie e a gravação atômica de curiosidades. O catálogo existente não foi substituído. A interface continua compatível com `message`, `drink`, `alternatives` e `preferences`, acrescentando feedback e diagnóstico opcional.

## Módulos

| Responsabilidade | Arquivo | Papel |
|---|---|---|
| Processador de entrada | `engine/input_processor.py` | Valida tamanho, ação e filtros; identifica a forma da mensagem. |
| Normalizador linguístico | `engine/normalizer.py` | Normalização Unicode, abreviações, sinônimos e correções conservadoras com `difflib`. |
| Classificador de intenções | `engine/intents.py` | Expressões configuráveis, prioridade e confiança heurística. |
| Extrator de entidades | `engine/entities.py` | Bebidas, ingredientes, sabores, negações, referências, números, unidades e datas. |
| Contexto e memória | `engine/context.py` | Histórico de até 60 mensagens, preferências, mudanças, assuntos e tarefas pendentes. |
| Regras e inferências | `engine/rules.py` | Restrições obrigatórias, ranking e encadeamento de regras até ponto fixo. |
| Base de conhecimento | `engine/knowledge.py` | Catálogo e regras JSON, índices e nomes de bebidas sem sobreposição. |
| Planejador | `engine/planner.py` | Decide entre consulta, comparação e esclarecimento; resolve o alvo no contexto. |
| Gerador | `engine/generator.py` | Templates parametrizados, variação determinística, respostas curtas ou detalhadas. |
| Validador | `engine/validator.py` | Resposta não vazia, bebida proveniente do catálogo e respeito aos filtros de recomendação. |
| Orquestração | `engine/conversation.py` | Executa o fluxo e as transições de estado. |
| Registro para revisão | `engine/feedback.py` | Feedback, pedidos não reconhecidos, falhas de classificação e sugestões de regras. |

Fluxo: entrada → normalização → entidades → intenção → resolução de estado/conflito → contexto → planejamento/regras → geração → validação → histórico e resposta HTTP.

## Decisões e conflitos

- Restrições de álcool, ingredientes e sabores rejeitados eliminam candidatos antes da pontuação.
- Sabor compatível soma 5 pontos; cada ingrediente disponível encontrado soma 2. A inferência de refrescância sem álcool soma 1 quando aplicável.
- Exemplo de encadeamento: `wants_no_alcohol` implica `exclude_alcohol`; este fato, combinado com `wants_refreshing`, implica `prefer_refreshing_non_alcoholic`.
- As regras de intenção em `data/regras.json` possuem prioridade explícita. Pedidos específicos de receita ou explicação têm precedência sobre a mera presença de um nome de bebida.
- Preferências contraditórias na mesma mensagem geram esclarecimento sem recomendar. As demais preferências daquele pedido são recuperadas após a resposta.
- Uma preferência explícita mais recente substitui a anterior entre mensagens; a mudança é informada. Campos enviados pela interface são atualizações explícitas; campos omitidos preservam o contexto.
- Consultas de receita podem mostrar uma bebida que não atende às restrições, com aviso claro de que se trata de consulta. Recomendações nunca ignoram as restrições.
- “Outra opção” exclui as bebidas já sugeridas na sessão. Empates são resolvidos pelo ID do catálogo, garantindo previsibilidade.
- A confiança é uma pontuação de regras, não uma probabilidade estatística de acerto. O painel de interpretação mostra a intenção, os candidatos, as entidades e as regras acionadas.

## Estados e memória

`idle`, `awaiting_preferences`, `awaiting_clarification` e `awaiting_contribution` representam o fluxo. A última bebida permite entender “como preparar ela?”. Uma comparação aceita duas bebidas explícitas ou uma bebida mais o assunto anterior. Em casos ambíguos, prefira informar o nome.

Histórico e preferências ficam na memória do processo e não sobrevivem à reinicialização. Curiosidades ficam no JSON e sobrevivem. “Nova conversa” limpa a sessão e os filtros, sem apagar o catálogo ou o registro de feedback.

Durante a coleta de curiosidades, perguntas de receita não são gravadas como contribuições. Feedback também permanece separado. As contribuições são identificadas como não verificadas e nunca viram código, regras ou instruções executáveis.

## Melhoria controlada

Os registros locais ficam em `data/feedback.jsonl`. Categorias: `unrecognized`, `misclassified_intent`, `low_performance`, `explicit_feedback`, `rule_suggestion` e `knowledge_gap`. Cada evento guarda a mensagem, interpretação e turno anterior para revisão. Ao ultrapassar aproximadamente 1 MB, o arquivo é rotacionado para uma geração anterior.

Esses arquivos podem conter texto digitado pelo usuário. São locais, não são enviados a serviços externos e não devem ser incluídos ao compartilhar o projeto. O ZIP de distribuição exclui esses registros. O sistema não aprende automaticamente.

Processo de manutenção:

1. Examine os registros e identifique um caso reproduzível.
2. Acrescente um teste com a mensagem que falhou e a resposta ou ação esperada.
3. Para uma nova expressão de intenção existente, altere `patterns` em `data/regras.json`, mantendo limites de palavra e prioridades coerentes.
4. Para sinônimos, altere `ALIASES`. Para novas entidades, altere `EntityExtractor`.
5. Para uma capacidade nova, adicione a intenção, um plano e a geração correspondente. Se faltar conhecimento, adicione dados verificados ao catálogo em vez de fabricar uma resposta.
6. Para inferências, adicione uma `Rule` com fatos necessários, conclusão e prioridade; atualize a decisão que consome a conclusão.
7. Execute `python -m unittest -v`, revise os exemplos e reinicie o servidor quando modificar Python. O JSON é lido a cada turno.

## Limites explícitos

É um sistema especialista de domínio restrito, não um interpretador geral de português. Negações têm escopo local; ironia, orações muito complexas e termos fora do vocabulário podem exigir reformulação. A correção aproximada só atua sobre palavras longas próximas do vocabulário; não garante corrigir qualquer erro e aparece no diagnóstico.

“Pouco doce” ou “menos doce” é tratado conservadoramente como exclusão do perfil doce: não há escala sensorial numérica no catálogo. Ingredientes são comparados por nome; não há inferência automática de alergias. Datas aceitas são explícitas, no formato `dd/mm/aaaa`, e são validadas. Datas relativas não são convertidas. Números e unidades são extraídos. O módulo de capacidades calcula porções multiplicando as quantidades cadastradas; não converte gramas em mililitros nem medidas vagas. Calorias e teor alcoólico não são estimados. Custos usam exclusivamente valores fornecidos pelo usuário.

O validador garante invariantes do programa, não verifica fatos do mundo real. O histórico é limitado, e referências usam principalmente o último assunto. A aplicação continua local, de um único processo, sem autenticação para implantação pública. O catálogo é pequeno; sua leitura por turno é intencional para refletir contribuições imediatamente. Para uma base muito maior, pode-se adicionar cache por data de modificação, preservando os mesmos contratos.

## Extensão de capacidades práticas

`engine/capabilities.py` adiciona intenções práticas e tarefas pendentes próprias. `engine/online.py` realiza consulta enciclopédica externa apenas quando solicitada. Veja `NOVAS_CAPACIDADES.md` para contratos, exemplos e limites. Nenhum desses módulos grava no catálogo.
