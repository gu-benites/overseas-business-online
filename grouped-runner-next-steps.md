# Grouped Runner Next Steps

## Contexto atual

O fluxo individual com [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py) já foi validado.

Também já existe a base SQLite para grupos em:

- [`groups.db`](/home/otavio/overseas-business-online/groups.db)
- [`groups_db.py`](/home/otavio/overseas-business-online/groups_db.py)

Além disso:

- grupos já podem ser criados no Streamlit
- queries são geradas por IA e salvas no SQLite
- cada grupo possui:
  - `city_name`
  - `rsw_id`
  - `proxy`
  - `enabled`
  - queries próprias

## Decisão de arquitetura

### Não reutilizar `run_ad_clicker.py` para grupos

[`run_ad_clicker.py`](/home/otavio/overseas-business-online/run_ad_clicker.py) foi desenhado para:

- `query_file`
- `proxy_file`
- distribuição genérica entre browsers

Ele não respeita o novo conceito de:

- `1 grupo = 1 cidade + 1 proxy + queries do SQLite + rsw_id`

Por isso, o caminho correto é:

- manter [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py) como worker real
- criar um novo orquestrador específico para grupos

## Próximo componente a criar

Criar:

- [`run_grouped_ad_clicker.py`](/home/otavio/overseas-business-online/run_grouped_ad_clicker.py)

Responsabilidade:

1. ler grupos ativos no SQLite
2. iterar continuamente entre eles
3. selecionar a próxima query de cada grupo
4. chamar [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py) com:
   - `-q <query>`
   - `-p <proxy>`
5. registrar histórico em `group_runs`

## Progresso já implementado

### Concluído

- base SQLite criada em [`groups_db.py`](/home/otavio/overseas-business-online/groups_db.py)
- banco [`groups.db`](/home/otavio/overseas-business-online/groups.db) inicializável
- tabelas:
  - `groups`
  - `group_queries`
  - `group_runs`
- tela de grupos criada no Streamlit
- criação de grupo por cidade
- geração automática de queries por IA em background
- queries persistidas no SQLite
- campo `last_query_position` adicionado para rotação persistida
- primeira versão de [`run_grouped_ad_clicker.py`](/home/otavio/overseas-business-online/run_grouped_ad_clicker.py) criada

### O que o runner já faz

- lê grupos ativos do SQLite
- seleciona a próxima query de cada grupo
- atualiza a rotação com `last_query_position`
- suporta `--dry-run`
- suporta `--once`
- executa sequencialmente
- chama [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py)
- grava resultados básicos em `group_runs`

## Regras operacionais do runner agrupado

O runner agrupado deve:

- usar apenas grupos com `enabled = true`
- manter vínculo fixo:
  - grupo -> proxy -> queries
- usar o `rsw_id` como parte do contexto operacional
- registrar cidade e `rsw_id` em logs e histórico
- ignorar completamente `query_file` e `proxy_file` do fluxo antigo

## Estratégia recomendada de implementação

### Etapa 1: leitura e seleção

Implementar um modo inicial que:

1. liste grupos ativos
2. recupere queries de cada grupo
3. escolha a próxima query de cada grupo
4. logue a ordem de rotação

Sem abrir navegador ainda.

Objetivo:

- validar a rotação lógica sem custo de execução real

Status:

- concluído na implementação inicial via `--dry-run`

### Etapa 2: dry-run operacional

Criar um modo `dry-run` no [`run_grouped_ad_clicker.py`](/home/otavio/overseas-business-online/run_grouped_ad_clicker.py)
que apenas mostre algo como:

- grupo
- cidade
- `rsw_id`
- proxy
- query escolhida

Exemplo esperado:

- grupo Guaratinguetá -> query 1
- grupo Florianópolis -> query 1
- grupo Bauru -> query 1
- grupo Belo Horizonte -> query 1

Sem abrir browser.

Status:

- concluído

### Etapa 3: 1 ciclo real

Executar um ciclo real:

- uma execução de [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py) por grupo ativo
- uma query por grupo

Objetivo:

- validar a integração runner SQLite -> ad_clicker
- validar escrita em `group_runs`

Status:

- validado operacionalmente com grupos reais
- `run_grouped_ad_clicker.py --once` já executou os 4 grupos ativos
- `group_runs` já está sendo preenchido
- `last_query_position` já avança em ciclo real

### Etapa 4: loop contínuo

