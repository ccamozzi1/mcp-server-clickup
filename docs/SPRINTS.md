# Detalhamento das Sprints - MCP Server ClickUp v2.0

> **Referência:** PRD.md
> **Data:** 2026-01-10
> **Status:** Aprovado pelo Conselho Técnico

---

## Visão Geral

| Sprint | Foco | Tempo | Prioridade | Dependências |
|--------|------|-------|------------|--------------|
| 1 | Resolver Travamento | 1h35 | 🔴 CRÍTICA | Nenhuma |
| 2 | Tools Ausentes | 2h55 | 🟡 ALTA | Sprint 1 |
| 3 | Resiliência | 1h25 | 🟡 ALTA | Sprint 1 |
| 4 | Qualidade | 2h50 | 🟢 MÉDIA | Sprints 1-3 |
| 5 | Diferencial | 4h15 | 🔵 OPCIONAL | Sprints 1-4 |

---

## Sprint 1: Resolver Travamento

### Objetivo
Eliminar o problema crítico de travamento do Claude Desktop quando o MCP retorna muitos dados.

### Por que esta sprint primeiro?
- **Problema bloqueante:** Usuário não consegue usar o MCP com mais de ~50 tasks
- **Quick win:** 1h35 de trabalho resolve o problema mais doloroso
- **Fundação:** OutputMode será usado por todas as outras sprints

### Entregas

#### 1.1 Enum OutputMode (10 min)

**O que:** Criar enum para controlar verbosidade do output

**Código:**
```python
class OutputMode(str, Enum):
    """Modo de formatação do output."""
    COMPACT = "compact"      # 1 linha por item (DEFAULT)
    DETAILED = "detailed"    # Formato completo (12+ linhas)
    JSON = "json"            # Raw JSON
```

**Por que:** Permite ao usuário escolher quanto detalhe quer, com default seguro.

---

#### 1.2 format_tasks_compact() (20 min)

**O que:** Função de formatação resumida

**Código:**
```python
def format_tasks_compact(tasks: List[Dict], total: int = 0, page: int = 0) -> str:
    """Formata tasks em modo compacto: 1 linha por task."""
    lines = [f"**{len(tasks)} tasks** (página {page}):\n"]

    for i, task in enumerate(tasks, 1):
        status = task.get('status', {}).get('status', '?')[:10]
        name = task.get('name', 'Sem nome')[:50]
        due = format_timestamp(task.get('due_date')) or '-'
        task_id = task.get('id', '')

        lines.append(f"{i}. [{status}] {name} | {due} | `{task_id}`")

    if len(tasks) >= 25:
        lines.append(f"\n_Use `page={page+1}` para mais resultados_")

    return "\n".join(lines)
```

**Resultado:** 100 tasks = ~105 linhas (vs 1200 atual)

**Por que:** Redução de 92% no volume de dados.

---

#### 1.3 format_tasks_detailed() (5 min)

**O que:** Renomear função existente para clareza

**Código:**
```python
def format_tasks_detailed(tasks: List[Dict], total: int = 0, page: int = 0) -> str:
    """Formata tasks em modo detalhado: ~12 linhas por task."""
    # Código atual da format_tasks_list_markdown
    # Apenas renomear para deixar explícito que é modo verbose
```

**Por que:** Nomenclatura clara, mantém comportamento original disponível.

---

#### 1.4 Parâmetro output_mode em 10 tools (30 min)

**O que:** Adicionar parâmetro em todas as tools de listagem

**Tools afetadas:**
1. `get_workspaces`
2. `get_spaces`
3. `get_folders`
4. `get_lists`
5. `get_folderless_lists`
6. `get_tasks`
7. `get_filtered_team_tasks`
8. `get_task_comments`
9. `get_workspace_members`
10. `get_time_entries`

**Código exemplo:**
```python
class GetTasksInput(BaseModel):
    # ... campos existentes ...
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Formato: compact (1 linha), detailed (completo), json (raw)"
    )
```

**Por que:** Consistência em toda a API, usuário sempre pode escolher.

---

#### 1.5 Default = COMPACT (5 min)

**O que:** Garantir que COMPACT é o padrão em todos os modelos

**Por que:**
- Resolve o problema sem quebrar nada
- Usuário precisa explicitamente pedir DETAILED
- Backward compatible: quem quer detalhes, pede

---

#### 1.6 Parâmetro limit (15 min)

**O que:** Limitar quantidade de itens retornados

**Código:**
```python
class GetTasksInput(BaseModel):
    # ... campos existentes ...
    limit: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Máximo de itens a retornar (1-100)"
    )
```

