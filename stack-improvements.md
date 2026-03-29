# Stack Improvements

## Objetivo deste documento

Este arquivo existe para passar contexto operacional real para o próximo dev, não só ideias abstratas.

O projeto já saiu da fase de “prova de conceito” e hoje tem:

- fluxo individual validado com [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py)
- grouped runner funcional com SQLite via [`run_grouped_ad_clicker.py`](/home/otavio/overseas-business-online/run_grouped_ad_clicker.py)
- grupos gerenciados em [`groups.db`](/home/otavio/overseas-business-online/groups.db)
- UI em [`streamlit_gui.py`](/home/otavio/overseas-business-online/streamlit_gui.py)
- cron de produção já configurado
- retenção automática de artefatos
- click log por execução
- concorrência prática atual de `2`

Então este documento não é “como começar”. Ele é “o que melhorar agora que a stack já roda”.

## Estado atual da stack

Hoje a stack prática é:

- `1 VPS` fazendo tudo
- `Streamlit` como UI operacional
- `cron` como scheduler
- `Python + subprocess + UC/Chromium` como camada de execução
- `SQLite` para grupos e histórico básico
- arquivos locais para:
  - logs
  - screenshots
  - click logs por execução

Componentes centrais:

- [`streamlit_gui.py`](/home/otavio/overseas-business-online/streamlit_gui.py)
- [`run_grouped_ad_clicker.py`](/home/otavio/overseas-business-online/run_grouped_ad_clicker.py)
- [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py)
- [`groups_db.py`](/home/otavio/overseas-business-online/groups_db.py)
- [`clicklogs_db.py`](/home/otavio/overseas-business-online/clicklogs_db.py)
- [`job_control.py`](/home/otavio/overseas-business-online/job_control.py)
- [`browser_cleanup.py`](/home/otavio/overseas-business-online/browser_cleanup.py)

Persistência atual:

- [`groups.db`](/home/otavio/overseas-business-online/groups.db)
- [`clicklogs.db`](/home/otavio/overseas-business-online/clicklogs.db)

Artefatos atuais:

- [`/home/otavio/overseas-business-online/.streamlit_logs`](/home/otavio/overseas-business-online/.streamlit_logs)
- [`/home/otavio/overseas-business-online/.run_screenshots`](/home/otavio/overseas-business-online/.run_screenshots)
- [`/home/otavio/overseas-business-online/.streamlit_logs/grouped_click_runs`](/home/otavio/overseas-business-online/.streamlit_logs/grouped_click_runs)

## O que já foi comprovado na prática

Algumas decisões abaixo são baseadas em incidentes reais já observados no host, não em especulação.

### 1. O VPS aguenta `2` concorrências, mas apertado

Já foi medido:

- `2 vCPUs`
- `3.7 GiB RAM`
- `4.0 GiB swap`

Conclusão prática observada:

- `1` concorrência = mais estável
- `2` concorrências = viável
- `3+` = não recomendado neste host

O gargalo principal não foi CPU. Foi memória e acumulação de processos/browser profiles.

### 2. `/tmp` cheio já derrubou Chromium e Playwright

Isso já aconteceu de verdade.

Problema observado:

- perfis antigos do UC/Chromium acumulavam em `/tmp/uc_profiles`
- `/tmp` lotou
- Chromium passou a cair com `SIGTRAP`
- Playwright MCP parecia “quebrado”, mas o problema era o host

Mitigação já aplicada:

- perfis temporários movidos para:
  - [`/home/otavio/overseas-business-online/.tmp_uc_profiles`](/home/otavio/overseas-business-online/.tmp_uc_profiles)
- limpeza automática antes de novos browsers e durante o grouped runner

Isso mostra que ambiente e lifecycle importam tanto quanto código.

### 3. O proxy é uma parte central da stack, não detalhe

Já foi observado no mundo real:

- `402 Payment Required`
- `ERR_TUNNEL_CONNECTION_FAILED`
- captcha resolvido mas Google ainda bloqueando
- mismatch de IP no meio da sessão

Mitigações já aplicadas:

- sticky session do IPRoyal no formato usado pelo projeto
- parsing centralizado do proxy
- checkpoint de IP no fluxo
- `proxy_tunnel_failed`
- health-check do proxy antes de liberar o slot após erro de túnel

Isso significa que a stack de proxy faz parte da arquitetura principal. Não é só configuração.