Depois do ciclo real validado:

- colocar o runner em loop contínuo
- iterando apenas entre grupos ativos

Status:

- implementado no runner
- ainda falta validar em execução contínua mais longa

## Estado de rotação das queries

O runner agrupado vai precisar saber qual é a próxima query de cada grupo.

Opções:

### Opção simples inicial

Selecionar sempre em memória durante a execução do runner.

Vantagem:

- implementação mais rápida

Desvantagem:

- ao reiniciar o runner, a ordem reinicia

### Opção recomendada depois

Persistir a posição atual da última query usada no SQLite.

Possíveis caminhos:

1. adicionar campo em `groups`
   - `last_query_position`

ou

2. inferir pelo último `group_runs.query_used`

A opção 1 tende a ser mais simples e robusta.

Status:

- implementado com `last_query_position` em `groups`
- validado em `dry-run` e em ciclo real

## Integração com `group_runs`

Cada execução real deve registrar:

- `group_id`
- `city_name`
- `rsw_id`
- `started_at`
- `finished_at`
- `status`
- `query_used`
- `captcha_seen`
- `ads_found`
- `ads_clicked`
- `notes`

## Fluxo esperado do runner agrupado

Para cada grupo ativo:

1. carregar grupo
2. carregar queries do grupo
3. selecionar próxima query
4. criar `group_run` com status inicial
5. chamar [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py)
6. capturar resultado
7. finalizar `group_run`
8. seguir para o próximo grupo ativo

## Melhor abordagem de execução

Inicialmente, a melhor abordagem é:

- execução sequencial por grupo

Motivo:

- reduz complexidade
- facilita debugging
- facilita leitura dos logs
- evita misturar problemas de concorrência cedo demais

Paralelismo por grupo pode ser avaliado depois.

## Testes recomendados

### Teste 1: banco

Confirmar:

- grupos ativos são lidos corretamente
- queries por grupo existem
- proxies existem
- `rsw_id` existe

### Teste 2: dry-run

Confirmar:

- rotação entre grupos funciona
- query escolhida por grupo faz sentido

Status:

- validado
- o `--dry-run` mostra a ordem dos grupos reais corretamente
- o `--dry-run` não altera mais `last_query_position`

### Teste 3: ciclo real curto

Confirmar:

- runner consegue chamar [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py)
- `group_runs` é preenchido

Status:

- validado
- o runner já executou 1 ciclo real completo com os grupos atuais
- `group_runs` foi preenchido
- `last_query_position` avançou corretamente

### Teste 4: loop

Confirmar:

- grupos inativos são ignorados
- grupos ativos entram na rotação
- próxima query muda corretamente

Status:

- próximo teste recomendado
- ainda falta validar um loop mais longo em produção

## O que não fazer agora

- não adaptar [`run_ad_clicker.py`](/home/otavio/overseas-business-online/run_ad_clicker.py) para este novo modelo
- não acoplar o grouped runner ao frontend antes da validação do runner em CLI
- não introduzir concorrência multi-grupo antes da versão sequencial funcionar

## Próximos passos imediatos

Agora que o runner já foi validado em `--dry-run` e `--once`, os próximos passos passam a ser:

- validar melhor os estados finais do `ad_clicker` no runner agrupado
- persistir telemetria estruturada quando o run termina sem a tabela normal de summary
- classificar casos como:
  - captcha resolvido mas Google ainda bloqueou
  - run concluído sem ads clicáveis
  - run concluído com clique
- depois disso, integrar o grouped runner ao Streamlit

## Resumo executivo

O próximo passo correto agora é:

1. finalizar a telemetria estruturada do `ad_clicker` no runner agrupado
2. validar no SQLite os casos de `google_blocked_after_captcha`
3. corrigir qualquer ponto de configuração ainda inconsistente no fluxo agrupado
4. só depois integrar o runner agrupado ao frontend

## Progresso mais recente

### Já validado na prática

- `run_grouped_ad_clicker.py --dry-run`
- `run_grouped_ad_clicker.py --once`
- `run_grouped_ad_clicker.py --once --group-city '<cidade>'`
- criação de `group_runs`
- avanço de `last_query_position`

### O que foi descoberto

- alguns runs do [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py) terminam sem imprimir a tabela final de summary
- isso acontece especialmente quando:
  - o captcha é resolvido
  - o token é aplicado
  - mas o Google continua bloqueando a sessão
