# MCP Server ClickUp v2.5.0

> Servidor MCP para integração do ClickUp com Claude Desktop e outros clientes MCP.

## Status do Projeto

| Sprint | Status | Descrição |
|--------|--------|-----------|
| 1 | ✅ Concluída | Resolver travamento |
| 2 | ✅ Concluída | Tools ausentes |
| 3 | ✅ Concluída | Resiliência |
| 4 | ✅ Concluída | Qualidade |
| 5 | ✅ Concluída | Diferencial |
| 5.1 | ✅ Concluída | Refinamentos (Nota 9+) |
| 6 | ✅ Concluída | Custom Fields |
| 7 | ✅ Concluída | API Completa (Tags, Dependencies, Checklists, Timer, Templates) |

## Documentação

- [PRD completo](docs/PRD.md) - Requisitos e decisões técnicas
- [Detalhamento das Sprints](docs/SPRINTS.md) - O que fazer em cada sprint

## Instalação

```bash
# Clonar/copiar o projeto
cd "C:\Users\Claudio Camozzi\vscode\mcp server clickup"

# Instalar dependências
pip install -e .
```

## Configuração

Criar arquivo `.env`:

```env
CLICKUP_API_TOKEN=seu_token_aqui
```

## Uso com Claude Desktop

Adicionar ao `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "clickup": {
      "command": "python",
      "args": ["C:\\Users\\Claudio Camozzi\\vscode\\mcp server clickup\\src\\clickup_mcp.py"],
      "env": {
        "CLICKUP_API_TOKEN": "seu_token"
      }
    }
  }
}
```

## Tools Disponíveis

### Tools Atuais (v2.5 - 58 tools)

Estas tools já estão implementadas e funcionando:

| Categoria | Tools | Descrição |
|-----------|-------|-----------|
| Workspace | `clickup_get_workspaces` | Lista workspaces |
| Spaces | `clickup_get_spaces`, `get_space_details` | Lista e detalhes de spaces |
| Folders | `clickup_get_folders`, `create`, `update`, `delete` | CRUD de folders |
| Lists | `clickup_get_lists`, `get_folderless_lists`, `get_list_details`, `create`, `update`, `delete` | CRUD de lists |
| Tasks | `clickup_get_tasks`, `get_filtered_team_tasks`, `get_task`, `create`, `update`, `delete`, `move`, `duplicate` | CRUD completo de tasks |
| Comments | `clickup_get_task_comments`, `create_task_comment` | Comentários em tasks |
| Members | `clickup_get_workspace_members` | Lista membros |
| Time | `clickup_get_time_entries`, `create_time_entry`, `get_billable_report` | Time tracking + billable |
| Timer | `clickup_start_timer`, `stop_timer`, `get_running_timer` | Timer em tempo real |
| Custom Fields | `clickup_get_custom_fields`, `set_custom_field_value`, `remove_custom_field_value` | CRUD de valores de custom fields |
| Tags | `clickup_get_space_tags`, `create_space_tag`, `update_space_tag`, `delete_space_tag`, `add_tag_to_task`, `remove_tag_from_task` | CRUD completo de tags |
| Dependencies | `clickup_add_dependency`, `delete_dependency`, `add_task_link`, `delete_task_link` | Dependências e links entre tasks |
| Checklists | `clickup_get_checklists`, `create_checklist`, `update_checklist`, `delete_checklist`, `create_checklist_item`, `update_checklist_item`, `delete_checklist_item` | CRUD completo de checklists |
| Templates | `clickup_get_task_templates`, `create_task_from_template` | Templates de tasks |
| Attachments | `clickup_get_attachments` | Lista anexos de uma task |
| Analysis | `clickup_analyze_space_structure` | Análise morfológica completa |
| Docs | `clickup_get_docs`, `create_doc` | CRUD de documentos ClickUp |
| Search | `clickup_fuzzy_search_tasks` | Busca fuzzy aproximada |
| Diagnóstico | `clickup_get_metrics` | Métricas do servidor |

## Modos de Output (v2.0 - Implementado)

Todas as tools de listagem suportam 3 modos de output:

```python
# COMPACT (default) - 1 linha por item - RESOLVE TRAVAMENTO
output_mode="compact"

# DETAILED - formato completo (~12 linhas por item)
output_mode="detailed"

# JSON - raw JSON para processamento
output_mode="json"
```

## Resiliência (v2.1)

O servidor implementa:

- **Retry automático**: 3 tentativas com backoff exponencial para erros transientes
- **Cache TTL**: 5 min para estrutura (spaces, folders), 1 min para tasks
- **Rate limiting**: 100 requests/minuto para respeitar limites do ClickUp
- **Connection pooling**: Reutilização de conexões HTTP

Configurável via variáveis de ambiente:
```env
DEFAULT_TIMEOUT=30.0
CACHE_TTL_STRUCTURE=300
CACHE_TTL_TASKS=60
LOG_LEVEL=INFO
```

## Qualidade (v2.2)

- **Correlation ID**: Rastreamento de requests com ID único de 8 caracteres
- **Métricas**: Contadores de chamadas, cache hit rate, retries
- **Logging estruturado**: loguru com correlation ID em cada log
- **275 testes**: Cobertura completa de formatação, cache, métricas, correlation ID, retry, rate limiting, timeout, e tools MCP com mocks HTTP (96% cobertura)

Nova tool: `clickup_get_metrics` - retorna métricas de diagnóstico do servidor.

## Sprint 5 - Diferencial (v2.3)

Novas features que diferenciam este MCP:

### Modo Read-Only

Segurança para ambientes de produção. Configure via variável de ambiente:

```env
READ_ONLY_MODE=true
```

Quando ativo, todas as operações de escrita (create, update, delete) são bloqueadas.

### Busca Fuzzy

Nova tool `clickup_fuzzy_search_tasks` para busca aproximada:

```python
# Encontra tasks mesmo com erros de digitação
clickup_fuzzy_search_tasks(
    list_id="123",
    query="relatorio",      # encontra "Relatório Mensal"
    threshold=0.5           # 0.0-1.0, maior = mais preciso
)
```

### Time Tracking+

Novas tools para horas faturáveis:

- `clickup_create_time_entry` - Criar registro com flag billable
- `clickup_get_billable_report` - Relatório de horas faturáveis por período

## Custom Fields (v2.4)

Suporte completo para manipular valores de custom fields:

### Tools

- `clickup_get_custom_fields` - Lista campos disponíveis (obter IDs)
- `clickup_set_custom_field_value` - Define valor de um campo em uma task
- `clickup_remove_custom_field_value` - Remove valor de um campo
- `clickup_create_task` - Agora aceita `custom_fields` na criação

### Exemplos de Uso

```python
# Listar custom fields disponíveis
clickup_get_custom_fields(list_id="123")

# Definir valor de texto
clickup_set_custom_field_value(
    task_id="abc123",
    field_id="field_xyz",
    value="Meu texto"
)

# Definir dropdown (usar ID da opção)
clickup_set_custom_field_value(
    task_id="abc123",
    field_id="dropdown_field",
    value="option_id_aqui"
)

# Criar task com custom fields
clickup_create_task(
    list_id="123",
    name="Nova Task",
    custom_fields=[
        {"id": "field1", "value": "Texto"},
        {"id": "field2", "value": 100},
        {"id": "field3", "value": True}
    ]
)
```

### Formatos de Valor por Tipo

| Tipo | Formato | Exemplo |
|------|---------|---------|
| Text/Short Text | string | `"valor"` |
| Number/Currency | número | `123` |
| Dropdown | ID da opção | `"opt_abc123"` |
| Labels | array de IDs | `["lbl1", "lbl2"]` |
| Checkbox | boolean | `true` |
| Date | timestamp ms | `1704067200000` |
| Users/Tasks | objeto add/rem | `{"add": ["id1"], "rem": []}` |
| Email | string | `"email@ex.com"` |
| Phone | string | `"+5511999999999"` |
| Rating | inteiro | `4` |
| Progress | objeto | `{"current": 50}` |

## Sprint 7 - API Completa (v2.5)

### Tags

```python
# Listar tags do space
clickup_get_space_tags(space_id="space123")

# Criar tag
clickup_create_space_tag(space_id="space123", name="urgente", bg_color="#ff0000")

# Adicionar tag à task
clickup_add_tag_to_task(task_id="task123", tag_name="urgente")

# Remover tag da task
clickup_remove_tag_from_task(task_id="task123", tag_name="urgente")
```

### Dependencies

```python
# Adicionar dependência (task A espera task B)
clickup_add_dependency(
    task_id="taskA",
    depends_on="taskB"  # A espera B terminar
)

# Link bidirecional entre tasks
clickup_add_task_link(task_id="task1", links_to="task2")
```

### Checklists CRUD

```python
# Criar checklist
clickup_create_checklist(task_id="task123", name="Itens para Revisar")

# Adicionar item
clickup_create_checklist_item(
    checklist_id="checklist123",
    name="Revisar documentação",
    assignee="user_id"  # opcional
)

# Marcar como resolvido
clickup_update_checklist_item(
    checklist_id="checklist123",
    item_id="item456",
    resolved=True
)
```

### Timer

```python
# Iniciar timer na task
clickup_start_timer(team_id="team123", task_id="task456", billable=True)

# Verificar timer em execução
clickup_get_running_timer(team_id="team123")

# Parar timer
clickup_stop_timer(team_id="team123")
```

### Templates

```python
# Listar templates disponíveis
clickup_get_task_templates(team_id="team123")

# Criar task a partir de template
clickup_create_task_from_template(
    list_id="list123",
    template_id="tpl456",
    name="Nova Task do Template"
)
```

## Refinamentos v2.3.1 (Nota 9+)

Melhorias para atingir excelência em todos os aspectos:

### Performance
- **rapidfuzz**: Busca fuzzy otimizada com SIMD (O(n) vs O(n*m) do Levenshtein)

### Arquitetura
- **Exceções específicas**: `ClickUpError`, `ConfigurationError`, `ClickUpAPIError`, `RateLimitError`
- **Fail-fast**: `EnvironmentError` no startup para variáveis obrigatórias

### Observabilidade
- **Métricas de latência**: p50, p95, p99, avg, min, max
- **Logging para arquivo**: Rotação 10MB, retenção 7 dias, compressão gzip
- Variável: `LOG_FILE=/path/to/clickup.log`

### Segurança
- **Sanitização de output**: Remove caracteres de controle perigosos
- **Truncamento**: Outputs limitados a 100k caracteres

## Changelog

Ver [CHANGELOG.md](CHANGELOG.md)

## Licença

Proprietário - Uso interno

---

> Projeto aprovado pelo Conselho Técnico em 2026-01-10
> Sprints 1-5 concluídas em 2026-01-11
> Refinamentos (Nota 9+) concluídos em 2026-01-11
> Custom Fields (v2.4) concluídos em 2026-01-12
> API Completa (v2.5) concluída em 2026-01-12
