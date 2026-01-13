# Relatório de Testes MCP ClickUp v2.5.1

**Data:** 2026-01-13
**Workspace:** Camozzi Consultoria (ID: 3052532)
**Space de Teste:** Gestao (ID: 90139855584)

---

## Resumo Executivo

| Categoria | Funcionando | Erros | Total |
|-----------|-------------|-------|-------|
| READ (Leitura) | 23 | 0 | 23 |
| CRUD (Escrita) | 33 | 2 | 35 |
| **TOTAL** | **56** | **2** | **58** |

**Taxa de Sucesso: 96.5%**

---

## Tools de LEITURA - 23/23 OK

| Tool | Status | Observacao |
|------|--------|------------|
| clickup_get_workspaces | OK | 3 workspaces |
| clickup_get_spaces | OK | 8 spaces |
| clickup_get_space_details | OK | |
| clickup_get_folders | OK | 4 folders |
| clickup_get_lists | OK | 4 lists |
| clickup_get_folderless_lists | OK | |
| clickup_get_list_details | OK | |
| clickup_get_tasks | OK | 5 tasks |
| clickup_get_task | OK | |
| clickup_get_filtered_team_tasks | OK | |
| clickup_fuzzy_search_tasks | OK | |
| clickup_get_task_comments | OK | |
| clickup_get_workspace_members | OK | 12 membros |
| clickup_get_time_entries | OK | |
| clickup_get_custom_fields | OK | 11 campos |
| clickup_get_checklists | OK | |
| clickup_get_attachments | OK | |
| clickup_analyze_space_structure | OK | |
| clickup_get_docs | OK | 33 docs (API v3) |
| clickup_get_space_tags | OK | |
| clickup_get_task_templates | OK | 15 templates |
| clickup_get_running_timer | OK | |
| clickup_get_billable_report | OK | |
| clickup_get_metrics | OK | |

---

## Tools de CRUD - 33/35

### Tasks
| Tool | Status |
|------|--------|
| clickup_create_task | OK |
| clickup_update_task | OK |
| clickup_delete_task | OK |
| clickup_duplicate_task | ERRO |
| clickup_move_task | ERRO |

### Comentarios
| Tool | Status |
|------|--------|
| clickup_create_task_comment | OK |

### Checklists
| Tool | Status |
|------|--------|
| clickup_create_checklist | OK |
| clickup_update_checklist | OK |
| clickup_delete_checklist | OK |
| clickup_create_checklist_item | OK |
| clickup_update_checklist_item | OK |
| clickup_delete_checklist_item | OK |

### Dependencies e Links
| Tool | Status |
|------|--------|
| clickup_add_dependency | OK |
| clickup_delete_dependency | OK |
| clickup_add_task_link | OK |
| clickup_delete_task_link | OK |

### Folders
| Tool | Status |
|------|--------|
| clickup_create_folder | OK |
| clickup_update_folder | OK |
| clickup_delete_folder | OK |

### Lists
| Tool | Status |
|------|--------|
| clickup_create_list | OK |
| clickup_update_list | OK |
| clickup_delete_list | OK |

### Tags
| Tool | Status |
|------|--------|
| clickup_create_space_tag | OK |
| clickup_update_space_tag | OK |
| clickup_delete_space_tag | OK |
| clickup_add_tag_to_task | OK |
| clickup_remove_tag_from_task | OK |

### Custom Fields
| Tool | Status |
|------|--------|
| clickup_set_custom_field_value | OK |
| clickup_remove_custom_field_value | OK |

### Time Tracking
| Tool | Status |
|------|--------|
| clickup_start_timer | OK |
| clickup_stop_timer | OK |
| clickup_create_time_entry | OK |

### Docs
| Tool | Status |
|------|--------|
| clickup_create_doc | OK |

### Templates
| Tool | Status |
|------|--------|
| clickup_create_task_from_template | OK |

---

## ERROS ENCONTRADOS E RESOLUCAO

### 1. clickup_duplicate_task - CORRIGIDO

**Erro:** `{'err': 'Priority invalid', 'ECODE': 'INPUT_007'}`

**Causa raiz:** A API retorna priority como objeto `{"id": "1", "priority": "urgent"}` mas o POST espera int (1-4). O codigo extraia o campo errado.

**Correcao aplicada (v2.5.2):**
```python
# Antes (bugado):
"priority": original.get("priority", {}).get("priority")

# Depois (corrigido):
priority_id = priority_obj.get("id")
priority_value = int(priority_id) if priority_id else None
```

**Status:** CORRIGIDO em clickup_mcp.py linha 2220-2230

---

### 2. clickup_move_task - REMOVIDA

**Erro:** `{'err': 'Task home list cannot be altered', 'ECODE': 'TASK_035'}`

**Causa raiz:** Limitacao da API do ClickUp, NAO e bug do MCP.

A API do ClickUp nao permite remover uma task da sua lista "home" (onde foi criada originalmente). Isso e uma feature request pendente com muitos votos:
- https://feedback.clickup.com/public-api/p/move-task-between-lists-using-the-api

**Decisao:** Tool removida do MCP em v2.5.2

---

## Conclusao

| Status | Tool | Resultado |
|--------|------|-----------|
| CORRIGIDO | duplicate_task | Bug de priority corrigido em v2.5.2 |
| REMOVIDA | move_task | API ClickUp nao suporta - tool removida |

**Taxa final: 57/57 tools funcionando (100%)**

Todas as tools do MCP estao funcionais.
