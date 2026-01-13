#!/usr/bin/env python3
"""
ClickUp MCP Server - Complete API Integration
=============================================
Um servidor MCP completo para integração com o ClickUp, permitindo:
- CRUD completo de Tasks (criar, ler, editar, deletar, mover, copiar)
- Gerenciamento de Lists, Folders e Spaces
- Busca avançada com filtros e paginação
- Todas as informações incluindo datas de criação/atualização
- Extração automática de Tipo e Subtipo do nome das tasks
- Identificação de Cliente (List) e Plano (Folder)

Autor: Helper Consultoria
Versão: 2.5.0
"""

import os
import re
import json
import httpx
import asyncio
import contextvars
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from collections import defaultdict
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from cachetools import TTLCache
from loguru import logger
import sys

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

API_BASE_URL = "https://api.clickup.com/api/v2"
API_V3_BASE_URL = "https://api.clickup.com/api/v3"
API_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "")
DEFAULT_TIMEOUT = float(os.environ.get("DEFAULT_TIMEOUT", "30.0"))
CACHE_TTL_STRUCTURE = int(os.environ.get("CACHE_TTL_STRUCTURE", "300"))  # 5 min para estrutura
CACHE_TTL_TASKS = int(os.environ.get("CACHE_TTL_TASKS", "60"))  # 1 min para tasks
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Rate limiting
RATE_LIMIT_REQUESTS = 100  # requests por janela
RATE_LIMIT_WINDOW = 60  # janela em segundos

# Modo operacional (Sprint 5)
READ_ONLY_MODE = os.environ.get("READ_ONLY_MODE", "false").lower() == "true"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Remove default logger
logger.remove()

# Configuração de log em arquivo (opcional)
LOG_FILE = os.environ.get("LOG_FILE", "")

# Add stderr logger with custom format (para debug durante desenvolvimento)
logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    format="<level>{level: <8}</level> | [{extra[correlation_id]}] <cyan>{function}</cyan>:<cyan>{line}</cyan> - {message}",
    colorize=True
)

# Add file logger with rotation (se LOG_FILE configurado)
if LOG_FILE:
    logger.add(
        LOG_FILE,
        level=LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | [{extra[correlation_id]}] {function}:{line} - {message}",
        rotation="10 MB",      # Rotaciona quando arquivo atinge 10MB
        retention="7 days",    # Mantém logs por 7 dias
        compression="gz",      # Comprime arquivos antigos
        serialize=False,       # Formato texto (não JSON)
        enqueue=True           # Thread-safe
    )

# ============================================================================
# CORRELATION ID
# ============================================================================

# Variável de contexto para correlation ID
_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    'correlation_id',
    default='no-cid'
)


def get_correlation_id() -> str:
    """Retorna o correlation ID atual."""
    return _correlation_id.get()


def set_new_correlation_id() -> str:
    """Gera e define um novo correlation ID."""
    new_id = str(uuid.uuid4())[:8]  # 8 chars é suficiente
    _correlation_id.set(new_id)
    return new_id


# Configura logger para incluir correlation_id automaticamente
logger = logger.bind(correlation_id=get_correlation_id)

# ============================================================================
# MÉTRICAS COM LATÊNCIA
# ============================================================================

import statistics
from time import perf_counter
from contextlib import contextmanager


class Metrics:
    """
    Métricas completas para diagnóstico e observabilidade.

    Inclui contadores, taxas e métricas de latência (p50, p95, p99).
    """

    def __init__(self, max_latency_samples: int = 1000):
        """
        Inicializa métricas.

        Args:
            max_latency_samples: Máximo de amostras de latência a manter (para memória)
        """
        self.tool_calls: Dict[str, int] = defaultdict(int)
        self.tool_errors: Dict[str, int] = defaultdict(int)
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.api_calls: int = 0
        self.retries: int = 0
        self._max_samples = max_latency_samples
        self._latencies: List[float] = []  # em milissegundos
        self._tool_latencies: Dict[str, List[float]] = defaultdict(list)

    def record_tool_call(self, tool_name: str) -> None:
        """Registra chamada de tool."""
        self.tool_calls[tool_name] += 1

    def record_tool_error(self, tool_name: str) -> None:
        """Registra erro em tool."""
        self.tool_errors[tool_name] += 1

    def record_cache_hit(self) -> None:
        """Registra cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Registra cache miss."""
        self.cache_misses += 1

    def record_api_call(self) -> None:
        """Registra chamada à API."""
        self.api_calls += 1

    def record_retry(self) -> None:
        """Registra retry."""
        self.retries += 1

    def record_latency(self, latency_ms: float, tool_name: Optional[str] = None) -> None:
        """
        Registra latência de uma operação.

        Args:
            latency_ms: Latência em milissegundos
            tool_name: Nome da tool (opcional, para métricas por tool)
        """
        # Mantém apenas as últimas N amostras
        if len(self._latencies) >= self._max_samples:
            self._latencies.pop(0)
        self._latencies.append(latency_ms)

        if tool_name:
            tool_latencies = self._tool_latencies[tool_name]
            if len(tool_latencies) >= self._max_samples // 10:  # Menos amostras por tool
                tool_latencies.pop(0)
            tool_latencies.append(latency_ms)

    @contextmanager
    def measure_latency(self, tool_name: Optional[str] = None):
        """
        Context manager para medir latência automaticamente.

        Usage:
            with _metrics.measure_latency("get_tasks"):
                result = await get_tasks(params)
        """
        start = perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (perf_counter() - start) * 1000
            self.record_latency(elapsed_ms, tool_name)

    def _calculate_percentiles(self, data: List[float]) -> Dict[str, float]:
        """Calcula percentis de latência."""
        if not data:
            return {"p50": 0, "p95": 0, "p99": 0, "avg": 0, "min": 0, "max": 0}

        sorted_data = sorted(data)
        n = len(sorted_data)

        return {
            "p50": sorted_data[int(n * 0.50)] if n > 0 else 0,
            "p95": sorted_data[int(n * 0.95)] if n > 1 else sorted_data[-1],
            "p99": sorted_data[int(n * 0.99)] if n > 1 else sorted_data[-1],
            "avg": statistics.mean(sorted_data),
            "min": sorted_data[0],
            "max": sorted_data[-1],
            "samples": n
        }

    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo completo das métricas."""
        summary = {
            "tool_calls": dict(self.tool_calls),
            "tool_errors": dict(self.tool_errors),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": (
                self.cache_hits / (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0 else 0
            ),
            "api_calls": self.api_calls,
            "retries": self.retries,
            "latency_ms": self._calculate_percentiles(self._latencies)
        }

        # Latência por tool (top 5 mais chamadas)
        if self._tool_latencies:
            top_tools = sorted(
                self.tool_calls.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            summary["latency_by_tool"] = {
                tool: self._calculate_percentiles(self._tool_latencies.get(tool, []))
                for tool, _ in top_tools
                if tool in self._tool_latencies
            }

        return summary


# Instância global de métricas
_metrics = Metrics()

# ============================================================================
# VALIDAÇÃO DE CONFIGURAÇÃO
# ============================================================================

# Flag para permitir startup sem token (útil para testes)
# Detecta automaticamente se está rodando em pytest
_PYTEST_RUNNING = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
ALLOW_MISSING_TOKEN = os.environ.get("ALLOW_MISSING_TOKEN", "false").lower() == "true" or _PYTEST_RUNNING


def validate_config() -> None:
    """
    Valida configuração no startup. Fail-fast para variáveis obrigatórias.

    Raises:
        EnvironmentError: Se variável obrigatória não está configurada

    Note:
        Configure ALLOW_MISSING_TOKEN=true para testes sem token real.
    """
    required = ["CLICKUP_API_TOKEN"]
    optional = ["DEFAULT_TIMEOUT", "CACHE_TTL_STRUCTURE", "CACHE_TTL_TASKS", "LOG_LEVEL", "READ_ONLY_MODE", "ALLOW_MISSING_TOKEN", "LOG_FILE"]

    # Fail-fast para obrigatórias
    missing = []
    for var in required:
        if not os.environ.get(var):
            missing.append(var)

    if missing and not ALLOW_MISSING_TOKEN:
        error_msg = f"Variáveis de ambiente obrigatórias não configuradas: {', '.join(missing)}"
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
    elif missing:
        logger.warning(f"Variáveis não configuradas (permitido por ALLOW_MISSING_TOKEN): {', '.join(missing)}")

    # Warning para desconhecidas (possível typo)
    env_vars = {k for k in os.environ.keys() if k.startswith("CLICKUP_") or k in optional}
    known_vars = set(required + optional + ["CLICKUP_API_TOKEN"])
    unknown = env_vars - known_vars
    for var in unknown:
        logger.warning(f"Variável desconhecida ignorada (possível typo?): {var}")

    # Log do modo operacional
    mode = "READ_ONLY" if READ_ONLY_MODE else "READ_WRITE"
    logger.info(f"Configuração validada | Modo: {mode}")


# Validar no startup
validate_config()

# Inicializa o servidor MCP
mcp = FastMCP("clickup_mcp")

# ============================================================================
# CACHE
# ============================================================================

# Cache para estrutura (spaces, folders, lists) - TTL maior
_structure_cache: TTLCache = TTLCache(maxsize=100, ttl=CACHE_TTL_STRUCTURE)

# Cache para tasks - TTL menor
_tasks_cache: TTLCache = TTLCache(maxsize=50, ttl=CACHE_TTL_TASKS)


def cache_key(endpoint: str, params: Optional[Dict] = None) -> str:
    """Gera chave de cache única para endpoint + params."""
    params_str = json.dumps(params, sort_keys=True) if params else ""
    return f"{endpoint}:{params_str}"


def get_cached(endpoint: str, params: Optional[Dict] = None, cache_type: str = "structure") -> Optional[Dict]:
    """Busca valor no cache apropriado."""
    key = cache_key(endpoint, params)
    cache = _structure_cache if cache_type == "structure" else _tasks_cache
    result = cache.get(key)
    if result:
        _metrics.record_cache_hit()
        logger.debug(f"Cache HIT: {endpoint}")
    else:
        _metrics.record_cache_miss()
    return result


def set_cached(endpoint: str, data: Dict, params: Optional[Dict] = None, cache_type: str = "structure") -> None:
    """Armazena valor no cache apropriado."""
    key = cache_key(endpoint, params)
    cache = _structure_cache if cache_type == "structure" else _tasks_cache
    cache[key] = data
    logger.debug(f"Cache SET: {endpoint}")


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """Rate limiter simples baseado em janela deslizante."""

    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Aguarda até que seja seguro fazer uma requisição."""
        async with self._lock:
            now = asyncio.get_event_loop().time()

            # Remove requests fora da janela
            self.requests = [t for t in self.requests if now - t < self.window_seconds]

            if len(self.requests) >= self.max_requests:
                # Calcula tempo de espera
                oldest = self.requests[0]
                wait_time = self.window_seconds - (now - oldest) + 0.1
                logger.warning(f"Rate limit atingido. Aguardando {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            self.requests.append(now)


# Instância global do rate limiter
_rate_limiter = RateLimiter()

# ============================================================================
# CONNECTION POOLING
# ============================================================================

_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Retorna cliente HTTP com connection pooling."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
    return _http_client

# ============================================================================
# ENUMS E MODELOS BASE
# ============================================================================

class ResponseFormat(str, Enum):
    """Formato de resposta das ferramentas."""
    MARKDOWN = "markdown"
    JSON = "json"

class OrderBy(str, Enum):
    """Opções de ordenação para listagem de tasks."""
    ID = "id"
    CREATED = "created"
    UPDATED = "updated"
    DUE_DATE = "due_date"

class Priority(int, Enum):
    """Níveis de prioridade do ClickUp."""
    URGENT = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class OutputMode(str, Enum):
    """Modo de formatação do output - resolve problema de travamento."""
    COMPACT = "compact"      # 1 linha por item (DEFAULT) - resolve travamento
    DETAILED = "detailed"    # Formato completo (~12 linhas por item)
    JSON = "json"            # Raw JSON para processamento


class OperationMode(str, Enum):
    """Modo de operação do servidor (Sprint 5)."""
    READ_WRITE = "read_write"  # Todas as operações permitidas
    READ_ONLY = "read_only"    # Apenas leitura (segurança)


# ============================================================================
# EXCEÇÕES ESPECÍFICAS
# ============================================================================

class ClickUpError(Exception):
    """Exceção base para erros do ClickUp MCP."""
    pass


class ConfigurationError(ClickUpError):
    """Erro de configuração (variáveis de ambiente, etc)."""
    pass


class ReadOnlyModeError(ClickUpError):
    """Erro quando operação de escrita é bloqueada em modo read-only."""
    pass


class ClickUpAPIError(ClickUpError):
    """Erro retornado pela API do ClickUp."""

    def __init__(self, message: str, status_code: int, endpoint: str, err_code: Optional[str] = None):
        self.status_code = status_code
        self.endpoint = endpoint
        self.err_code = err_code
        super().__init__(f"[{status_code}] {message} (endpoint: {endpoint})")


class RetryableError(ClickUpError):
    """Erro que pode ser retentado (network, timeout, 429, 5xx)."""
    pass


class NonRetryableError(ClickUpError):
    """Erro que não deve ser retentado (4xx exceto 429)."""
    pass


class ValidationError(ClickUpError):
    """Erro de validação de entrada."""
    pass


def check_write_permission(operation: str) -> None:
    """
    Verifica se operações de escrita são permitidas.

    Args:
        operation: Nome da operação sendo executada

    Raises:
        ReadOnlyModeError: Se servidor está em modo read-only
    """
    if READ_ONLY_MODE:
        raise ReadOnlyModeError(
            f"Operação '{operation}' bloqueada: servidor em modo READ_ONLY. "
            f"Para habilitar escrita, configure READ_ONLY_MODE=false"
        )


# ============================================================================
# CLIENTE HTTP
# ============================================================================

def get_headers() -> Dict[str, str]:
    """
    Retorna headers para autenticação na API.

    Returns:
        Dict com headers Authorization e Content-Type

    Raises:
        ConfigurationError: Se CLICKUP_API_TOKEN não está configurado
    """
    if not API_TOKEN:
        raise ConfigurationError(
            "CLICKUP_API_TOKEN não configurado! "
            "Configure a variável de ambiente CLICKUP_API_TOKEN com seu token de API do ClickUp. "
            "Obtenha em: ClickUp → Settings → Apps → API Token"
        )
    return {
        "Authorization": API_TOKEN,
        "Content-Type": "application/json"
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(RetryableError),
    reraise=True
)
async def _make_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict] = None,
    json_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """Faz requisição HTTP com retry automático para erros transientes."""
    try:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data
        )

        # Rate limit (429) - retryable
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning(f"Rate limited (429). Aguardando {retry_after}s")
            await asyncio.sleep(retry_after)
            raise RetryableError(f"Rate limited (429)")

        # Server errors (5xx) - retryable
        if response.status_code >= 500:
            raise RetryableError(f"Server error ({response.status_code})")

        response.raise_for_status()

        if response.status_code == 204:
            return {"success": True}

        return response.json()

    except httpx.TimeoutException:
        _metrics.record_retry()
        logger.warning("Timeout na requisição, retentando...")
        raise RetryableError("Timeout")
    except httpx.ConnectError:
        _metrics.record_retry()
        logger.warning("Erro de conexão, retentando...")
        raise RetryableError("Connection error")
    except httpx.HTTPStatusError as e:
        error_detail = ""
        try:
            error_detail = e.response.json()
        except (json.JSONDecodeError, ValueError):
            error_detail = e.response.text
        raise NonRetryableError(f"Erro API ({e.response.status_code}): {error_detail}")


