# Configuração e detecção anti-bot (PT-BR)

Este documento descreve cada campo de `config.json` e como ele afeta comportamento automático e risco de detecção antifraude/anti-bot.

> Observação: valores mais "humanos" (menos previsíveis, com pausas e variações) tendem a reduzir sinais óbvios de automação. Não há configuração que elimine risco completamente.

## Estrutura `paths`

### `query_file`
- O que faz: caminho do arquivo com uma query por linha.
- Uso: principal para `run_ad_clicker.py` e `run_in_loop.py`.
- Impacto anti-bot:  
  - Médio. Ter muitas consultas de uma vez reduz repetição exata de padrões, mas um volume alto pode parecer automatizado.
  - Em contexto de fraude, misture queries naturais e não repita o mesmo termo em ciclos rápidos.

### `proxy_file`
- O que faz: caminho do arquivo com proxies (`IP:PORT` ou `user:pass@IP:PORT`).
- Uso: seleciona proxy aleatório por execução.
- Impacto anti-bot: **alto**.  
  - IPs compartilhados, datacenter estável e rotacionados com frequência baixa podem aumentar bloqueios.
  - Proxies de baixa qualidade normalmente disparam CAPTCHAs e bloqueios de comportamento.

### `user_agents`
- O que faz: arquivo de user agents disponíveis.
- Uso: define UA do navegador a cada instância.
- Impacto anti-bot: **médio-alto**.  
  - UA inconsistente com fingerprint real (SO/versão Chrome etc.) aumenta suspeita.
  - Use UAs reais e compatíveis com proxies/geo para reduzir inconsistência.

### `filtered_domains`
- O que faz: domains a filtrar nos links não-anúncio.
- Uso: impede clicar em domínios específicos.
- Impacto anti-bot: baixo.  
  - Indiretamente ajuda a controlar padrão de tráfego e qualidade de cliques.

## Estrutura `webdriver`

### `proxy`
- O que faz: proxy único para `ad_clicker.py` (override de `proxy_file`).
- Impacto anti-bot: **médio**.  
  - Troca de origem por execução ajuda reduzir rastreio por IP, mas abuso de IPs novos pode disparar heurísticas de risco.
- Regra do sistema: não pode ser usado junto com `proxy_file`.

### `auth`
- O que faz: indica proxy com autenticação (`user:pass@host:port`).
- Impacto anti-bot: pode ser neutro para detecção, mas formato/uso errados falham conexões e podem causar comportamento de erro repetitivo (padrão de automação).

### `incognito`
- O que faz: abre navegador em modo anônimo.
- Impacto anti-bot: **médio**.  
  - Limpa estado local (cookies/cache local), mas também perde continuidade de sessão natural.
  - Pode reduzir sinais de comportamento humano de retorno de sessão.

### `country_domain`
- O que faz: ajusta domínio de busca conforme país/proxy.
- Impacto anti-bot: **alto** se coerente com proxy; **médio** se incoerente.
  - Inconsistência entre idioma/país da busca e proxy geográfico pode parecer comportamento anômalo.

### `language_from_proxy`
- O que faz: define idioma/navegador conforme país do proxy.
- Impacto anti-bot: **médio**.  
  - Alinhamento de idioma/locale com geolocalização reduz inconsistências de fingerprint.

### `ss_on_exception`
- O que faz: captura screenshot quando exceção acontece.
- Impacto anti-bot: indireto/baixo.  
  - Não altera tráfego; auxilia auditoria para investigar falhas de detecção (CAPTCHA, bloqueio, timeout).

### `window_size`
- O que faz: tamanho da janela do navegador (`width,height`).
- Impacto anti-bot: **baixo-médio**.
  - Tamanho fixo e fora do padrão pode ser menos humano; variação moderada pode ajudar.

### `shift_windows`
- O que faz: aplica deslocamentos aleatórios de posição da janela.
- Impacto anti-bot: **médio**.  
  - Ajuda a quebrar assinatura visual repetitiva em ambientes com captura de comportamento.

### `use_seleniumbase`
- O que faz: alterna modo SeleniumBase em vez de UC.
- Impacto anti-bot: variável.  
  - Diferentes engines geram fingerprints diferentes; pode ajudar ou piorar dependendo do alvo/ambiente.

## Estrutura `behavior`

### `query`
- O que faz: termo de busca único (exclusivo com `query_file`).
- Impacto anti-bot: **alto se repetitivo**.  
  - Queries fixas e repetidas em alta frequência elevam chance de bloqueio.

### `ad_page_min_wait` / `ad_page_max_wait`
- O que fazem: intervalo aleatório entre abrir e clicar links de anúncio.
- Impacto anti-bot: **alto**.  
  - Pausas mais humanas reduzem padrão mecânico.

### `nonad_page_min_wait` / `nonad_page_max_wait`
- O que fazem: intervalo em páginas não-anúncio.
- Impacto anti-bot: **alto** para detecção de tempo de leitura.