**Por que:**
- Default 25 é seguro para qualquer uso
- Usuário pode aumentar se precisar
- Nunca ultrapassa 100 (limite da API ClickUp)

---

#### 1.7 Paginação inteligente (10 min)

**O que:** Aviso claro quando há mais páginas

**Código:**
```python
if len(tasks) >= limit:
    lines.append(f"\n⚠️ **Mostrando {limit} de {total or '?'}.**")
    lines.append(f"Use `page={page + 1}` para próxima página.")
```

**Por que:** Usuário sabe que há mais dados e como obtê-los.

---

### Critério de Aceite Sprint 1

- [ ] 100 tasks listadas sem travar Claude Desktop
- [ ] Tempo de resposta < 3s para 100 tasks
- [ ] Output COMPACT tem máximo 2 linhas por task
- [ ] Todas as 10 tools de listagem têm output_mode
- [ ] Default é COMPACT em todos os casos

---

## Sprint 2: Tools Ausentes

### Objetivo
Adicionar tools que faltam para análises estruturais e equiparar com concorrência.

### Por que esta sprint?
- **Habilita análises:** Usuário pediu análise morfológica que o MCP não suporta
- **Gap competitivo:** Nazruden e taazkareem têm custom fields
- **Valor agregado:** Cada tool nova é uma capacidade a mais

### Entregas

#### 2.1 get_custom_fields (25 min)

**O que:** Listar campos customizados de uma list

**Endpoint ClickUp:** `GET /list/{list_id}/field`

**Código:**
```python
@mcp.tool(name="clickup_get_custom_fields")
async def get_custom_fields(params: GetCustomFieldsInput) -> str:
    """
    Lista os campos customizados de uma list.

    Útil para:
    - Ver quais campos existem
    - Identificar campos repetidos entre lists
    - Planejar padronização
    """
    data = await api_request("GET", f"/list/{params.list_id}/field")
    fields = data.get("fields", [])

    if params.output_mode == OutputMode.JSON:
        return json.dumps(data, indent=2)

    lines = [f"**{len(fields)} campos customizados:**\n"]
    for f in fields:
        tipo = f.get("type", "?")
        nome = f.get("name", "Sem nome")
        required = "✓" if f.get("required") else ""
        lines.append(f"- **{nome}** ({tipo}) {required}")

    return "\n".join(lines)
```

**Por que:** Essencial para análise estrutural que o usuário pediu.

---

#### 2.2 get_space_details (20 min)

**O que:** Detalhes completos de um space

**Endpoint ClickUp:** `GET /space/{space_id}`

**Retorna:**
- Status disponíveis no space
- Features ativas (due dates, time tracking, etc.)
- Membros com acesso

**Por que:** Responde "quais status existem neste espaço?".

---

#### 2.3 get_list_details (20 min)

**O que:** Detalhes de uma list específica

**Endpoint ClickUp:** `GET /list/{list_id}`

**Retorna:**
- Configurações da list
- Status específicos (se diferentes do space)
- Contagem de tasks

**Por que:** Complementa get_lists com detalhes sob demanda.

---

#### 2.4 get_checklists (15 min)

**O que:** Extrair checklists de uma task

**Implementação:** Checklists já vêm no GET /task/{id}, só formatar

**Por que:** Benchmark mostra que Nazruden tem, nós não.

---

#### 2.5 analyze_space_structure ⭐ (45 min)

**O que:** Tool especial para análise morfológica completa

**Código:**
```python
@mcp.tool(name="clickup_analyze_space_structure")
async def analyze_space_structure(params: AnalyzeSpaceInput) -> str:
    """
    Análise morfológica completa de um space.

    Retorna:
    - Hierarquia: folders → lists → contagem de tasks
    - Campos customizados: únicos vs repetidos
    - Status configurados
    - Membros com acesso

    Útil para:
    - Entender estrutura antes de reorganizar
    - Identificar inconsistências
    - Planejar padronização
    """
    # Busca dados
    space = await api_request("GET", f"/space/{params.space_id}")
    folders = await api_request("GET", f"/space/{params.space_id}/folder")

    # Analisa estrutura
    # ... lógica de análise ...

    return formatted_analysis
```

**Por que:** Responde diretamente ao prompt do usuário sobre análise morfológica.

---

#### 2.6 get_attachments (20 min)

**O que:** Listar anexos de uma task

**Endpoint ClickUp:** Incluído em GET /task/{id}

**Por que:** taazkareem tem, nós não.

---

#### 2.7 create_doc / get_docs (30 min)

**O que:** CRUD de documentos ClickUp

**Endpoints ClickUp:** `GET /workspace/{id}/doc`, `POST /workspace/{id}/doc`

