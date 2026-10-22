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

Usa Waitress, com um adaptador WSGI para o mesmo motor. Configure `HOST=0.0.0.0`, `PORT` e as variáveis descritas em [HOSPEDAGEM.md](#hospedagem). Em desenvolvimento, o padrão é `127.0.0.1:8000`. Recomendamos instalar dependências em um ambiente virtual (`python -m venv .venv`).

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

A suíte está reunida em `test_baria.py`, organizada por classes. Ela cobre preferências, contexto, negações, receitas, capacidades adicionais, persistência, HTTP, cache e validação do catálogo. O GitHub Actions executa os testes em Python 3.10 e 3.13, inicia os dois servidores para verificar requisições reais e constrói a imagem Docker para validar sua inicialização e conteúdo. `demo.py` atualiza a seção de exemplos deste README usando uma cópia temporária do catálogo.

## Organização

| Arquivo/pasta | Responsabilidade |
| --- | --- |
| `app.py` | Servidor local e persistência JSON. |
| `serve.py`, `web.py` | Servidor Waitress e interface WSGI. |
| `config.py` | Configurações e limites compartilhados pelos dois servidores. |
| `engine/catalog.py` | Validação do catálogo e cache da base de conhecimento. |
| `engine/` | Interpretação, entidades, intenções, contexto, regras e respostas. |
| `data/regras.json` | Padrões e prioridades configuráveis. |
| `data/memoria.json` | Catálogo inicial. |
| `static/` | Interface HTML, CSS e JavaScript responsiva. |
| `test_baria.py` | Testes automatizados. |

## Documentação

Toda a documentação está reunida neste arquivo.

- [Arquitetura e extensão](#arquitetura)
- [Capacidades e limitações](#capacidades-praticas)
- [Exemplos reais de conversa](#exemplos-de-conversas)
- [Hospedagem e operação](#hospedagem)
- [Como contribuir](#contribuir)
- [Segurança e dados](#seguranca)

## Limites

O entendimento depende das regras cadastradas. Confiança é uma pontuação heurística, não uma probabilidade. Não há aprendizado automático nem cadastro de receitas completas pelo chat. Ingredientes a evitar são comparados por texto, sem garantia de detecção de alérgenos. Receitas são referências culinárias.

A implantação utiliza **um processo e uma instância**. Escalar exige migrar sessões e gravações para armazenamento compartilhado. Não há autenticação nem moderação prévia das curiosidades.

Nenhuma licença de código aberto foi atribuída; o titular pode escolhê-la posteriormente. Dependências mantêm suas próprias licenças.

Se beber, não dirija. Bebidas alcoólicas são destinadas a maiores de idade.

---

## Guia completo

- [Arquitetura do motor conversacional](#arquitetura)
- [Capacidades práticas](#capacidades-praticas)
- [Exemplos de conversas](#exemplos-de-conversas)
- [Hospedagem e operação](#hospedagem)
- [Como contribuir](#contribuir)
- [Segurança e dados](#seguranca)
- [Arquivos de dados](#arquivos-de-dados)
- [Arquivos da interface](#arquivos-da-interface)

---

<a id="arquitetura"></a>

## Arquitetura do motor conversacional

### Análise do código anterior

O servidor, a recomendação e o diálogo estavam concentrados em `app.py`. A extração usava expressões regulares simples, não distinguia “doce” de “não gosto de doce” e não tinha histórico, classificação de intenção ou respostas próprias para perguntas de acompanhamento. Os campos da interface eram enviados em todas as mensagens, podendo substituir preferências já expressas na conversa. O estado de contribuição aceitava perguntas como se fossem curiosidades.

A evolução preserva o servidor da biblioteca padrão, o catálogo JSON, as receitas, o isolamento por cookie e a gravação atômica de curiosidades. O catálogo existente não foi substituído. A interface continua compatível com `message`, `drink`, `alternatives` e `preferences`, acrescentando feedback e diagnóstico opcional.

### Módulos

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

### Decisões e conflitos

- Restrições de álcool, ingredientes e sabores rejeitados eliminam candidatos antes da pontuação.
- Sabor compatível soma 5 pontos; cada ingrediente disponível encontrado soma 2. A inferência de refrescância sem álcool soma 1 quando aplicável.
- Exemplo de encadeamento: `wants_no_alcohol` implica `exclude_alcohol`; este fato, combinado com `wants_refreshing`, implica `prefer_refreshing_non_alcoholic`.
- As regras de intenção em `data/regras.json` possuem prioridade explícita. Pedidos específicos de receita ou explicação têm precedência sobre a mera presença de um nome de bebida.
- Preferências contraditórias na mesma mensagem geram esclarecimento sem recomendar. As demais preferências daquele pedido são recuperadas após a resposta.
- Uma preferência explícita mais recente substitui a anterior entre mensagens; a mudança é informada. Campos enviados pela interface são atualizações explícitas; campos omitidos preservam o contexto.
- Consultas de receita podem mostrar uma bebida que não atende às restrições, com aviso claro de que se trata de consulta. Recomendações nunca ignoram as restrições.
- “Outra opção” exclui as bebidas já sugeridas na sessão. Empates são resolvidos pelo ID do catálogo, garantindo previsibilidade.
- A confiança é uma pontuação de regras, não uma probabilidade estatística de acerto. O painel de interpretação mostra a intenção, os candidatos, as entidades e as regras acionadas.

### Estados e memória

`idle`, `awaiting_preferences`, `awaiting_clarification` e `awaiting_contribution` representam o fluxo. A última bebida permite entender “como preparar ela?”. Uma comparação aceita duas bebidas explícitas ou uma bebida mais o assunto anterior. Em casos ambíguos, prefira informar o nome.

Histórico e preferências ficam na memória do processo e não sobrevivem à reinicialização. Curiosidades ficam no JSON e sobrevivem. “Nova conversa” limpa a sessão e os filtros, sem apagar o catálogo ou o registro de feedback.

Durante a coleta de curiosidades, perguntas de receita não são gravadas como contribuições. Feedback também permanece separado. As contribuições são identificadas como não verificadas e nunca viram código, regras ou instruções executáveis.

### Melhoria controlada

Os registros locais ficam em `data/feedback.jsonl`. Categorias: `unrecognized`, `misclassified_intent`, `low_performance`, `explicit_feedback`, `rule_suggestion` e `knowledge_gap`. Cada evento guarda a mensagem, interpretação e turno anterior para revisão. Ao ultrapassar aproximadamente 1 MB, o arquivo é rotacionado para uma geração anterior.

Esses arquivos podem conter texto digitado pelo usuário. São locais, não são enviados a serviços externos e não devem ser incluídos ao compartilhar o projeto. O ZIP de distribuição exclui esses registros. O sistema não aprende automaticamente.

Processo de manutenção:

1. Examine os registros e identifique um caso reproduzível.
2. Acrescente um teste com a mensagem que falhou e a resposta ou ação esperada.
3. Para uma nova expressão de intenção existente, altere `patterns` em `data/regras.json`, mantendo limites de palavra e prioridades coerentes.
4. Para sinônimos, altere `ALIASES`. Para novas entidades, altere `EntityExtractor`.
5. Para uma capacidade nova, adicione a intenção, um plano e a geração correspondente. Se faltar conhecimento, adicione dados verificados ao catálogo em vez de fabricar uma resposta.
6. Para inferências, adicione uma `Rule` com fatos necessários, conclusão e prioridade; atualize a decisão que consome a conclusão.
7. Execute `python -m unittest -v`, revise os exemplos e reinicie o servidor quando modificar Python. Alterações nos arquivos JSON invalidam o cache automaticamente.

### Limites explícitos

É um sistema especialista de domínio restrito, não um interpretador geral de português. Negações têm escopo local; ironia, orações muito complexas e termos fora do vocabulário podem exigir reformulação. A correção aproximada só atua sobre palavras longas próximas do vocabulário; não garante corrigir qualquer erro e aparece no diagnóstico.

“Pouco doce” ou “menos doce” é tratado conservadoramente como exclusão do perfil doce: não há escala sensorial numérica no catálogo. Ingredientes são comparados por nome; não há inferência automática de alergias. Datas aceitas são explícitas, no formato `dd/mm/aaaa`, e são validadas. Datas relativas não são convertidas. Números e unidades são extraídos. O módulo de capacidades calcula porções multiplicando as quantidades cadastradas; não converte gramas em mililitros nem medidas vagas. Calorias e teor alcoólico não são estimados. Custos usam exclusivamente valores fornecidos pelo usuário.

O validador garante invariantes do programa, não verifica fatos do mundo real. O histórico é limitado, e referências usam principalmente o último assunto. A aplicação usa um único processo e não possui autenticação para implantação pública; o servidor de hospedagem está descrito na [seção de hospedagem](#hospedagem).

### Cache e validação de dados

`engine/catalog.py` mantém apenas a versão ativa do catálogo e da base de conhecimento em cache. A cada consulta, verifica caminho, datas de modificação/criação, tamanho e identidade dos arquivos. Os JSONs só são relidos e os índices reconstruídos quando essa assinatura muda. Salvar uma curiosidade invalida o cache imediatamente. Catálogo e regras continuam editáveis sem reiniciar; mudanças no código Python precisam de reinicialização.

A inicialização valida campos obrigatórios, IDs únicos, álcool booleano, ingredientes, quantidades não vazias/positivas e a estrutura das contribuições. Também verifica padrões, prioridades e confiança das regras. Isso não valida a veracidade culinária de receitas ou medidas textuais. Arquivos inválidos impedem a inicialização; se uma edição inválida ocorrer com o serviço em execução, as consultas retornam indisponibilidade em vez de usar silenciosamente dados antigos.

Cópias do catálogo e respostas retornadas a chamadores são isoladas do cache, evitando que uma alteração acidental em uma resposta contamine outras conversas.

### Servidores e configurações compartilhadas

O servidor local em `app.py` adapta suas requisições para `web.application`, a mesma aplicação usada pelo Waitress. Rotas, validação, cookies, expiração e limites de sessão seguem a mesma lógica nos dois modos. Requisições de chat exigem `Content-Type: application/json`, incluindo variantes com `charset`. A interface já envia esse cabeçalho.

`config.py` centraliza rotas estáticas, portas padrão, caminhos e limites. `HOST`, `PORT`, `BARIA_DATA_DIR`, `BARIA_PUBLIC_URL`, `BARIA_SECURE_COOKIE` e `BARIA_STORAGE_MODE` continuam configuráveis pelo ambiente. Para ajustar limites de desenvolvimento, edite as constantes do módulo e execute os testes.

### Extensão de capacidades práticas

`engine/capabilities.py` adiciona intenções práticas e tarefas pendentes próprias. `engine/online.py` realiza consulta enciclopédica externa apenas quando solicitada. Veja [seção correspondente](#capacidades-praticas) para contratos, exemplos e limites. Nenhum desses módulos grava no catálogo.

---

<a id="capacidades-praticas"></a>

## Capacidades práticas

Estas funções usam programação tradicional e os dados existentes. Nenhuma função cadastra novas bebidas ou muda uma receita do catálogo. A opção original de adicionar uma curiosidade ao encerrar a conversa continua disponível.

### Experimente no chat

| Recurso | Mensagem |
|---|---|
| Substituição | “Posso trocar cachaça por vodka na caipirinha?” |
| Porções | “Como faço caipirinha para dez pessoas?” |
| Equipamento | “Como faço sem coqueteleira?” |
| Ajuste de sabor | “Achei muito forte, como suavizar?” / “Ficou fraca ou aguada” |
| Ocasião | “O que combina com churrasco sem álcool?” |
| Orçamento | “Caipirinha com orçamento de 20 reais” |
| Conservação | “Posso preparar hoje e servir amanhã?” |
| Consulta externa | “Pesquise na internet sobre Aviation” |

Depois de escolher uma bebida, é possível perguntar “quanto preciso para 5 pessoas?” ou “como guardar?”. O assunto anterior é recuperado. Escreva “cancelar” para abandonar uma solicitação pendente, como o preenchimento dos custos.

### Substituições e adaptações

As trocas suportadas estão em `SUBSTITUTIONS`, no arquivo `engine/capabilities.py`. Incluem cachaça/vodka, rum branco/vodka, leite/bebida de aveia, leite/leite de coco, açúcar/mel, água com gás/água e água tônica/água com gás. O BARIA explica quando a troca altera o sabor ou a textura. Trocas não cadastradas não são inventadas. Restrições registradas de álcool e ingredientes são verificadas.

As orientações de equipamentos cobrem coqueteleira, liquidificador, coador, dosador e macerador. Não prometem textura idêntica. Não se deve agitar líquidos quentes ou gaseificados em recipiente fechado.

Os ajustes de sabor são sugestões graduais em uma pequena amostra. Não há uma quantidade universal que corrija qualquer receita. Com restrições registradas, o sistema pede quais ingredientes podem ser usados antes de sugerir adições. Diluir não elimina o álcool já presente.

### Variações para ajustar a bebida

O BARIA reconhece “bebida forte”, “achei ele muito forte”, “ficou pesada”, “quero menos forte”, “mais suave”, “mais leve”, “mais fraca”, “suavizar”, “amenizar” e “diluir”. Também aceita a grafia comum incorreta “suavisar”/“suavisa-lo” nessas solicitações.

“Ficou fraca”, “aguada”, “ralo”, “sem sabor”, “quero mais forte” e “menos aguado” acionam orientações para intensificar o sabor. O sistema não aumenta o álcool automaticamente. “Quero mais doce” e “quero menos doce” têm orientações diferentes; também há ajustes para amargor e acidez.

Exemplo: “Gostei do Espresso Martini, mas achei ele muito forte. Poderia mudar algo para suavisa-lo?” recebe sugestões de ajuste para o Espresso Martini, em vez de apenas sua descrição. O nome da bebida passa a ser o assunto para perguntas seguintes. A receita salva permanece inalterada.

As regras distinguem observações de objetivos: “ficou fraca” pede mais sabor; “quero mais fraca” pede suavização. Negativas como “não ficou forte” não disparam correção. Pedidos opostos na mesma mensagem, como “mais forte e mais fraco”, geram esclarecimento. Preferências novas como “quero algo doce” continuam no fluxo de recomendação. Essas regras têm escopo limitado e não compreendem qualquer construção de linguagem natural.

### Porções

O cálculo assume **uma receita cadastrada por porção e uma porção por pessoa**, explicitamente na resposta. Aceita de 1 a 200 porções, números e algumas formas por extenso como “dez”. Multiplica valores numéricos e frações, como `1/2 xícara`. Quantidades “a gosto” e opcionais ficam para ajuste ao servir. A receita-base no painel lateral permanece inalterada. Não há conversão de gramas para mililitros nem estimativa de consumo de uma festa inteira.

### Ocasiões

Há regras para churrasco, praia, piscina, festa, aniversário, jantar, pizza, sobremesa, café da manhã e dia frio. São sugestões de combinação por perfil de sabor, não avaliações objetivas ou garantias de harmonização. Restrições de álcool, sabores e ingredientes continuam sendo aplicadas.

### Orçamento sem preços inventados

Informe um limite e os custos das quantidades usadas em **uma receita**, por ingrediente. Exemplo:

> Caipirinha com orçamento de 20 reais
>
> cachaça = 3; limão = 1,50; açúcar = 0,20; gelo = 0

O resultado é R$ 4,70 para uma receita com esses dados de exemplo. Eles não são preços de mercado. O custo de qualquer ingrediente sem valor informado permanece desconhecido; não é assumido como zero. Você pode informar zero para um item já disponível, quando quiser estimar somente o gasto adicional.

Os valores são guardados na sessão, não no catálogo. O cálculo não representa a compra de embalagens inteiras e não inclui frete, utensílios ou serviços. Não use “garrafa de 1 litro custa 30 reais” no formato acima: o módulo espera o custo da quantidade consumida, não faz conversão de embalagens. Opções com custo completo podem ser comparadas ao limite informado.

### Conservação

O BARIA distingue produtos engarrafados de misturas preparadas e inclui links para a fonte. Para perecíveis, segue as orientações gerais de refrigeração da [FDA](https://www.fda.gov/food/buy-store-serve-safe-food/refrigerator-thermometers-cold-facts-about-food-safety). Não inventa uma validade específica para cada mistura nem garante conservação até o dia seguinte. Para produtos prontos, indica seguir o rótulo.

### Pesquisa externa

`engine/online.py` consulta a API pública da Wikipédia em português, com tentativa em inglês quando não há correspondência, via HTTPS, usando apenas `urllib` e `json` da biblioteca padrão. Não utiliza LLM, modelo treinado ou serviço de geração de texto. A [documentação do TextExtracts](https://www.mediawiki.org/wiki/Extension:TextExtracts) descreve os resumos consultados.

Somente quando solicitada a pesquisa, o termo informado é enviado ao serviço. Histórico, custos e curiosidades não são enviados. O sistema exige correspondência do nome no título e termos de bebida na introdução; mostra até três trechos com links das fontes. Resultados em inglês são identificados e não são traduzidos automaticamente. São resultados externos: podem tratar de nomes semelhantes e não são receitas validadas pelo BARIA.

A consulta depende da conexão e da disponibilidade da Wikipédia. Há timeout, limite de tamanho da resposta e tratamento de falha; o catálogo local continua funcionando sem internet. Nenhum resultado externo é salvo no JSON. Os links são criados como elementos de texto na interface, com destinos HTTPS permitidos.

### Manutenção e testes

`engine/capabilities.py` contém o reconhecimento e as regras das capacidades práticas. `engine/conversation.py` as integra às sessões, antes da resposta genérica de desconhecimento. `test_baria.py` verifica as novas funções e usa respostas simuladas para testar o serviço externo sem depender da rede.

Execute:

```powershell
python -m unittest -v
```

Depois de atualizar o código Python, pare o servidor antigo com Ctrl+C, execute `python app.py` novamente e recarregue a página com Ctrl+F5.

---

<a id="exemplos-de-conversas"></a>

## Exemplos de conversas

<!-- BARIA:EXAMPLES:START -->

Transcrições geradas por `python demo.py`, usando a mesma função chamada pela interface web e uma cópia temporária do catálogo.

### Conversa simples e contextual

**Usuário:** Olá!

**BARIA:** Olá! Vamos encontrar sua bebida? Você prefere com ou sem álcool, e qual sabor?

**Usuário:** Quero algo cítrico sem álcool

**BARIA:** Minha sugestão é Mojito sem álcool. Respeita sua escolha sem álcool.
Também combina com o perfil citrico.
A receita está no painel. Ao encerrar a conversa, você poderá adicionar uma curiosidade.

Ingredientes:
• Limão: 25 ml de suco
• Hortelã: 8 folhas
• Açúcar: 2 colheres de chá
• Água com gás: 150 ml
• Gelo: a gosto

**Usuário:** Como preparar ela?

**BARIA:** Para preparar Mojito sem álcool:
1. Separe: Limão: 25 ml de suco; Hortelã: 8 folhas; Açúcar: 2 colheres de chá; Água com gás: 150 ml; Gelo: a gosto.
2. Pressione hortelã com açúcar e limão. Adicione gelo e água com gás.
As quantidades são da receita de referência cadastrada.

**Usuário:** Por que escolheu essa?

**BARIA:** Escolhi Mojito sem álcool porque respeita sua escolha sem álcool; combina com o perfil citrico.
Primeiro apliquei as restrições de álcool, ingredientes e sabores excluídos. Depois ordenei as opções por afinidade de sabor e ingredientes disponíveis. Empates usam a ordem do catálogo.

**Usuário:** Outra opção

**BARIA:** Para essas preferências, sugiro Limonada. Respeita sua escolha sem álcool.
Também combina com o perfil citrico.
A receita está no painel. Ao encerrar a conversa, você poderá adicionar uma curiosidade.

Ingredientes:
• Limão: 40 ml de suco
• Água: 200 ml
• Açúcar: 2 colheres de chá
• Gelo: a gosto

**Usuário:** O que eu pedi?

**BARIA:** Nesta conversa, lembro: bebidas sem álcool; perfil citrico; última bebida: Limonada.

### Negação, erro de digitação e mudança de preferência

**Usuário:** Não gosto de doce, quero algo refescante sem álcool

**BARIA:** Minha sugestão é Mojito sem álcool. Respeita sua escolha sem álcool.
Também combina com o perfil refrescante; respeita os perfis de sabor que você excluiu.
A receita está no painel. Ao encerrar a conversa, você poderá adicionar uma curiosidade.

Ingredientes:
• Limão: 25 ml de suco
• Hortelã: 8 folhas
• Açúcar: 2 colheres de chá
• Água com gás: 150 ml
• Gelo: a gosto
Interpretei: refescante → refrescante.

**Usuário:** Na verdade, agora prefiro com álcool e amargo

**BARIA:** Atualizei suas preferências conforme o pedido mais recente.
Para essas preferências, sugiro Negroni. Respeita sua escolha com álcool.
Também combina com o perfil amargo; respeita os perfis de sabor que você excluiu.
A receita está no painel. Ao encerrar a conversa, você poderá adicionar uma curiosidade.

Ingredientes:
• Gin: 30 ml
• Campari: 30 ml
• Vermute tinto: 30 ml
• Gelo: a gosto
• Laranja: 1 fatia

**Usuário:** Receita curta

**BARIA:** Negroni — preparo: Misture os líquidos com gelo e finalize com laranja.

### Contradição e esclarecimento

**Usuário:** Quero algo cítrico com álcool e sem álcool

**BARIA:** Encontrei preferências contraditórias na mesma mensagem. Você quer com ou sem álcool?

**Usuário:** Sem álcool

**BARIA:** Minha sugestão é Mojito sem álcool. Respeita sua escolha sem álcool.
Também combina com o perfil citrico.
A receita está no painel. Ao encerrar a conversa, você poderá adicionar uma curiosidade.

Ingredientes:
• Limão: 25 ml de suco
• Hortelã: 8 folhas
• Açúcar: 2 colheres de chá
• Água com gás: 150 ml
• Gelo: a gosto

**Usuário:** Compare Mojito e Mojito sem álcool

**BARIA:** Mojito: com álcool; sabores: citrico, refrescante.
Mojito sem álcool: sem álcool; sabores: citrico, refrescante.
Ingredientes de Mojito: Rum branco, Limão, Hortelã, Açúcar, Água com gás, Gelo.
Ingredientes de Mojito sem álcool: Limão, Hortelã, Açúcar, Água com gás, Gelo.
Para uma pergunta sobre apenas uma delas, use o nome da bebida.

### Limite da base e feedback

**Usuário:** Quantas calorias tem a Caipirinha?

**BARIA:** Minha base não contém dados confiáveis para responder a essa pergunta. Posso consultar os ingredientes, o preparo e as curiosidades cadastradas, sem estimar essa informação.

**Usuário:** florb zzz blarg

**BARIA:** Não consegui identificar seu pedido com segurança. Posso recomendar bebidas, mostrar receitas ou comparar duas opções. Por exemplo: “algo cítrico sem álcool”.

**Usuário:** Não foi isso que eu pedi

**BARIA:** Registrei seu comentário para revisão manual. As regras não são alteradas automaticamente. O que você queria saber? Pode reformular seu pedido.

**Usuário:** Sugiro uma regra: reconhecer aromas florais

**BARIA:** Registrei seu comentário para revisão manual. As regras não são alteradas automaticamente.

### Contribuição persistente

**Usuário:** Limonada

**BARIA:** Limonada é uma bebida da categoria Suco, sem álcool. Perfis cadastrados: citrico, refrescante. A quantidade de açúcar pode ser ajustada à acidez do limão.

**Usuário:** encerrar

**BARIA:** Deseja adicionar alguma informação ou curiosidade sobre Limonada? Escreva sua contribuição ou responda “não”.

**Usuário:** sim

**BARIA:** Conte a informação ou curiosidade que deseja salvar.

**Usuário:** Eu prefiro servir a limonada com bastante gelo.

**BARIA:** Curiosidade salva na memória JSON como contribuição do usuário, ainda não verificada. Até a próxima!

<!-- BARIA:EXAMPLES:END -->

---

<a id="hospedagem"></a>

## Hospedagem e operação

### Render: demonstração gratuita

1. Conecte `PedroJona00/Baria` ao Render.
2. Crie um Blueprint com `render.yaml`, ou um **Web Service** Python no plano **Free**.
3. Build: `pip install -r requirements.txt`. Start: `python serve.py`. Health check: `/healthz`.
4. Configure as variáveis abaixo; no Blueprint elas já estão declaradas.
5. Aguarde o deploy terminar e teste a URL HTTPS, uma recomendação e uma pergunta de acompanhamento.

| Variável | Render Free | Uso |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Interface de escuta. |
| `PORT` | Fornecida pela plataforma | Porta interna. |
| `BARIA_DATA_DIR` | `/tmp/baria-data` | Memória e feedback graváveis. |
| `BARIA_STORAGE_MODE` | `ephemeral` | Aviso de armazenamento temporário. |
| `BARIA_SECURE_COOKIE` | `1` | Cookie somente por HTTPS. |
| `BARIA_PUBLIC_URL` | Opcional no Render | Origem HTTPS exata, sem barra final. |

O Render fornece `RENDER_EXTERNAL_URL`, usada para validar a origem quando `BARIA_PUBLIC_URL` não foi definida. Para domínio próprio, defina esta última com a URL exata.

**No Free, arquivos alterados são perdidos em reinicializações, novos deploys e suspensão por inatividade.** O catálogo inicial será recuperado do repositório. A página e o fluxo de curiosidades avisam disso. O primeiro acesso depois de inatividade pode demorar. Revise limites e possíveis excedentes da sua conta antes de divulgação ampla.

Fontes oficiais: [plano gratuito](https://render.com/docs/free), [serviço Python](https://render.com/docs/deploy-flask), [discos persistentes](https://render.com/docs/disks).

### Preservar o JSON

No Render, disco persistente requer serviço pago. Revise os custos antes de contratar. Para habilitar:

1. Monte o disco em `/var/data`.
2. Defina `BARIA_DATA_DIR=/var/data/baria` e `BARIA_STORAGE_MODE=persistent`.
3. Mantenha **uma instância e um processo**. As threads do Waitress compartilham o lock de gravação.
4. Faça backup de `memoria.json` e, se necessário, `feedback.jsonl`.

Na primeira execução, a aplicação copia o catálogo para a pasta. Nas seguintes, não o sobrescreve. Atualizações futuras do catálogo no GitHub precisam ser conciliadas manualmente com o JSON persistido para preservar contribuições. Pare o serviço e faça backup antes de editar o arquivo de produção.

### Docker

```sh
docker build -t baria .
docker volume create baria-data
docker run --rm -p 8000:8000 -v baria-data:/data -e BARIA_DATA_DIR=/data -e BARIA_STORAGE_MODE=persistent baria
```

Abra `http://localhost:8000`. O volume nomeado mantém dados ao recriar o contêiner. A imagem executa como usuário sem privilégios e copia apenas o servidor, os módulos, a interface e os dois JSONs de distribuição; testes, geradores e documentação ficam fora da imagem. Para internet, coloque atrás de um proxy HTTPS e configure `BARIA_PUBLIC_URL=https://seu-dominio` e `BARIA_SECURE_COOKIE=1`.

### Verificação e operação

Execute `python -m unittest -v`. Consulte `https://SEU-DOMINIO/healthz`: deve retornar `status: ok` e o total do catálogo. No navegador, peça uma receita, faça uma pergunta de acompanhamento e teste uma contribuição. Reiniciar apaga sessões; curiosidades só devem sobreviver quando há armazenamento persistente.

O servidor valida a origem contra a URL configurada, sem confiar em cabeçalhos arbitrários de encaminhamento. Requisições têm limite de 12 KB; mensagens têm limite de 2.000 caracteres. Sessões expiram em uma hora, há até 1.000 sessões e um limite básico de 30 mensagens/minuto por sessão. Trocar o cookie permite contornar esse limite: para exposição ampla, use proteção de tráfego no proxy.

Não há login ou moderação prévia: qualquer visitante pode enviar curiosidades, visíveis a outros visitantes e marcadas como não verificadas. O motor serializa requisições pelo lock, inclusive buscas externas. Esta versão atende projetos pequenos; alta concorrência requer armazenamento compartilhado e redesenho das sessões antes de adicionar réplicas.

### Atualizar e reverter

Envie mudanças para `main` após passar nos testes e acompanhe o deploy no Render. Configure o serviço para aguardar checks do GitHub se disponível. Para reverter código, use um deploy anterior no painel. Reversão de código não restaura a memória: mantenha backup separado.

Arquivos `.env`, logs, backups e dados de `runtime/` são excluídos do Git. A aplicação não carrega `.env` automaticamente: configure variáveis no terminal ou no painel da hospedagem.

---

<a id="contribuir"></a>

## Como contribuir

1. Crie uma branch com uma alteração delimitada.
2. Inclua testes de conversa que demonstrem o novo comportamento e casos negativos.
3. Execute `python -m unittest -v`.
4. Abra um pull request descrevendo a mudança e sua validação.

### Adicionar bebidas

Edite `data/memoria.json`: cada item precisa de `id` único, `nome`, `alcool` booleano, `categoria`, `tags`, `ingredientes` (nome/quantidade), `preparo`, `curiosidade` e `contribuicoes` inicialmente vazio. Confira as informações e atualize o total na interface, README e teste de catálogo.

### Novas regras

Consulte [seção correspondente](#arquitetura) e [seção correspondente](#capacidades-praticas). Padrões e prioridades ficam em `data/regras.json`; extração, inferência e respostas ficam em `engine/`. Teste negações, conflitos, erros simples e acompanhamentos. Preserve a abordagem sem modelos treinados.

Feedback é insumo para revisão humana. Não publique logs brutos: transforme falhas em exemplos fictícios, revise a regra e acrescente testes. Não há aprendizado ou atualização automática.

---

<a id="seguranca"></a>

## Segurança e dados

Não publique senhas, tokens, mensagens privadas ou logs em issues. Para problemas sensíveis, use o reporte privado do GitHub quando habilitado pelo mantenedor; não exponha detalhes antes da correção.

Curiosidades do chat podem aparecer para outros visitantes e não passam por moderação prévia. Mensagens não reconhecidas e feedback podem ser registrados no servidor. Não envie dados pessoais. Sessões são temporárias e o cookie contém um identificador aleatório, não a conversa. Não há autenticação nem garantia de anonimato perante a hospedagem.

O repositório inclui apenas o catálogo de distribuição. `.gitignore` exclui logs, backups, `.env`, ambiente virtual e `runtime/`. Não envie o JSON de produção sem revisar e remover contribuições de usuários.

Use HTTPS, `BARIA_SECURE_COOKIE=1`, origem pública correta, backups e uma instância/um processo. Revise dependências e contribuições periodicamente. Para maior exposição, acrescente moderação, autenticação administrativa e limites de tráfego no proxy.

---

<a id="arquivos-de-dados"></a>

## Arquivos de dados

`data/memoria.json` contém o catálogo inicial. `data/regras.json` contém padrões de intenção. Logs e backups locais ficam fora do Git.

---

<a id="arquivos-da-interface"></a>

## Arquivos da interface

Arquivos HTML, CSS e JavaScript servidos pelo backend Python. A interface usa a API /api/chat para manter contexto e mostrar receitas.