### `max_scroll_limit`
- O que faz: limita número máximo de scrolls nos resultados.
- Impacto anti-bot: **médio**.  
  - Zero (sem limite) simula leitura mais natural; valor pequeno em excesso pode parecer comportamento de script.

### `check_shopping_ads`
- O que faz: ativa clique em shopping ads (até 5).
- Impacto anti-bot: **médio**.  
  - Aumenta ação repetitiva em bloco; ajuste conforme objetivo e perfil do site.

### `excludes`
- O que faz: palavras/chunks para ignorar resultados.
- Impacto anti-bot: baixo.  
  - Filtragem pode reduzir cliques repetidos em domínios com alta chance de bloqueio.

### `random_mouse`
- O que faz: movimenta mouse aleatoriamente durante a sessão.
- Impacto anti-bot: **alto positivo**.  
  - Gera entropia de interação e reduz rigidez de automação.

### `custom_cookies`
- O que faz: usa cookies customizados de `cookies.txt`.
- Impacto anti-bot: **alto (duplo)**.
  - Pode aumentar credibilidade se válidos e coerentes.
  - Cookies inválidos/incoerentes causam padrões suspeitos e falhas imediatas.

### `click_order` (1 a 5)
- O que faz: ordem de cliques entre anúncios e não-anúncios.
- Impacto anti-bot: **médio**.
  - Ordem fixa e repetida é assinatura de bot.  
  - Valores com mistura (`3`, `4`, `5`) tendem a parecer menos mecânicos.

### `browser_count`
- O que faz: número de browsers simultâneos.
- Impacto anti-bot: **alto**.
  - Mais instâncias paralelas = mais volume em janela curta = alerta de automação.

### `multiprocess_style`
- O que faz:
  - `1`: queries diferentes por browser.
  - `2`: mesma query em todos os browsers.
- Impacto anti-bot: **médio-alto**.
  - `2` pode parecer padrão de ataque/farm se repetitivo.

### `loop_wait_time`
- O que faz: espera entre ciclos de `run_in_loop.py`.
- Impacto anti-bot: **alto** quando muito baixo.
  - Valores curtos (poucos segundos) geram volume suspeito.

### `wait_factor`
- O que faz: multiplica todos os tempos de espera (exceto loop wait).
- Impacto anti-bot: **alto**.
  - Menor que 1 acelera demais e é suspeito.
  - Um pouco acima de 1 imita melhor comportamento humano.

### `running_interval_start` / `running_interval_end`
- O que fazem: janela de execução (`HH:MM`).
- Impacto anti-bot: **alto** para cobertura temporal.
  - Operar só em horários humanos reduz assinaturas de script 24/7.

### `2captcha_apikey`
- O que faz: chave para resolução de CAPTCHA.
- Impacto anti-bot: **duplo**.
  - Evita bloqueio manual quando aparece CAPTCHA.
  - Em alguns cenários pode elevar custo operacional e ainda gerar padrões (se usado de forma massiva).

### `hooks_enabled`
- O que faz: ativa hooks customizados em `hooks.py`.
- Impacto anti-bot: depende da implementação.
  - Qualquer lógica custom pode adicionar comportamento mais humano ou tornar o tráfego ainda mais mecânico.

### `telegram_enabled`
- O que faz: envio de alertas por Telegram.
- Impacto anti-bot: mínimo. Só observabilidade, sem impacto direto no browsing.

### `send_to_android`
- O que faz: envia links para Android conectado.
- Impacto anti-bot: pode aumentar sinais de multi-dispositivo.
  - Se feito com muita cadência, pode ser anômalo.

### `request_boost`
- O que faz: dispara até 10 requisições paralelas adicionais por clique.
- Impacto anti-bot: **muito alto**.
  - Isso dispara volume de request acima do normal e pode parecer claramente anômalo.

## Interação de campos (importantíssimo)

- `query` e `query_file` são mutuamente exclusivos (o projeto também valida isso).
- `proxy` e `proxy_file` também não devem ser usados juntos.
- `request_boost` + `browser_count` alto + `loop_wait_time` baixo formam o pior padrão anti-bot (alto risco).
- Maior proteção geral vem de:
  - proxies consistentes por sessão,
  - espera realista (`wait_factor` >= 1, pausas não lineares),
  - mouse/scroll leves,
  - menos paralelismo agressivo,
  - rotação natural de queries e horários.

## Guia rápido de postura menos detectável

1. Comece com parâmetros conservadores (menos browsers, mais espera, menos frequência).
2. Monitore erros e CAPTCHAs por algumas rodadas.
3. Ajuste gradualmente só um parâmetro por vez.
4. Se aparecer bloqueio repetido, reduza `browser_count`, aumente `loop_wait_time` e mantenha horários humanos.