**Por que:** taazkareem tem, é diferencial competitivo.

---

### Critério de Aceite Sprint 2

- [ ] 7 novas tools funcionando
- [ ] analyze_space_structure retorna análise completa
- [ ] Custom fields listados corretamente
- [ ] Documentação de cada nova tool

---

## Sprint 3: Resiliência

### Objetivo
Tornar o MCP robusto contra falhas de rede e otimizar performance.

### Por que esta sprint?
- **Estabilidade:** Falhas temporárias não devem quebrar o fluxo
- **Performance:** Cache evita requisições repetidas
- **Profissionalismo:** MCP de produção precisa de resiliência

### Entregas

#### 3.0 Validação de Configuração (10 min) ⚠️ ADICIONADO

**O que:** Validar variáveis de ambiente no startup

**Código:**
```python
from loguru import logger

def validate_config() -> None:
    """Valida configuração no startup. Fail-fast para variáveis obrigatórias."""
    required = ["CLICKUP_API_TOKEN"]
    optional = ["DEFAULT_TIMEOUT", "CACHE_TTL_STRUCTURE", "CACHE_TTL_TASKS", "LOG_LEVEL"]

    # Fail-fast para obrigatórias
    for var in required:
        if not os.environ.get(var):
            raise EnvironmentError(f"Variável obrigatória não configurada: {var}")

    # Warning para desconhecidas (possível typo)
    env_vars = {k for k in os.environ.keys() if k.startswith("CLICKUP_") or k in optional}
    known_vars = set(required + optional)
    unknown = env_vars - known_vars
    for var in unknown:
        logger.warning(f"Variável desconhecida ignorada: {var}")

    logger.info("Configuração validada com sucesso")

# Chamar no startup
validate_config()
```

**Por que:**
- Fail-fast evita erros silenciosos
- Warning para typos (ex: CLICKUP_API_TOKE)
- Exigido pelo Head de Infraestrutura

---

#### 3.1 Connection pooling (15 min)

**O que:** Reutilizar cliente HTTP

**Código:**
```python
_client: Optional[httpx.AsyncClient] = None

async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_connections=10)
        )
    return _client
```

**Por que:** Evita overhead de conexão a cada request.

---

#### 3.2 Retry com exponential backoff (15 min)

**O que:** Tentar novamente em falhas temporárias

**Código:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError))
)
async def api_request(...):
    # ...
```

**Por que:** 95% das falhas temporárias são recuperadas.

---

#### 3.3 Cache TTL (25 min)

**O que:** Cachear dados que mudam pouco

**Código:**
```python
from cachetools import TTLCache

# Cache por tipo de dado
structure_cache = TTLCache(maxsize=100, ttl=300)  # 5min para estrutura
tasks_cache = TTLCache(maxsize=50, ttl=60)        # 1min para tasks
```

**Política:**
- Workspaces, Spaces, Folders: 5 min
- Lists: 3 min
- Tasks: 1 min
- Custom Fields: 5 min

**Por que:** Reduz latência em 80%+ para dados repetidos.

---

#### 3.4 Timeout configurável (10 min)

**O que:** Timeout por operação

**Código:**
```python
class GetTasksInput(BaseModel):
    # ...
    timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Timeout em segundos"
    )
```

**Por que:** Operações pesadas podem precisar de mais tempo.

---

#### 3.5 Rate limiting interno (20 min)

**O que:** Respeitar limites da API ClickUp

**Código:**
```python
import asyncio
from collections import deque
from time import time

class RateLimiter:
    def __init__(self, max_requests: int = 100, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests = deque()

    async def acquire(self):
        now = time()
        while self.requests and self.requests[0] < now - self.window:
            self.requests.popleft()

        if len(self.requests) >= self.max_requests:
            wait_time = self.requests[0] + self.window - now
            await asyncio.sleep(wait_time)

        self.requests.append(now)
```

**Por que:** Evita ban da API ClickUp.

---

### Critério de Aceite Sprint 3

- [ ] Retry recupera falhas de rede
- [ ] Cache hit tem latência < 50ms
- [ ] Rate limiter previne erros 429
- [ ] Connection pooling ativo

---

## Sprint 4: Qualidade

### Objetivo
Garantir manutenibilidade e facilitar debug.

### Por que esta sprint?
- **Manutenção:** Sem testes, qualquer mudança pode quebrar
- **Debug:** Sem logs, impossível diagnosticar problemas
- **Adoção:** Sem docs, difícil de usar

### Entregas

#### 4.1 Logging estruturado (20 min)

**O que:** Logs úteis com loguru

**Código:**
```python
from loguru import logger

logger.add(
    "clickup_mcp.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="10 MB"
)

# Em cada tool:
logger.info(f"Listando tasks: list_id={list_id}, limit={limit}, mode={output_mode}")
logger.info(f"Retornando {len(tasks)} tasks, {len(output)} caracteres")
```

---

#### 4.2 Log específico SRE (5 min)

**O que:** Formato exato aprovado pelo conselho

**Código:**
```python
logger.info(
    f"Gerando output: {len(items)} items, modo {output_mode.value}, "
    f"{len(output)} caracteres"
)
```

---

#### 4.2.1 Correlation ID (15 min) ⚠️ ADICIONADO

**O que:** Identificador único por sessão para rastreabilidade

**Código:**
```python
import contextvars
import uuid

# Variável de contexto para correlation ID
correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    'correlation_id',
    default='no-correlation-id'
)