- nesses casos, o runner agrupado perdia métricas porque dependia demais do summary textual

### O que já foi implementado para resolver isso

- [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py) agora suporta `--json-summary`
- o worker já imprime `JSON_SUMMARY:` no caminho normal de sucesso
- o worker agora também emite `JSON_SUMMARY:` no encerramento do run, mesmo fora do caminho “feliz”
- [`run_grouped_ad_clicker.py`](/home/otavio/overseas-business-online/run_grouped_ad_clicker.py) já consome `JSON_SUMMARY:` antes do parser textual
- o runner já classifica explicitamente:
  - `google_blocked_after_captcha`
  - `captcha_seen`
  - `captcha_token_received`
  - `captcha_token_applied`
  - `captcha_accepted`
- o parsing de proxy foi centralizado em [`proxy.py`](/home/otavio/overseas-business-online/proxy.py)
- o formato operacional principal agora suportado de forma explícita é:
  - `host:port:user:pass`
- a sticky session do IPRoyal agora também é aplicada nesse formato
- [`utils.py`](/home/otavio/overseas-business-online/utils.py) passou a montar `proxy_url` válido para requests auxiliares usando o proxy normalizado

### Próximo passo operacional imediato

- adicionar checkpoints de IP para detectar `ip_changed_mid_session`
- depois decidir se o grouped runner já pode ser integrado ao Streamlit ou se ainda precisa de mais endurecimento operacional

## Validações mais recentes

### Caso validado: captcha resolvido, mas Google continua bloqueando

Foi validado em execução real com:

- [`run_grouped_ad_clicker.py`](/home/otavio/overseas-business-online/run_grouped_ad_clicker.py) `--once --group-city 'Belo Horizonte'`

Resultado persistido no SQLite:

- `status = google_blocked_after_captcha`
- `captcha_seen = True`
- `ads_found = 0`
- `ads_clicked = 0`
- `notes` com:
  - `captcha_token_received=True`
  - `captcha_token_applied=True`
  - `captcha_accepted=False`
  - `google_blocked_after_captcha=True`

Isso confirma que:

- o runner agrupado já consegue distinguir esse caso do simples `completed`
- o `group_runs` ficou mais útil para debug operacional

### Caso validado: sticky session para o formato atual do IPRoyal

Foi endurecido o suporte ao formato que será usado no projeto:

- `geo.iproyal.com:12321:USUARIO:SENHA`

O que passou a valer:

- sticky session também nesse formato
- extração de `session_id`
- geração de `proxy_url` válido para requests auxiliares
- uso consistente do mesmo proxy no browser e no solver

Exemplo de transformação validada:

- entrada:
  - `geo.iproyal.com:12321:xGT...:N5k..._country-br_city-belohorizonte`
- saída sticky:
  - `geo.iproyal.com:12321:xGT...:N5k..._country-br_city-belohorizonte_session-<id>_lifetime-30m`

Isso reduz o risco de troca de IP no meio da sessão, que é um dos fatores mais fortes para `google_blocked_after_captcha`.

### Caso validado: checkpoints de IP no meio da sessão

O fluxo agora registra checkpoints de IP no [`search_controller.py`](/home/otavio/overseas-business-online/search_controller.py).

Checkpoints atuais:

- `session_start`
- `captcha_seen`
- `post_captcha_token_applied`

Comportamento implementado:

- salva `initial_proxy_ip`
- atualiza `latest_proxy_ip`
- marca `ip_changed_mid_session=True` se houver divergência
- interrompe o run se a troca for detectada
- o runner agrupado classifica esse caso com status:
  - `ip_changed_mid_session`

Validação prática já feita:

- Belo Horizonte rodou com:
  - `initial_proxy_ip=45.175.53.255`
  - `latest_proxy_ip=45.175.53.255`
  - `ip_changed_mid_session=No`
  - `status=completed`
  - `ads_found=4`
  - `ads_clicked=4`

### Caso esclarecido: allowlist vazia com denylist ativa

O runtime atual com:

- `Ad allowlist: []`
- `Ad denylist: [...]`

não representa erro, desde que a intenção operacional seja:

- permitir clique em qualquer domínio de anúncio
- exceto os domínios presentes na denylist

O log foi ajustado para ficar explícito:

- `Ad allowlist mode: disabled (all domains are eligible except those blocked by the denylist)`
- `Ad denylist mode: active (...)`

