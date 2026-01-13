"""
Testes para funções de formatação e infraestrutura.

Testes ativos:
- extract_tipo_subtipo: 5 testes
- format_timestamp: 3 testes
- format_tasks_compact: 3 testes
- format_tasks_detailed: 2 testes
- OutputMode: 2 testes
- Correlation ID: 2 testes
- Metrics: 2 testes
- Cache: 2 testes
"""
import pytest
import sys
import os

# Adiciona src ao path para importar o módulo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from clickup_mcp import (
    extract_tipo_subtipo,
    format_timestamp,
    format_tasks_compact,
    format_tasks_detailed,
    OutputMode,
    get_correlation_id,
    set_new_correlation_id,
    Metrics,
    cache_key,
    get_cached,
    set_cached
)


class TestExtractTipoSubtipo:
    """Testes para extração de Tipo e Subtipo do nome da task."""

    def test_tipo_e_subtipo(self):
        """Deve extrair tipo e subtipo corretamente."""
        tipo, subtipo = extract_tipo_subtipo("Notificação Extrajudicial - Pirataria")
        assert tipo == "Notificação Extrajudicial"
        assert subtipo == "Pirataria"

    def test_apenas_tipo(self):
        """Deve retornar apenas tipo quando não há subtipo."""
        tipo, subtipo = extract_tipo_subtipo("Acordo de Sócios")
        assert tipo == "Acordo de Sócios"
        assert subtipo is None

    def test_com_prefixo_numerico(self):
        """Deve ignorar prefixo numérico."""
        tipo, subtipo = extract_tipo_subtipo("3 - Contrato - Empresarial")
        assert tipo == "Contrato"
        assert subtipo == "Empresarial"

    def test_nome_vazio(self):
        """Deve retornar None para nome vazio."""
        tipo, subtipo = extract_tipo_subtipo("")
        assert tipo is None
        assert subtipo is None

    def test_tres_partes(self):
        """Deve pegar apenas tipo e subtipo, ignorando terceira parte."""
        tipo, subtipo = extract_tipo_subtipo("Pedido de Registro - INPI - Nome da Marca")
        assert tipo == "Pedido de Registro"
        assert subtipo == "INPI"


class TestFormatTimestamp:
    """Testes para formatação de timestamps."""

    def test_timestamp_valido(self):
        """Deve formatar timestamp em milissegundos."""
        result = format_timestamp(1704067200000)
        assert result is not None
        # Pode variar por fuso horário, verifica formato YYYY-MM-DD HH:MM:SS
        assert len(result) == 19  # "2024-01-01 00:00:00"
        assert "-" in result and ":" in result

    def test_timestamp_none(self):
        """Deve retornar None para input None."""
        result = format_timestamp(None)
        assert result is None

    def test_timestamp_invalido(self):
        """Deve retornar string para timestamp inválido."""
        result = format_timestamp("invalid")
        assert result == "invalid"


class TestFormatTasksCompact:
    """Testes para formatação compacta de tasks."""

    def test_formato_compacto(self, mock_tasks):
        """Deve gerar no máximo 2 linhas por task."""
        result = format_tasks_compact(mock_tasks)
        lines = result.strip().split("\n")
        # Header + 10 tasks = 11 linhas (não 120)
        assert len(lines) <= 15

    def test_trunca_nome_longo(self, mock_task):
        """Deve truncar nomes maiores que 60 caracteres."""
        mock_task["name"] = "A" * 100
        result = format_tasks_compact([mock_task])
        # Nome truncado, resultado curto
        assert len(result) < 200

    def test_aviso_paginacao(self, mock_tasks):
        """Deve avisar quando há mais páginas."""
        # 25 tasks com limit=25 deve mostrar aviso
        tasks_25 = mock_tasks * 3  # 30 tasks > 25
        result = format_tasks_compact(tasks_25[:25], total=30, page=0, limit=25)
        assert "page=" in result.lower()


class TestFormatTasksDetailed:
    """Testes para formatação detalhada de tasks."""

    def test_formato_detalhado(self, mock_task):
        """Deve incluir todos os campos."""
        result = format_tasks_detailed([mock_task])
        assert "ID:" in result
        assert "Status:" in result
        assert "Tipo:" in result
        assert "Cliente:" in result

    def test_inclui_url(self, mock_task):
        """Deve incluir URL se presente."""
        result = format_tasks_detailed([mock_task])
        assert "URL:" in result


class TestOutputMode:
    """Testes para o enum OutputMode."""

    def test_valores_enum(self):
        """Deve ter os três modos definidos."""
        assert OutputMode.COMPACT.value == "compact"
        assert OutputMode.DETAILED.value == "detailed"
        assert OutputMode.JSON.value == "json"

    def test_default_compact(self):
        """COMPACT deve ser acessível."""
        assert OutputMode.COMPACT is not None
        assert OutputMode.COMPACT == OutputMode("compact")


class TestCorrelationID:
    """Testes para Correlation ID (Sprint 4)."""

    def test_get_correlation_id(self):
        """Deve retornar um ID."""
        cid = get_correlation_id()
        assert cid is not None
        assert isinstance(cid, str)

    def test_set_new_correlation_id(self):
        """Deve gerar novo ID de 8 caracteres."""
        cid = set_new_correlation_id()
        assert len(cid) == 8
        # Deve ser diferente a cada chamada
        cid2 = set_new_correlation_id()
        assert cid != cid2


class TestMetrics:
    """Testes para Métricas (Sprint 4)."""

    def test_record_and_summary(self):
        """Deve registrar e retornar métricas."""
        metrics = Metrics()
        metrics.record_tool_call("test_tool")
        metrics.record_tool_call("test_tool")
        metrics.record_cache_hit()
        metrics.record_api_call()

        summary = metrics.get_summary()
        assert summary["tool_calls"]["test_tool"] == 2
        assert summary["cache_hits"] == 1
        assert summary["api_calls"] == 1

    def test_cache_hit_rate(self):
        """Deve calcular cache hit rate corretamente."""
        metrics = Metrics()
        metrics.record_cache_hit()
        metrics.record_cache_hit()
        metrics.record_cache_miss()

        summary = metrics.get_summary()
        # 2 hits / 3 total = 0.666...
        assert 0.66 < summary["cache_hit_rate"] < 0.67


class TestCache:
    """Testes para Cache (Sprint 3)."""

    def test_cache_key(self):
        """Deve gerar chave única."""
        key1 = cache_key("/test", {"a": 1})
        key2 = cache_key("/test", {"a": 2})
        key3 = cache_key("/test", {"a": 1})

        assert key1 != key2
        assert key1 == key3

    def test_set_and_get_cached(self):
        """Deve armazenar e recuperar do cache."""
        test_data = {"test": "data"}
        set_cached("/test/endpoint", test_data, {"param": "value"})

        result = get_cached("/test/endpoint", {"param": "value"})
        assert result == test_data
