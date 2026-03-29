# Grouped Runner Next Steps

## Estado atual

O fluxo agrupado já está operacional.

Componentes principais:

- [`run_grouped_ad_clicker.py`](/home/otavio/overseas-business-online/run_grouped_ad_clicker.py)
- [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py)
- [`groups.db`](/home/otavio/overseas-business-online/groups.db)
- [`groups_db.py`](/home/otavio/overseas-business-online/groups_db.py)
- [`streamlit_gui.py`](/home/otavio/overseas-business-online/streamlit_gui.py)
- [`clicklogs.db`](/home/otavio/overseas-business-online/clicklogs.db)

## O que já funciona

- grupos são criados no Streamlit
- queries são geradas por IA e salvas no SQLite
- cada grupo tem:
  - `city_name`
  - `rsw_id`
  - `proxy`
  - `enabled`
  - queries próprias
- o grouped runner lê só grupos ativos
- a rotação usa `last_query_position`
- o runner suporta:
  - `--dry-run`
  - `--once`
  - `--group-city`
  - `--max-concurrent-groups`
  - `--launch-stagger-seconds`
  - `--max-runtime-minutes`
- o grouped runner já roda pela UI do Streamlit
- o grouped runner já roda pela CLI
- o lifecycle forte existe em UI e CLI
- há stop por process group
- há click log por execução
- há click summary por ciclo
- há detecção de:
  - `google_blocked_after_captcha`
  - `ip_changed_mid_session`
  - `proxy_tunnel_failed`
- o proxy IPRoyal no formato:
  - `host:port:user:pass`
  já está suportado no codebase inteiro
- sticky session do IPRoyal está aplicada nesse formato
- cleanup automático existe para:
  - browsers órfãos
  - perfis UC antigos
  - artefatos antigos de logs e screenshots

## Logs e artefatos

Log operacional principal do cron:

- [`/home/otavio/overseas-business-online/.streamlit_logs/grouped_runner_cron.log`](/home/otavio/overseas-business-online/.streamlit_logs/grouped_runner_cron.log)

Log por execução do grouped runner:

- [`/home/otavio/overseas-business-online/.streamlit_logs/grouped_click_runs`](/home/otavio/overseas-business-online/.streamlit_logs/grouped_click_runs)

Padrão:

- `grouped_clicks_YYYYMMDD_HHMMSS_microseconds.log`

Cada linha contém:

- `timestamp`
- `city`
- `rsw_id`
- `query`
- `final_url`

Screenshots:

- [`/home/otavio/overseas-business-online/.run_screenshots`](/home/otavio/overseas-business-online/.run_screenshots)

## Cron atual

O servidor está em:

- `America/Sao_Paulo`

Cron atualmente configurado:

```cron
0 6 * * 1-5 cd /home/otavio/overseas-business-online && /home/otavio/overseas-business-online/.venv/bin/python run_grouped_ad_clicker.py --max-concurrent-groups 2 --max-runtime-minutes 540 >> /home/otavio/overseas-business-online/.streamlit_logs/grouped_runner_cron.log 2>&1
15 15 * * 1-5 cd /home/otavio/overseas-business-online && /home/otavio/overseas-business-online/.venv/bin/python scripts/stop_grouped_runner.py >> /home/otavio/overseas-business-online/.streamlit_logs/grouped_runner_cron.log 2>&1 && /home/otavio/overseas-business-online/.venv/bin/python /home/otavio/overseas-business-online/scripts/cleanup_old_artifacts.py --days 7 >> /home/otavio/overseas-business-online/.streamlit_logs/grouped_runner_cron.log 2>&1
0 6 * * 6 cd /home/otavio/overseas-business-online && /home/otavio/overseas-business-online/.venv/bin/python run_grouped_ad_clicker.py --max-concurrent-groups 2 --max-runtime-minutes 420 >> /home/otavio/overseas-business-online/.streamlit_logs/grouped_runner_cron.log 2>&1
15 13 * * 6 cd /home/otavio/overseas-business-online && /home/otavio/overseas-business-online/.venv/bin/python scripts/stop_grouped_runner.py >> /home/otavio/overseas-business-online/.streamlit_logs/grouped_runner_cron.log 2>&1 && /home/otavio/overseas-business-online/.venv/bin/python /home/otavio/overseas-business-online/scripts/cleanup_old_artifacts.py --days 7 >> /home/otavio/overseas-business-online/.streamlit_logs/grouped_runner_cron.log 2>&1
```

Significado:

- segunda a sexta:
  - inicia `06:00`
  - timer interno até `15:00`
  - guard em `15:15`
- sábado:
  - inicia `06:00`
  - timer interno até `13:00`
  - guard em `13:15`

## Validações já feitas

- `--dry-run` validado
- `--once` validado
- `--once --group-city` validado
- loop contínuo validado
- UI do Streamlit validada
- CLI validada
- stop por UI validado
- stop por CLI validado
- sticky session validada
- health-check após `402` validado
- click log por execução validado
- sessão longa de aproximadamente `3h` validada

Sessão longa validada:

- arquivo:
  - [`grouped_clicks_20260328_124018_652520.log`](/home/otavio/overseas-business-online/.streamlit_logs/grouped_click_runs/grouped_clicks_20260328_124018_652520.log)
- total de cliques:
  - `119`

Distribuição observada:

- `Guaratinguetá`: `24`
- `Florianópolis`: `23`
- `Belo Horizonte`: `23`
- `Brasilia`: `19`
- `Porto Alegre`: `19`
- `Bauru`: `11`

Também já foi validado:

- `proxy_tunnel_failed=Yes`
- espera do slot até o proxy voltar
- log:
  - `Proxy health restored after 402 Payment Required: ...`

## Regras operacionais atuais

- allowlist vazia é válida
- nesse caso:
  - todos os domínios são elegíveis
  - exceto os presentes na denylist
- no grouped runner, o `ad_clicker` não pode cair no fallback global de [`queries.txt`](/home/otavio/overseas-business-online/queries.txt)
- o grouped runner usa apenas queries do SQLite dos grupos

## Capacidade operacional atual do VPS

No estado atual:

- `max_concurrent_groups = 1`
  - mais estável
- `max_concurrent_groups = 2`
  - viável e já usado em produção
- `3+`
  - não recomendado neste VPS

Motivo principal:

- memória, swap e footprint dos browsers

## O que ainda falta de verdade

1. Continuar observando a estabilidade real com `2` concorrências por mais dias.
- A implementação está pronta.
- O ponto pendente é confiança operacional de longo prazo.

2. Se quiser mais visibilidade, criar uma tela simples de monitoramento no Streamlit para:
- `group_runs`
- `clicklogs.db`
- arquivos em [`grouped_click_runs`](/home/otavio/overseas-business-online/.streamlit_logs/grouped_click_runs)

3. Opcionalmente, adicionar relatórios agregados por:
- cidade
- `rsw_id`
- dia
- query

## O que não precisa mais entrar como pendência

- integração com Streamlit
- timer do loop
- concorrência configurável
- stagger
- sticky session do IPRoyal
- parsing do proxy `host:port:user:pass`
- lifecycle forte em UI
- lifecycle forte em CLI
- click log por execução
- health-check após `402`
- limpeza automática de artefatos antigos

## Próximo passo recomendado

O próximo passo mais útil agora é:

1. criar uma tela simples de monitoramento dos resultados no Streamlit

ou, se a prioridade for operação:

1. apenas continuar rodando e acompanhar estabilidade por alguns dias
