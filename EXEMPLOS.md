# Exemplos executados pelo BARIA

Transcrições geradas por `python demo.py`, usando a mesma função chamada pela interface web e uma cópia temporária do catálogo.

## Conversa simples e contextual

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

## Negação, erro de digitação e mudança de preferência

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

## Contradição e esclarecimento

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

## Limite da base e feedback

**Usuário:** Quantas calorias tem a Caipirinha?

**BARIA:** Minha base não contém dados confiáveis para responder a essa pergunta. Posso consultar os ingredientes, o preparo e as curiosidades cadastradas, sem estimar essa informação.

**Usuário:** florb zzz blarg

**BARIA:** Não consegui identificar seu pedido com segurança. Posso recomendar bebidas, mostrar receitas ou comparar duas opções. Por exemplo: “algo cítrico sem álcool”.

**Usuário:** Não foi isso que eu pedi

**BARIA:** Registrei seu comentário para revisão manual. As regras não são alteradas automaticamente. O que você queria saber? Pode reformular seu pedido.

**Usuário:** Sugiro uma regra: reconhecer aromas florais

**BARIA:** Registrei seu comentário para revisão manual. As regras não são alteradas automaticamente.

## Contribuição persistente

**Usuário:** Limonada

**BARIA:** Limonada é uma bebida da categoria Suco, sem álcool. Perfis cadastrados: citrico, refrescante. A quantidade de açúcar pode ser ajustada à acidez do limão.

**Usuário:** encerrar

**BARIA:** Deseja adicionar alguma informação ou curiosidade sobre Limonada? Escreva sua contribuição ou responda “não”.

**Usuário:** sim

**BARIA:** Conte a informação ou curiosidade que deseja salvar.

**Usuário:** Eu prefiro servir a limonada com bastante gelo.

**BARIA:** Curiosidade salva na memória JSON como contribuição do usuário, ainda não verificada. Até a próxima!
