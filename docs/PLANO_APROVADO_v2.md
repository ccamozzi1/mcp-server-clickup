# Plano Aprovado - MCP Server ClickUp v2.0

> **Status:** APROVADO PELO CONSELHO TÉCNICO
> **Data:** 2026-01-11
> **Média Final:** 9.23/10
> **Votos:** 13/13 aprovados (todos >= 9.0)

---

## Resumo Executivo

### Problema
O MCP Server ClickUp v1.2.0 **trava o Claude Desktop** quando retorna muitas tasks (100+ tasks = 1200 linhas de output).

### Solução
Refatoração em 5 sprints para:
1. Resolver travamento (output compacto)
2. Adicionar 7 novas tools
3. Implementar resiliência (retry, cache)
4. Garantir qualidade (testes, logs)
5. Diferenciais competitivos (opcional)

### Investimento
- **Mínimo viável:** 8h45 (Sprints 1-4)
- **Completo:** 13h00 (todas as sprints)

---

## Votação do Conselho Técnico

| # | Liderança | Nota | Status |
|---|-----------|------|--------|
| 1 | Head de Infraestrutura | 9.0 | ✅ |
| 2 | Head de QA | 9.5 | ✅ |
| 3 | Head de Qualidade Técnica | 9.0 | ✅ |
| 4 | Head de Segurança | 9.5 | ✅ |
| 5 | Head de SRE/Observabilidade | 9.0 | ✅ |
| 6 | Head de Performance | 9.5 | ✅ |
| 7 | Head de Arquitetura | 9.0 | ✅ |
| 8 | Head de Estratégia | 9.5 | ✅ |
| 9 | Head de Tecnologias | 9.0 | ✅ |
| 10 | Head de Integração/E2E | 9.0 | ✅ |
| 11 | Head de Aceitação/UAT | 9.0 | ✅ |
| 12 | Head de Governança Docs | 9.5 | ✅ |
| 13 | Head de Projeto/PO | 9.5 | ✅ |

---

## Sprints

### Sprint 1: Resolver Travamento
**Tempo:** 1h35 | **Prioridade:** CRÍTICA

| Entrega | Tempo | Descrição |
|---------|-------|-----------|
| OutputMode enum | 10min | COMPACT, DETAILED, JSON |
| format_tasks_compact() | 20min | 1 linha por task |
| format_tasks_detailed() | 5min | Renomear função existente |
| output_mode em 10 tools | 30min | Parâmetro em todas as listagens |
| Default COMPACT | 5min | Resolve travamento |
| Parâmetro limit | 15min | Default 25, max 100 |
| Paginação inteligente | 10min | Aviso quando há mais páginas |

**Critério de Aceite:**
- [ ] 100 tasks listadas sem travar
- [ ] Tempo < 3s para 100 tasks
- [ ] Output COMPACT = máximo 2 linhas/task

---

### Sprint 2: Tools Ausentes
**Tempo:** 2h55 | **Prioridade:** ALTA

| Tool | Tempo | Endpoint |
|------|-------|----------|
| get_custom_fields | 25min | GET /list/{id}/field |
| get_space_details | 20min | GET /space/{id} |
| get_list_details | 20min | GET /list/{id} |
| get_checklists | 15min | Incluído em GET /task/{id} |
| analyze_space_structure | 45min | Composição interna |
| get_attachments | 20min | GET /task/{id}/attachment |
| create_doc / get_docs | 30min | GET/POST /doc |

**Critério de Aceite:**
- [ ] 7 novas tools funcionando
- [ ] analyze_space_structure retorna análise completa

---

### Sprint 3: Resiliência
**Tempo:** 1h35 | **Prioridade:** ALTA

| Entrega | Tempo | Tecnologia |
|---------|-------|------------|
| validate_config() | 10min | Fail-fast no startup |
| Connection pooling | 15min | httpx.AsyncClient |
| Retry + backoff | 15min | tenacity |
| Cache TTL | 25min | cachetools |
| Timeout configurável | 10min | Por operação |
| Rate limiting | 20min | Respeitar limites ClickUp |