## Próximo passo correto agora

1. validar um caso real em que o proxy troque de IP no meio da sessão
2. continuar observando o loop contínuo por mais ciclos para medir taxa de falha por proxy/grupo
3. endurecer a classificação de falhas transitórias como `ERR_TUNNEL_CONNECTION_FAILED`
4. depois decidir se ele já pode entrar em loop contínuo de produção

## Integração com Streamlit

### Já implementado

O [`streamlit_gui.py`](/home/otavio/overseas-business-online/streamlit_gui.py) agora já permite iniciar o runner agrupado.

Controles disponíveis:

- `RUN active groups loop`
- `RUN active groups once`
- `RUN selected group once`
- `Enable loop timer`
- `Loop duration (minutes)`

Também foram adicionados na seção de jobs:

- `grouped runner loop`
- `grouped runner once`
- `selected group once`

Isso permite operar os grupos ativos via UI, no mesmo estilo prático do runner original.

Também foi adicionado timer opcional para o loop contínuo:

- checkbox para habilitar/desabilitar
- duração configurável em minutos
- quando o timer expira, o runner encerra o loop de forma limpa

### O que isso torna possível agora

- clicar para iniciar a rotação contínua dos grupos ativos
- limitar em minutos quanto tempo a rotação contínua deve durar
- clicar para rodar um ciclo único de todos os grupos ativos
- clicar para testar um grupo específico uma vez
- parar os jobs pela própria UI
- acompanhar logs recentes do runner agrupado pela UI

### Suporte em CLI

O [`run_grouped_ad_clicker.py`](/home/otavio/overseas-business-online/run_grouped_ad_clicker.py) agora também aceita:

- `--max-runtime-minutes <N>`

Esse parâmetro foi pensado para o loop contínuo e faz o runner parar de forma limpa ao atingir a duração configurada.

### Validação já feita na UI

Foi validado via interface web do Streamlit que:

- o botão `RUN active groups once` dispara o job corretamente
- a UI passa a mostrar `grouped runner once: running`
- o log do job é criado em:
  - [`/home/otavio/overseas-business-online/.streamlit_logs/run_grouped_ad_clicker_once.log`](/home/otavio/overseas-business-online/.streamlit_logs/run_grouped_ad_clicker_once.log)

No teste validado, o runner já iniciou com:

- grupo `Bauru`
- query `desentupidora em Bauru`

Também foi validado na prática o caminho de loop contínuo:

- a UI mostrou `grouped runner loop: running (pid=2633732)`
- o job correspondente escreveu em:
  - [`/home/otavio/overseas-business-online/.streamlit_logs/run_grouped_ad_clicker.log`](/home/otavio/overseas-business-online/.streamlit_logs/run_grouped_ad_clicker.log)

## Observação real de 5 minutos do loop contínuo

Janela observada:

- aproximadamente entre `2026-03-27 16:20 UTC` e `2026-03-27 16:25 UTC`

Sequência observada no log do runner:

1. `Bauru`
   - início já estava logado em `16:17:25 UTC`
   - terminou em `16:21:05 UTC`
   - status:
     - `completed`
   - métricas:
     - `ads_found=4`
     - `ads_clicked=4`
     - `captcha_seen=No`
   - IP:
     - `initial_proxy_ip=187.109.131.215`
     - `latest_proxy_ip=187.109.131.215`
   - duração observada:
     - cerca de `3m40s`

2. `Belo Horizonte`
   - começou em `16:21:05 UTC`
   - terminou em `16:23:42 UTC`
   - status:
     - `failed`
   - causa identificada no [`adclicker.log`](/home/otavio/overseas-business-online/logs/adclicker.log):
     - `net::ERR_TUNNEL_CONNECTION_FAILED`
   - observação:
     - falhou antes de produzir métricas de captcha/IP úteis
   - duração observada:
     - cerca de `2m37s`

3. `Brasilia`
   - começou em `16:23:42 UTC`
   - aos `16:24:19 UTC` já tinha checkpoint de IP inicial:
     - `189.6.36.43`
   - aos `16:24:53 UTC` já tinha encontrado anúncios
   - entre `16:24:56 UTC` e `16:26:22 UTC` estava clicando anúncios normalmente
   - run finalizado depois da janela principal de 5 minutos com:
     - `status=completed`
     - `ads_found=4`
     - `ads_clicked=3`
     - `captcha_seen=No`
     - `initial_proxy_ip=189.6.36.43`
     - `latest_proxy_ip=189.6.36.43`

