# BARIA — capacidades práticas

Estas funções usam programação tradicional e os dados existentes. Nenhuma função cadastra novas bebidas ou muda uma receita do catálogo. A opção original de adicionar uma curiosidade ao encerrar a conversa continua disponível.

## Experimente no chat

| Recurso | Mensagem |
|---|---|
| Substituição | “Posso trocar cachaça por vodka na caipirinha?” |
| Porções | “Como faço caipirinha para dez pessoas?” |
| Equipamento | “Como faço sem coqueteleira?” |
| Ajuste de sabor | “Ficou muito doce. Como ajusto?” |
| Ocasião | “O que combina com churrasco sem álcool?” |
| Orçamento | “Caipirinha com orçamento de 20 reais” |
| Conservação | “Posso preparar hoje e servir amanhã?” |
| Consulta externa | “Pesquise na internet sobre Aviation” |

Depois de escolher uma bebida, é possível perguntar “quanto preciso para 5 pessoas?” ou “como guardar?”. O assunto anterior é recuperado. Escreva “cancelar” para abandonar uma solicitação pendente, como o preenchimento dos custos.

## Substituições e adaptações

As trocas suportadas estão em `SUBSTITUTIONS`, no arquivo `engine/capabilities.py`. Incluem cachaça/vodka, rum branco/vodka, leite/bebida de aveia, leite/leite de coco, açúcar/mel, água com gás/água e água tônica/água com gás. O BARIA explica quando a troca altera o sabor ou a textura. Trocas não cadastradas não são inventadas. Restrições registradas de álcool e ingredientes são verificadas.

As orientações de equipamentos cobrem coqueteleira, liquidificador, coador, dosador e macerador. Não prometem textura idêntica. Não se deve agitar líquidos quentes ou gaseificados em recipiente fechado.

Os ajustes de sabor são sugestões graduais em uma pequena amostra. Não há uma quantidade universal que corrija qualquer receita. Com restrições registradas, o sistema começa pela diluição com água. Diluir não elimina o álcool já presente.

## Porções

O cálculo assume **uma receita cadastrada por porção e uma porção por pessoa**, explicitamente na resposta. Aceita de 1 a 200 porções, números e algumas formas por extenso como “dez”. Multiplica valores numéricos e frações, como `1/2 xícara`. Quantidades “a gosto” e opcionais ficam para ajuste ao servir. A receita-base no painel lateral permanece inalterada. Não há conversão de gramas para mililitros nem estimativa de consumo de uma festa inteira.

## Ocasiões

Há regras para churrasco, praia, piscina, festa, aniversário, jantar, pizza, sobremesa, café da manhã e dia frio. São sugestões de combinação por perfil de sabor, não avaliações objetivas ou garantias de harmonização. Restrições de álcool, sabores e ingredientes continuam sendo aplicadas.

## Orçamento sem preços inventados

Informe um limite e os custos das quantidades usadas em **uma receita**, por ingrediente. Exemplo:

> Caipirinha com orçamento de 20 reais
>
> cachaça = 3; limão = 1,50; açúcar = 0,20; gelo = 0

O resultado é R$ 4,70 para uma receita com esses dados de exemplo. Eles não são preços de mercado. O custo de qualquer ingrediente sem valor informado permanece desconhecido; não é assumido como zero. Você pode informar zero para um item já disponível, quando quiser estimar somente o gasto adicional.

Os valores são guardados na sessão, não no catálogo. O cálculo não representa a compra de embalagens inteiras e não inclui frete, utensílios ou serviços. Não use “garrafa de 1 litro custa 30 reais” no formato acima: o módulo espera o custo da quantidade consumida, não faz conversão de embalagens. Opções com custo completo podem ser comparadas ao limite informado.

## Conservação

O BARIA distingue produtos engarrafados de misturas preparadas e inclui links para a fonte. Para perecíveis, segue as orientações gerais de refrigeração da [FDA](https://www.fda.gov/food/buy-store-serve-safe-food/refrigerator-thermometers-cold-facts-about-food-safety). Não inventa uma validade específica para cada mistura nem garante conservação até o dia seguinte. Para produtos prontos, indica seguir o rótulo.

## Pesquisa externa

`engine/online.py` consulta a API pública da Wikipédia em português, com tentativa em inglês quando não há correspondência, via HTTPS, usando apenas `urllib` e `json` da biblioteca padrão. Não utiliza LLM, modelo treinado ou serviço de geração de texto. A [documentação do TextExtracts](https://www.mediawiki.org/wiki/Extension:TextExtracts) descreve os resumos consultados.

Somente quando solicitada a pesquisa, o termo informado é enviado ao serviço. Histórico, custos e curiosidades não são enviados. O sistema exige correspondência do nome no título e termos de bebida na introdução; mostra até três trechos com links das fontes. Resultados em inglês são identificados e não são traduzidos automaticamente. São resultados externos: podem tratar de nomes semelhantes e não são receitas validadas pelo BARIA.

A consulta depende da conexão e da disponibilidade da Wikipédia. Há timeout, limite de tamanho da resposta e tratamento de falha; o catálogo local continua funcionando sem internet. Nenhum resultado externo é salvo no JSON. Os links são criados como elementos de texto na interface, com destinos HTTPS permitidos.

## Manutenção e testes

`engine/capabilities.py` contém o reconhecimento e as regras das capacidades práticas. `engine/conversation.py` as integra às sessões, antes da resposta genérica de desconhecimento. `test_capabilities.py` verifica as novas funções e usa respostas simuladas para testar o serviço externo sem depender da rede.

Execute:

```powershell
python -m unittest -v
```

Depois de atualizar o código Python, pare o servidor antigo com Ctrl+C, execute `python app.py` novamente e recarregue a página com Ctrl+F5.