**Critério de Aceite:**
- [ ] Retry recupera falhas de rede
- [ ] Cache hit < 50ms
- [ ] Rate limiter previne 429

---

### Sprint 4: Qualidade
**Tempo:** 2h50 | **Prioridade:** MÉDIA

| Entrega | Tempo | Descrição |
|---------|-------|-----------|
| Logging estruturado | 20min | loguru |
| Log SRE específico | 5min | Formato aprovado |
| Correlation ID | 15min | contextvars |
| Métricas | 20min | Contadores por tool |
| Testes unitários | 45min | pytest, 80% cobertura |
| Testes E2E | 30min | respx mock |
| README.md | 20min | Documentação completa |
| CHANGELOG.md | 10min | Semver |

**Critério de Aceite:**
- [ ] Cobertura > 80% em formatação
- [ ] Logs com correlation ID
- [ ] README permite usar sem ajuda

---

### Sprint 5: Diferencial (Opcional)
**Tempo:** 4h15 | **Prioridade:** BAIXA

| Entrega | Tempo | Benefício |
|---------|-------|-----------|
| Modos operacionais | 30min | read-only mode |
| Transport SSE | 1h | n8n compatibility |
| Transport HTTP | 1h | Flexibilidade |
| Busca fuzzy | 30min | UX melhorada |
| Chat/Messages | 45min | Feature completa |
| Time tracking+ | 30min | Billable hours |

---

## Pendências Resolvidas

Antes da aprovação, o Conselho exigiu correções:

| Pendência | Solução | Arquivo |
|-----------|---------|---------|
| Testes inativos | 8 testes ativados e passando | test_formatting.py |
| README confuso | Separado atual vs planejado | README.md |
| .env não validado | validate_config() documentado | SPRINTS.md |
| Correlation ID vago | Implementação com contextvars | SPRINTS.md |
| Sem smoke test | Checklist completo | SPRINTS.md |
| Código monolítico | Backlog de modularização | SPRINTS.md |

---

## Arquivos do Projeto

```
mcp server clickup/
├── src/
│   └── clickup_mcp.py       # Código principal (1500 linhas)
├── tests/
│   ├── test_formatting.py   # 8 testes ativos
│   └── conftest.py          # Fixtures
├── docs/
│   ├── PRD.md               # Requisitos
│   ├── SPRINTS.md           # Detalhamento técnico
│   └── PLANO_APROVADO_v2.md # Este documento
├── README.md                # Guia de uso
├── CHANGELOG.md             # Histórico
├── pyproject.toml           # Dependências
└── .env.example             # Configuração
```

---

## Smoke Test

Executar após cada sprint:

### Sprint 1
- [ ] `clickup_get_workspaces` → retorna workspaces
- [ ] `clickup_get_tasks` (100+ tasks) → não trava, COMPACT ativo
- [ ] `output_mode=detailed` → formato completo funciona

### Sprint 2
- [ ] `clickup_get_custom_fields` → lista campos
- [ ] `clickup_analyze_space_structure` → análise completa

### Sprint 3
- [ ] Retry funciona após falha de rede
- [ ] Cache ativo (< 50ms em requests repetidos)

### Sprint 4
- [ ] Arquivo `clickup_mcp.log` criado
- [ ] `pytest tests/ -v` → todos passam

---

## Backlog Pós-v2.0

Refatorações recomendadas para após estabilização:

1. **Modularização** (~4h)
   - Separar em models/, formatters/, tools/, infra/
   - Arquivos < 200 linhas cada

2. **Helper query_params** (30min)
   - Eliminar duplicação em 10+ tools

---

## Próximos Passos

1. ✅ Proposta aprovada pelo Conselho (9.23/10)
2. ⏳ Iniciar Sprint 1: Resolver Travamento
3. ⏳ Executar Smoke Test Sprint 1
4. ⏳ Continuar com Sprints 2-4
5. ⏳ Avaliar necessidade de Sprint 5

---

> Documento gerado em: 2026-01-11
> Aprovado pelo Conselho Técnico com média 9.23/10
