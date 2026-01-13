# PRD - MCP Server ClickUp v2.0

> **Documento:** Product Requirements Document
> **Projeto:** MCP Server ClickUp - Refatoração Completa
> **Versão:** 1.0
> **Data:** 2026-01-10
> **Autor:** Conselho Técnico (13 lideranças)
> **Status:** Aprovado por Unanimidade

---

## 1. Contexto e Problema

### 1.1 Situação Atual

O MCP Server ClickUp atual (v1.2.0) apresenta os seguintes problemas:

| Problema | Impacto | Severidade |
|----------|---------|------------|
| Output excessivo (12 linhas/task) | Claude Desktop trava com 100+ tasks | 🔴 CRÍTICO |
| Sem limite de tasks | API retorna até 100, sempre | 🔴 CRÍTICO |
| Cliente HTTP não reutilizado | Overhead de conexão | 🟡 ALTO |
| Timeout fixo (30s) | Operações pesadas falham | 🟡 ALTO |
| Sem retry/backoff | Falhas temporárias não recuperam | 🟡 ALTO |
| Sem cache | Requisições repetidas desnecessárias | 🟡 ALTO |
| Sem logging | Debug impossível | 🟢 MÉDIO |
| Sem testes | Regressões não detectadas | 🟢 MÉDIO |
| Tools ausentes | Análises limitadas | 🟡 ALTO |

### 1.2 Análise de Mercado (Benchmark)

| MCP | Tools | Licença | Diferenciais | Limitações |
|-----|-------|---------|--------------|------------|
| taazkareem | 50+ | 💰 Sponsorware | SSE, HTTP, Docs, Chat | Pago |
| Nazruden | 30+ | MIT | Custom Fields | Sem cache/retry |
| hauptsacheNet | 12 | MIT | Modos operacionais | Poucas tools |
| **Nosso (atual)** | 23 | Próprio | Tipo/Subtipo extraction | Trava com volume |

### 1.3 Objetivo

Transformar o MCP Server ClickUp no **melhor MCP gratuito do mercado**, superando alternativas pagas em estabilidade e alternativas gratuitas em funcionalidades.

---

## 2. Requisitos Funcionais

### 2.1 Resolução de Travamento (MUST)

| ID | Requisito | Critério de Aceite |
|----|-----------|-------------------|
| RF01 | Modo COMPACT de output | 1 linha por task, máximo 150 caracteres |
| RF02 | Modo DETAILED de output | Formato atual (12 linhas), sob demanda |
| RF03 | Modo JSON de output | Raw JSON para processamento |
| RF04 | Default COMPACT | Todas as tools de listagem usam COMPACT por padrão |
| RF05 | Parâmetro limit | Default 25, máximo 100, configurável |
| RF06 | Paginação inteligente | Aviso claro quando há mais páginas |

### 2.2 Tools Ausentes (SHOULD)

| ID | Requisito | Endpoint ClickUp |
|----|-----------|------------------|
| RF07 | get_custom_fields | GET /list/{id}/field |
| RF08 | get_space_details | GET /space/{id} |
| RF09 | get_list_details | GET /list/{id} |
| RF10 | get_checklists | Incluído em GET /task/{id} |
| RF11 | analyze_space_structure | Composição interna |
| RF12 | get_attachments | GET /task/{id}/attachment |
| RF13 | create_doc / get_docs | GET/POST /doc |

### 2.3 Resiliência (SHOULD)

| ID | Requisito | Implementação |
|----|-----------|---------------|
| RF14 | Retry com backoff | tenacity, 3 tentativas, exponential |
| RF15 | Connection pooling | httpx.AsyncClient reutilizado |
| RF16 | Cache TTL | cachetools, 5min estrutura, 1min tasks |
| RF17 | Timeout configurável | Por operação, 5-120s |
| RF18 | Rate limiting interno | Respeitar limites ClickUp API |

### 2.4 Observabilidade (SHOULD)

| ID | Requisito | Implementação |
|----|-----------|---------------|
| RF19 | Logging estruturado | loguru, JSON format |
| RF20 | Log de output | "Gerando: {n} tasks, modo {mode}, {chars} chars" |
| RF21 | Métricas de uso | calls, errors, response_time por tool |
| RF22 | Correlation ID | UUID por sessão para debug |

### 2.5 Diferenciais Competitivos (COULD)

| ID | Requisito | Origem |
|----|-----------|--------|
| RF23 | Modos operacionais | read-minimal, read, write |
| RF24 | Transport SSE | Além de STDIO |
| RF25 | Transport HTTP | Além de STDIO |
| RF26 | Busca fuzzy | Similaridade em nomes de tasks |
| RF27 | Chat/Messages | Integração com ClickUp Chat |

---

## 3. Requisitos Não-Funcionais

| ID | Requisito | Métrica |
|----|-----------|---------|
| RNF01 | Não travar Claude Desktop | 100 tasks em < 2s |
| RNF02 | Latência de resposta | < 500ms para cache hit |
| RNF03 | Disponibilidade | Retry recupera 95% das falhas |
| RNF04 | Cobertura de testes | > 80% em formatação |
| RNF05 | Documentação | README + CHANGELOG + docstrings |

---

## 4. Arquitetura