async def api_request(
    method: str,
    endpoint: str,
    params: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    use_cache: bool = True,
    cache_type: str = "structure",
    api_version: str = "v2"
) -> Dict[str, Any]:
    """
    Faz requisição à API do ClickUp com retry, cache e rate limiting.

    Args:
        method: Método HTTP (GET, POST, PUT, DELETE)
        endpoint: Endpoint da API (sem base URL)
        params: Query parameters
        json_data: Dados JSON para POST/PUT
        use_cache: Se deve usar cache (apenas para GET)
        cache_type: Tipo de cache ("structure" ou "tasks")
        api_version: Versão da API ("v2" ou "v3")

    Returns:
        Resposta da API como dicionário

    Raises:
        Exception: Em caso de erro na API
    """
    # Cache apenas para GET
    if method == "GET" and use_cache:
        cached = get_cached(endpoint, params, cache_type)
        if cached is not None:
            return cached

    # Rate limiting
    await _rate_limiter.acquire()

    # Seleciona base URL conforme versão da API
    base_url = API_V3_BASE_URL if api_version == "v3" else API_BASE_URL
    url = f"{base_url}{endpoint}"
    client = await get_http_client()

    try:
        _metrics.record_api_call()
        logger.debug(f"API {method} {endpoint}")
        result = await _make_request(client, method, url, get_headers(), params, json_data)

        # Armazena no cache (apenas GET)
        if method == "GET" and use_cache:
            set_cached(endpoint, result, params, cache_type)

        return result

    except RetryableError as e:
        raise Exception(f"Erro após 3 tentativas: {str(e)}")
    except NonRetryableError as e:
        raise Exception(str(e))
    except Exception as e:
        raise Exception(f"Erro inesperado: {str(e)}")

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def sanitize_output(text: str) -> str:
    """
    Sanitiza texto de output para prevenir injection.

    Remove/escapa caracteres perigosos que podem causar problemas
    em clientes MCP ou sistemas downstream.

    Args:
        text: Texto a sanitizar

    Returns:
        Texto sanitizado
    """
    if not isinstance(text, str):
        text = str(text)

    # Remove caracteres de controle (exceto newline e tab)
    sanitized = ''.join(
        char for char in text
        if char in '\n\t' or (ord(char) >= 32 and ord(char) != 127)
    )

    # Limita tamanho para evitar DoS
    max_length = 100000  # 100KB
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "\n\n[... output truncado ...]"

    return sanitized


def sanitize_dict_values(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitiza valores string em um dicionário recursivamente.

    Args:
        d: Dicionário a sanitizar

    Returns:
        Dicionário com valores sanitizados
    """
    result = {}
    for key, value in d.items():
        if isinstance(value, str):
            result[key] = sanitize_output(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict_values(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict_values(item) if isinstance(item, dict)
                else sanitize_output(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def format_timestamp(ts: Optional[int]) -> Optional[str]:
    """
    Converte timestamp em milissegundos para string legível.

    Args:
        ts: Timestamp em milissegundos

    Returns:
        String formatada YYYY-MM-DD HH:MM:SS ou None
    """
    if ts is None:
        return None
    try:
        dt = datetime.fromtimestamp(int(ts) / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return str(ts)

def format_task_markdown(task: Dict) -> str:
    """Formata uma task em Markdown com Tipo, Subtipo e hierarquia completa."""
    task_name = task.get('name', 'Sem nome')
    lines = []
    lines.append(f"## {task_name}")
    lines.append(f"- **ID:** {task.get('id', 'N/A')}")
    lines.append(f"- **Status:** {task.get('status', {}).get('status', 'N/A')}")
    lines.append(f"- **URL:** {task.get('url', 'N/A')}")
    
    # Extrai Tipo e Subtipo do nome
    tipo, subtipo = extract_tipo_subtipo(task_name)
    if tipo:
        lines.append(f"- **Tipo:** {tipo}")
    if subtipo:
        lines.append(f"- **Subtipo:** {subtipo}")
    
    # Datas
    date_created = format_timestamp(task.get('date_created'))
    date_updated = format_timestamp(task.get('date_updated'))
    date_closed = format_timestamp(task.get('date_closed'))
    due_date = format_timestamp(task.get('due_date'))
    start_date = format_timestamp(task.get('start_date'))
    
    if date_created:
        lines.append(f"- **Criado em:** {date_created}")
    if date_updated:
        lines.append(f"- **Modificado em:** {date_updated}")
    if due_date:
        lines.append(f"- **Prazo:** {due_date}")
    if start_date:
        lines.append(f"- **Início:** {start_date}")
    if date_closed:
        lines.append(f"- **Fechado em:** {date_closed}")
    
    # Prioridade
    priority = task.get('priority')
    if priority:
        lines.append(f"- **Prioridade:** {priority.get('priority', 'N/A')}")
    
    # Assignees
    assignees = task.get('assignees', [])
    if assignees:
        names = [a.get('username', a.get('email', 'N/A')) for a in assignees]
        lines.append(f"- **Responsáveis:** {', '.join(names)}")
    
    # Tags
    tags = task.get('tags', [])
    if tags:
        tag_names = [t.get('name', '') for t in tags]
        lines.append(f"- **Tags:** {', '.join(tag_names)}")
    
    # Cliente (List) / Plano (Folder) / Space
    list_info = task.get('list', {})
    folder_info = task.get('folder', {})
    space_info = task.get('space', {})
    
    if list_info:
        list_name = list_info.get('name', 'N/A') if isinstance(list_info, dict) else list_info
        lines.append(f"- **Cliente:** {list_name}")
    if folder_info:
        folder_name = folder_info.get('name') if isinstance(folder_info, dict) else None
        if folder_name:
            lines.append(f"- **Plano:** {folder_name}")
    if space_info:
        space_name = space_info.get('name', 'N/A') if isinstance(space_info, dict) else space_info
        lines.append(f"- **Space:** {space_name}")
    
    # Descrição
    description = task.get('description', '')
    if description:
        lines.append(f"\n### Descrição\n{description}")
    
    # Time estimate e tracked
    time_estimate = task.get('time_estimate')
    time_spent = task.get('time_spent')
    if time_estimate:
        lines.append(f"- **Tempo estimado:** {time_estimate // 60000} min")
    if time_spent:
        lines.append(f"- **Tempo gasto:** {time_spent // 60000} min")
    
    return "\n".join(lines)

def extract_tipo_subtipo(task_name: str) -> tuple:
    """
    Extrai Tipo e Subtipo do nome da task.
    
    Padrão esperado: "Tipo - Subtipo" ou "Tipo - Subtipo - Detalhes"
    Exemplos:
        "Notificação Extrajudicial - Pirataria" → ("Notificação Extrajudicial", "Pirataria")
        "Análise de documento - Empresarial" → ("Análise de documento", "Empresarial")
        "Pedido de Registro de Marca - INPI - Nome da Marca" → ("Pedido de Registro de Marca", "INPI")
        "Acordo de Sócios / Quotistas / Cotistas" → ("Acordo de Sócios / Quotistas / Cotistas", None)
    
    Returns:
        Tuple (tipo, subtipo) onde subtipo pode ser None
    """
    if not task_name:
        return (None, None)
    
    # Remove prefixos numéricos como "3 - " ou "15 - "
    clean_name = re.sub(r'^\d+\s*-\s*', '', task_name.strip())
    
    # Divide pelo separador " - "
    parts = clean_name.split(' - ')
    
    if len(parts) >= 2:
        tipo = parts[0].strip()
        subtipo = parts[1].strip()
        return (tipo, subtipo)
    else:
        # Não tem subtipo, o nome inteiro é o tipo
        return (clean_name.strip(), None)


def format_tasks_compact(tasks: List[Dict], total: int = 0, page: int = 0, limit: int = 25) -> str:
    """
    Formata tasks em modo compacto: 1 linha por task.
    RESOLVE O PROBLEMA DE TRAVAMENTO do Claude Desktop.

    Formato: {i}. [{status}] {nome} | {prazo} | `{id}`
    """
    if not tasks:
        return "Nenhuma task encontrada."

    lines = [f"**{len(tasks)} tasks** (página {page}):\n"]

    for i, task in enumerate(tasks, 1):
        status = task.get('status', {}).get('status', '?')[:12]
        name = task.get('name', 'Sem nome')[:60]
        due = format_timestamp(task.get('due_date'))
        due_str = due[:10] if due else '-'  # Só a data, sem hora
        task_id = task.get('id', '')

        lines.append(f"{i}. [{status}] {name} | {due_str} | `{task_id}`")

    # Aviso de paginação
    if len(tasks) >= limit:
        lines.append(f"\n_Mostrando {limit} de {total or '?'}. Use `page={page + 1}` para mais._")

    return "\n".join(lines)


def format_tasks_detailed(tasks: List[Dict], total: int = 0, page: int = 0, limit: int = 25) -> str:
    """
    Formata lista de tasks em modo detalhado (~12 linhas por task).
    Equivalente ao formato anterior (format_tasks_list_markdown).
    """
    if not tasks:
        return "Nenhuma task encontrada."

    lines = []
    if total:
        lines.append(f"**Tasks retornadas:** {len(tasks)} de {total}")
        lines.append("")

    for i, task in enumerate(tasks, 1):
        task_name = task.get('name', 'Sem nome')
        date_created = format_timestamp(task.get('date_created'))
        date_updated = format_timestamp(task.get('date_updated'))
        status = task.get('status', {}).get('status', 'N/A')

        # Extrai Tipo e Subtipo do nome
        tipo, subtipo = extract_tipo_subtipo(task_name)

        # Informações de hierarquia
        list_info = task.get('list', {})
        folder_info = task.get('folder', {})

        lines.append(f"### {i}. {task_name}")
        lines.append(f"- ID: `{task.get('id')}`")
        lines.append(f"- Status: {status}")

        # Tipo e Subtipo
        if tipo:
            lines.append(f"- Tipo: {tipo}")
        if subtipo:
            lines.append(f"- Subtipo: {subtipo}")

        # Cliente (List) e Plano (Folder)
        if list_info:
            list_name = list_info.get('name') if isinstance(list_info, dict) else list_info
            lines.append(f"- Cliente: {list_name}")
        if folder_info:
            folder_name = folder_info.get('name') if isinstance(folder_info, dict) else None
            if folder_name:
                lines.append(f"- Plano: {folder_name}")

        # Datas
        lines.append(f"- Criado: {date_created or 'N/A'}")
        if date_updated:
            lines.append(f"- Modificado: {date_updated}")

        due_date = format_timestamp(task.get('due_date'))
        if due_date:
            lines.append(f"- Prazo: {due_date}")

        # Responsáveis
        assignees = task.get('assignees', [])
        if assignees:
            names = [a.get('username', 'N/A') for a in assignees]
            lines.append(f"- Responsáveis: {', '.join(names)}")

        lines.append(f"- URL: {task.get('url', 'N/A')}")
        lines.append("")

    # Aviso de paginação
    if len(tasks) >= limit:
        lines.append(f"_Mostrando {limit} de {total or '?'}. Use `page={page + 1}` para mais._")

    return "\n".join(lines)


# Alias para compatibilidade
def format_tasks_list_markdown(tasks: List[Dict], total: int = 0, page: int = 0) -> str:
    """Alias para format_tasks_detailed (compatibilidade)."""
    return format_tasks_detailed(tasks, total, page)


# ============================================================================
# FUZZY SEARCH (Sprint 5) - Usando rapidfuzz para performance O(n)
# ============================================================================

from rapidfuzz import fuzz, process


def fuzzy_ratio(s1: str, s2: str) -> float:
    """
    Calcula similaridade entre duas strings (0.0 a 1.0).

    Usa rapidfuzz para performance otimizada O(n) com SIMD.

    Args:
        s1: Primeira string
        s2: Segunda string

    Returns:
        Score de similaridade entre 0.0 e 1.0
    """
    if not s1 or not s2:
        return 0.0
    # rapidfuzz retorna 0-100, convertemos para 0-1
    return fuzz.ratio(s1.lower(), s2.lower()) / 100.0


def fuzzy_search_tasks(tasks: List[Dict], query: str, threshold: float = 0.4) -> List[Dict]:
    """
    Busca fuzzy em tasks por nome usando rapidfuzz.

    Usa process.extract para busca otimizada em lote.
    Performance: O(n) com SIMD, escala para milhares de tasks.

    Args:
        tasks: Lista de tasks para buscar
        query: Texto de busca
        threshold: Limiar mínimo de similaridade (0.0 a 1.0)

    Returns:
        Tasks ordenadas por relevância (maior similaridade primeiro)
    """
    if not tasks or not query:
        return []

    # Cria mapeamento nome -> task para lookup rápido
    task_map: Dict[str, Dict] = {}
    names: List[str] = []

    for task in tasks:
        name = task.get('name', '')
        if name:
            # Usa ID como sufixo para garantir unicidade
            key = f"{name}||{task.get('id', '')}"
            task_map[key] = task
            names.append(key)

    if not names:
        return []

    # Busca em lote com rapidfuzz - muito mais rápido
    # score_cutoff converte threshold de 0-1 para 0-100
    matches = process.extract(
        query,
        names,
        scorer=fuzz.WRatio,  # Weighted Ratio - melhor para buscas parciais
        score_cutoff=threshold * 100,
        limit=None  # Retorna todos acima do threshold
    )

    # Converte resultados
    results = []
    for match_name, score, _ in matches:
        task = task_map.get(match_name)
        if task:
            results.append(task)

    return results


# ============================================================================
# MODELOS DE INPUT
# ============================================================================

class GetWorkspacesInput(BaseModel):
    """Input para listar workspaces."""
    model_config = ConfigDict(str_strip_whitespace=True)
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )

class GetSpacesInput(BaseModel):
    """Input para listar spaces de um workspace."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)
    archived: bool = Field(default=False, description="Incluir spaces arquivados")
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )

class GetFoldersInput(BaseModel):
    """Input para listar folders de um space."""
    model_config = ConfigDict(str_strip_whitespace=True)
    space_id: str = Field(..., description="ID do space", min_length=1)
    archived: bool = Field(default=False, description="Incluir folders arquivados")
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )

class GetListsInput(BaseModel):
    """Input para listar lists de um folder."""
    model_config = ConfigDict(str_strip_whitespace=True)
    folder_id: str = Field(..., description="ID do folder", min_length=1)
    archived: bool = Field(default=False, description="Incluir lists arquivadas")
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )

class GetFolderlessListsInput(BaseModel):
    """Input para listar lists sem folder (diretamente no space)."""
    model_config = ConfigDict(str_strip_whitespace=True)
    space_id: str = Field(..., description="ID do space", min_length=1)
    archived: bool = Field(default=False, description="Incluir lists arquivadas")
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )

class GetTasksInput(BaseModel):
    """Input para listar tasks de uma list."""
    model_config = ConfigDict(str_strip_whitespace=True)
    list_id: str = Field(..., description="ID da list", min_length=1)
    archived: bool = Field(default=False, description="Incluir tasks arquivadas")
    include_closed: bool = Field(default=True, description="Incluir tasks fechadas")
    page: int = Field(default=0, description="Página (começa em 0)", ge=0)
    limit: int = Field(default=25, ge=1, le=100, description="Máximo de tasks a retornar (1-100)")
    order_by: Optional[OrderBy] = Field(default=None, description="Ordenar por: id, created, updated, due_date")
    reverse: bool = Field(default=False, description="Ordem reversa")
    subtasks: bool = Field(default=False, description="Incluir subtasks")
    statuses: Optional[List[str]] = Field(default=None, description="Filtrar por status (lista)")
    assignees: Optional[List[str]] = Field(default=None, description="Filtrar por assignee IDs")
    due_date_gt: Optional[int] = Field(default=None, description="Due date maior que (timestamp ms)")
    due_date_lt: Optional[int] = Field(default=None, description="Due date menor que (timestamp ms)")
    date_created_gt: Optional[int] = Field(default=None, description="Criado após (timestamp ms)")
    date_created_lt: Optional[int] = Field(default=None, description="Criado antes (timestamp ms)")
    date_updated_gt: Optional[int] = Field(default=None, description="Atualizado após (timestamp ms)")
    date_updated_lt: Optional[int] = Field(default=None, description="Atualizado antes (timestamp ms)")
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )

class GetFilteredTeamTasksInput(BaseModel):
    """Input para busca filtrada de tasks em todo o workspace."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)
    page: int = Field(default=0, description="Página (começa em 0)", ge=0)
    limit: int = Field(default=25, ge=1, le=100, description="Máximo de tasks a retornar (1-100)")
    order_by: Optional[OrderBy] = Field(default=None, description="Ordenar por: id, created, updated, due_date")
    reverse: bool = Field(default=False, description="Ordem reversa")
    subtasks: bool = Field(default=False, description="Incluir subtasks")
    space_ids: Optional[List[str]] = Field(default=None, description="Filtrar por space IDs")
    project_ids: Optional[List[str]] = Field(default=None, description="Filtrar por folder IDs")
    list_ids: Optional[List[str]] = Field(default=None, description="Filtrar por list IDs")
    statuses: Optional[List[str]] = Field(default=None, description="Filtrar por status")
    include_closed: bool = Field(default=True, description="Incluir tasks fechadas")
    assignees: Optional[List[str]] = Field(default=None, description="Filtrar por assignee IDs")
    due_date_gt: Optional[int] = Field(default=None, description="Due date maior que (timestamp ms)")
    due_date_lt: Optional[int] = Field(default=None, description="Due date menor que (timestamp ms)")
    date_created_gt: Optional[int] = Field(default=None, description="Criado após (timestamp ms)")
    date_created_lt: Optional[int] = Field(default=None, description="Criado antes (timestamp ms)")
    date_updated_gt: Optional[int] = Field(default=None, description="Atualizado após (timestamp ms)")
    date_updated_lt: Optional[int] = Field(default=None, description="Atualizado antes (timestamp ms)")
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )

class GetTaskInput(BaseModel):
    """Input para buscar uma task específica."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task", min_length=1)
    include_subtasks: bool = Field(default=True, description="Incluir subtasks")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

class CreateTaskInput(BaseModel):
    """Input para criar uma nova task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    list_id: str = Field(..., description="ID da list onde criar a task", min_length=1)
    name: str = Field(..., description="Nome da task", min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, description="Descrição da task")
    assignees: Optional[List[int]] = Field(default=None, description="IDs dos responsáveis")
    tags: Optional[List[str]] = Field(default=None, description="Tags da task")
    status: Optional[str] = Field(default=None, description="Status inicial")
    priority: Optional[int] = Field(default=None, description="Prioridade (1=urgent, 2=high, 3=normal, 4=low)", ge=1, le=4)
    due_date: Optional[int] = Field(default=None, description="Due date (timestamp em ms)")
    due_date_time: bool = Field(default=False, description="Se due_date inclui horário")
    start_date: Optional[int] = Field(default=None, description="Start date (timestamp em ms)")
    start_date_time: bool = Field(default=False, description="Se start_date inclui horário")
    time_estimate: Optional[int] = Field(default=None, description="Tempo estimado em ms")
    notify_all: bool = Field(default=True, description="Notificar todos os responsáveis")
    parent: Optional[str] = Field(default=None, description="ID da task pai (para subtask)")
    custom_fields: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Lista de custom fields: [{'id': 'field_id', 'value': valor}]. Formatos de valor por tipo: text='string', number=123, dropdown='option_id', checkbox=true/false, date=timestamp_ms, labels=['id1','id2'], users={'add':['id'],'rem':['id']}"
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

class UpdateTaskInput(BaseModel):
    """Input para atualizar uma task existente."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task a atualizar", min_length=1)
    name: Optional[str] = Field(default=None, description="Novo nome da task")
    description: Optional[str] = Field(default=None, description="Nova descrição")
    status: Optional[str] = Field(default=None, description="Novo status")
    priority: Optional[int] = Field(default=None, description="Nova prioridade (1-4)", ge=1, le=4)
    due_date: Optional[int] = Field(default=None, description="Novo due date (timestamp ms)")
    due_date_time: bool = Field(default=False, description="Se due_date inclui horário")
    start_date: Optional[int] = Field(default=None, description="Novo start date (timestamp ms)")
    start_date_time: bool = Field(default=False, description="Se start_date inclui horário")
    time_estimate: Optional[int] = Field(default=None, description="Novo tempo estimado (ms)")
    assignees_add: Optional[List[int]] = Field(default=None, description="IDs de responsáveis a adicionar")
    assignees_remove: Optional[List[int]] = Field(default=None, description="IDs de responsáveis a remover")
    archived: Optional[bool] = Field(default=None, description="Arquivar/desarquivar")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

class DeleteTaskInput(BaseModel):
    """Input para deletar uma task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task a deletar", min_length=1)

class MoveTaskInput(BaseModel):
    """Input para mover uma task para outra list."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task a mover", min_length=1)
    list_id: str = Field(..., description="ID da list de destino", min_length=1)

class DuplicateTaskInput(BaseModel):
    """Input para duplicar uma task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task a duplicar", min_length=1)
    list_id: str = Field(..., description="ID da list de destino", min_length=1)
    name: Optional[str] = Field(default=None, description="Nome da cópia (opcional)")

class CreateListInput(BaseModel):
    """Input para criar uma nova list."""
    model_config = ConfigDict(str_strip_whitespace=True)
    folder_id: Optional[str] = Field(default=None, description="ID do folder (se dentro de folder)")
    space_id: Optional[str] = Field(default=None, description="ID do space (se folderless)")
    name: str = Field(..., description="Nome da list", min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, description="Descrição da list")
    due_date: Optional[int] = Field(default=None, description="Due date (timestamp ms)")
    priority: Optional[int] = Field(default=None, description="Prioridade (1-4)")
    status: Optional[str] = Field(default=None, description="Status da list")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

class UpdateListInput(BaseModel):
    """Input para atualizar uma list."""
    model_config = ConfigDict(str_strip_whitespace=True)
    list_id: str = Field(..., description="ID da list a atualizar", min_length=1)
    name: Optional[str] = Field(default=None, description="Novo nome")
    content: Optional[str] = Field(default=None, description="Nova descrição")
    due_date: Optional[int] = Field(default=None, description="Novo due date")
    priority: Optional[int] = Field(default=None, description="Nova prioridade")
    unset_status: bool = Field(default=False, description="Remover status")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

class DeleteListInput(BaseModel):
    """Input para deletar uma list."""
    model_config = ConfigDict(str_strip_whitespace=True)
    list_id: str = Field(..., description="ID da list a deletar", min_length=1)

class CreateFolderInput(BaseModel):
    """Input para criar um novo folder."""
    model_config = ConfigDict(str_strip_whitespace=True)
    space_id: str = Field(..., description="ID do space", min_length=1)
    name: str = Field(..., description="Nome do folder", min_length=1, max_length=200)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

class UpdateFolderInput(BaseModel):
    """Input para atualizar um folder."""
    model_config = ConfigDict(str_strip_whitespace=True)
    folder_id: str = Field(..., description="ID do folder a atualizar", min_length=1)
    name: str = Field(..., description="Novo nome do folder", min_length=1, max_length=200)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

class DeleteFolderInput(BaseModel):
    """Input para deletar um folder."""
    model_config = ConfigDict(str_strip_whitespace=True)
    folder_id: str = Field(..., description="ID do folder a deletar", min_length=1)

class SearchTasksInput(BaseModel):
    """Input para busca de tasks por texto."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)
    query: str = Field(..., description="Texto para buscar", min_length=1)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class FuzzySearchTasksInput(BaseModel):
    """Input para busca fuzzy de tasks (Sprint 5)."""
    model_config = ConfigDict(str_strip_whitespace=True)
    list_id: str = Field(..., description="ID da list onde buscar", min_length=1)
    query: str = Field(..., description="Texto aproximado para buscar (ex: 'relatorio' encontra 'Relatório Mensal')", min_length=1)
    threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Limiar de similaridade (0.0-1.0). Menor = mais resultados, maior = mais preciso"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Máximo de resultados")
    include_closed: bool = Field(default=False, description="Incluir tasks fechadas")
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )

class GetTaskCommentsInput(BaseModel):
    """Input para buscar comentários de uma task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task", min_length=1)
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )

class CreateTaskCommentInput(BaseModel):
    """Input para criar comentário em uma task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task", min_length=1)
    comment_text: str = Field(..., description="Texto do comentário", min_length=1)
    assignee: Optional[int] = Field(default=None, description="ID do usuário a mencionar")
    notify_all: bool = Field(default=True, description="Notificar todos")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

class GetTimeEntriesInput(BaseModel):
    """Input para buscar time entries."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)
    start_date: Optional[int] = Field(default=None, description="Data início (timestamp ms)")
    end_date: Optional[int] = Field(default=None, description="Data fim (timestamp ms)")
    assignee: Optional[int] = Field(default=None, description="Filtrar por usuário")
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )

class GetMembersInput(BaseModel):
    """Input para buscar membros do workspace."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )


class CreateTimeEntryInput(BaseModel):
    """Input para criar time entry (Sprint 5)."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)
    task_id: Optional[str] = Field(default=None, description="ID da task (opcional)")
    description: Optional[str] = Field(default=None, description="Descrição do trabalho realizado")
    start: int = Field(..., description="Timestamp de início (ms)")
    duration: int = Field(..., description="Duração em milissegundos", ge=0)
    billable: bool = Field(default=False, description="Marcar como hora faturável")
    tags: Optional[List[str]] = Field(default=None, description="Tags para categorizar")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetBillableReportInput(BaseModel):
    """Input para relatório de horas faturáveis (Sprint 5)."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)
    start_date: int = Field(..., description="Data início (timestamp ms)")
    end_date: int = Field(..., description="Data fim (timestamp ms)")
    assignee: Optional[int] = Field(default=None, description="Filtrar por usuário")
    output_mode: OutputMode = Field(
        default=OutputMode.DETAILED,
        description="Modo de output: compact (resumo), detailed (completo), json (raw)"
    )


# ============================================================================
# TOOLS - WORKSPACES
# ============================================================================

