# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [2.5.2] - 2026-01-13

### Corrigido

#### duplicate_task - Priority parsing
- Corrigido bug onde `duplicate_task` falhava com erro "Priority invalid"
- API retorna priority como objeto `{"id": "1", "priority": "urgent"}` mas POST espera int
- Agora extrai corretamente o ID numerico da prioridade

### Removido

#### move_task - Removida por limitacao da API ClickUp
- Tool `clickup_move_task` removida do MCP
- Motivo: API do ClickUp nao permite remover task da lista "home" (erro TASK_035)
- Feature request pendente: https://feedback.clickup.com/public-api/p/move-task-between-lists-using-the-api
- Total de tools: 58 → 57

---

## [2.5.1] - 2026-01-13

### Corrigido (Bugfix - API Docs)

#### Endpoint Docs corrigido para API v3
- `clickup_get_docs` corrigido de `/api/v2/team/{id}/doc` (404) para `/api/v3/workspaces/{id}/docs`
- `clickup_create_doc` corrigido para usar API v3

#### Suporte a múltiplas versões da API
- Adicionada constante `API_V3_BASE_URL` para endpoints v3
- Função `api_request()` agora aceita parâmetro `api_version` ("v2" ou "v3")
- Detecção automática de estrutura de resposta (lista vs dict)

#### Correção de parsing
- Campo `creator` agora tratado como ID numérico (API v3 retorna int, não objeto)
- Formatação ajustada para exibir ID do criador

### Notas
- API de Docs do ClickUp requer API v3 (não existe em v2)
- Demais endpoints continuam usando API v2

---

## [2.5.0] - 2026-01-12

### Adicionado (Sprint 7 - API Completa)

#### Tags (6 tools)
- `clickup_get_space_tags` - Lista todas as tags de um space
- `clickup_create_space_tag` - Cria nova tag no space
- `clickup_update_space_tag` - Atualiza nome/cor de tag existente
- `clickup_delete_space_tag` - Remove tag do space
- `clickup_add_tag_to_task` - Adiciona tag a uma task
- `clickup_remove_tag_from_task` - Remove tag de uma task

#### Dependencies (4 tools)
- `clickup_add_dependency` - Adiciona dependência entre tasks (waiting_on/blocking)
- `clickup_delete_dependency` - Remove dependência entre tasks
- `clickup_add_task_link` - Adiciona link entre tasks (relacionamento bidirecional)
- `clickup_delete_task_link` - Remove link entre tasks

#### Checklists CRUD (6 tools)
- `clickup_create_checklist` - Cria nova checklist em uma task
- `clickup_update_checklist` - Renomeia checklist existente
- `clickup_delete_checklist` - Remove checklist
- `clickup_create_checklist_item` - Adiciona item à checklist
- `clickup_update_checklist_item` - Atualiza item (nome, resolved, assignee)
- `clickup_delete_checklist_item` - Remove item da checklist

#### Timer (3 tools)
- `clickup_start_timer` - Inicia timer de tracking em uma task
- `clickup_stop_timer` - Para timer e salva tempo registrado
- `clickup_get_running_timer` - Mostra timer atualmente em execução

#### Templates (2 tools)
- `clickup_get_task_templates` - Lista templates disponíveis no workspace
- `clickup_create_task_from_template` - Cria task a partir de template

### Testes
- 275 testes (+88 novos)
- 96% cobertura (acima da meta de 95%)
- Testes completos para Tags, Dependencies, Checklists, Timer e Templates
- Testes de error handlers para todas as tools
- Testes de output modes detailed para todas as tools de listagem

### Notas
- Total de 58 tools disponíveis (+21 novas)
- Cobertura completa da API ClickUp v2 para operações comuns

---

## [2.4.0] - 2026-01-12

### Adicionado (Custom Fields)

#### Novas Tools
- `clickup_set_custom_field_value` - Define valor de custom field em task
- `clickup_remove_custom_field_value` - Remove valor de custom field

#### Melhorias em Tools Existentes
- `clickup_create_task` agora aceita parâmetro `custom_fields` para definir campos ao criar

#### Tipos de Custom Fields Suportados
- **Text/Short Text**: `"valor string"`
- **Number/Currency**: `123`
- **Dropdown**: `"option_id"` (ID da opção)
- **Labels**: `["label_id_1", "label_id_2"]`
- **Checkbox**: `true/false`
- **Date**: `1704067200000` (timestamp ms)
- **Users/Tasks (Relationship)**: `{"add": ["id1"], "rem": ["id2"]}`
- **Email**: `"email@example.com"`
- **Phone**: `"+5511999999999"`
- **Location**: `{"location": {"lat": -23.5, "lng": -46.6}, "formatted_address": "..."}`
- **Rating**: `4` (inteiro)
- **Progress**: `{"current": 50}`

### Testes
- 164 testes (+8 novos para custom fields)
- 90% cobertura mantida
- Testes para todos os tipos de custom fields

### Notas
- Criação de Custom Fields (definição) não é suportada pela API do ClickUp
- Custom Fields devem ser criados manualmente no ClickUp UI
- Use `clickup_get_custom_fields` para obter IDs dos campos existentes

---

## [2.3.1] - 2026-01-11

### Melhorado (Refinamentos - Nota 9+)