### 4.1 Estrutura de Arquivos

```
mcp server clickup/
├── src/
│   └── clickup_mcp.py          # Código principal
├── tests/
│   ├── test_formatting.py      # Testes de formatação
│   ├── test_validation.py      # Testes de modelos
│   ├── test_integration.py     # Testes E2E com mock
│   └── conftest.py             # Fixtures
├── docs/
│   ├── PRD.md                  # Este documento
│   └── SPRINTS.md              # Detalhamento das sprints
├── README.md                   # Guia de uso
├── CHANGELOG.md                # Histórico de versões
├── pyproject.toml              # Dependências
└── .env.example                # Variáveis de ambiente
```

### 4.2 Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Server ClickUp v2                    │
├─────────────────────────────────────────────────────────────┤
│  CAMADA DE APRESENTAÇÃO                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   COMPACT   │ │  DETAILED   │ │    JSON     │            │
│  │  Formatter  │ │  Formatter  │ │  Formatter  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
├─────────────────────────────────────────────────────────────┤
│  CAMADA DE TOOLS (36 tools)                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │Workspace│ │  Tasks  │ │ Custom  │ │Structure│           │
│  │  Tools  │ │  Tools  │ │ Fields  │ │ Analyzer│           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
├─────────────────────────────────────────────────────────────┤
│  CAMADA DE INFRAESTRUTURA                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   HTTP      │ │   Cache     │ │  Logging    │            │
│  │   Client    │ │   (TTL)     │ │  (loguru)   │            │
│  │  (pooling)  │ │             │ │             │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐                            │
│  │   Retry     │ │   Rate      │                            │
│  │  (tenacity) │ │   Limiter   │                            │
│  └─────────────┘ └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Dependências

```toml
[project]
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "tenacity>=8.0.0",
    "loguru>=0.7.0",
    "cachetools>=5.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.4.0",
]
```

---

## 5. Decisões Técnicas

### 5.1 Por que COMPACT como default?

| Fator | Análise |
|-------|---------|
| Problema atual | 100 tasks × 12 linhas = 1200 linhas → trava |
| Com COMPACT | 100 tasks × 1 linha = 100 linhas → funciona |
| Backward compatible | Usuário pode pedir DETAILED quando precisar |
| Experiência | 90% dos casos precisa só de resumo |

### 5.2 Por que manter Python?

| Fator | Análise |
|-------|---------|
| Stack existente | Já está em Python, menor atrito |
| FastMCP | Framework maduro e bem documentado |
| Ecossistema | Mesmo stack do Transcription Flow |
| IA implementa | Não há curva de aprendizado |

### 5.3 Por que não migrar para taazkareem?

| Fator | Análise |
|-------|---------|
| Custo | Sponsorware = pago |
| Controle | Dependência de terceiro |
| Customização | Tipo/Subtipo extraction é único |
| Investimento | 13h para ter MCP melhor e gratuito |

---

## 6. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| FastMCP não suporta SSE | Média | Sprint 5 | Verificar antes, ter fallback STDIO |
| API ClickUp muda | Baixa | Alto | Testes E2E detectam |
| Cache causa dados stale | Média | Médio | TTL curto (5min max) |
| Complexidade aumenta | Média | Médio | Testes obrigatórios |

---

## 7. Métricas de Sucesso

| Métrica | Atual | Meta Sprint 1 | Meta Final |
|---------|-------|---------------|------------|
| Tasks sem travar | ~50 | 100+ | 500+ |
| Nota Conselho | 8.98 | 9.5 | 9.9 |
| Tools disponíveis | 23 | 23 | 36 |
| Cobertura testes | 0% | 50% | 80% |
| Tempo resposta (cache) | N/A | < 500ms | < 200ms |

---

## 8. Cronograma

| Sprint | Foco | Duração | Entregas |
|--------|------|---------|----------|
| 1 | Travamento | 1h35 | OutputMode, limit, formatters |
| 2 | Tools | 2h55 | 7 novas tools |
| 3 | Resiliência | 1h25 | Retry, cache, pooling |
| 4 | Qualidade | 2h50 | Testes, logs, docs |
| 5 | Diferencial | 4h15 | Modos, transports (opcional) |

**Total:** 13h00 (Sprint 5 opcional: 8h45 sem ela)

---

## 9. Aprovações

| Conselheiro | Voto | Data |
|-------------|------|------|
| Head de Infraestrutura | ✅ | 2026-01-10 |
| Head de QA | ✅ | 2026-01-10 |
| Head de Qualidade Técnica | ✅ | 2026-01-10 |
| Head de Segurança | ✅ | 2026-01-10 |
| Head de SRE | ✅ | 2026-01-10 |
| Head de Performance | ✅ | 2026-01-10 |
| Head de Arquitetura | ✅ | 2026-01-10 |
| Head de Estratégia | ✅ | 2026-01-10 |
| Head de Tecnologias | ✅ | 2026-01-10 |
| Head de Integração | ✅ | 2026-01-10 |
| Head de Governança | ✅ | 2026-01-10 |
| Head de Projeto | ✅ | 2026-01-10 |

**Status: APROVADO POR UNANIMIDADE**

---

> Documento gerado em: 2026-01-10
> Próxima revisão: Após Sprint 4