4. `Florianópolis`
   - já estava marcado como `started` logo após `Brasilia`
   - ainda sem conclusão no momento do fechamento desta observação

## Pace observado

Ritmo real visto neste monitoramento:

- quando o grupo roda sem captcha e sem erro de proxy, o ciclo tende a levar cerca de `3` a `4` minutos
- uma falha precoce de túnel/proxy pode encerrar um grupo em cerca de `2` a `3` minutos
- o runner agenda o próximo grupo imediatamente após finalizar o anterior
- dentro de um grupo bem-sucedido, o tempo até começar a clicar anúncios ficou em torno de `1` minuto após o start do grupo

Conclusão operacional deste monitoramento:

- o loop contínuo está funcional
- ele não trava entre grupos
- o principal gargalo observado nesta janela não foi captcha, mas sim instabilidade pontual de túnel/proxy em um dos grupos

## Capacidade atual estimada do VPS

Medição feita com o loop rodando e um `ad_clicker` ativo:

- CPU disponível:
  - `2 vCPUs`
- memória total:
  - `3.7 GiB`
- swap total:
  - `4.0 GiB`
- memória disponível no momento da medição:
  - cerca de `997 MiB`
- swap já em uso no momento da medição:
  - cerca de `2.1 GiB`
- load average:
  - `2.37 / 1.56 / 1.03`

Footprint do run ativo medido pela árvore do processo do grouped runner:

- `1 ad_clicker` ativo com browser Chromium:
  - `TOTAL_RSS_KB 1677096`
  - aproximadamente `1.6 GiB` de RSS somando Python + chromedriver + processos do Chromium
  - uso instantâneo agregado de CPU da árvore:
    - cerca de `62.9%`

Observação importante:

- havia também pelo menos um browser órfão antigo ainda aberto
- isso consumia algo na faixa de `700-800 MiB`
- então qualquer estimativa de concorrência precisa assumir limpeza de processos órfãos entre runs

### Recomendação de concorrência no VPS atual

Sem mudar a máquina:

1. `1` concorrência
   - seguro
   - recomendado para estabilidade atual

2. `2` concorrências
   - possível, mas limítrofe
   - só recomendável após garantir limpeza de browsers órfãos
   - risco real de aumentar swap, latência e crashes de Chromium

3. `3` ou mais concorrências
   - não recomendável neste VPS atual
   - alto risco de pressão de memória, swap excessivo e degradação forte

### Conclusão prática para evolução do runner

- o próximo passo de escala deve ser um `max_concurrent_groups` configurável
- no VPS atual, o ponto de partida mais razoável é:
  - `max_concurrent_groups = 2`
- para produção estável, `1` continua sendo o valor conservador
- para algo como `100` grupos, será necessário:
  - concorrência limitada com fila
  - limpeza rigorosa de browsers órfãos
  - e, idealmente, um VPS com mais RAM antes de subir muito além de `2`

### Endurecimento já implementado depois desta medição

O grouped runner agora faz limpeza automática de browsers órfãos antes de iniciar cada grupo:

- detecta árvores órfãs do app com PPID `1`
- cobre processos ligados a:
  - `/tmp/uc_profiles/`
  - `proxy_auth_plugin/`
  - `undetected_chromedriver`
- envia `SIGTERM`
- espera um curto intervalo
- e envia `SIGKILL` se ainda houver sobreviventes

Isso foi adicionado para reduzir:

- vazamento de memória entre grupos
- pressão de swap acumulada
- distorção na medição de capacidade real de concorrência

Com isso, a recomendação de concorrência continua:

- `1` como valor seguro
- `2` como valor experimental razoável no VPS atual

mas agora com uma base operacional melhor para testar esse limite.

## Concorrência limitada implementada no grouped runner

O [`run_grouped_ad_clicker.py`](/home/otavio/overseas-business-online/run_grouped_ad_clicker.py) agora suporta concorrência limitada por ciclo.

Capacidades novas:

- parâmetro de CLI:
  - `--max-concurrent-groups <N>`
- parâmetro persistido em [`config.json`](/home/otavio/overseas-business-online/config.json):
  - `behavior.max_concurrent_groups`
- controle na UI do Streamlit:
  - `Grouped runner max concurrent groups`