#### Performance
- Busca fuzzy otimizada com rapidfuzz (O(n) SIMD) em vez de Levenshtein customizado
- Detecção automática de ambiente pytest para fail-fast sem bloqueio

#### Arquitetura
- Hierarquia de exceções específicas: `ClickUpError`, `ConfigurationError`, `ClickUpAPIError`, `RateLimitError`, `ReadOnlyModeError`
- `ClickUpAPIError` com atributos: `status_code`, `endpoint`, `err_code`
- Fail-fast no startup com `EnvironmentError` para variáveis obrigatórias

#### Observabilidade
- Métricas de latência: p50, p95, p99, avg, min, max
- Context manager `measure_latency()` para medição automática
- Latência por tool individual
- Logging para arquivo com rotação (10MB, 7 dias, gzip)

#### Segurança
- `sanitize_output()` remove caracteres de controle perigosos
- `sanitize_dict_values()` para sanitização recursiva de dicts
- Truncamento de outputs muito longos (100k chars)

### Testes
- 156 testes (+16 novos)
- 90% cobertura mantida
- Testes de performance fuzzy (1000 tasks)
- Testes de latência e percentis
- Testes de sanitização e exceptions

---

## [2.3.0] - 2026-01-11

### Adicionado (Sprint 5 - Diferencial)

#### Modo Read-Only
- Nova variável de ambiente `READ_ONLY_MODE` para bloquear operações de escrita
- `ReadOnlyModeError` exception para operações bloqueadas
- `check_write_permission()` em todas as tools de escrita (create, update, delete, move, duplicate)
- Modo de operação visível em `clickup_get_metrics`

#### Busca Fuzzy
- Nova tool `clickup_fuzzy_search_tasks` para busca aproximada por nome
- Implementação com rapidfuzz (O(n) SIMD otimizado)
- Suporte a threshold configurável (0.0 a 1.0)
- Ordenação por relevância (mais similar primeiro)
- Busca encontra tasks mesmo com erros de digitação

#### Time Tracking+
- Nova tool `clickup_create_time_entry` com suporte a horas faturáveis
- Nova tool `clickup_get_billable_report` para relatório de horas faturáveis
- Agrupamento por usuário e por task
- Formatação em horas/minutos

### Melhorado
- Cobertura de testes aumentada para 90% (156 testes)
- 35 tools disponíveis (+4 novas)

---

## [2.2.0] - 2026-01-11

### Adicionado (Sprint 4 - Qualidade)

#### Observabilidade
- Correlation ID (8 chars) para rastreamento de requests
- Logging estruturado com loguru
- Métricas de uso: chamadas por tool, cache hit rate, retries
- Nova tool `clickup_get_metrics` para diagnóstico

#### Testes
- 119 testes unitários e de integração
- 90% de cobertura de código
- Mocks HTTP com respx
- Fixtures para cache e rate limiter

#### Documentação
- README.md completo com exemplos
- CHANGELOG.md no formato Keep a Changelog
- Docstrings atualizadas em todas as tools

---

## [2.1.0] - 2026-01-11

### Adicionado (Sprint 3 - Resiliência)

#### Infraestrutura
- Connection pooling com httpx.AsyncClient
- Retry automático com exponential backoff (tenacity)
- Cache TTL diferenciado: 5min estrutura, 1min tasks (cachetools)
- Rate limiting interno: 100 req/min
- Validação de configuração no startup

#### Configuração
- `DEFAULT_TIMEOUT` - timeout configurável (default 30s)
- `CACHE_TTL_STRUCTURE` - TTL cache estrutura (default 300s)
- `CACHE_TTL_TASKS` - TTL cache tasks (default 60s)
- `LOG_LEVEL` - nível de log (default INFO)

---

## [2.0.0] - 2026-01-11

### Adicionado (Sprints 1-2 - Travamento + Tools)

#### Sprint 1 - Resolver Travamento
- Enum `OutputMode` (COMPACT, DETAILED, JSON)
- `format_tasks_compact()` - 1 linha por task (92% redução)
- Parâmetro `output_mode` em todas as tools de listagem
- Default COMPACT para evitar travamento
- Parâmetro `limit` (default 25, max 100)
- Paginação inteligente com aviso

#### Sprint 2 - Tools Ausentes
- `clickup_get_custom_fields` - lista campos customizados
- `clickup_get_space_details` - detalhes de um space
- `clickup_get_list_details` - detalhes de uma list
- `clickup_get_checklists` - checklists de uma task
- `clickup_analyze_space_structure` - análise morfológica
- `clickup_get_attachments` - anexos de uma task
- `clickup_get_docs` / `clickup_create_doc` - documentos ClickUp
- `clickup_get_workspace_members` - membros do workspace

### Corrigido
- Travamento do Claude Desktop com 100+ tasks
- Output excessivo reduzido de 1200 para 105 linhas

---

## [1.2.0] - 2026-01-09

### Adicionado
- 23 tools completas para ClickUp API
- Extração automática de Tipo/Subtipo do nome das tasks
- Suporte a formato Markdown e JSON
- Integração com Claude Desktop

### Problemas Conhecidos
- Trava com 100+ tasks (output excessivo)
- Sem retry em falhas de rede
- Sem cache
- Sem logging estruturado
- Sem testes

---

## [1.0.0] - 2026-01-01

### Adicionado
- Versão inicial do MCP Server ClickUp
- CRUD básico de tasks, lists, folders
- Autenticação via API Token