def get_correlation_id() -> str:
    """Retorna o correlation ID atual."""
    return correlation_id.get()

def set_new_correlation_id() -> str:
    """Gera e define um novo correlation ID."""
    new_id = str(uuid.uuid4())[:8]  # 8 chars é suficiente
    correlation_id.set(new_id)
    return new_id

# No início de cada tool:
@mcp.tool(name="clickup_get_tasks")
async def get_tasks(params: GetTasksInput) -> str:
    cid = set_new_correlation_id()
    logger.bind(correlation_id=cid).info(f"Iniciando get_tasks: list_id={params.list_id}")
    # ... resto da função ...
    logger.bind(correlation_id=cid).info(f"Finalizando get_tasks: {len(tasks)} tasks")
```

**Formato do log:**
```
2026-01-11 10:30:00 | INFO | [a1b2c3d4] Iniciando get_tasks: list_id=123
2026-01-11 10:30:01 | INFO | [a1b2c3d4] Finalizando get_tasks: 50 tasks
```

**Por que:**
- Rastrear requests entre múltiplas chamadas
- Debug de problemas em produção
- Exigido pelo Head de SRE/Observabilidade

---

#### 4.3 Métricas (20 min)

**O que:** Contadores para diagnóstico

**Código:**
```python
from collections import defaultdict

metrics = {
    "calls": defaultdict(int),
    "errors": defaultdict(int),
    "total_time_ms": defaultdict(float),
}

def record_call(tool_name: str, duration_ms: float, error: bool = False):
    metrics["calls"][tool_name] += 1
    metrics["total_time_ms"][tool_name] += duration_ms
    if error:
        metrics["errors"][tool_name] += 1
```

---

#### 4.4 Testes unitários (45 min)

**O que:** Testes de formatação e validação

**Arquivos:**
- `tests/test_formatting.py` - format_compact, format_detailed
- `tests/test_validation.py` - modelos Pydantic
- `tests/conftest.py` - fixtures

**Cobertura mínima:** 80% em funções de formatação

---

#### 4.5 Testes E2E (30 min)

**O que:** Testes de integração com mock

**Código:**
```python
@pytest.mark.asyncio
async def test_get_tasks_compact():
    with respx.mock:
        respx.get(...).respond(json=mock_tasks)
        result = await get_tasks(GetTasksInput(
            list_id="123",
            output_mode=OutputMode.COMPACT
        ))
        assert len(result.split("\n")) < 50