@mcp.tool(
    name="clickup_get_workspaces",
    annotations={
        "title": "Listar Workspaces",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_workspaces(params: GetWorkspacesInput) -> str:
    """
    Lista todos os workspaces (teams) que você tem acesso.

    Modos de output: compact (default), detailed, json.
    """
    try:
        data = await api_request("GET", "/team")
        teams = data.get("teams", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(teams)} workspaces:**\n"]
            for i, team in enumerate(teams, 1):
                name = team.get('name', 'Sem nome')
                members = len(team.get('members', []))
                lines.append(f"{i}. {name} | {members} membros | `{team.get('id')}`")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Workspaces\n"]
        for team in teams:
            lines.append(f"## {team.get('name', 'Sem nome')}")
            lines.append(f"- **ID:** `{team.get('id')}`")
            members = team.get('members', [])
            lines.append(f"- **Membros:** {len(members)}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar workspaces: {str(e)}"

# ============================================================================
# TOOLS - SPACES
# ============================================================================

@mcp.tool(
    name="clickup_get_spaces",
    annotations={
        "title": "Listar Spaces",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_spaces(params: GetSpacesInput) -> str:
    """
    Lista todos os spaces de um workspace.

    Modos de output: compact (default), detailed, json.
    """
    try:
        query_params = {"archived": str(params.archived).lower()}
        data = await api_request("GET", f"/team/{params.team_id}/space", params=query_params)
        spaces = data.get("spaces", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(spaces)} spaces:**\n"]
            for i, space in enumerate(spaces, 1):
                name = space.get('name', 'Sem nome')
                priv = "privado" if space.get('private') else "público"
                lines.append(f"{i}. {name} | {priv} | `{space.get('id')}`")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Spaces\n"]
        for space in spaces:
            lines.append(f"## {space.get('name', 'Sem nome')}")
            lines.append(f"- **ID:** `{space.get('id')}`")
            lines.append(f"- **Privado:** {'Sim' if space.get('private') else 'Não'}")
            statuses = space.get('statuses', [])
            if statuses:
                status_names = [s.get('status', '') for s in statuses]
                lines.append(f"- **Status disponíveis:** {', '.join(status_names)}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar spaces: {str(e)}"

# ============================================================================
# TOOLS - FOLDERS
# ============================================================================

@mcp.tool(
    name="clickup_get_folders",
    annotations={
        "title": "Listar Folders",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_folders(params: GetFoldersInput) -> str:
    """
    Lista todos os folders de um space.

    Modos de output: compact (default), detailed, json.
    """
    try:
        query_params = {"archived": str(params.archived).lower()}
        data = await api_request("GET", f"/space/{params.space_id}/folder", params=query_params)
        folders = data.get("folders", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(folders)} folders:**\n"]
            for i, folder in enumerate(folders, 1):
                name = folder.get('name', 'Sem nome')
                lists_count = len(folder.get('lists', []))
                lines.append(f"{i}. {name} | {lists_count} lists | `{folder.get('id')}`")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Folders\n"]
        for folder in folders:
            lines.append(f"## {folder.get('name', 'Sem nome')}")
            lines.append(f"- **ID:** `{folder.get('id')}`")
            lists = folder.get('lists', [])
            lines.append(f"- **Lists:** {len(lists)}")
            if lists:
                for lst in lists:
                    lines.append(f"  - {lst.get('name')} (`{lst.get('id')}`)")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar folders: {str(e)}"

@mcp.tool(
    name="clickup_create_folder",
    annotations={
        "title": "Criar Folder",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_folder(params: CreateFolderInput) -> str:
    """
    Cria um novo folder em um space.

    Returns:
        Detalhes do folder criado.
    """
    try:
        check_write_permission("create_folder")
        data = await api_request(
            "POST",
            f"/space/{params.space_id}/folder",
            json_data={"name": params.name}
        )
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        return f"✅ Folder '{data.get('name')}' criado com sucesso!\n- **ID:** `{data.get('id')}`"
    except Exception as e:
        return f"Erro ao criar folder: {str(e)}"

@mcp.tool(
    name="clickup_update_folder",
    annotations={
        "title": "Atualizar Folder",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def update_folder(params: UpdateFolderInput) -> str:
    """
    Atualiza o nome de um folder.

    Returns:
        Detalhes do folder atualizado.
    """
    try:
        check_write_permission("update_folder")
        data = await api_request(
            "PUT",
            f"/folder/{params.folder_id}",
            json_data={"name": params.name}
        )
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        return f"✅ Folder atualizado para '{data.get('name')}'"
    except Exception as e:
        return f"Erro ao atualizar folder: {str(e)}"

@mcp.tool(
    name="clickup_delete_folder",
    annotations={
        "title": "Deletar Folder",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def delete_folder(params: DeleteFolderInput) -> str:
    """
    Deleta um folder. ATENÇÃO: Esta ação é irreversível!

    Returns:
        Confirmação da exclusão.
    """
    try:
        check_write_permission("delete_folder")
        await api_request("DELETE", f"/folder/{params.folder_id}")
        return f"✅ Folder `{params.folder_id}` deletado com sucesso!"
    except Exception as e:
        return f"Erro ao deletar folder: {str(e)}"

# ============================================================================
# TOOLS - LISTS
# ============================================================================

@mcp.tool(
    name="clickup_get_lists",
    annotations={
        "title": "Listar Lists de um Folder",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_lists(params: GetListsInput) -> str:
    """
    Lista todas as lists de um folder.

    Modos de output: compact (default), detailed, json.
    """
    try:
        query_params = {"archived": str(params.archived).lower()}
        data = await api_request("GET", f"/folder/{params.folder_id}/list", params=query_params)
        lists = data.get("lists", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(lists)} lists:**\n"]
            for i, lst in enumerate(lists, 1):
                name = lst.get('name', 'Sem nome')
                tasks = lst.get('task_count', 0)
                lines.append(f"{i}. {name} | {tasks} tasks | `{lst.get('id')}`")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Lists\n"]
        for lst in lists:
            lines.append(f"## {lst.get('name', 'Sem nome')}")
            lines.append(f"- **ID:** `{lst.get('id')}`")
            lines.append(f"- **Tasks:** {lst.get('task_count', 0)}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar lists: {str(e)}"

@mcp.tool(
    name="clickup_get_folderless_lists",
    annotations={
        "title": "Listar Lists sem Folder",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_folderless_lists(params: GetFolderlessListsInput) -> str:
    """
    Lista as lists que estão diretamente no space (sem folder).

    Modos de output: compact (default), detailed, json.
    """
    try:
        query_params = {"archived": str(params.archived).lower()}
        data = await api_request("GET", f"/space/{params.space_id}/list", params=query_params)
        lists = data.get("lists", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(lists)} lists (sem folder):**\n"]
            for i, lst in enumerate(lists, 1):
                name = lst.get('name', 'Sem nome')
                tasks = lst.get('task_count', 0)
                lines.append(f"{i}. {name} | {tasks} tasks | `{lst.get('id')}`")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Lists (sem folder)\n"]
        for lst in lists:
            lines.append(f"## {lst.get('name', 'Sem nome')}")
            lines.append(f"- **ID:** `{lst.get('id')}`")
            lines.append(f"- **Tasks:** {lst.get('task_count', 0)}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar lists: {str(e)}"

@mcp.tool(
    name="clickup_create_list",
    annotations={
        "title": "Criar List",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_list(params: CreateListInput) -> str:
    """
    Cria uma nova list em um folder ou diretamente em um space.

    Returns:
        Detalhes da list criada.
    """
    try:
        check_write_permission("create_list")
        if not params.folder_id and not params.space_id:
            return "Erro: Informe folder_id OU space_id"
        
        json_data = {"name": params.name}
        if params.content:
            json_data["content"] = params.content
        if params.due_date:
            json_data["due_date"] = params.due_date
        if params.priority:
            json_data["priority"] = params.priority
        if params.status:
            json_data["status"] = params.status
        
        if params.folder_id:
            endpoint = f"/folder/{params.folder_id}/list"
        else:
            endpoint = f"/space/{params.space_id}/list"
        
        data = await api_request("POST", endpoint, json_data=json_data)
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        return f"✅ List '{data.get('name')}' criada com sucesso!\n- **ID:** `{data.get('id')}`"
    except Exception as e:
        return f"Erro ao criar list: {str(e)}"

@mcp.tool(
    name="clickup_update_list",
    annotations={
        "title": "Atualizar List",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def update_list(params: UpdateListInput) -> str:
    """
    Atualiza uma list existente.

    Returns:
        Detalhes da list atualizada.
    """
    try:
        check_write_permission("update_list")
        json_data = {}
        if params.name:
            json_data["name"] = params.name
        if params.content:
            json_data["content"] = params.content
        if params.due_date:
            json_data["due_date"] = params.due_date
        if params.priority:
            json_data["priority"] = params.priority
        if params.unset_status:
            json_data["unset_status"] = True
        
        data = await api_request("PUT", f"/list/{params.list_id}", json_data=json_data)
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        return f"✅ List '{data.get('name')}' atualizada com sucesso!"
    except Exception as e:
        return f"Erro ao atualizar list: {str(e)}"

@mcp.tool(
    name="clickup_delete_list",
    annotations={
        "title": "Deletar List",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def delete_list(params: DeleteListInput) -> str:
    """
    Deleta uma list. ATENÇÃO: Esta ação é irreversível!

    Returns:
        Confirmação da exclusão.
    """
    try:
        check_write_permission("delete_list")
        await api_request("DELETE", f"/list/{params.list_id}")
        return f"✅ List `{params.list_id}` deletada com sucesso!"
    except Exception as e:
        return f"Erro ao deletar list: {str(e)}"

# ============================================================================
# TOOLS - TASKS
# ============================================================================

@mcp.tool(
    name="clickup_get_tasks",
    annotations={
        "title": "Listar Tasks de uma List",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_tasks(params: GetTasksInput) -> str:
    """
    Lista as tasks de uma list específica com filtros avançados.

    Modos de output:
    - compact (default): 1 linha por task - resolve travamento
    - detailed: formato completo (~12 linhas por task)
    - json: raw JSON para processamento

    Returns:
        Lista de tasks formatada conforme output_mode.
    """
    try:
        query_params = {
            "archived": str(params.archived).lower(),
            "include_closed": str(params.include_closed).lower(),
            "page": params.page,
            "subtasks": str(params.subtasks).lower()
        }

        if params.order_by:
            query_params["order_by"] = params.order_by.value
        if params.reverse:
            query_params["reverse"] = "true"
        if params.statuses:
            query_params["statuses[]"] = params.statuses
        if params.assignees:
            query_params["assignees[]"] = params.assignees
        if params.due_date_gt:
            query_params["due_date_gt"] = params.due_date_gt
        if params.due_date_lt:
            query_params["due_date_lt"] = params.due_date_lt
        if params.date_created_gt:
            query_params["date_created_gt"] = params.date_created_gt
        if params.date_created_lt:
            query_params["date_created_lt"] = params.date_created_lt
        if params.date_updated_gt:
            query_params["date_updated_gt"] = params.date_updated_gt
        if params.date_updated_lt:
            query_params["date_updated_lt"] = params.date_updated_lt

        data = await api_request("GET", f"/list/{params.list_id}/task", params=query_params)
        tasks = data.get("tasks", [])

        # Aplica limite
        total = len(tasks)
        tasks = tasks[:params.limit]

        # Formata conforme output_mode
        if params.output_mode == OutputMode.JSON:
            return json.dumps({"tasks": tasks, "total": total, "page": params.page}, indent=2, ensure_ascii=False)
        elif params.output_mode == OutputMode.DETAILED:
            return format_tasks_detailed(tasks, total, params.page, params.limit)
        else:  # COMPACT (default)
            return format_tasks_compact(tasks, total, params.page, params.limit)
    except Exception as e:
        return f"Erro ao listar tasks: {str(e)}"


@mcp.tool(
    name="clickup_fuzzy_search_tasks",
    annotations={
        "title": "Busca Fuzzy de Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def fuzzy_search_tasks_tool(params: FuzzySearchTasksInput) -> str:
    """
    Busca tasks por nome com correspondência aproximada (fuzzy).

    Útil quando você não lembra o nome exato da task.
    Exemplos:
    - "relatorio" encontra "Relatório Mensal de Vendas"
    - "config" encontra "Configuração do Sistema"
    - "reunao" encontra "Reunião com Cliente"

    O threshold controla a precisão:
    - 0.3: mais resultados, menos preciso
    - 0.5: balanceado (recomendado)
    - 0.7: menos resultados, mais preciso

    Returns:
        Tasks ordenadas por relevância (mais similar primeiro).
    """
    cid = set_new_correlation_id()
    logger.bind(correlation_id=cid).info(f"Busca fuzzy: query='{params.query}', list={params.list_id}")

    try:
        # Busca todas as tasks da list
        query_params = {
            "archived": "false",
            "include_closed": str(params.include_closed).lower(),
            "subtasks": "true"
        }

        data = await api_request("GET", f"/list/{params.list_id}/task", params=query_params)
        all_tasks = data.get("tasks", [])

        # Aplica busca fuzzy
        matched_tasks = fuzzy_search_tasks(all_tasks, params.query, params.threshold)

        # Aplica limite
        total_matches = len(matched_tasks)
        matched_tasks = matched_tasks[:params.limit]

        logger.bind(correlation_id=cid).info(
            f"Fuzzy search: {total_matches} matches de {len(all_tasks)} tasks"
        )

        if not matched_tasks:
            return f"Nenhuma task encontrada para '{params.query}' (threshold={params.threshold})"

        # Formata conforme output_mode
        if params.output_mode == OutputMode.JSON:
            return json.dumps({
                "query": params.query,
                "threshold": params.threshold,
                "total_matches": total_matches,
                "tasks": matched_tasks
            }, indent=2, ensure_ascii=False)
        elif params.output_mode == OutputMode.DETAILED:
            header = f"**Busca fuzzy:** '{params.query}' ({total_matches} resultados)\n\n"
            return header + format_tasks_detailed(matched_tasks, total_matches, 0, params.limit)
        else:  # COMPACT
            header = f"**Busca fuzzy:** '{params.query}' ({total_matches} resultados)\n"
            return header + format_tasks_compact(matched_tasks, total_matches, 0, params.limit)

    except Exception as e:
        return f"Erro na busca fuzzy: {str(e)}"


@mcp.tool(
    name="clickup_get_filtered_team_tasks",
    annotations={
        "title": "Buscar Tasks do Workspace (Filtros Avançados)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_filtered_team_tasks(params: GetFilteredTeamTasksInput) -> str:
    """
    Busca tasks em todo o workspace com filtros avançados.
    Útil para relatórios e análises que cruzam múltiplas lists.

    Modos de output:
    - compact (default): 1 linha por task - resolve travamento
    - detailed: formato completo (~12 linhas por task)
    - json: raw JSON para processamento

    Returns:
        Lista de tasks formatada conforme output_mode.
    """
    try:
        query_params = {
            "page": params.page,
            "subtasks": str(params.subtasks).lower(),
            "include_closed": str(params.include_closed).lower()
        }

        if params.order_by:
            query_params["order_by"] = params.order_by.value
        if params.reverse:
            query_params["reverse"] = "true"
        if params.space_ids:
            query_params["space_ids[]"] = params.space_ids
        if params.project_ids:
            query_params["project_ids[]"] = params.project_ids
        if params.list_ids:
            query_params["list_ids[]"] = params.list_ids
        if params.statuses:
            query_params["statuses[]"] = params.statuses
        if params.assignees:
            query_params["assignees[]"] = params.assignees
        if params.due_date_gt:
            query_params["due_date_gt"] = params.due_date_gt
        if params.due_date_lt:
            query_params["due_date_lt"] = params.due_date_lt
        if params.date_created_gt:
            query_params["date_created_gt"] = params.date_created_gt
        if params.date_created_lt:
            query_params["date_created_lt"] = params.date_created_lt
        if params.date_updated_gt:
            query_params["date_updated_gt"] = params.date_updated_gt
        if params.date_updated_lt:
            query_params["date_updated_lt"] = params.date_updated_lt

        data = await api_request("GET", f"/team/{params.team_id}/task", params=query_params)
        tasks = data.get("tasks", [])

        # Aplica limite
        total = len(tasks)
        tasks = tasks[:params.limit]

        # Formata conforme output_mode
        if params.output_mode == OutputMode.JSON:
            return json.dumps({"tasks": tasks, "total": total, "page": params.page}, indent=2, ensure_ascii=False)
        elif params.output_mode == OutputMode.DETAILED:
            return format_tasks_detailed(tasks, total, params.page, params.limit)
        else:  # COMPACT (default)
            return format_tasks_compact(tasks, total, params.page, params.limit)
    except Exception as e:
        return f"Erro ao buscar tasks: {str(e)}"

@mcp.tool(
    name="clickup_get_task",
    annotations={
        "title": "Buscar Task Específica",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_task(params: GetTaskInput) -> str:
    """
    Busca detalhes completos de uma task específica pelo ID.
    
    Returns:
        Todos os detalhes da task incluindo datas, assignees, tags, etc.
    """
    try:
        query_params = {"include_subtasks": str(params.include_subtasks).lower()}
        data = await api_request("GET", f"/task/{params.task_id}", params=query_params)
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        return format_task_markdown(data)
    except Exception as e:
        return f"Erro ao buscar task: {str(e)}"

@mcp.tool(
    name="clickup_create_task",
    annotations={
        "title": "Criar Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_task(params: CreateTaskInput) -> str:
    """
    Cria uma nova task em uma list.

    Suporta custom fields ao criar a task. Use clickup_get_custom_fields para
    obter os IDs dos campos disponíveis.

    Returns:
        Detalhes da task criada.
    """
    try:
        check_write_permission("create_task")
        json_data = {
            "name": params.name,
            "notify_all": params.notify_all
        }

        if params.description:
            json_data["description"] = params.description
        if params.assignees:
            json_data["assignees"] = params.assignees
        if params.tags:
            json_data["tags"] = params.tags
        if params.status:
            json_data["status"] = params.status
        if params.priority:
            json_data["priority"] = params.priority
        if params.due_date:
            json_data["due_date"] = params.due_date
            json_data["due_date_time"] = params.due_date_time
        if params.start_date:
            json_data["start_date"] = params.start_date
            json_data["start_date_time"] = params.start_date_time
        if params.time_estimate:
            json_data["time_estimate"] = params.time_estimate
        if params.parent:
            json_data["parent"] = params.parent
        if params.custom_fields:
            json_data["custom_fields"] = params.custom_fields

        data = await api_request("POST", f"/list/{params.list_id}/task", json_data=json_data)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        return f"✅ Task '{data.get('name')}' criada com sucesso!\n- **ID:** `{data.get('id')}`\n- **URL:** {data.get('url')}"
    except Exception as e:
        return f"Erro ao criar task: {str(e)}"

@mcp.tool(
    name="clickup_update_task",
    annotations={
        "title": "Atualizar Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def update_task(params: UpdateTaskInput) -> str:
    """
    Atualiza uma task existente.

    Returns:
        Detalhes da task atualizada.
    """
    try:
        check_write_permission("update_task")
        json_data = {}
        
        if params.name:
            json_data["name"] = params.name
        if params.description is not None:
            json_data["description"] = params.description
        if params.status:
            json_data["status"] = params.status
        if params.priority:
            json_data["priority"] = params.priority
        if params.due_date:
            json_data["due_date"] = params.due_date
            json_data["due_date_time"] = params.due_date_time
        if params.start_date:
            json_data["start_date"] = params.start_date
            json_data["start_date_time"] = params.start_date_time
        if params.time_estimate:
            json_data["time_estimate"] = params.time_estimate
        if params.archived is not None:
            json_data["archived"] = params.archived
        
        # Assignees
        if params.assignees_add or params.assignees_remove:
            json_data["assignees"] = {}
            if params.assignees_add:
                json_data["assignees"]["add"] = params.assignees_add
            if params.assignees_remove:
                json_data["assignees"]["rem"] = params.assignees_remove
        
        data = await api_request("PUT", f"/task/{params.task_id}", json_data=json_data)
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        return f"✅ Task '{data.get('name')}' atualizada com sucesso!"
    except Exception as e:
        return f"Erro ao atualizar task: {str(e)}"

@mcp.tool(
    name="clickup_delete_task",
    annotations={
        "title": "Deletar Task",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def delete_task(params: DeleteTaskInput) -> str:
    """
    Deleta uma task. ATENÇÃO: Esta ação é irreversível!

    Returns:
        Confirmação da exclusão.
    """
    try:
        check_write_permission("delete_task")
        await api_request("DELETE", f"/task/{params.task_id}")
        return f"✅ Task `{params.task_id}` deletada com sucesso!"
    except Exception as e:
        return f"Erro ao deletar task: {str(e)}"

@mcp.tool(
    name="clickup_move_task",
    annotations={
        "title": "Mover Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def move_task(params: MoveTaskInput) -> str:
    """
    Move uma task para outra list.

    Returns:
        Confirmação da movimentação.
    """
    try:
        check_write_permission("move_task")
        # Primeiro busca a task para obter a list atual
        task = await api_request("GET", f"/task/{params.task_id}")
        current_list_id = task.get("list", {}).get("id")
        
        # Adiciona a task à nova list
        await api_request(
            "POST",
            f"/list/{params.list_id}/task/{params.task_id}"
        )
        
        # Remove da list original (se diferente)
        if current_list_id and str(current_list_id) != str(params.list_id):
            await api_request(
                "DELETE",
                f"/list/{current_list_id}/task/{params.task_id}"
            )
        
        return f"✅ Task `{params.task_id}` movida para list `{params.list_id}` com sucesso!"
    except Exception as e:
        return f"Erro ao mover task: {str(e)}"

@mcp.tool(
    name="clickup_duplicate_task",
    annotations={
        "title": "Duplicar Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def duplicate_task(params: DuplicateTaskInput) -> str:
    """
    Cria uma cópia de uma task existente.

    Returns:
        Detalhes da task duplicada.
    """
    try:
        check_write_permission("duplicate_task")
        # Busca a task original
        original = await api_request("GET", f"/task/{params.task_id}")
        
        # Cria a cópia
        json_data = {
            "name": params.name or f"Cópia de {original.get('name', 'Task')}",
            "description": original.get("description", ""),
            "status": original.get("status", {}).get("status"),
            "priority": original.get("priority", {}).get("priority") if original.get("priority") else None,
        }
        
        # Remove campos None
        json_data = {k: v for k, v in json_data.items() if v is not None}
        
        data = await api_request("POST", f"/list/{params.list_id}/task", json_data=json_data)
        
        return f"✅ Task duplicada com sucesso!\n- **Nova ID:** `{data.get('id')}`\n- **Nome:** {data.get('name')}\n- **URL:** {data.get('url')}"
    except Exception as e:
        return f"Erro ao duplicar task: {str(e)}"

# ============================================================================
# TOOLS - COMMENTS
# ============================================================================

@mcp.tool(
    name="clickup_get_task_comments",
    annotations={
        "title": "Listar Comentários da Task",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_task_comments(params: GetTaskCommentsInput) -> str:
    """
    Lista todos os comentários de uma task.

    Modos de output: compact (default), detailed, json.
    """
    try:
        data = await api_request("GET", f"/task/{params.task_id}/comment")
        comments = data.get("comments", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if not comments:
            return "Nenhum comentário encontrado."

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(comments)} comentários:**\n"]
            for i, comment in enumerate(comments, 1):
                user = comment.get("user", {}).get('username', 'Anônimo')
                date = format_timestamp(comment.get("date"))
                text = comment.get('comment_text', '')[:50]
                lines.append(f"{i}. {user} ({date[:10] if date else '-'}): {text}...")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Comentários\n"]
        for comment in comments:
            user = comment.get("user", {})
            date = format_timestamp(comment.get("date"))
            lines.append(f"### {user.get('username', 'Anônimo')} - {date}")
            lines.append(f"{comment.get('comment_text', '')}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar comentários: {str(e)}"

@mcp.tool(
    name="clickup_create_task_comment",
    annotations={
        "title": "Criar Comentário",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_task_comment(params: CreateTaskCommentInput) -> str:
    """
    Adiciona um comentário a uma task.

    Returns:
        Confirmação do comentário criado.
    """
    try:
        check_write_permission("create_task_comment")
        json_data = {
            "comment_text": params.comment_text,
            "notify_all": params.notify_all
        }
        if params.assignee:
            json_data["assignee"] = params.assignee
        
        data = await api_request("POST", f"/task/{params.task_id}/comment", json_data=json_data)
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        return "✅ Comentário adicionado com sucesso!"
    except Exception as e:
        return f"Erro ao criar comentário: {str(e)}"

# ============================================================================
# TOOLS - MEMBERS
# ============================================================================

@mcp.tool(
    name="clickup_get_workspace_members",
    annotations={
        "title": "Listar Membros do Workspace",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_workspace_members(params: GetMembersInput) -> str:
    """
    Lista todos os membros de um workspace.

    Modos de output: compact (default), detailed, json.
    """
    try:
        # Busca o workspace para pegar os membros
        data = await api_request("GET", "/team")
        teams = data.get("teams", [])

        # Encontra o team correto
        team = None
        for t in teams:
            if str(t.get("id")) == str(params.team_id):
                team = t
                break

        if not team:
            return f"Workspace {params.team_id} não encontrado."

        members = team.get("members", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps({"members": members}, indent=2, ensure_ascii=False)

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(members)} membros:**\n"]
            for i, member in enumerate(members, 1):
                user = member.get("user", {})
                name = user.get('username', 'Sem nome')
                role = member.get('role', '?')
                lines.append(f"{i}. {name} | {role} | `{user.get('id')}`")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Membros do Workspace\n"]
        for member in members:
            user = member.get("user", {})
            lines.append(f"## {user.get('username', 'Sem nome')}")
            lines.append(f"- **ID:** `{user.get('id')}`")
            lines.append(f"- **Email:** {user.get('email', 'N/A')}")
            lines.append(f"- **Role:** {member.get('role', 'N/A')}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar membros: {str(e)}"

# ============================================================================
# TOOLS - TIME TRACKING
# ============================================================================

@mcp.tool(
    name="clickup_get_time_entries",
    annotations={
        "title": "Buscar Time Entries",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_time_entries(params: GetTimeEntriesInput) -> str:
    """
    Busca registros de tempo do workspace.

    Modos de output: compact (default), detailed, json.
    """
    try:
        query_params = {}
        if params.start_date:
            query_params["start_date"] = params.start_date
        if params.end_date:
            query_params["end_date"] = params.end_date
        if params.assignee:
            query_params["assignee"] = params.assignee

        data = await api_request("GET", f"/team/{params.team_id}/time_entries", params=query_params)
        entries = data.get("data", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if not entries:
            return "Nenhum registro de tempo encontrado."

        total_ms = sum(int(e.get("duration", 0)) for e in entries)

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(entries)} entries** | Total: {total_ms // 60000} min\n"]
            for i, entry in enumerate(entries, 1):
                duration_min = int(entry.get("duration", 0)) // 60000
                task = entry.get("task", {}).get('name', '?')[:30]
                user = entry.get("user", {}).get('username', '?')
                lines.append(f"{i}. {user} | {duration_min}min | {task}")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Time Entries\n", f"**Total:** {total_ms // 60000} minutos\n"]
        for entry in entries:
            duration = int(entry.get("duration", 0))
            duration_min = duration // 60000
            task = entry.get("task", {})
            user = entry.get("user", {})
            start = format_timestamp(entry.get("start"))

            lines.append(f"### {task.get('name', 'Task não especificada')}")
            lines.append(f"- **Duração:** {duration_min} min")
            lines.append(f"- **Usuário:** {user.get('username', 'N/A')}")
            lines.append(f"- **Início:** {start}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao buscar time entries: {str(e)}"


@mcp.tool(
    name="clickup_create_time_entry",
    annotations={
        "title": "Criar Time Entry",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_time_entry(params: CreateTimeEntryInput) -> str:
    """
    Cria um registro de tempo (Sprint 5 - Time Tracking+).

    Suporta:
    - Horas faturáveis (billable)
    - Tags para categorização
    - Associação opcional a tasks

    Returns:
        Confirmação com ID do registro criado.
    """
    try:
        check_write_permission("create_time_entry")

        json_data = {
            "start": params.start,
            "duration": params.duration,
            "billable": params.billable
        }

        if params.task_id:
            json_data["tid"] = params.task_id
        if params.description:
            json_data["description"] = params.description
        if params.tags:
            json_data["tags"] = [{"name": tag} for tag in params.tags]

        data = await api_request(
            "POST",
            f"/team/{params.team_id}/time_entries",
            json_data=json_data
        )

        entry = data.get("data", {})
        duration_min = params.duration // 60000
        billable_icon = "💰" if params.billable else "⏱️"

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        return (
            f"✅ Time entry criado!\n"
            f"- **ID:** `{entry.get('id', 'N/A')}`\n"
            f"- **Duração:** {duration_min} minutos {billable_icon}\n"
            f"- **Faturável:** {'Sim' if params.billable else 'Não'}"
        )
    except Exception as e:
        return f"Erro ao criar time entry: {str(e)}"


@mcp.tool(
    name="clickup_get_billable_report",
    annotations={
        "title": "Relatório de Horas Faturáveis",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_billable_report(params: GetBillableReportInput) -> str:
    """
    Gera relatório de horas faturáveis (Sprint 5 - Time Tracking+).

    Filtra apenas time entries marcados como billable e agrupa por:
    - Total de horas faturáveis
    - Por usuário
    - Por task

    Útil para faturamento de clientes e análise de produtividade.

    Returns:
        Relatório formatado de horas faturáveis.
    """
    cid = set_new_correlation_id()
    logger.bind(correlation_id=cid).info("Gerando relatório de billable hours")

    try:
        query_params = {
            "start_date": params.start_date,
            "end_date": params.end_date
        }
        if params.assignee:
            query_params["assignee"] = params.assignee

        data = await api_request("GET", f"/team/{params.team_id}/time_entries", params=query_params)
        all_entries = data.get("data", [])

        # Filtra apenas billable
        billable_entries = [e for e in all_entries if e.get("billable", False)]

        if params.output_mode == OutputMode.JSON:
            return json.dumps({
                "total_entries": len(all_entries),
                "billable_entries": len(billable_entries),
                "entries": billable_entries
            }, indent=2, ensure_ascii=False)

        if not billable_entries:
            return "Nenhuma hora faturável encontrada no período."

        # Calcula totais
        total_ms = sum(int(e.get("duration", 0)) for e in billable_entries)
        total_hours = total_ms / 3600000
        total_minutes = (total_ms % 3600000) // 60000

        # Agrupa por usuário
        by_user: Dict[str, int] = defaultdict(int)
        by_task: Dict[str, int] = defaultdict(int)

        for entry in billable_entries:
            user = entry.get("user", {}).get("username", "Unknown")
            task = entry.get("task", {}).get("name", "Sem task")
            duration = int(entry.get("duration", 0))

            by_user[user] += duration
            by_task[task] += duration

        if params.output_mode == OutputMode.COMPACT:
            return (
                f"**💰 Horas Faturáveis** | "
                f"{int(total_hours)}h{int(total_minutes)}min | "
                f"{len(billable_entries)} entries | "
                f"{len(by_user)} usuários"
            )

        # DETAILED
        start_fmt = format_timestamp(params.start_date)
        end_fmt = format_timestamp(params.end_date)

        lines = [
            "# 💰 Relatório de Horas Faturáveis\n",
            f"**Período:** {start_fmt} a {end_fmt}\n",
            f"## Resumo",
            f"- **Total:** {int(total_hours)}h {int(total_minutes)}min",
            f"- **Entries:** {len(billable_entries)} de {len(all_entries)} total",
            f"- **Usuários:** {len(by_user)}",
        ]

        lines.append("\n## Por Usuário")
        for user, ms in sorted(by_user.items(), key=lambda x: -x[1]):
            h = ms // 3600000
            m = (ms % 3600000) // 60000
            lines.append(f"- **{user}:** {h}h {m}min")

        lines.append("\n## Por Task (Top 10)")
        sorted_tasks = sorted(by_task.items(), key=lambda x: -x[1])[:10]
        for task, ms in sorted_tasks:
            h = ms // 3600000
            m = (ms % 3600000) // 60000
            lines.append(f"- {task[:40]}: {h}h {m}min")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao gerar relatório: {str(e)}"


# ============================================================================
# TOOLS - SPRINT 2: NOVAS TOOLS
# ============================================================================

class GetCustomFieldsInput(BaseModel):
    """Input para listar custom fields de uma list."""
    model_config = ConfigDict(str_strip_whitespace=True)
    list_id: str = Field(..., description="ID da list", min_length=1)
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )


@mcp.tool(
    name="clickup_get_custom_fields",
    annotations={
        "title": "Listar Custom Fields",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_custom_fields(params: GetCustomFieldsInput) -> str:
    """
    Lista todos os campos customizados de uma list.

    Útil para saber quais campos podem ser usados ao criar/atualizar tasks.

    Modos de output: compact (default), detailed, json.
    """
    try:
        data = await api_request("GET", f"/list/{params.list_id}/field")
        fields = data.get("fields", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if not fields:
            return "Nenhum campo customizado encontrado nesta list."

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(fields)} campos customizados:**\n"]
            for i, field in enumerate(fields, 1):
                name = field.get('name', 'Sem nome')
                ftype = field.get('type', '?')
                required = "obrigatório" if field.get('required') else "opcional"
                lines.append(f"{i}. {name} | {ftype} | {required} | `{field.get('id')}`")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Custom Fields\n"]
        for field in fields:
            lines.append(f"## {field.get('name', 'Sem nome')}")
            lines.append(f"- **ID:** `{field.get('id')}`")
            lines.append(f"- **Tipo:** {field.get('type', 'N/A')}")
            lines.append(f"- **Obrigatório:** {'Sim' if field.get('required') else 'Não'}")

            # Opções para campos de dropdown/label
            type_config = field.get('type_config', {})
            if 'options' in type_config:
                options = [o.get('name', '') for o in type_config['options']]
                lines.append(f"- **Opções:** {', '.join(options)}")

            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar custom fields: {str(e)}"


class GetSpaceDetailsInput(BaseModel):
    """Input para buscar detalhes de um space."""
    model_config = ConfigDict(str_strip_whitespace=True)
    space_id: str = Field(..., description="ID do space", min_length=1)
    output_mode: OutputMode = Field(
        default=OutputMode.DETAILED,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )


@mcp.tool(
    name="clickup_get_space_details",
    annotations={
        "title": "Detalhes do Space",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_space_details(params: GetSpaceDetailsInput) -> str:
    """
    Busca detalhes completos de um space específico.

    Inclui: status disponíveis, features habilitadas, membros.

    Modos de output: compact, detailed (default), json.
    """
    try:
        data = await api_request("GET", f"/space/{params.space_id}")

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        name = data.get('name', 'Sem nome')
        space_id = data.get('id', '')
        private = data.get('private', False)
        statuses = data.get('statuses', [])
        features = data.get('features', {})
        members = data.get('members', [])

        if params.output_mode == OutputMode.COMPACT:
            status_count = len(statuses)
            member_count = len(members)
            priv = "privado" if private else "público"
            return f"**{name}** | {priv} | {status_count} status | {member_count} membros | `{space_id}`"

        # DETAILED
        lines = [f"# Space: {name}\n"]
        lines.append(f"- **ID:** `{space_id}`")
        lines.append(f"- **Privado:** {'Sim' if private else 'Não'}")

        # Status disponíveis
        if statuses:
            lines.append(f"\n## Status ({len(statuses)})")
            for s in statuses:
                color = s.get('color', '')
                lines.append(f"- {s.get('status', '')} ({s.get('type', '')}) `{color}`")

        # Features
        lines.append("\n## Features")
        for feat, config in features.items():
            enabled = config.get('enabled', False) if isinstance(config, dict) else config
            status = "✅" if enabled else "❌"
            lines.append(f"- {feat}: {status}")

        # Membros
        if members:
            lines.append(f"\n## Membros ({len(members)})")
            for m in members:
                user = m.get('user', {})
                lines.append(f"- {user.get('username', 'N/A')} ({user.get('email', '')})")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao buscar detalhes do space: {str(e)}"


class GetListDetailsInput(BaseModel):
    """Input para buscar detalhes de uma list."""
    model_config = ConfigDict(str_strip_whitespace=True)
    list_id: str = Field(..., description="ID da list", min_length=1)
    output_mode: OutputMode = Field(
        default=OutputMode.DETAILED,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )


@mcp.tool(
    name="clickup_get_list_details",
    annotations={
        "title": "Detalhes da List",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_list_details(params: GetListDetailsInput) -> str:
    """
    Busca detalhes completos de uma list específica.

    Inclui: status, prioridade, assignee padrão, datas.

    Modos de output: compact, detailed (default), json.
    """
    try:
        data = await api_request("GET", f"/list/{params.list_id}")

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        name = data.get('name', 'Sem nome')
        list_id = data.get('id', '')
        task_count = data.get('task_count', 0)
        folder = data.get('folder', {})
        space = data.get('space', {})
        statuses = data.get('statuses', [])

        if params.output_mode == OutputMode.COMPACT:
            folder_name = folder.get('name', 'Sem folder') if folder else 'Sem folder'
            return f"**{name}** | {task_count} tasks | {folder_name} | `{list_id}`"

        # DETAILED
        lines = [f"# List: {name}\n"]
        lines.append(f"- **ID:** `{list_id}`")
        lines.append(f"- **Tasks:** {task_count}")

        if folder:
            lines.append(f"- **Folder:** {folder.get('name', 'N/A')} (`{folder.get('id', '')}`)")
        if space:
            lines.append(f"- **Space:** {space.get('name', 'N/A')} (`{space.get('id', '')}`)")

        # Datas
        due_date = format_timestamp(data.get('due_date'))
        start_date = format_timestamp(data.get('start_date'))
        if due_date:
            lines.append(f"- **Due Date:** {due_date}")
        if start_date:
            lines.append(f"- **Start Date:** {start_date}")

        # Status disponíveis
        if statuses:
            lines.append(f"\n## Status Disponíveis ({len(statuses)})")
            for s in statuses:
                lines.append(f"- {s.get('status', '')} ({s.get('type', '')})")

        # Assignee padrão
        assignee = data.get('assignee')
        if assignee:
            lines.append(f"\n## Assignee Padrão")
            lines.append(f"- {assignee.get('username', 'N/A')}")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao buscar detalhes da list: {str(e)}"


class GetChecklistsInput(BaseModel):
    """Input para buscar checklists de uma task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task", min_length=1)
    output_mode: OutputMode = Field(
        default=OutputMode.DETAILED,
        description="Modo de output: compact (resumo), detailed (completo), json (raw)"
    )


@mcp.tool(
    name="clickup_get_checklists",
    annotations={
        "title": "Listar Checklists",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_checklists(params: GetChecklistsInput) -> str:
    """
    Lista todas as checklists de uma task.

    Checklists são listas de itens dentro de uma task.
    Os dados vêm do endpoint GET /task/{id}.

    Modos de output: compact (resumo), detailed (default), json.
    """
    try:
        data = await api_request("GET", f"/task/{params.task_id}")
        checklists = data.get("checklists", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps({"checklists": checklists}, indent=2, ensure_ascii=False)

        if not checklists:
            return "Nenhuma checklist encontrada nesta task."

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(checklists)} checklists:**\n"]
            for i, cl in enumerate(checklists, 1):
                name = cl.get('name', 'Sem nome')
                items = cl.get('items', [])
                resolved = sum(1 for item in items if item.get('resolved'))
                total = len(items)
                lines.append(f"{i}. {name} | {resolved}/{total} concluídos | `{cl.get('id')}`")
            return "\n".join(lines)

        # DETAILED
        lines = [f"# Checklists ({len(checklists)})\n"]
        for cl in checklists:
            name = cl.get('name', 'Sem nome')
            items = cl.get('items', [])
            resolved = sum(1 for item in items if item.get('resolved'))

            lines.append(f"## {name} ({resolved}/{len(items)})")
            lines.append(f"- **ID:** `{cl.get('id')}`")

            if items:
                lines.append("\n### Itens:")
                for item in items:
                    check = "✅" if item.get('resolved') else "⬜"
                    item_name = item.get('name', 'Sem nome')
                    assignee = item.get('assignee')
                    assignee_str = f" (@{assignee.get('username', '')})" if assignee else ""
                    lines.append(f"- {check} {item_name}{assignee_str}")

            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao buscar checklists: {str(e)}"


class GetAttachmentsInput(BaseModel):
    """Input para buscar anexos de uma task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task", min_length=1)
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )


@mcp.tool(
    name="clickup_get_attachments",
    annotations={
        "title": "Listar Anexos",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_attachments(params: GetAttachmentsInput) -> str:
    """
    Lista todos os anexos de uma task.

    Modos de output: compact (default), detailed, json.
    """
    try:
        data = await api_request("GET", f"/task/{params.task_id}")
        attachments = data.get("attachments", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps({"attachments": attachments}, indent=2, ensure_ascii=False)

        if not attachments:
            return "Nenhum anexo encontrado nesta task."

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(attachments)} anexos:**\n"]
            for i, att in enumerate(attachments, 1):
                title = att.get('title', 'Sem título')[:40]
                ext = att.get('extension', '?')
                size = att.get('size', 0)
                size_kb = size // 1024 if size else 0
                lines.append(f"{i}. {title}.{ext} | {size_kb}KB | `{att.get('id')}`")
            return "\n".join(lines)

        # DETAILED
        lines = [f"# Anexos ({len(attachments)})\n"]
        for att in attachments:
            title = att.get('title', 'Sem título')
            lines.append(f"## {title}")
            lines.append(f"- **ID:** `{att.get('id')}`")
            lines.append(f"- **Extensão:** {att.get('extension', 'N/A')}")
            lines.append(f"- **Tamanho:** {att.get('size', 0) // 1024} KB")
            lines.append(f"- **URL:** {att.get('url', 'N/A')}")

            date = format_timestamp(att.get('date'))
            if date:
                lines.append(f"- **Data:** {date}")

            user = att.get('user', {})
            if user:
                lines.append(f"- **Enviado por:** {user.get('username', 'N/A')}")

            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao buscar anexos: {str(e)}"


class AnalyzeSpaceStructureInput(BaseModel):
    """Input para análise morfológica do space."""
    model_config = ConfigDict(str_strip_whitespace=True)
    space_id: str = Field(..., description="ID do space", min_length=1)
    include_tasks_count: bool = Field(default=True, description="Incluir contagem de tasks por list")
    output_mode: OutputMode = Field(
        default=OutputMode.DETAILED,
        description="Modo de output: compact (resumo), detailed (completo), json (raw)"
    )


@mcp.tool(
    name="clickup_analyze_space_structure",
    annotations={
        "title": "Analisar Estrutura do Space",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def analyze_space_structure(params: AnalyzeSpaceStructureInput) -> str:
    """
    Análise morfológica completa de um space.

    Retorna a estrutura hierárquica: Space > Folders > Lists.
    Útil para entender a organização antes de criar tasks.

    Modos de output: compact (resumo), detailed (default), json.
    """
    try:
        # Busca dados em paralelo
        space_data = await api_request("GET", f"/space/{params.space_id}")
        folders_data = await api_request("GET", f"/space/{params.space_id}/folder")
        folderless_data = await api_request("GET", f"/space/{params.space_id}/list")

        space_name = space_data.get('name', 'Sem nome')
        folders = folders_data.get("folders", [])
        folderless_lists = folderless_data.get("lists", [])

        # Estrutura para JSON
        structure = {
            "space": {
                "id": params.space_id,
                "name": space_name,
                "private": space_data.get('private', False)
            },
            "folders": [],
            "folderless_lists": []
        }

        # Processa folders
        total_lists = 0
        total_tasks = 0

        for folder in folders:
            folder_info = {
                "id": folder.get('id'),
                "name": folder.get('name'),
                "lists": []
            }

            for lst in folder.get('lists', []):
                task_count = lst.get('task_count', 0)
                total_tasks += task_count
                total_lists += 1
                folder_info["lists"].append({
                    "id": lst.get('id'),
                    "name": lst.get('name'),
                    "task_count": task_count
                })

            structure["folders"].append(folder_info)

        # Processa lists sem folder
        for lst in folderless_lists:
            task_count = lst.get('task_count', 0)
            total_tasks += task_count
            total_lists += 1
            structure["folderless_lists"].append({
                "id": lst.get('id'),
                "name": lst.get('name'),
                "task_count": task_count
            })

        if params.output_mode == OutputMode.JSON:
            structure["summary"] = {
                "total_folders": len(folders),
                "total_lists": total_lists,
                "total_tasks": total_tasks
            }
            return json.dumps(structure, indent=2, ensure_ascii=False)

        if params.output_mode == OutputMode.COMPACT:
            return (
                f"**{space_name}** | "
                f"{len(folders)} folders | "
                f"{total_lists} lists | "
                f"{total_tasks} tasks | "
                f"`{params.space_id}`"
            )

        # DETAILED
        lines = [f"# Análise: {space_name}\n"]
        lines.append(f"**ID:** `{params.space_id}`")
        lines.append(f"**Resumo:** {len(folders)} folders, {total_lists} lists, {total_tasks} tasks\n")

        # Folders e suas lists
        if folders:
            lines.append("## Folders\n")
            for folder in folders:
                folder_name = folder.get('name', 'Sem nome')
                folder_lists = folder.get('lists', [])
                lines.append(f"### 📁 {folder_name} (`{folder.get('id')}`)")

                if folder_lists:
                    for lst in folder_lists:
                        task_count = lst.get('task_count', 0)
                        task_str = f" ({task_count} tasks)" if params.include_tasks_count else ""
                        lines.append(f"  - 📋 {lst.get('name')}{task_str} `{lst.get('id')}`")
                else:
                    lines.append("  - _(vazio)_")

                lines.append("")

        # Lists sem folder
        if folderless_lists:
            lines.append("## Lists (sem folder)\n")
            for lst in folderless_lists:
                task_count = lst.get('task_count', 0)
                task_str = f" ({task_count} tasks)" if params.include_tasks_count else ""
                lines.append(f"- 📋 {lst.get('name')}{task_str} `{lst.get('id')}`")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao analisar estrutura: {str(e)}"


class GetDocsInput(BaseModel):
    """Input para listar docs de um workspace."""
    model_config = ConfigDict(str_strip_whitespace=True)
    workspace_id: str = Field(..., description="ID do workspace", min_length=1)
    output_mode: OutputMode = Field(
        default=OutputMode.COMPACT,
        description="Modo de output: compact (1 linha), detailed (completo), json (raw)"
    )


@mcp.tool(
    name="clickup_get_docs",
    annotations={
        "title": "Listar Docs",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_docs(params: GetDocsInput) -> str:
    """
    Lista todos os documentos (Docs) de um workspace.

    Docs são documentos colaborativos do ClickUp.
    Usa API v3 que é obrigatória para o recurso de Docs.

    Modos de output: compact (default), detailed, json.
    """
    try:
        # API v3: /workspaces/{workspace_id}/docs
        data = await api_request(
            "GET",
            f"/workspaces/{params.workspace_id}/docs",
            api_version="v3"
        )

        # API v3 retorna lista direta ou dict com estrutura diferente
        if isinstance(data, list):
            docs = data
        elif isinstance(data, dict):
            docs = data.get("docs", data.get("data", []))
        else:
            docs = []

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if not docs:
            return "Nenhum documento encontrado neste workspace."

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(docs)} documentos:**\n"]
            for i, doc in enumerate(docs, 1):
                name = doc.get('name', 'Sem nome')[:50]
                creator = doc.get('creator', '?')
                lines.append(f"{i}. {name} | criador: {creator} | `{doc.get('id')}`")
            return "\n".join(lines)

        # DETAILED
        lines = [f"# Documentos ({len(docs)})\n"]
        for doc in docs:
            lines.append(f"## {doc.get('name', 'Sem nome')}")
            lines.append(f"- **ID:** `{doc.get('id')}`")

            creator = doc.get('creator')
            if creator:
                lines.append(f"- **Criador ID:** {creator}")

            date_created = format_timestamp(doc.get('date_created'))
            if date_created:
                lines.append(f"- **Criado em:** {date_created}")

            parent = doc.get('parent', {})
            if parent:
                lines.append(f"- **Parent:** {parent.get('type', '')} `{parent.get('id', '')}`")

            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar docs: {str(e)}"


class CreateDocInput(BaseModel):
    """Input para criar um documento."""
    model_config = ConfigDict(str_strip_whitespace=True)
    workspace_id: str = Field(..., description="ID do workspace", min_length=1)
    name: str = Field(..., description="Nome do documento", min_length=1)
    content: Optional[str] = Field(default=None, description="Conteúdo inicial do documento (markdown)")
    parent_id: Optional[str] = Field(default=None, description="ID do parent (space, folder, list ou task)")
    parent_type: Optional[str] = Field(default=None, description="Tipo do parent: space, folder, list, task")


@mcp.tool(
    name="clickup_create_doc",
    annotations={
        "title": "Criar Documento",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_doc(params: CreateDocInput) -> str:
    """
    Cria um novo documento (Doc) no workspace.

    Docs são documentos colaborativos do ClickUp.
    Podem ser associados a spaces, folders, lists ou tasks.
    Usa API v3 que é obrigatória para o recurso de Docs.

    Returns:
        Confirmação com ID do documento criado.
    """
    try:
        check_write_permission("create_doc")
        json_data = {
            "name": params.name
        }

        if params.content:
            json_data["content"] = params.content

        if params.parent_id and params.parent_type:
            json_data["parent"] = {
                "id": params.parent_id,
                "type": params.parent_type
            }

        # API v3: /workspaces/{workspace_id}/docs
        data = await api_request(
            "POST",
            f"/workspaces/{params.workspace_id}/docs",
            json_data=json_data,
            api_version="v3"
        )

        doc_id = data.get('id', 'N/A')
        doc_name = data.get('name', params.name)

        return f"✅ Documento criado com sucesso!\n- **Nome:** {doc_name}\n- **ID:** `{doc_id}`"
    except Exception as e:
        return f"Erro ao criar documento: {str(e)}"


# ============================================================================
# TOOLS - DIAGNÓSTICO
# ============================================================================

class GetMetricsInput(BaseModel):
    """Input para buscar métricas do servidor."""
    model_config = ConfigDict(str_strip_whitespace=True)
    output_mode: OutputMode = Field(
        default=OutputMode.DETAILED,
        description="Modo de output: compact (resumo), detailed (completo), json (raw)"
    )


@mcp.tool(
    name="clickup_get_metrics",
    annotations={
        "title": "Métricas do Servidor",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_metrics(params: GetMetricsInput) -> str:
    """
    Retorna métricas de diagnóstico do servidor MCP.

    Inclui: chamadas por tool, cache hit rate, API calls, retries.

    Modos de output: compact (resumo), detailed (default), json.
    """
    cid = set_new_correlation_id()
    logger.bind(correlation_id=cid).info("Gerando métricas")

    summary = _metrics.get_summary()
    operation_mode = "READ_ONLY" if READ_ONLY_MODE else "READ_WRITE"
    summary["operation_mode"] = operation_mode

    if params.output_mode == OutputMode.JSON:
        return json.dumps(summary, indent=2, ensure_ascii=False)

    if params.output_mode == OutputMode.COMPACT:
        mode_icon = "🔒" if READ_ONLY_MODE else "✏️"
        return (
            f"**Métricas** | "
            f"Modo: {mode_icon} {operation_mode} | "
            f"API: {summary['api_calls']} calls | "
            f"Cache: {summary['cache_hit_rate']:.0%} hit | "
            f"Retries: {summary['retries']}"
        )

    # DETAILED
    lines = ["# Métricas do Servidor\n"]

    lines.append("## Configuração")
    mode_icon = "🔒" if READ_ONLY_MODE else "✏️"
    lines.append(f"- **Modo de Operação:** {mode_icon} {operation_mode}")

    lines.append("\n## Resumo")
    lines.append(f"- **API Calls:** {summary['api_calls']}")
    lines.append(f"- **Cache Hits:** {summary['cache_hits']}")
    lines.append(f"- **Cache Misses:** {summary['cache_misses']}")
    lines.append(f"- **Cache Hit Rate:** {summary['cache_hit_rate']:.1%}")
    lines.append(f"- **Retries:** {summary['retries']}")

    if summary['tool_calls']:
        lines.append("\n## Chamadas por Tool")
        for tool, count in sorted(summary['tool_calls'].items(), key=lambda x: -x[1]):
            lines.append(f"- {tool}: {count}")

    if summary['tool_errors']:
        lines.append("\n## Erros por Tool")
        for tool, count in sorted(summary['tool_errors'].items(), key=lambda x: -x[1]):
            lines.append(f"- {tool}: {count}")

    return "\n".join(lines)


# ============================================================================
# TOOLS - CUSTOM FIELDS
# ============================================================================

class SetCustomFieldValueInput(BaseModel):
    """Input para definir valor de um custom field em uma task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task", min_length=1)
    field_id: str = Field(..., description="ID do custom field (use clickup_get_custom_fields para obter)", min_length=1)
    value: Any = Field(
        ...,
        description="Valor do campo. Formato varia por tipo: text='string', number=123, dropdown='option_id', checkbox=true/false, date=timestamp_ms (int), labels=['id1','id2'], users={'add':['user_id'],'rem':['user_id']}, tasks={'add':['task_id'],'rem':['task_id']}, location={'location':{'lat':0,'lng':0},'formatted_address':'addr'}, currency=1000, progress={'current':50}, rating=4, email='a@b.com', phone='+5511999999999'"
    )
    value_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Opções adicionais. Para date: {'time': true} para mostrar horário"
    )


@mcp.tool(
    name="clickup_set_custom_field_value",
    annotations={
        "title": "Definir Valor de Custom Field",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def set_custom_field_value(params: SetCustomFieldValueInput) -> str:
    """
    Define o valor de um custom field em uma task existente.

    Use clickup_get_custom_fields para obter os IDs dos campos disponíveis.
    Para campos do tipo dropdown, use o ID da opção (não o nome).

    Formatos de valor por tipo:
    - text/short_text: "string"
    - number/currency: 123 (número)
    - dropdown: "option_id" (ID da opção)
    - labels: ["label_id_1", "label_id_2"]
    - checkbox: true/false
    - date: 1234567890000 (timestamp ms)
    - users/tasks: {"add": ["id1"], "rem": ["id2"]}
    - email: "email@example.com"
    - phone: "+5511999999999"
    - location: {"location": {"lat": -23.5, "lng": -46.6}, "formatted_address": "São Paulo, SP"}
    - rating: 4 (inteiro)
    - progress: {"current": 50}

    Returns:
        Confirmação da atualização.
    """
    try:
        check_write_permission("set_custom_field_value")

        json_data = {"value": params.value}
        if params.value_options:
            json_data["value_options"] = params.value_options

        await api_request("POST", f"/task/{params.task_id}/field/{params.field_id}", json_data=json_data)

        return f"✅ Custom field atualizado com sucesso!\n- **Task:** `{params.task_id}`\n- **Field:** `{params.field_id}`"
    except Exception as e:
        return f"Erro ao definir custom field: {str(e)}"


class RemoveCustomFieldValueInput(BaseModel):
    """Input para remover valor de um custom field."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task", min_length=1)
    field_id: str = Field(..., description="ID do custom field", min_length=1)


@mcp.tool(
    name="clickup_remove_custom_field_value",
    annotations={
        "title": "Remover Valor de Custom Field",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def remove_custom_field_value(params: RemoveCustomFieldValueInput) -> str:
    """
    Remove o valor de um custom field de uma task (deixa o campo vazio).

    Returns:
        Confirmação da remoção.
    """
    try:
        check_write_permission("remove_custom_field_value")

        await api_request("DELETE", f"/task/{params.task_id}/field/{params.field_id}")

        return f"✅ Valor do custom field removido!\n- **Task:** `{params.task_id}`\n- **Field:** `{params.field_id}`"
    except Exception as e:
        return f"Erro ao remover custom field: {str(e)}"


# ============================================================================
# TOOLS - TAGS
# ============================================================================

class GetSpaceTagsInput(BaseModel):
    """Input para listar tags de um space."""
    model_config = ConfigDict(str_strip_whitespace=True)
    space_id: str = Field(..., description="ID do space", min_length=1)
    output_mode: OutputMode = Field(default=OutputMode.COMPACT, description="Modo de output")


@mcp.tool(
    name="clickup_get_space_tags",
    annotations={
        "title": "Listar Tags do Space",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_space_tags(params: GetSpaceTagsInput) -> str:
    """
    Lista todas as tags disponíveis em um space.

    Tags são usadas para categorizar tasks (ex: "urgente", "bug", "feature").
    """
    try:
        data = await api_request("GET", f"/space/{params.space_id}/tag")
        tags = data.get("tags", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if not tags:
            return "Nenhuma tag encontrada neste space."

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(tags)} tags:**\n"]
            for tag in tags:
                name = tag.get('name', 'Sem nome')
                color = tag.get('tag_fg', '#000')
                lines.append(f"- {name} ({color})")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Tags do Space\n"]
        for tag in tags:
            lines.append(f"## {tag.get('name', 'Sem nome')}")
            lines.append(f"- **Cor do texto:** {tag.get('tag_fg', 'N/A')}")
            lines.append(f"- **Cor do fundo:** {tag.get('tag_bg', 'N/A')}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar tags: {str(e)}"


class CreateSpaceTagInput(BaseModel):
    """Input para criar tag em um space."""
    model_config = ConfigDict(str_strip_whitespace=True)
    space_id: str = Field(..., description="ID do space", min_length=1)
    name: str = Field(..., description="Nome da tag", min_length=1, max_length=100)
    tag_fg: Optional[str] = Field(default=None, description="Cor do texto (hex, ex: #FFFFFF)")
    tag_bg: Optional[str] = Field(default=None, description="Cor do fundo (hex, ex: #000000)")


@mcp.tool(
    name="clickup_create_space_tag",
    annotations={
        "title": "Criar Tag no Space",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_space_tag(params: CreateSpaceTagInput) -> str:
    """
    Cria uma nova tag em um space.

    A tag ficará disponível para uso em todas as tasks do space.
    """
    try:
        check_write_permission("create_space_tag")

        json_data = {"tag": {"name": params.name}}
        if params.tag_fg:
            json_data["tag"]["tag_fg"] = params.tag_fg
        if params.tag_bg:
            json_data["tag"]["tag_bg"] = params.tag_bg

        await api_request("POST", f"/space/{params.space_id}/tag", json_data=json_data)

        return f"✅ Tag '{params.name}' criada com sucesso no space!"
    except Exception as e:
        return f"Erro ao criar tag: {str(e)}"


class UpdateSpaceTagInput(BaseModel):
    """Input para atualizar tag de um space."""
    model_config = ConfigDict(str_strip_whitespace=True)
    space_id: str = Field(..., description="ID do space", min_length=1)
    tag_name: str = Field(..., description="Nome atual da tag", min_length=1)
    new_name: Optional[str] = Field(default=None, description="Novo nome da tag")
    tag_fg: Optional[str] = Field(default=None, description="Nova cor do texto (hex)")
    tag_bg: Optional[str] = Field(default=None, description="Nova cor do fundo (hex)")


@mcp.tool(
    name="clickup_update_space_tag",
    annotations={
        "title": "Atualizar Tag do Space",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def update_space_tag(params: UpdateSpaceTagInput) -> str:
    """
    Atualiza uma tag existente em um space (nome e/ou cores).
    """
    try:
        check_write_permission("update_space_tag")

        json_data = {"tag": {}}
        if params.new_name:
            json_data["tag"]["name"] = params.new_name
        if params.tag_fg:
            json_data["tag"]["tag_fg"] = params.tag_fg
        if params.tag_bg:
            json_data["tag"]["tag_bg"] = params.tag_bg

        await api_request("PUT", f"/space/{params.space_id}/tag/{params.tag_name}", json_data=json_data)

        new_name = params.new_name or params.tag_name
        return f"✅ Tag atualizada! Novo nome: '{new_name}'"
    except Exception as e:
        return f"Erro ao atualizar tag: {str(e)}"


class DeleteSpaceTagInput(BaseModel):
    """Input para deletar tag de um space."""
    model_config = ConfigDict(str_strip_whitespace=True)
    space_id: str = Field(..., description="ID do space", min_length=1)
    tag_name: str = Field(..., description="Nome da tag a deletar", min_length=1)


@mcp.tool(
    name="clickup_delete_space_tag",
    annotations={
        "title": "Deletar Tag do Space",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def delete_space_tag(params: DeleteSpaceTagInput) -> str:
    """
    Deleta uma tag de um space.

    ATENÇÃO: A tag será removida de todas as tasks que a usam.
    """
    try:
        check_write_permission("delete_space_tag")

        await api_request("DELETE", f"/space/{params.space_id}/tag/{params.tag_name}")

        return f"✅ Tag '{params.tag_name}' deletada do space!"
    except Exception as e:
        return f"Erro ao deletar tag: {str(e)}"


class AddTagToTaskInput(BaseModel):
    """Input para adicionar tag a uma task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task", min_length=1)
    tag_name: str = Field(..., description="Nome da tag a adicionar", min_length=1)


@mcp.tool(
    name="clickup_add_tag_to_task",
    annotations={
        "title": "Adicionar Tag à Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def add_tag_to_task(params: AddTagToTaskInput) -> str:
    """
    Adiciona uma tag existente a uma task.

    A tag deve existir no space da task.
    """
    try:
        check_write_permission("add_tag_to_task")

        await api_request("POST", f"/task/{params.task_id}/tag/{params.tag_name}")

        return f"✅ Tag '{params.tag_name}' adicionada à task!"
    except Exception as e:
        return f"Erro ao adicionar tag: {str(e)}"


class RemoveTagFromTaskInput(BaseModel):
    """Input para remover tag de uma task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task", min_length=1)
    tag_name: str = Field(..., description="Nome da tag a remover", min_length=1)


@mcp.tool(
    name="clickup_remove_tag_from_task",
    annotations={
        "title": "Remover Tag da Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def remove_tag_from_task(params: RemoveTagFromTaskInput) -> str:
    """
    Remove uma tag de uma task.
    """
    try:
        check_write_permission("remove_tag_from_task")

        await api_request("DELETE", f"/task/{params.task_id}/tag/{params.tag_name}")

        return f"✅ Tag '{params.tag_name}' removida da task!"
    except Exception as e:
        return f"Erro ao remover tag: {str(e)}"


# ============================================================================
# TOOLS - TASK DEPENDENCIES
# ============================================================================

class AddDependencyInput(BaseModel):
    """Input para adicionar dependência entre tasks."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task que terá a dependência", min_length=1)
    depends_on: str = Field(..., description="ID da task da qual depende", min_length=1)


@mcp.tool(
    name="clickup_add_dependency",
    annotations={
        "title": "Adicionar Dependência",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def add_dependency(params: AddDependencyInput) -> str:
    """
    Cria dependência entre tasks: task_id depende de depends_on.

    Significa que task_id só pode começar quando depends_on terminar.
    """
    try:
        check_write_permission("add_dependency")

        json_data = {"depends_on": params.depends_on}
        await api_request("POST", f"/task/{params.task_id}/dependency", json_data=json_data)

        return f"✅ Dependência criada!\n- Task `{params.task_id}` depende de `{params.depends_on}`"
    except Exception as e:
        return f"Erro ao criar dependência: {str(e)}"


class DeleteDependencyInput(BaseModel):
    """Input para remover dependência entre tasks."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task que tem a dependência", min_length=1)
    depends_on: str = Field(..., description="ID da task da qual dependia", min_length=1)


@mcp.tool(
    name="clickup_delete_dependency",
    annotations={
        "title": "Remover Dependência",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def delete_dependency(params: DeleteDependencyInput) -> str:
    """
    Remove dependência entre tasks.
    """
    try:
        check_write_permission("delete_dependency")

        await api_request("DELETE", f"/task/{params.task_id}/dependency", params={"depends_on": params.depends_on})

        return f"✅ Dependência removida!\n- Task `{params.task_id}` não depende mais de `{params.depends_on}`"
    except Exception as e:
        return f"Erro ao remover dependência: {str(e)}"


class AddTaskLinkInput(BaseModel):
    """Input para criar link entre tasks."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task origem", min_length=1)
    links_to: str = Field(..., description="ID da task destino", min_length=1)


@mcp.tool(
    name="clickup_add_task_link",
    annotations={
        "title": "Criar Link entre Tasks",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def add_task_link(params: AddTaskLinkInput) -> str:
    """
    Cria um link entre duas tasks (relacionamento sem dependência).

    Diferente de dependência, um link é apenas uma referência.
    """
    try:
        check_write_permission("add_task_link")

        json_data = {"links_to": params.links_to}
        await api_request("POST", f"/task/{params.task_id}/link/{params.links_to}", json_data=json_data)

        return f"✅ Link criado entre tasks!\n- `{params.task_id}` ↔ `{params.links_to}`"
    except Exception as e:
        return f"Erro ao criar link: {str(e)}"


class DeleteTaskLinkInput(BaseModel):
    """Input para remover link entre tasks."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task origem", min_length=1)
    links_to: str = Field(..., description="ID da task destino", min_length=1)


@mcp.tool(
    name="clickup_delete_task_link",
    annotations={
        "title": "Remover Link entre Tasks",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def delete_task_link(params: DeleteTaskLinkInput) -> str:
    """
    Remove um link entre duas tasks.
    """
    try:
        check_write_permission("delete_task_link")

        await api_request("DELETE", f"/task/{params.task_id}/link/{params.links_to}")

        return f"✅ Link removido entre tasks!\n- `{params.task_id}` ↮ `{params.links_to}`"
    except Exception as e:
        return f"Erro ao remover link: {str(e)}"


# ============================================================================
# TOOLS - CHECKLISTS
# ============================================================================

class CreateChecklistInput(BaseModel):
    """Input para criar checklist em uma task."""
    model_config = ConfigDict(str_strip_whitespace=True)
    task_id: str = Field(..., description="ID da task", min_length=1)
    name: str = Field(..., description="Nome do checklist", min_length=1, max_length=200)


@mcp.tool(
    name="clickup_create_checklist",
    annotations={
        "title": "Criar Checklist",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_checklist(params: CreateChecklistInput) -> str:
    """
    Cria um novo checklist em uma task.

    Após criar o checklist, use clickup_create_checklist_item para adicionar itens.
    """
    try:
        check_write_permission("create_checklist")

        json_data = {"name": params.name}
        data = await api_request("POST", f"/task/{params.task_id}/checklist", json_data=json_data)

        checklist = data.get("checklist", {})
        return f"✅ Checklist criado!\n- **Nome:** {checklist.get('name')}\n- **ID:** `{checklist.get('id')}`"
    except Exception as e:
        return f"Erro ao criar checklist: {str(e)}"


class UpdateChecklistInput(BaseModel):
    """Input para atualizar checklist."""
    model_config = ConfigDict(str_strip_whitespace=True)
    checklist_id: str = Field(..., description="ID do checklist", min_length=1)
    name: Optional[str] = Field(default=None, description="Novo nome do checklist")
    position: Optional[int] = Field(default=None, description="Nova posição (ordem)")


@mcp.tool(
    name="clickup_update_checklist",
    annotations={
        "title": "Atualizar Checklist",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def update_checklist(params: UpdateChecklistInput) -> str:
    """
    Atualiza um checklist existente (nome e/ou posição).
    """
    try:
        check_write_permission("update_checklist")

        json_data = {}
        if params.name:
            json_data["name"] = params.name
        if params.position is not None:
            json_data["position"] = params.position

        data = await api_request("PUT", f"/checklist/{params.checklist_id}", json_data=json_data)

        checklist = data.get("checklist", {})
        return f"✅ Checklist atualizado!\n- **Nome:** {checklist.get('name')}"
    except Exception as e:
        return f"Erro ao atualizar checklist: {str(e)}"


class DeleteChecklistInput(BaseModel):
    """Input para deletar checklist."""
    model_config = ConfigDict(str_strip_whitespace=True)
    checklist_id: str = Field(..., description="ID do checklist a deletar", min_length=1)


@mcp.tool(
    name="clickup_delete_checklist",
    annotations={
        "title": "Deletar Checklist",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def delete_checklist(params: DeleteChecklistInput) -> str:
    """
    Deleta um checklist e todos os seus itens.
    """
    try:
        check_write_permission("delete_checklist")

        await api_request("DELETE", f"/checklist/{params.checklist_id}")

        return f"✅ Checklist `{params.checklist_id}` deletado!"
    except Exception as e:
        return f"Erro ao deletar checklist: {str(e)}"


class CreateChecklistItemInput(BaseModel):
    """Input para criar item em checklist."""
    model_config = ConfigDict(str_strip_whitespace=True)
    checklist_id: str = Field(..., description="ID do checklist", min_length=1)
    name: str = Field(..., description="Nome/texto do item", min_length=1, max_length=500)
    assignee: Optional[int] = Field(default=None, description="ID do responsável pelo item")


@mcp.tool(
    name="clickup_create_checklist_item",
    annotations={
        "title": "Criar Item no Checklist",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_checklist_item(params: CreateChecklistItemInput) -> str:
    """
    Adiciona um item a um checklist existente.
    """
    try:
        check_write_permission("create_checklist_item")

        json_data = {"name": params.name}
        if params.assignee:
            json_data["assignee"] = params.assignee

        data = await api_request("POST", f"/checklist/{params.checklist_id}/checklist_item", json_data=json_data)

        checklist = data.get("checklist", {})
        items = checklist.get("items", [])
        new_item = items[-1] if items else {}

        return f"✅ Item adicionado!\n- **Item:** {new_item.get('name', params.name)}\n- **ID:** `{new_item.get('id', 'N/A')}`"
    except Exception as e:
        return f"Erro ao criar item: {str(e)}"


class UpdateChecklistItemInput(BaseModel):
    """Input para atualizar item do checklist."""
    model_config = ConfigDict(str_strip_whitespace=True)
    checklist_id: str = Field(..., description="ID do checklist", min_length=1)
    checklist_item_id: str = Field(..., description="ID do item", min_length=1)
    name: Optional[str] = Field(default=None, description="Novo nome/texto do item")
    resolved: Optional[bool] = Field(default=None, description="Marcar como concluído (true) ou pendente (false)")
    assignee: Optional[int] = Field(default=None, description="ID do responsável")
    parent: Optional[str] = Field(default=None, description="ID do item pai (para criar sub-itens)")


@mcp.tool(
    name="clickup_update_checklist_item",
    annotations={
        "title": "Atualizar Item do Checklist",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def update_checklist_item(params: UpdateChecklistItemInput) -> str:
    """
    Atualiza um item do checklist (nome, status, responsável).

    Use resolved=true para marcar como concluído.
    """
    try:
        check_write_permission("update_checklist_item")

        json_data = {}
        if params.name:
            json_data["name"] = params.name
        if params.resolved is not None:
            json_data["resolved"] = params.resolved
        if params.assignee is not None:
            json_data["assignee"] = params.assignee
        if params.parent:
            json_data["parent"] = params.parent

        await api_request("PUT", f"/checklist/{params.checklist_id}/checklist_item/{params.checklist_item_id}", json_data=json_data)

        status = "✅ concluído" if params.resolved else "⬜ pendente" if params.resolved is False else ""
        return f"✅ Item atualizado! {status}"
    except Exception as e:
        return f"Erro ao atualizar item: {str(e)}"


class DeleteChecklistItemInput(BaseModel):
    """Input para deletar item do checklist."""
    model_config = ConfigDict(str_strip_whitespace=True)
    checklist_id: str = Field(..., description="ID do checklist", min_length=1)
    checklist_item_id: str = Field(..., description="ID do item a deletar", min_length=1)


@mcp.tool(
    name="clickup_delete_checklist_item",
    annotations={
        "title": "Deletar Item do Checklist",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def delete_checklist_item(params: DeleteChecklistItemInput) -> str:
    """
    Deleta um item de um checklist.
    """
    try:
        check_write_permission("delete_checklist_item")

        await api_request("DELETE", f"/checklist/{params.checklist_id}/checklist_item/{params.checklist_item_id}")

        return f"✅ Item `{params.checklist_item_id}` deletado do checklist!"
    except Exception as e:
        return f"Erro ao deletar item: {str(e)}"


# ============================================================================
# TOOLS - TIMER (START/STOP)
# ============================================================================

class StartTimeEntryInput(BaseModel):
    """Input para iniciar timer."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)
    task_id: Optional[str] = Field(default=None, description="ID da task (opcional)")
    description: Optional[str] = Field(default=None, description="Descrição do que está fazendo")
    billable: bool = Field(default=False, description="Se é hora faturável")


@mcp.tool(
    name="clickup_start_timer",
    annotations={
        "title": "Iniciar Timer",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def start_timer(params: StartTimeEntryInput) -> str:
    """
    Inicia um timer de tracking de tempo.

    O timer fica rodando até você chamar clickup_stop_timer.
    Pode associar a uma task específica ou não.
    """
    try:
        check_write_permission("start_timer")

        json_data = {"billable": params.billable}
        if params.task_id:
            json_data["tid"] = params.task_id
        if params.description:
            json_data["description"] = params.description

        data = await api_request("POST", f"/team/{params.team_id}/time_entries/start", json_data=json_data)

        entry = data.get("data", {})
        return f"⏱️ Timer iniciado!\n- **ID:** `{entry.get('id')}`\n- **Task:** {params.task_id or 'Nenhuma'}\n- **Billable:** {'Sim' if params.billable else 'Não'}"
    except Exception as e:
        return f"Erro ao iniciar timer: {str(e)}"


class StopTimeEntryInput(BaseModel):
    """Input para parar timer."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)


@mcp.tool(
    name="clickup_stop_timer",
    annotations={
        "title": "Parar Timer",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def stop_timer(params: StopTimeEntryInput) -> str:
    """
    Para o timer em execução e salva o tempo registrado.
    """
    try:
        check_write_permission("stop_timer")

        data = await api_request("POST", f"/team/{params.team_id}/time_entries/stop")

        entry = data.get("data", {})
        duration_ms = entry.get("duration", 0)
        duration_min = int(duration_ms) // 60000 if duration_ms else 0

        return f"⏹️ Timer parado!\n- **Duração:** {duration_min} minutos\n- **ID:** `{entry.get('id')}`"
    except Exception as e:
        return f"Erro ao parar timer: {str(e)}"


class GetRunningTimeEntryInput(BaseModel):
    """Input para obter timer em execução."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)


@mcp.tool(
    name="clickup_get_running_timer",
    annotations={
        "title": "Ver Timer em Execução",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_running_timer(params: GetRunningTimeEntryInput) -> str:
    """
    Mostra o timer atualmente em execução (se houver).
    """
    try:
        data = await api_request("GET", f"/team/{params.team_id}/time_entries/current")

        entry = data.get("data")
        if not entry:
            return "⏸️ Nenhum timer em execução."

        task = entry.get("task", {})
        task_name = task.get("name", "Sem task") if task else "Sem task"
        start = entry.get("start")
        start_fmt = format_timestamp(start) if start else "N/A"

        return f"⏱️ Timer em execução!\n- **Task:** {task_name}\n- **Início:** {start_fmt}\n- **Billable:** {'Sim' if entry.get('billable') else 'Não'}"
    except Exception as e:
        return f"Erro ao obter timer: {str(e)}"


# ============================================================================
# TOOLS - TEMPLATES
# ============================================================================

class GetTaskTemplatesInput(BaseModel):
    """Input para listar templates de tasks."""
    model_config = ConfigDict(str_strip_whitespace=True)
    team_id: str = Field(..., description="ID do workspace/team", min_length=1)
    page: int = Field(default=0, description="Página de resultados (começa em 0)")
    output_mode: OutputMode = Field(default=OutputMode.COMPACT, description="Modo de output")


@mcp.tool(
    name="clickup_get_task_templates",
    annotations={
        "title": "Listar Templates de Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_task_templates(params: GetTaskTemplatesInput) -> str:
    """
    Lista todos os templates de tasks disponíveis no workspace.

    Use o ID do template com clickup_create_task_from_template.
    """
    try:
        data = await api_request("GET", f"/team/{params.team_id}/taskTemplate", params={"page": params.page})
        templates = data.get("templates", [])

        if params.output_mode == OutputMode.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)

        if not templates:
            return "Nenhum template encontrado."

        if params.output_mode == OutputMode.COMPACT:
            lines = [f"**{len(templates)} templates:**\n"]
            for tpl in templates:
                name = tpl.get('name', 'Sem nome')
                tpl_id = tpl.get('id', '')
                lines.append(f"- {name} | `{tpl_id}`")
            return "\n".join(lines)

        # DETAILED
        lines = ["# Templates de Tasks\n"]
        for tpl in templates:
            lines.append(f"## {tpl.get('name', 'Sem nome')}")
            lines.append(f"- **ID:** `{tpl.get('id')}`")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Erro ao listar templates: {str(e)}"


class CreateTaskFromTemplateInput(BaseModel):
    """Input para criar task a partir de template."""
    model_config = ConfigDict(str_strip_whitespace=True)
    list_id: str = Field(..., description="ID da list onde criar a task", min_length=1)
    template_id: str = Field(..., description="ID do template", min_length=1)
    name: str = Field(..., description="Nome da nova task", min_length=1, max_length=500)


@mcp.tool(
    name="clickup_create_task_from_template",
    annotations={
        "title": "Criar Task a partir de Template",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_task_from_template(params: CreateTaskFromTemplateInput) -> str:
    """
    Cria uma nova task baseada em um template existente.

    A task herdará descrição, checklists, custom fields e outros atributos do template.
    """
    try:
        check_write_permission("create_task_from_template")

        json_data = {"name": params.name}
        data = await api_request("POST", f"/list/{params.list_id}/taskTemplate/{params.template_id}", json_data=json_data)

        task = data.get("task", data)
        return f"✅ Task criada a partir do template!\n- **Nome:** {task.get('name')}\n- **ID:** `{task.get('id')}`\n- **URL:** {task.get('url', 'N/A')}"
    except Exception as e:
        return f"Erro ao criar task do template: {str(e)}"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    mcp.run()