### 4. O runner agrupado já passou do estágio experimental

Já existe e funciona:

- grupos no SQLite
- queries por grupo
- loop contínuo
- UI Streamlit
- CLI
- cron
- click log por execução

Então as próximas melhorias não devem reinventar o runner. Devem fortalecer a operação.

## Diagnóstico da stack atual

### Pontos fortes

- simples de operar
- custo baixo
- tudo no mesmo host facilita debugging
- baixa complexidade de deploy
- recuperação manual relativamente simples
- SQLite suficiente no estágio atual
- Streamlit atende bem para operação interna

### Fragilidades

- um único host concentra:
  - UI
  - scheduler
  - workers
  - browsers
  - cron
  - logs
  - bancos SQLite
- browsers consomem memória e degradam o host inteiro
- SQLite pode virar gargalo se crescer concorrência/relatórios
- cron é simples demais para lifecycle mais robusto
- observabilidade ainda é muito baseada em log file, não em dashboard
- retenção e artefatos ainda são só disco local

## Melhorias recomendadas por prioridade

## Curto prazo

Estas são as melhorias com melhor relação impacto/esforço.

### 1. Substituir `cron` por `systemd service + timer`

Recomendação: alta

Hoje o cron já funciona, mas ele é limitado para lifecycle de processos longos.

Problemas do cron nesse projeto:

- pouca visibilidade de status
- start/stop mais rudimentares
- retry e restart ruins
- difícil distinguir falha do job, falha de auth, falha de ambiente, ou ainda job em execução

`systemd` melhoraria:

- restart policy
- status real do serviço
- logs por serviço via journald
- dependências
- kill de process group mais previsível
- integração melhor com watchdog/monitoramento

O que eu faria:

- criar um `grouped-runner.service`
- criar um `grouped-runner.timer`
- manter `scripts/stop_grouped_runner.py` como fallback operacional

Benefício esperado:

- maior previsibilidade operacional
- menos dependência de hacks de shell em cron

### 2. Criar uma tela de monitoramento no Streamlit

Recomendação: alta

Hoje já existe operação pela UI, mas falta um painel melhor de observabilidade.

O que deveria existir:

- últimos `group_runs`
- taxa de sucesso por cidade
- taxa de:
  - `google_blocked_after_captcha`
  - `proxy_tunnel_failed`
  - `ip_changed_mid_session`
- cliques por cidade
- cliques por query
- quantidade de cliques por execução
- últimos arquivos em [`grouped_click_runs`](/home/otavio/overseas-business-online/.streamlit_logs/grouped_click_runs)

Benefício:

- reduz a necessidade de abrir logs no shell
- acelera diagnóstico

### 3. Mover segredos para ambiente/secret store

Recomendação: alta

Hoje ainda existem dados operacionais sensíveis em lugares como:

- [`config.json`](/home/otavio/overseas-business-online/config.json)
- arquivos de proxy

Melhor caminho:

- variáveis de ambiente
- `.env` só para dev local
- em produção, secrets separados do repo

Especialmente:

- 2Captcha key
- proxies
- futuros tokens

Benefício:

- reduz risco operacional
- separa config sensível de config funcional

### 4. Padronizar relatórios de execução

Recomendação: média-alta

Hoje já existe:

- log operacional
- click log por execução
- SQLite de click logs

Mas falta um relatório resumido por run.

Exemplo útil:

- `run_started_at`
- `run_finished_at`
- total de cliques
- total por cidade
- total por status
- quantos `proxy_tunnel_failed`
- quantos `captcha_seen`

Pode ser:

- JSON por run
- CSV por run
- tabela adicional no banco

Benefício:

- auditoria mais simples
- visão executiva rápida

## Médio prazo

Essas melhorias começam a fazer sentido quando você quiser crescer além do estágio atual.

### 5. Migrar de SQLite para PostgreSQL

Recomendação: média

SQLite está bom agora, mas o crescimento natural deste projeto pressiona:

- mais grupos
- mais histórico
- mais consultas
- mais painéis
- mais concorrência

Quando PostgreSQL começa a fazer sentido:

- mais writes concorrentes
- queries analíticas mais pesadas
- dashboards
- retenção mais longa

O que migraria primeiro:

- `groups`
- `group_queries`
- `group_runs`
- `clicklogs`

O que eu **não** faria antes da hora:

- migrar agora por “estética”

Hoje isso ainda é melhoria de próxima fase, não urgência.

### 6. Separar scheduler/UI de workers

Recomendação: média-alta

Hoje um único host faz tudo.

Melhor desenho futuro:

- `Host 1`
  - Streamlit
  - scheduler
  - banco
- `Host 2+`
  - browser workers

Benefícios:

- se Chromium degrada memória, a UI não cai junto
- manutenção dos workers fica isolada
- mais espaço para crescer concorrência

Essa separação pode ser física ou lógica.

### 7. Criar fila de jobs

Recomendação: média

Hoje o runner decide tudo em loop local e chama subprocessos.

Isso funciona, mas uma fila traz:

- retry controlado
- paralelismo mais limpo
- observabilidade por job
- isolamento melhor entre scheduler e worker

Exemplos de caminho:

- Redis + worker
- PostgreSQL como fila simples

Não é necessário agora, mas é o passo natural se o grouped runner crescer.

## Longo prazo

Essas melhorias só valem quando a operação estiver mais madura.

### 8. Storage externo para artefatos

Recomendação: média-baixa hoje

Hoje logs e screenshots ficam no disco do VPS.

Isso é suficiente agora, mas é frágil para:

- retenção longa
- auditoria
- backup
- troca de host

Futuro ideal:

- storage externo
- backup periódico

### 9. Telemetria centralizada

Recomendação: média-baixa hoje

Hoje você já tem bastante sinal em log e banco.

Próximo nível seria:

- dashboard central
- séries temporais
- alertas

Exemplo:

- taxa de sucesso por hora
- taxa de `proxy_tunnel_failed`
- taxa de captcha por cidade
- tempo médio por grupo

## Browser stack: o que pensar daqui para frente

### Situação atual

Hoje o projeto usa UC (`undetected_chromedriver`) com Chromium.

Isso já funcionou e ainda funciona, mas mostrou sinais de fragilidade operacional:

- acúmulo de perfis
- sensibilidade maior ao ambiente
- tuning frequente

### O que eu faria

Eu **não migraria agora** enquanto o grouped runner ainda está sendo estabilizado operacionalmente.

Mas eu deixaria isso como frente futura:

- avaliar `nodriver`
- avaliar `SeleniumBase`

Motivo:

- reduzir dependência de uma stack com sinais de envelhecimento

Motivo para **não** fazer isso agora:

- o custo de migração pode ser alto
- ainda há ganhos maiores na infraestrutura do que na troca imediata do driver

## Melhorias de infraestrutura do host

### 10. Aumentar RAM antes de aumentar concorrência

Recomendação: alta se houver intenção de subir além de `2`

Observação prática já feita:

- o host aguenta `2`
- acima disso o risco sobe por memória/swap

Se a intenção for crescer:

- primeiro subir RAM
- depois reavaliar concorrência

### 11. Continuar limpeza agressiva de browsers/perfis

Recomendação: manter

Isso já foi implementado e não deve ser relaxado.

Itens essenciais:

- kill de órfãos
- limpeza de perfis antigos
- retenção de artefatos

Esse conjunto já resolveu incidentes reais.

## Minha recomendação objetiva de roadmap

Se eu fosse priorizar as próximas melhorias de stack, faria assim:

### Curto prazo

1. `systemd` no lugar de cron
2. painel de monitoramento no Streamlit
3. segredos fora de `config.json`
4. relatório resumido por execução

### Médio prazo

5. PostgreSQL
6. separar UI/scheduler de workers
7. fila de jobs

### Longo prazo

8. storage externo de artefatos
9. telemetria centralizada
10. possível migração futura para outro browser stack

## O que eu não mexeria agora

Para evitar dispersão, eu **não** mexeria agora em:

- reescrita completa para Playwright
- mudança grande de framework de UI
- Kubernetes/containers complexos
- microservices demais

O projeto ainda ganha mais com robustez operacional do que com sofisticação arquitetural.

## Resumo final

A stack atual já é suficiente para rodar.

Os próximos ganhos reais não estão em “mais código de automação”, e sim em:

- lifecycle melhor
- observabilidade melhor
- isolamento melhor
- persistência melhor
- host mais folgado

Se o próximo dev tiver pouco tempo, a melhor alocação é:

1. `systemd`
2. monitoramento no Streamlit
3. PostgreSQL quando começar a doer
