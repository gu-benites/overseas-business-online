# Next Tasks

## Objetivo

Adicionar suporte a grupos operacionais no sistema de execução de anúncios.

Cada grupo deve representar uma unidade independente de execução com:

- uma cidade
- um proxy dedicado
- um conjunto de queries dedicado
- um `rsw_id` interno

O fluxo desejado é:

1. criar um grupo
2. associar cidade, proxy, `rsw_id` e arquivo de queries
3. ao criar o grupo, gerar automaticamente queries via IA
4. as queries devem sempre partir da base:
   - `desentupidora <nome_cidade>`
5. o runner agrupado deve rodar respeitando o vínculo fixo:
   - `grupo -> proxy -> query set`

## Cidades iniciais para grupos

Criar grupos para:

- Guaratinguetá
- Florianópolis
- Porto Alegre
- Brasília
- Bauru
- Belo Horizonte

## Regras de negócio dos grupos

Cada grupo deve conter pelo menos:

- `id`
- `city_name`
- `rsw_id`
- `proxy`
- `enabled`
- `created_at`
- `updated_at`

Observações:

- o nome do grupo deve ser somente o nome da cidade
- `allowlist` e `denylist` continuam globais
- `ad_allowlist.txt` e `ad_denylist.txt` não serão por grupo
- o grupo só controla proxy + cidade + queries + identidade operacional
- cada grupo terá exatamente 1 proxy
- apenas grupos marcados como ativos (`enabled`) entram na rotação do runner

## Geração automática de queries por IA

Ao criar um grupo, a IA deve gerar queries automaticamente com base no nome da cidade.

Seed fixa por regra:

- `desentupidora <nome_cidade>`

Exemplos:

- `desentupidora guaratinguetá`
- `desentupidora florianópolis`
- `desentupidora porto alegre`
- `desentupidora brasília`
- `desentupidora bauru`
- `desentupidora belo horizonte`

Comportamento esperado:

1. grupo é criado
2. sistema monta a seed base
3. IA gera 10 variações pt-BR focadas na cidade
4. resultado é salvo no SQLite para aquele grupo
5. uma nova geração deve sobrescrever as queries anteriormente salvas do grupo

## Estrutura sugerida de persistência

SQLite faz sentido para o cenário de múltiplos grupos.

### Tabela `groups`

Campos sugeridos:

- `id`
- `city_name`
- `rsw_id`
- `proxy`
- `enabled`
- `created_at`
- `updated_at`

### Tabela `group_queries`

Campos sugeridos:

- `id`
- `group_id`
- `query_text`
- `position`
- `created_at`
- `updated_at`

### Tabela `group_runs`

Campos sugeridos:

- `id`
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

## Novo runner sugerido

Criar um runner dedicado, por exemplo:

- `run_grouped_ad_clicker.py`

Responsabilidades:

1. ler grupos ativos do SQLite
2. para cada grupo, carregar:
   - proxy do grupo
   - queries do grupo no SQLite
   - `rsw_id`
3. executar mantendo vínculo fixo entre proxy e queries
4. registrar histórico em `group_runs`
5. iterar continuamente entre os grupos ativos
6. ignorar grupos desativados

## Integração com Streamlit

Adicionar no futuro:

- tela para listar grupos
- criar grupo
- editar grupo
- ativar/desativar grupo
- gerar queries por IA no momento da criação
- regenerar queries por IA sobrescrevendo o conjunto atual salvo
- visualizar último status de cada grupo
- exibir `rsw_id` em listagens e detalhes

## Pontos de implementação

### Fase 1

- criar `groups.db`
- criar tabela `groups`
- criar tabela `group_queries`
- criar tabela `group_runs`
- criar utilitário para cadastrar grupos iniciais

### Fase 2

- criar `run_grouped_ad_clicker.py`
- executar 1 grupo = 1 proxy + 1 conjunto de queries
- registrar resultado por grupo
- iterar continuamente entre grupos ativos

### Fase 3

- integrar criação/edição de grupos no Streamlit
- gerar queries via IA automaticamente ao criar grupo
- permitir regeneração de queries sobrescrevendo o conteúdo salvo no banco

## Grupos iniciais esperados

Cada grupo inicial deverá ter:

- cidade
- `rsw_id`
- proxy
- queries salvas no SQLite

Lista inicial:

- Guaratinguetá
- Florianópolis
- Porto Alegre
- Brasília
- Bauru
- Belo Horizonte

## Decisões já esclarecidas

- nome do grupo: somente o nome da cidade
- queries: armazenadas no SQLite, não em arquivos `.txt`
- `rsw_id`: deve aparecer em logs, relatórios e Streamlit
- proxy por grupo: exatamente 1
- execução: loop contínuo entre grupos ativos
- geração por IA: sobrescreve as queries atuais salvas no banco
