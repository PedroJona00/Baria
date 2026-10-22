# Hospedagem do BARIA

## Render: demonstração gratuita

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

## Preservar o JSON

No Render, disco persistente requer serviço pago. Revise os custos antes de contratar. Para habilitar:

1. Monte o disco em `/var/data`.
2. Defina `BARIA_DATA_DIR=/var/data/baria` e `BARIA_STORAGE_MODE=persistent`.
3. Mantenha **uma instância e um processo**. As threads do Waitress compartilham o lock de gravação.
4. Faça backup de `memoria.json` e, se necessário, `feedback.jsonl`.

Na primeira execução, a aplicação copia o catálogo para a pasta. Nas seguintes, não o sobrescreve. Atualizações futuras do catálogo no GitHub precisam ser conciliadas manualmente com o JSON persistido para preservar contribuições. Pare o serviço e faça backup antes de editar o arquivo de produção.

## Docker

```sh
docker build -t baria .
docker volume create baria-data
docker run --rm -p 8000:8000 -v baria-data:/data -e BARIA_DATA_DIR=/data -e BARIA_STORAGE_MODE=persistent baria
```

Abra `http://localhost:8000`. O volume nomeado mantém dados ao recriar o contêiner. A imagem executa como usuário sem privilégios. Para internet, coloque atrás de um proxy HTTPS e configure `BARIA_PUBLIC_URL=https://seu-dominio` e `BARIA_SECURE_COOKIE=1`.

## Verificação e operação

Execute `python -m unittest -v`. Consulte `https://SEU-DOMINIO/healthz`: deve retornar `status: ok` e o total do catálogo. No navegador, peça uma receita, faça uma pergunta de acompanhamento e teste uma contribuição. Reiniciar apaga sessões; curiosidades só devem sobreviver quando há armazenamento persistente.

O servidor valida a origem contra a URL configurada, sem confiar em cabeçalhos arbitrários de encaminhamento. Requisições têm limite de 12 KB; mensagens têm limite de 2.000 caracteres. Sessões expiram em uma hora, há até 1.000 sessões e um limite básico de 30 mensagens/minuto por sessão. Trocar o cookie permite contornar esse limite: para exposição ampla, use proteção de tráfego no proxy.

Não há login ou moderação prévia: qualquer visitante pode enviar curiosidades, visíveis a outros visitantes e marcadas como não verificadas. O motor serializa requisições pelo lock, inclusive buscas externas. Esta versão atende projetos pequenos; alta concorrência requer armazenamento compartilhado e redesenho das sessões antes de adicionar réplicas.

## Atualizar e reverter

Envie mudanças para `main` após passar nos testes e acompanhe o deploy no Render. Configure o serviço para aguardar checks do GitHub se disponível. Para reverter código, use um deploy anterior no painel. Reversão de código não restaura a memória: mantenha backup separado.

Arquivos `.env`, logs, backups e dados de `runtime/` são excluídos do Git. A aplicação não carrega `.env` automaticamente: configure variáveis no terminal ou no painel da hospedagem.
