# Contribuir com BARIA

1. Crie uma branch com uma alteração delimitada.
2. Inclua testes de conversa que demonstrem o novo comportamento e casos negativos.
3. Execute `python -m unittest -v`.
4. Abra um pull request descrevendo a mudança e sua validação.

## Adicionar bebidas

Edite `data/memoria.json`: cada item precisa de `id` único, `nome`, `alcool` booleano, `categoria`, `tags`, `ingredientes` (nome/quantidade), `preparo`, `curiosidade` e `contribuicoes` inicialmente vazio. Confira as informações e atualize o total na interface, README e teste de catálogo.

## Novas regras

Consulte `ARQUITETURA.md` e `NOVAS_CAPACIDADES.md`. Padrões e prioridades ficam em `data/regras.json`; extração, inferência e respostas ficam em `engine/`. Teste negações, conflitos, erros simples e acompanhamentos. Preserve a abordagem sem modelos treinados.

Feedback é insumo para revisão humana. Não publique logs brutos: transforme falhas em exemplos fictícios, revise a regra e acrescente testes. Não há aprendizado ou atualização automática.