```

---

#### 4.6 README.md (20 min)

**Conteúdo:**
- Instalação
- Configuração (.env)
- Exemplos de uso
- Lista de tools

---

#### 4.7 CHANGELOG.md (10 min)

**Formato:** Semver + Keep a Changelog

---

### Critério de Aceite Sprint 4

- [ ] Cobertura de testes > 80% em formatação
- [ ] Logs aparecem corretamente
- [ ] README permite usar sem ajuda
- [ ] CHANGELOG documenta v2.0

---

## Sprint 5: Diferencial (Opcional)

### Objetivo
Superar a concorrência com features avançadas.

### Por que opcional?
- **Sprints 1-4 já resolvem os problemas**
- **ROI menor:** mais esforço, ganho incremental
- **Reavaliar:** após Sprint 4, decidir se vale

### Entregas (se aprovado)

| Item | Esforço | Benefício |
|------|---------|-----------|
| Modos operacionais | 30 min | Segurança (read-only) |
| Transport SSE | 1h | Compatibilidade n8n |
| Transport HTTP | 1h | Flexibilidade |
| Busca fuzzy | 30 min | UX melhorada |
| Chat/Messages | 45 min | Feature completa |
| Time tracking+ | 30 min | Billable hours |

---

## Resumo de Tempo

| Sprint | Tempo | Acumulado |
|--------|-------|-----------|
| 1 | 1h35 | 1h35 |
| 2 | 2h55 | 4h30 |
| 3 | 1h25 | 5h55 |
| 4 | 2h50 | 8h45 |
| 5 | 4h15 | 13h00 |

**Mínimo viável (Sprints 1-4):** 8h45
**Completo (todas):** 13h00

---

## Smoke Test - Claude Desktop ⚠️ ADICIONADO

> Checklist manual de validação. Executar após cada Sprint.

### Pré-requisitos
- [ ] Claude Desktop instalado e configurado
- [ ] MCP Server ClickUp configurado no `claude_desktop_config.json`
- [ ] Token ClickUp válido

### Testes Obrigatórios

#### Após Sprint 1 (Travamento)
- [ ] Reiniciar Claude Desktop
- [ ] `clickup_get_workspaces` → retorna lista de workspaces
- [ ] `clickup_get_tasks` com list de 100+ tasks → **não trava**, modo COMPACT ativo
- [ ] `clickup_get_tasks output_mode=detailed` → formato completo funciona
- [ ] Tempo de resposta < 3s para 100 tasks

#### Após Sprint 2 (Tools)
- [ ] `clickup_get_custom_fields` → lista campos de uma list
- [ ] `clickup_analyze_space_structure` → retorna análise completa
- [ ] `clickup_get_space_details` → detalhes do space

#### Após Sprint 3 (Resiliência)
- [ ] Desconectar internet → tentar request → reconectar → retry funciona
- [ ] Requests repetidos → cache ativo (< 50ms)
- [ ] Muitos requests rápidos → rate limiter previne 429

#### Após Sprint 4 (Qualidade)
- [ ] Verificar arquivo `clickup_mcp.log` criado
- [ ] Logs têm correlation ID
- [ ] `pytest tests/ -v` → todos os testes passam

### Como Reportar Falhas
1. Capturar screenshot do erro
2. Copiar logs relevantes
3. Documentar passos para reproduzir
4. Criar issue no repositório

---

## Backlog Pós-Sprint 4 ⚠️ ADICIONADO

> Refatorações recomendadas pelo Conselho Técnico. Prioridade: BAIXA.

### Modularização do Código

**Problema:** Arquivo único de 1500+ linhas dificulta manutenção.

**Estrutura Proposta:**
```
src/
├── clickup_mcp.py          # Entry point, inicialização MCP
├── config.py               # Constantes e configuração
├── models/
│   ├── __init__.py
│   ├── inputs.py           # Modelos Pydantic de input
│   └── enums.py            # OutputMode, OrderBy, Priority
├── formatters/
│   ├── __init__.py
│   ├── compact.py          # format_tasks_compact()
│   ├── detailed.py         # format_tasks_detailed()
│   └── base.py             # Funções auxiliares
├── tools/
│   ├── __init__.py
│   ├── workspaces.py       # get_workspaces
│   ├── spaces.py           # get_spaces, get_space_details
│   ├── folders.py          # CRUD folders
│   ├── lists.py            # CRUD lists
│   ├── tasks.py            # CRUD tasks
│   └── comments.py         # Comentários
└── infra/
    ├── __init__.py
    ├── http_client.py      # Connection pooling, retry
    ├── cache.py            # TTLCache
    └── rate_limiter.py     # Rate limiting
```

**Benefícios:**
- Arquivos < 200 linhas cada
- Fácil localizar código
- Testes isolados por módulo
- Code review simplificado

### Helper para Query Params

**Problema:** Duplicação em 10+ tools.

**Solução:**
```python
def build_query_params(params: BaseModel, fields: List[str]) -> Dict[str, Any]:
    """Constrói query params a partir de modelo Pydantic."""
    query = {}
    for field in fields:
        value = getattr(params, field, None)
        if value is not None:
            if isinstance(value, bool):
                query[field] = str(value).lower()
            elif isinstance(value, list):
                query[f"{field}[]"] = value
            else:
                query[field] = value
    return query

# Uso:
query = build_query_params(params, ["archived", "include_closed", "page", "statuses"])
```

### Estimativa de Esforço

| Item | Tempo | Risco |
|------|-------|-------|
| Separar em módulos | 2h | Médio |
| Helper query_params | 30min | Baixo |
| Atualizar imports | 30min | Baixo |
| Atualizar testes | 1h | Médio |

**Total:** ~4h

**Recomendação:** Implementar após v2.0 estável, antes de adicionar novas features.

---

> Documento gerado em: 2026-01-10
> Atualizado em: 2026-01-11 (pendências do Conselho)
> Aprovado pelo Conselho Técnico