Comportamento:

- `1`:
  - execução sequencial, como antes
- `2` ou mais:
  - o runner usa um pool limitado e dispara até `N` grupos em paralelo dentro do ciclo
  - cada grupo continua executando o worker real [`ad_clicker.py`](/home/otavio/overseas-business-online/ad_clicker.py)
  - o cleanup de browsers órfãos continua acontecendo antes de submeter cada novo grupo

Estado atual configurado:

- padrão em config:
  - `max_concurrent_groups = 2`

Observação operacional:

- isso foi implementado para permitir o próximo passo de escala
- ainda falta validação longa de estabilidade com `2` concorrências reais em produção
- se houver aumento de swap, crashes de Chromium ou falhas de túnel, o fallback recomendado continua sendo voltar para `1`

### Stagger de launch para concorrência

Depois da primeira validação com `2` concorrências, apareceu um padrão operacional importante:

- o orquestrador conseguia rodar `2` grupos em paralelo
- porém vários grupos falhavam cedo com erro de startup do Chrome/UC, como:
  - `session not created: cannot connect to chrome at 127.0.0.1:<port>`

Para reduzir colisão no startup paralelo, foi implementado um stagger configurável entre os launches concorrentes.

Capacidades novas:

- config:
  - `behavior.concurrent_group_launch_stagger_seconds`
- CLI:
  - `--launch-stagger-seconds <N>`
- Streamlit:
  - `Grouped runner launch stagger (seconds)`

Estado atual padrão:

- `concurrent_group_launch_stagger_seconds = 8.0`

Comportamento:

- quando `max_concurrent_groups > 1`
- o runner espera `N` segundos entre submeter um grupo concorrente e o próximo
- isso reduz a chance de dois Chromes/UC iniciarem exatamente no mesmo instante

Objetivo:

- manter `2` concorrências
- mas diminuir falhas precoces de criação de sessão do browser

## Medição real com `max_concurrent_groups = 2`

Foi feita uma medição com o Streamlit ativo e o grouped runner iniciado pela UI com:

- `grouped runner loop: running`
- `--max-concurrent-groups 2`

Estado observado do runner:

- PID do grouped runner:
  - `2650393`
- `2` workers `ad_clicker.py` ativos ao mesmo tempo:
  - `Belo Horizonte`
  - `Bauru`

### CPU

Métricas observadas:

- VPS:
  - `2 vCPUs`
- load average:
  - `0.92 / 0.70 / 0.83`
- no `vmstat`, houve folga relevante:
  - `idle` ainda em torno de `65%`
- árvore do grouped runner + 2 browsers:
  - `TOTAL_CPU_PERCENT 63.1`

Leitura prática:

- com `2` concorrências, CPU continua aceitável
- CPU não apareceu como gargalo principal neste teste

### Memória

Métricas observadas:

- RAM total:
  - `3.7 GiB`
- memória disponível:
  - cerca de `1.0 GiB`
- memória livre:
  - cerca de `113 MiB`
- swap em uso:
  - cerca de `2.0 GiB`

Árvore do grouped runner:

- `TOTAL_RSS_KB 2038024`
- aproximadamente `1.94 GiB RSS`

Leitura prática:

- `2` concorrências funcionam no VPS atual
- mas ainda deixam a máquina apertada em memória
- o sistema continua apoiado em swap
- o gargalo principal segue sendo memória, não CPU

### Conclusão operacional atual

- `1` concorrência:
  - modo mais estável
- `2` concorrências:
  - aceitável e operacional no VPS atual
  - melhor teto prático atual
- `3` ou mais:
  - continuam não recomendadas neste VPS

Conclusão direta:

- o cleanup automático de browsers órfãos ajudou
- o VPS agora consegue sustentar `2` concorrências reais
- ainda não há margem saudável para subir além disso

## Tratamento de interrupção manual

Foi observado anteriormente um traceback com `KeyboardInterrupt` enquanto o runner aguardava um `subprocess.run(...)` de um grupo.

Leitura correta desse caso:

- não era falha do fluxo de rotação do grupo em si
- era uma interrupção externa/manual do processo do grouped runner

O runner foi ajustado para tratar isso de forma limpa:

- agora, em caso de `KeyboardInterrupt`, ele registra:
  - `Grouped runner interrupted by user. Stopping cleanly.`
- e evita despejar traceback feio no log como se fosse erro operacional do ciclo
