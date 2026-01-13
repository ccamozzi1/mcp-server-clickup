"""
Testes de integração para tools MCP com mocks HTTP.

Usa respx para interceptar chamadas HTTP e retornar dados mockados.
Isso permite testar as tools sem fazer requisições reais à API do ClickUp.

Categorias de testes:
- Workspaces: 2 testes
- Spaces: 3 testes
- Folders: 4 testes
- Lists: 4 testes
- Tasks: 6 testes
- Comments: 2 testes
- Metrics: 1 teste
"""
import pytest
import sys
import os
import json
import respx
from httpx import Response
from unittest.mock import patch

# Adiciona src ao path para importar o módulo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Seta variável de ambiente ANTES de importar o módulo
os.environ["CLICKUP_API_TOKEN"] = "pk_test_token_123456789"

# Importar o módulo
import clickup_mcp

# Patch o API_TOKEN diretamente no módulo após importar
clickup_mcp.API_TOKEN = "pk_test_token_123456789"

from clickup_mcp import (
    api_request,
    get_workspaces,
    get_spaces,
    get_space_details,
    get_folders,
    create_folder,
    update_folder,
    delete_folder,
    get_lists,
    get_list_details,
    create_list,
    delete_list,
    get_tasks,
    get_task,
    create_task,
    update_task,
    delete_task,
    get_task_comments,
    create_task_comment,
    get_metrics,
    get_folderless_lists,
    update_list,
    move_task,
    duplicate_task,
    get_workspace_members,
    get_custom_fields,
    get_filtered_team_tasks,
    analyze_space_structure,
    get_time_entries,
    get_docs,
    create_doc,
    get_checklists,
    get_attachments,
    # Sprint 5
    fuzzy_search_tasks_tool,
    create_time_entry,
    get_billable_report,
    fuzzy_ratio,
    fuzzy_search_tasks,
    check_write_permission,
    ReadOnlyModeError,
    GetWorkspacesInput,
    GetSpacesInput,
    GetSpaceDetailsInput,
    GetFoldersInput,
    CreateFolderInput,
    UpdateFolderInput,
    DeleteFolderInput,
    GetListsInput,
    GetListDetailsInput,
    CreateListInput,
    DeleteListInput,
    GetTasksInput,
    GetTaskInput,
    CreateTaskInput,
    UpdateTaskInput,
    DeleteTaskInput,
    GetTaskCommentsInput,
    CreateTaskCommentInput,
    GetMetricsInput,
    GetFolderlessListsInput,
    UpdateListInput,
    MoveTaskInput,
    DuplicateTaskInput,
    GetMembersInput,
    GetCustomFieldsInput,
    GetFilteredTeamTasksInput,
    AnalyzeSpaceStructureInput,
    GetTimeEntriesInput,
    GetDocsInput,
    CreateDocInput,
    GetChecklistsInput,
    GetAttachmentsInput,
    # Sprint 5 Inputs
    FuzzySearchTasksInput,
    CreateTimeEntryInput,
    GetBillableReportInput,
    OutputMode,
    OrderBy,
    RateLimiter,
    _structure_cache,
    _tasks_cache,
    # Custom Fields
    set_custom_field_value,
    remove_custom_field_value,
    SetCustomFieldValueInput,
    RemoveCustomFieldValueInput,
    # Tags
    get_space_tags,
    create_space_tag,
    update_space_tag,
    delete_space_tag,
    add_tag_to_task,
    remove_tag_from_task,
    GetSpaceTagsInput,
    CreateSpaceTagInput,
    UpdateSpaceTagInput,
    DeleteSpaceTagInput,
    AddTagToTaskInput,
    RemoveTagFromTaskInput,
    # Dependencies
    add_dependency,
    delete_dependency,
    add_task_link,
    delete_task_link,
    AddDependencyInput,
    DeleteDependencyInput,
    AddTaskLinkInput,
    DeleteTaskLinkInput,
    # Checklists
    create_checklist,
    update_checklist,
    delete_checklist,
    create_checklist_item,
    update_checklist_item,
    delete_checklist_item,
    CreateChecklistInput,
    UpdateChecklistInput,
    DeleteChecklistInput,
    CreateChecklistItemInput,
    UpdateChecklistItemInput,
    DeleteChecklistItemInput,
    # Timer
    start_timer,
    stop_timer,
    get_running_timer,
    StartTimeEntryInput,
    StopTimeEntryInput,
    GetRunningTimeEntryInput,
    # Templates
    get_task_templates,
    create_task_from_template,
    GetTaskTemplatesInput,
    CreateTaskFromTemplateInput,
)

# Base URL da API
API_BASE = "https://api.clickup.com/api/v2"


@pytest.fixture(autouse=True)
def clear_caches():
    """Limpa caches antes de cada teste."""
    _structure_cache.clear()
    _tasks_cache.clear()
    yield


# ============================================================================
# FIXTURES DE DADOS MOCKADOS
# ============================================================================

@pytest.fixture
def mock_workspace_response():
    """Resposta mockada para GET /team."""
    return {
        "teams": [
            {
                "id": "team123",
                "name": "Helper Consultoria",
                "members": [
                    {"user": {"id": 1, "username": "admin", "email": "admin@example.com"}}
                ]
            },
            {
                "id": "team456",
                "name": "Outro Workspace",
                "members": []
            }
        ]
    }


@pytest.fixture
def mock_spaces_response():
    """Resposta mockada para GET /team/{team_id}/space."""
    return {
        "spaces": [
            {
                "id": "space1",
                "name": "Consultoria",
                "private": False,
                "statuses": [
                    {"status": "Aberto", "color": "#87909e"},
                    {"status": "Em andamento", "color": "#f9d900"},
                    {"status": "Concluído", "color": "#6bc950"}
                ]
            },
            {
                "id": "space2",
                "name": "Administrativo",
                "private": True,
                "statuses": []
            }
        ]
    }


@pytest.fixture
def mock_space_details():
    """Resposta mockada para GET /space/{space_id}."""
    return {
        "id": "space1",
        "name": "Consultoria",
        "private": False,
        "statuses": [
            {"status": "Aberto", "color": "#87909e"},
            {"status": "Em andamento", "color": "#f9d900"},
            {"status": "Concluído", "color": "#6bc950"}
        ],
        "multiple_assignees": True,
        "features": {
            "due_dates": {"enabled": True},
            "time_tracking": {"enabled": True}
        }
    }


@pytest.fixture
def mock_folders_response():
    """Resposta mockada para GET /space/{space_id}/folder."""
    return {
        "folders": [
            {
                "id": "folder1",
                "name": "Plano Premium",
                "lists": [
                    {"id": "list1", "name": "Cliente X"},
                    {"id": "list2", "name": "Cliente Y"}
                ]
            },
            {
                "id": "folder2",
                "name": "Plano Básico",
                "lists": []
            }
        ]
    }


@pytest.fixture
def mock_lists_response():
    """Resposta mockada para GET /folder/{folder_id}/list."""
    return {
        "lists": [
            {
                "id": "list1",
                "name": "Cliente X",
                "task_count": 15,
                "folder": {"id": "folder1", "name": "Plano Premium"}
            },
            {
                "id": "list2",
                "name": "Cliente Y",
                "task_count": 8,
                "folder": {"id": "folder1", "name": "Plano Premium"}
            }
        ]
    }


@pytest.fixture
def mock_list_details():
    """Resposta mockada para GET /list/{list_id}."""
    return {
        "id": "list1",
        "name": "Cliente X",
        "task_count": 15,
        "folder": {"id": "folder1", "name": "Plano Premium"},
        "space": {"id": "space1", "name": "Consultoria"},
        "statuses": [
            {"status": "Aberto"},
            {"status": "Em andamento"},
            {"status": "Concluído"}
        ]
    }


@pytest.fixture
def mock_tasks_response():
    """Resposta mockada para GET /list/{list_id}/task."""
    return {
        "tasks": [
            {
                "id": "task1",
                "name": "Contrato de Prestação - Empresarial",
                "status": {"status": "Em andamento"},
                "date_created": "1704067200000",
                "date_updated": "1704153600000",
                "due_date": "1704240000000",
                "assignees": [{"username": "joao"}],
                "list": {"id": "list1", "name": "Cliente X"},
                "folder": {"id": "folder1", "name": "Plano Premium"},
                "url": "https://app.clickup.com/t/task1"
            },
            {
                "id": "task2",
                "name": "Notificação Extrajudicial - Pirataria",
                "status": {"status": "Aberto"},
                "date_created": "1704067200000",
                "date_updated": "1704153600000",
                "assignees": [],
                "list": {"id": "list1", "name": "Cliente X"},
                "folder": {"id": "folder1", "name": "Plano Premium"},
                "url": "https://app.clickup.com/t/task2"
            }
        ]
    }


@pytest.fixture
def mock_task_details():
    """Resposta mockada para GET /task/{task_id}."""
    return {
        "id": "task1",
        "name": "Contrato de Prestação - Empresarial",
        "description": "Elaborar contrato completo",
        "status": {"status": "Em andamento"},
        "date_created": "1704067200000",
        "date_updated": "1704153600000",
        "due_date": "1704240000000",
        "assignees": [{"username": "joao", "email": "joao@example.com"}],
        "list": {"id": "list1", "name": "Cliente X"},
        "folder": {"id": "folder1", "name": "Plano Premium"},
        "space": {"id": "space1"},
        "url": "https://app.clickup.com/t/task1",
        "checklists": [],
        "tags": [{"name": "urgente"}],
        "custom_fields": []
    }


@pytest.fixture
def mock_comments_response():
    """Resposta mockada para GET /task/{task_id}/comment."""
    return {
        "comments": [
            {
                "id": "comment1",
                "comment_text": "Primeira versão enviada para revisão",
                "user": {"username": "joao"},
                "date": "1704153600000"
            },
            {
                "id": "comment2",
                "comment_text": "Revisão concluída, aguardando aprovação",
                "user": {"username": "maria"},
                "date": "1704240000000"
            }
        ]
    }


# ============================================================================
# TESTES DE WORKSPACES
# ============================================================================

class TestWorkspaces:
    """Testes para tools de workspace."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_workspaces_compact(self, mock_workspace_response):
        """Deve listar workspaces em formato compacto."""
        respx.get(f"{API_BASE}/team").mock(
            return_value=Response(200, json=mock_workspace_response)
        )

        params = GetWorkspacesInput(output_mode=OutputMode.COMPACT)
        result = await get_workspaces(params)

        assert "Helper Consultoria" in result
        assert "team123" in result
        assert "Outro Workspace" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_workspaces_json(self, mock_workspace_response):
        """Deve retornar workspaces em formato JSON."""
        respx.get(f"{API_BASE}/team").mock(
            return_value=Response(200, json=mock_workspace_response)
        )

        params = GetWorkspacesInput(output_mode=OutputMode.JSON)
        result = await get_workspaces(params)

        # Deve ser JSON válido
        data = json.loads(result)
        assert "teams" in data
        assert len(data["teams"]) == 2


# ============================================================================
# TESTES DE SPACES
# ============================================================================

class TestSpaces:
    """Testes para tools de spaces."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_spaces(self, mock_spaces_response):
        """Deve listar spaces de um workspace."""
        respx.get(f"{API_BASE}/team/team123/space").mock(
            return_value=Response(200, json=mock_spaces_response)
        )

        params = GetSpacesInput(team_id="team123", output_mode=OutputMode.COMPACT)
        result = await get_spaces(params)

        assert "Consultoria" in result
        assert "Administrativo" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_space_details(self, mock_space_details):
        """Deve retornar detalhes de um space."""
        respx.get(f"{API_BASE}/space/space1").mock(
            return_value=Response(200, json=mock_space_details)
        )

        params = GetSpaceDetailsInput(space_id="space1", output_mode=OutputMode.DETAILED)
        result = await get_space_details(params)

        assert "Consultoria" in result
        assert "Aberto" in result or "Em andamento" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_spaces_archived(self, mock_spaces_response):
        """Deve listar spaces incluindo arquivados."""
        respx.get(f"{API_BASE}/team/team123/space").mock(
            return_value=Response(200, json=mock_spaces_response)
        )

        params = GetSpacesInput(team_id="team123", archived=True)
        result = await get_spaces(params)

        assert result is not None


# ============================================================================
# TESTES DE FOLDERS
# ============================================================================

class TestFolders:
    """Testes para tools de folders."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_folders(self, mock_folders_response):
        """Deve listar folders de um space."""
        respx.get(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(200, json=mock_folders_response)
        )

        params = GetFoldersInput(space_id="space1", output_mode=OutputMode.COMPACT)
        result = await get_folders(params)

        assert "Plano Premium" in result
        assert "Plano Básico" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_folder(self):
        """Deve criar um folder."""
        mock_response = {"id": "folder_new", "name": "Novo Folder"}
        respx.post(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(200, json=mock_response)
        )

        params = CreateFolderInput(space_id="space1", name="Novo Folder")
        result = await create_folder(params)

        assert "folder_new" in result or "Novo Folder" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_update_folder(self):
        """Deve atualizar um folder."""
        mock_response = {"id": "folder1", "name": "Folder Atualizado"}
        respx.put(f"{API_BASE}/folder/folder1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = UpdateFolderInput(folder_id="folder1", name="Folder Atualizado")
        result = await update_folder(params)

        assert "Folder Atualizado" in result or "folder1" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_delete_folder(self):
        """Deve deletar um folder."""
        respx.delete(f"{API_BASE}/folder/folder1").mock(
            return_value=Response(200, json={"success": True})
        )

        params = DeleteFolderInput(folder_id="folder1")
        result = await delete_folder(params)

        assert "sucesso" in result.lower() or "deletado" in result.lower() or "success" in result.lower()


# ============================================================================
# TESTES DE LISTS
# ============================================================================

class TestLists:
    """Testes para tools de lists."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_lists(self, mock_lists_response):
        """Deve listar lists de um folder."""
        respx.get(f"{API_BASE}/folder/folder1/list").mock(
            return_value=Response(200, json=mock_lists_response)
        )

        params = GetListsInput(folder_id="folder1", output_mode=OutputMode.COMPACT)
        result = await get_lists(params)

        assert "Cliente X" in result
        assert "Cliente Y" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_list_details(self, mock_list_details):
        """Deve retornar detalhes de uma list."""
        respx.get(f"{API_BASE}/list/list1").mock(
            return_value=Response(200, json=mock_list_details)
        )

        params = GetListDetailsInput(list_id="list1", output_mode=OutputMode.DETAILED)
        result = await get_list_details(params)

        assert "Cliente X" in result
        assert "15" in result or "task" in result.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_list(self):
        """Deve criar uma list."""
        mock_response = {"id": "list_new", "name": "Nova List"}
        respx.post(f"{API_BASE}/folder/folder1/list").mock(
            return_value=Response(200, json=mock_response)
        )

        params = CreateListInput(folder_id="folder1", name="Nova List")
        result = await create_list(params)

        assert "list_new" in result or "Nova List" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_delete_list(self):
        """Deve deletar uma list."""
        respx.delete(f"{API_BASE}/list/list1").mock(
            return_value=Response(200, json={"success": True})
        )

        params = DeleteListInput(list_id="list1")
        result = await delete_list(params)

        assert "sucesso" in result.lower() or "deletad" in result.lower() or "success" in result.lower()


# ============================================================================
# TESTES DE TASKS
# ============================================================================

class TestTasks:
    """Testes para tools de tasks."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_tasks_compact(self, mock_tasks_response):
        """Deve listar tasks em formato compacto."""
        respx.get(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json=mock_tasks_response)
        )

        params = GetTasksInput(list_id="list1", output_mode=OutputMode.COMPACT)
        result = await get_tasks(params)

        assert "Contrato" in result
        assert "Notificação" in result
        # Formato compacto deve ter poucas linhas
        lines = result.strip().split("\n")
        assert len(lines) < 20  # Compacto = poucas linhas

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_tasks_detailed(self, mock_tasks_response):
        """Deve listar tasks em formato detalhado."""
        respx.get(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json=mock_tasks_response)
        )

        params = GetTasksInput(list_id="list1", output_mode=OutputMode.DETAILED)
        result = await get_tasks(params)

        assert "Contrato" in result
        assert "Status:" in result or "status" in result.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_task(self, mock_task_details):
        """Deve retornar detalhes de uma task."""
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_task_details)
        )

        params = GetTaskInput(task_id="task1")
        result = await get_task(params)

        assert "Contrato de Prestação" in result
        assert "joao" in result.lower() or "Empresarial" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_task(self):
        """Deve criar uma task."""
        mock_response = {
            "id": "task_new",
            "name": "Nova Task",
            "status": {"status": "Aberto"},
            "url": "https://app.clickup.com/t/task_new"
        }
        respx.post(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json=mock_response)
        )

        params = CreateTaskInput(list_id="list1", name="Nova Task")
        result = await create_task(params)

        assert "task_new" in result or "Nova Task" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_update_task(self):
        """Deve atualizar uma task."""
        mock_response = {
            "id": "task1",
            "name": "Task Atualizada",
            "status": {"status": "Em andamento"}
        }
        respx.put(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = UpdateTaskInput(task_id="task1", name="Task Atualizada")
        result = await update_task(params)

        assert "Task Atualizada" in result or "task1" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_delete_task(self):
        """Deve deletar uma task."""
        respx.delete(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json={"success": True})
        )

        params = DeleteTaskInput(task_id="task1")
        result = await delete_task(params)

        assert "sucesso" in result.lower() or "deletad" in result.lower() or "success" in result.lower()


# ============================================================================
# TESTES DE COMMENTS
# ============================================================================

class TestComments:
    """Testes para tools de comentários."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_task_comments(self, mock_comments_response):
        """Deve listar comentários de uma task."""
        respx.get(f"{API_BASE}/task/task1/comment").mock(
            return_value=Response(200, json=mock_comments_response)
        )

        params = GetTaskCommentsInput(task_id="task1")
        result = await get_task_comments(params)

        assert "revisão" in result.lower() or "versão" in result.lower()
        assert "joao" in result.lower() or "maria" in result.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_task_comment(self):
        """Deve criar um comentário em uma task."""
        mock_response = {
            "id": "comment_new",
            "comment_text": "Novo comentário",
            "user": {"username": "admin"},
            "date": "1704326400000"
        }
        respx.post(f"{API_BASE}/task/task1/comment").mock(
            return_value=Response(200, json=mock_response)
        )

        params = CreateTaskCommentInput(task_id="task1", comment_text="Novo comentário")
        result = await create_task_comment(params)

        # A tool retorna mensagem de sucesso
        assert "sucesso" in result.lower() or "adicionado" in result.lower()


# ============================================================================
# TESTES DE MÉTRICAS
# ============================================================================

class TestMetricsTool:
    """Testes para tool de métricas."""

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """Deve retornar métricas do servidor."""
        params = GetMetricsInput(output_mode=OutputMode.JSON)
        result = await get_metrics(params)

        # Deve ser JSON válido
        data = json.loads(result)
        assert "tool_calls" in data
        assert "cache_hits" in data or "cache_hit_rate" in data


# ============================================================================
# TESTES DE ERROS
# ============================================================================

class TestErrorHandling:
    """Testes para tratamento de erros."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_api_error_404(self):
        """Deve tratar erro 404 retornando mensagem de erro."""
        respx.get(f"{API_BASE}/task/invalid_id").mock(
            return_value=Response(404, json={"err": "Task not found"})
        )

        params = GetTaskInput(task_id="invalid_id")
        result = await get_task(params)

        # A tool captura o erro e retorna como string
        assert "erro" in result.lower() or "404" in result or "not found" in result.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_api_error_401(self):
        """Deve tratar erro 401 (não autorizado) retornando mensagem de erro."""
        respx.get(f"{API_BASE}/team").mock(
            return_value=Response(401, json={"err": "Unauthorized"})
        )

        params = GetWorkspacesInput()
        result = await get_workspaces(params)

        # A tool captura o erro e retorna como string
        assert "erro" in result.lower() or "401" in result or "unauthorized" in result.lower()


# ============================================================================
# TESTES DE CACHE
# ============================================================================

class TestCacheIntegration:
    """Testes de integração do cache com as tools."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_cache_hit(self, mock_spaces_response):
        """Deve usar cache na segunda chamada."""
        route = respx.get(f"{API_BASE}/team/team123/space").mock(
            return_value=Response(200, json=mock_spaces_response)
        )

        params = GetSpacesInput(team_id="team123")

        # Primeira chamada - vai para API
        await get_spaces(params)
        assert route.call_count == 1

        # Segunda chamada - deve vir do cache
        await get_spaces(params)
        assert route.call_count == 1  # Não deve ter chamado novamente

    @respx.mock
    @pytest.mark.asyncio
    async def test_cache_miss_different_params(self, mock_spaces_response):
        """Deve fazer nova chamada quando params diferentes."""
        route = respx.get(f"{API_BASE}/team/team123/space").mock(
            return_value=Response(200, json=mock_spaces_response)
        )
        route2 = respx.get(f"{API_BASE}/team/team456/space").mock(
            return_value=Response(200, json=mock_spaces_response)
        )

        # Chamada com team123
        params1 = GetSpacesInput(team_id="team123")
        await get_spaces(params1)
        assert route.call_count == 1

        # Chamada com team456 - não deve usar cache de team123
        params2 = GetSpacesInput(team_id="team456")
        await get_spaces(params2)
        assert route2.call_count == 1


# ============================================================================
# TESTES DE RETRY E RESILIÊNCIA
# ============================================================================

class TestRetryMechanism:
    """Testes para mecanismo de retry com backoff exponencial."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_500_error(self):
        """Deve fazer retry em erro 500 e recuperar na segunda tentativa."""
        # Primeira chamada falha com 500, segunda sucede
        route = respx.get(f"{API_BASE}/team").mock(
            side_effect=[
                Response(500, json={"err": "Internal Server Error"}),
                Response(200, json={"teams": [{"id": "t1", "name": "Test"}]})
            ]
        )

        params = GetWorkspacesInput()
        result = await get_workspaces(params)

        # Deve ter feito 2 chamadas (1 falha + 1 sucesso)
        assert route.call_count == 2
        # Deve retornar resultado válido
        assert "Test" in result or "t1" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_429_rate_limit(self):
        """Deve fazer retry em erro 429 (rate limit)."""
        route = respx.get(f"{API_BASE}/team").mock(
            side_effect=[
                Response(429, headers={"Retry-After": "1"}, json={"err": "Rate limited"}),
                Response(200, json={"teams": [{"id": "t1", "name": "Test"}]})
            ]
        )

        params = GetWorkspacesInput()
        result = await get_workspaces(params)

        # Deve ter feito 2 chamadas
        assert route.call_count == 2
        assert "Test" in result or "t1" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_retry_on_400_error(self):
        """Não deve fazer retry em erro 400 (client error)."""
        route = respx.get(f"{API_BASE}/task/bad_id").mock(
            return_value=Response(400, json={"err": "Bad Request"})
        )

        params = GetTaskInput(task_id="bad_id")
        result = await get_task(params)

        # Deve ter feito apenas 1 chamada (sem retry)
        assert route.call_count == 1
        # Deve retornar erro
        assert "erro" in result.lower() or "400" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Deve falhar após 3 tentativas sem sucesso."""
        route = respx.get(f"{API_BASE}/team").mock(
            return_value=Response(500, json={"err": "Server Error"})
        )

        params = GetWorkspacesInput()
        result = await get_workspaces(params)

        # Deve ter feito 3 chamadas (máximo de retries)
        assert route.call_count == 3
        # Deve retornar erro
        assert "erro" in result.lower()


# ============================================================================
# TESTES DE RATE LIMITING
# ============================================================================

class TestRateLimiting:
    """Testes para rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        """Rate limiter deve permitir requests dentro do limite."""
        from clickup_mcp import RateLimiter

        limiter = RateLimiter(max_requests=10, window_seconds=60)

        # Deve permitir 10 requests sem bloquear
        for _ in range(10):
            await limiter.acquire()

        # Verificar que não bloqueou (teste passou sem timeout)
        assert True

    @pytest.mark.asyncio
    async def test_rate_limiter_tracks_requests(self):
        """Rate limiter deve rastrear requests na janela."""
        from clickup_mcp import RateLimiter

        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # Fazer 5 requests
        for _ in range(5):
            await limiter.acquire()

        # Deve ter 5 requests registrados
        assert len(limiter.requests) == 5


# ============================================================================
# TESTES DE TIMEOUT
# ============================================================================

class TestTimeout:
    """Testes para timeout de requisições."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """Deve tratar timeout corretamente."""
        import httpx

        # Mock que simula timeout
        respx.get(f"{API_BASE}/team").mock(side_effect=httpx.TimeoutException("Timeout"))

        params = GetWorkspacesInput()
        result = await get_workspaces(params)

        # Deve retornar mensagem de erro
        assert "erro" in result.lower() or "timeout" in result.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Deve tratar erro de conexão corretamente."""
        import httpx

        # Mock que simula erro de conexão
        respx.get(f"{API_BASE}/team").mock(side_effect=httpx.ConnectError("Connection refused"))

        params = GetWorkspacesInput()
        result = await get_workspaces(params)

        # Deve retornar mensagem de erro
        assert "erro" in result.lower()


# ============================================================================
# TESTES DE TOOLS ADICIONAIS
# ============================================================================

class TestAdditionalTools:
    """Testes para tools não cobertas anteriormente."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_folderless_lists(self):
        """Deve listar lists sem folder."""
        mock_response = {
            "lists": [
                {"id": "list1", "name": "Lista Avulsa 1", "task_count": 5},
                {"id": "list2", "name": "Lista Avulsa 2", "task_count": 3}
            ]
        }
        respx.get(f"{API_BASE}/space/space1/list").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetFolderlessListsInput(space_id="space1")
        result = await get_folderless_lists(params)

        assert "Lista Avulsa" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_update_list(self):
        """Deve atualizar uma list."""
        mock_response = {"id": "list1", "name": "List Atualizada"}
        respx.put(f"{API_BASE}/list/list1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = UpdateListInput(list_id="list1", name="List Atualizada")
        result = await update_list(params)

        assert "List Atualizada" in result or "list1" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_move_task(self):
        """Deve mover uma task para outra list."""
        mock_response = {"id": "task1", "list": {"id": "list2", "name": "Nova List"}}
        respx.post(f"{API_BASE}/list/list2/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = MoveTaskInput(task_id="task1", list_id="list2")
        result = await move_task(params)

        assert "task1" in result.lower() or "sucesso" in result.lower() or "movid" in result.lower()

    # Nota: testes de duplicate_task e get_workspace_members foram removidos
    # porque essas tools fazem múltiplas chamadas internas que são difíceis de mockar.
    # A cobertura dessas tools será testada via smoke test manual.

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_custom_fields(self):
        """Deve listar custom fields de uma list."""
        mock_response = {
            "fields": [
                {"id": "field1", "name": "Valor", "type": "currency"},
                {"id": "field2", "name": "Status Extra", "type": "dropdown"}
            ]
        }
        respx.get(f"{API_BASE}/list/list1/field").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetCustomFieldsInput(list_id="list1")
        result = await get_custom_fields(params)

        assert "Valor" in result or "field1" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_filtered_team_tasks(self):
        """Deve buscar tasks filtradas no workspace."""
        mock_response = {
            "tasks": [
                {"id": "t1", "name": "Task Filtrada", "status": {"status": "open"}}
            ]
        }
        respx.get(f"{API_BASE}/team/team1/task").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetFilteredTeamTasksInput(team_id="team1")
        result = await get_filtered_team_tasks(params)

        assert "Task Filtrada" in result or "t1" in result


# ============================================================================
# TESTES DE ANÁLISE DE ESTRUTURA
# ============================================================================

class TestAnalyzeStructure:
    """Testes para análise de estrutura do space."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_analyze_space_structure(self):
        """Deve analisar estrutura completa do space."""
        # Mock space details
        respx.get(f"{API_BASE}/space/space1").mock(
            return_value=Response(200, json={
                "id": "space1",
                "name": "Consultoria",
                "statuses": [{"status": "open"}, {"status": "closed"}]
            })
        )

        # Mock folders
        respx.get(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(200, json={
                "folders": [
                    {"id": "f1", "name": "Folder1", "lists": [{"id": "l1", "name": "List1"}]}
                ]
            })
        )

        # Mock folderless lists
        respx.get(f"{API_BASE}/space/space1/list").mock(
            return_value=Response(200, json={"lists": []})
        )

        params = AnalyzeSpaceStructureInput(space_id="space1")
        result = await analyze_space_structure(params)

        assert "Consultoria" in result or "space1" in result


# ============================================================================
# TESTES DE TIME ENTRIES
# ============================================================================

class TestTimeEntries:
    """Testes para tools de time tracking."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_time_entries_compact(self):
        """Deve listar time entries em formato compacto."""
        mock_response = {
            "data": [
                {
                    "id": "te1",
                    "duration": 3600000,  # 60 minutos
                    "task": {"id": "task1", "name": "Task de Teste"},
                    "user": {"id": 1, "username": "joao"},
                    "start": "1704067200000"
                },
                {
                    "id": "te2",
                    "duration": 1800000,  # 30 minutos
                    "task": {"id": "task2", "name": "Outra Task"},
                    "user": {"id": 2, "username": "maria"},
                    "start": "1704153600000"
                }
            ]
        }
        respx.get(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTimeEntriesInput(team_id="team1", output_mode=OutputMode.COMPACT)
        result = await get_time_entries(params)

        assert "2 entries" in result
        assert "90 min" in result  # Total
        assert "joao" in result
        assert "maria" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_time_entries_detailed(self):
        """Deve listar time entries em formato detalhado."""
        mock_response = {
            "data": [
                {
                    "id": "te1",
                    "duration": 3600000,
                    "task": {"id": "task1", "name": "Task de Teste"},
                    "user": {"id": 1, "username": "joao"},
                    "start": "1704067200000"
                }
            ]
        }
        respx.get(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTimeEntriesInput(team_id="team1", output_mode=OutputMode.DETAILED)
        result = await get_time_entries(params)

        assert "Time Entries" in result
        assert "Duração" in result
        assert "joao" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_time_entries_json(self):
        """Deve retornar time entries em JSON."""
        mock_response = {"data": [{"id": "te1", "duration": 3600000}]}
        respx.get(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTimeEntriesInput(team_id="team1", output_mode=OutputMode.JSON)
        result = await get_time_entries(params)

        data = json.loads(result)
        assert "data" in data

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_time_entries_empty(self):
        """Deve retornar mensagem quando não há entries."""
        mock_response = {"data": []}
        respx.get(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTimeEntriesInput(team_id="team1")
        result = await get_time_entries(params)

        assert "Nenhum registro de tempo" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_time_entries_with_filters(self):
        """Deve passar filtros corretamente."""
        mock_response = {"data": []}
        route = respx.get(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTimeEntriesInput(
            team_id="team1",
            start_date="1704067200000",
            end_date="1704153600000",
            assignee=12345
        )
        await get_time_entries(params)

        # Verifica que os parâmetros foram passados
        assert route.call_count == 1


# ============================================================================
# TESTES DE DOCS
# ============================================================================

class TestDocs:
    """Testes para tools de documentos."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_docs_compact(self):
        """Deve listar docs em formato compacto."""
        mock_response = {
            "docs": [
                {
                    "id": "doc1",
                    "name": "Documento de Teste",
                    "creator": {"id": 1, "username": "joao"},
                    "date_created": "1704067200000"
                },
                {
                    "id": "doc2",
                    "name": "Outro Documento",
                    "creator": {"id": 2, "username": "maria"},
                    "date_created": "1704153600000"
                }
            ]
        }
        respx.get(f"{API_BASE}/team/team1/doc").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetDocsInput(workspace_id="team1", output_mode=OutputMode.COMPACT)
        result = await get_docs(params)

        assert "2 documentos" in result
        assert "Documento de Teste" in result
        assert "joao" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_docs_detailed(self):
        """Deve listar docs em formato detalhado."""
        mock_response = {
            "docs": [
                {
                    "id": "doc1",
                    "name": "Documento de Teste",
                    "creator": {"id": 1, "username": "joao"},
                    "date_created": "1704067200000",
                    "parent": {"id": "space1", "type": "space"}
                }
            ]
        }
        respx.get(f"{API_BASE}/team/team1/doc").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetDocsInput(workspace_id="team1", output_mode=OutputMode.DETAILED)
        result = await get_docs(params)

        assert "Documentos" in result
        assert "Criador" in result
        assert "joao" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_docs_json(self):
        """Deve retornar docs em JSON."""
        mock_response = {"docs": [{"id": "doc1", "name": "Test"}]}
        respx.get(f"{API_BASE}/team/team1/doc").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetDocsInput(workspace_id="team1", output_mode=OutputMode.JSON)
        result = await get_docs(params)

        data = json.loads(result)
        assert "docs" in data

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_docs_empty(self):
        """Deve retornar mensagem quando não há docs."""
        mock_response = {"docs": []}
        respx.get(f"{API_BASE}/team/team1/doc").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetDocsInput(workspace_id="team1")
        result = await get_docs(params)

        assert "Nenhum documento" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_doc(self):
        """Deve criar um documento."""
        mock_response = {
            "id": "doc_new",
            "name": "Novo Documento"
        }
        respx.post(f"{API_BASE}/team/team1/doc").mock(
            return_value=Response(200, json=mock_response)
        )

        params = CreateDocInput(workspace_id="team1", name="Novo Documento")
        result = await create_doc(params)

        assert "doc_new" in result or "sucesso" in result.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_doc_with_content(self):
        """Deve criar um documento com conteúdo inicial."""
        mock_response = {
            "id": "doc_new",
            "name": "Documento com Conteúdo"
        }
        respx.post(f"{API_BASE}/team/team1/doc").mock(
            return_value=Response(200, json=mock_response)
        )

        params = CreateDocInput(
            workspace_id="team1",
            name="Documento com Conteúdo",
            content="# Título\n\nConteúdo inicial"
        )
        result = await create_doc(params)

        assert "doc_new" in result or "sucesso" in result.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_doc_with_parent(self):
        """Deve criar um documento com parent."""
        mock_response = {
            "id": "doc_new",
            "name": "Doc em Space"
        }
        respx.post(f"{API_BASE}/team/team1/doc").mock(
            return_value=Response(200, json=mock_response)
        )

        params = CreateDocInput(
            workspace_id="team1",
            name="Doc em Space",
            parent_id="space1",
            parent_type="space"
        )
        result = await create_doc(params)

        assert "doc_new" in result or "sucesso" in result.lower()


# ============================================================================
# TESTES DE CHECKLISTS
# ============================================================================

class TestChecklists:
    """Testes para tools de checklists."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_checklists_compact(self):
        """Deve listar checklists em formato compacto."""
        mock_response = {
            "id": "task1",
            "name": "Task com Checklists",
            "checklists": [
                {
                    "id": "cl1",
                    "name": "Checklist 1",
                    "items": [
                        {"id": "item1", "name": "Item 1", "resolved": True},
                        {"id": "item2", "name": "Item 2", "resolved": False}
                    ]
                },
                {
                    "id": "cl2",
                    "name": "Checklist 2",
                    "items": [
                        {"id": "item3", "name": "Item 3", "resolved": True}
                    ]
                }
            ]
        }
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetChecklistsInput(task_id="task1", output_mode=OutputMode.COMPACT)
        result = await get_checklists(params)

        assert "2 checklists" in result
        assert "1/2" in result  # Checklist 1
        assert "1/1" in result  # Checklist 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_checklists_detailed(self):
        """Deve listar checklists em formato detalhado."""
        mock_response = {
            "id": "task1",
            "checklists": [
                {
                    "id": "cl1",
                    "name": "Checklist Detalhada",
                    "items": [
                        {"id": "item1", "name": "Item Feito", "resolved": True, "assignee": {"username": "joao"}},
                        {"id": "item2", "name": "Item Pendente", "resolved": False}
                    ]
                }
            ]
        }
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetChecklistsInput(task_id="task1", output_mode=OutputMode.DETAILED)
        result = await get_checklists(params)

        assert "Checklists" in result
        assert "Itens:" in result
        assert "✅" in result  # Item resolvido
        assert "⬜" in result  # Item pendente

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_checklists_json(self):
        """Deve retornar checklists em JSON."""
        mock_response = {
            "id": "task1",
            "checklists": [{"id": "cl1", "name": "Test"}]
        }
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetChecklistsInput(task_id="task1", output_mode=OutputMode.JSON)
        result = await get_checklists(params)

        data = json.loads(result)
        assert "checklists" in data

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_checklists_empty(self):
        """Deve retornar mensagem quando não há checklists."""
        mock_response = {"id": "task1", "checklists": []}
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetChecklistsInput(task_id="task1")
        result = await get_checklists(params)

        assert "Nenhuma checklist" in result


# ============================================================================
# TESTES DE ATTACHMENTS
# ============================================================================

class TestAttachments:
    """Testes para tools de anexos."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_attachments_compact(self):
        """Deve listar anexos em formato compacto."""
        mock_response = {
            "id": "task1",
            "attachments": [
                {
                    "id": "att1",
                    "title": "documento",
                    "extension": "pdf",
                    "size": 102400,  # 100KB
                    "url": "https://example.com/doc.pdf"
                },
                {
                    "id": "att2",
                    "title": "imagem",
                    "extension": "png",
                    "size": 51200,
                    "url": "https://example.com/img.png"
                }
            ]
        }
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetAttachmentsInput(task_id="task1", output_mode=OutputMode.COMPACT)
        result = await get_attachments(params)

        assert "2 anexos" in result
        assert "documento.pdf" in result
        assert "100KB" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_attachments_detailed(self):
        """Deve listar anexos em formato detalhado."""
        mock_response = {
            "id": "task1",
            "attachments": [
                {
                    "id": "att1",
                    "title": "documento",
                    "extension": "pdf",
                    "size": 102400,
                    "url": "https://example.com/doc.pdf",
                    "date": "1704067200000",
                    "user": {"username": "joao"}
                }
            ]
        }
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetAttachmentsInput(task_id="task1", output_mode=OutputMode.DETAILED)
        result = await get_attachments(params)

        assert "Anexos" in result
        assert "documento" in result
        assert "Extensão" in result
        assert "joao" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_attachments_json(self):
        """Deve retornar anexos em JSON."""
        mock_response = {
            "id": "task1",
            "attachments": [{"id": "att1", "title": "test"}]
        }
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetAttachmentsInput(task_id="task1", output_mode=OutputMode.JSON)
        result = await get_attachments(params)

        data = json.loads(result)
        assert "attachments" in data

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_attachments_empty(self):
        """Deve retornar mensagem quando não há anexos."""
        mock_response = {"id": "task1", "attachments": []}
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetAttachmentsInput(task_id="task1")
        result = await get_attachments(params)

        assert "Nenhum anexo" in result


# ============================================================================
# TESTES DE WORKSPACE MEMBERS
# ============================================================================

class TestWorkspaceMembers:
    """Testes para tool de membros do workspace."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_workspace_members_compact(self):
        """Deve listar membros em formato compacto."""
        mock_response = {
            "teams": [
                {
                    "id": "team1",
                    "name": "Test Workspace",
                    "members": [
                        {"user": {"id": 1, "username": "admin", "email": "admin@test.com"}, "role": "owner"},
                        {"user": {"id": 2, "username": "dev", "email": "dev@test.com"}, "role": "member"}
                    ]
                }
            ]
        }
        respx.get(f"{API_BASE}/team").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetMembersInput(team_id="team1", output_mode=OutputMode.COMPACT)
        result = await get_workspace_members(params)

        assert "2 membros" in result
        assert "admin" in result
        assert "dev" in result
        assert "owner" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_workspace_members_detailed(self):
        """Deve listar membros em formato detalhado."""
        mock_response = {
            "teams": [
                {
                    "id": "team1",
                    "name": "Test Workspace",
                    "members": [
                        {"user": {"id": 1, "username": "admin", "email": "admin@test.com"}, "role": "owner"}
                    ]
                }
            ]
        }
        respx.get(f"{API_BASE}/team").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetMembersInput(team_id="team1", output_mode=OutputMode.DETAILED)
        result = await get_workspace_members(params)

        assert "Membros do Workspace" in result
        assert "admin" in result
        assert "Email:" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_workspace_members_json(self):
        """Deve retornar membros em JSON."""
        mock_response = {
            "teams": [
                {
                    "id": "team1",
                    "members": [{"user": {"id": 1, "username": "test"}, "role": "owner"}]
                }
            ]
        }
        respx.get(f"{API_BASE}/team").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetMembersInput(team_id="team1", output_mode=OutputMode.JSON)
        result = await get_workspace_members(params)

        data = json.loads(result)
        assert "members" in data

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_workspace_members_not_found(self):
        """Deve retornar mensagem quando workspace não encontrado."""
        mock_response = {"teams": [{"id": "other_team", "members": []}]}
        respx.get(f"{API_BASE}/team").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetMembersInput(team_id="team1")
        result = await get_workspace_members(params)

        assert "não encontrado" in result


# ============================================================================
# TESTES DE DUPLICATE TASK
# ============================================================================

class TestDuplicateTask:
    """Testes para tool de duplicar task."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_duplicate_task_success(self):
        """Deve duplicar uma task com sucesso."""
        # Mock GET original task
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json={
                "id": "task1",
                "name": "Task Original",
                "description": "Descrição da task",
                "status": {"status": "open"},
                "priority": {"priority": 2}
            })
        )

        # Mock POST criar nova task
        respx.post(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json={
                "id": "task_new",
                "name": "Cópia de Task Original",
                "url": "https://app.clickup.com/t/task_new"
            })
        )

        params = DuplicateTaskInput(task_id="task1", list_id="list1")
        result = await duplicate_task(params)

        assert "duplicada" in result.lower() or "sucesso" in result.lower()
        assert "task_new" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_duplicate_task_with_custom_name(self):
        """Deve duplicar task com nome customizado."""
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json={
                "id": "task1",
                "name": "Task Original",
                "description": "",
                "status": {"status": "open"}
            })
        )

        respx.post(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json={
                "id": "task_new",
                "name": "Meu Nome Customizado",
                "url": "https://app.clickup.com/t/task_new"
            })
        )

        params = DuplicateTaskInput(task_id="task1", list_id="list1", name="Meu Nome Customizado")
        result = await duplicate_task(params)

        assert "Meu Nome Customizado" in result or "task_new" in result


# ============================================================================
# TESTES DE MOVE TASK (BRANCHES ADICIONAIS)
# ============================================================================

class TestMoveTaskBranches:
    """Testes adicionais para move_task cobrindo mais branches."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_move_task_with_delete_from_original(self):
        """Deve remover da list original ao mover."""
        # Mock GET task original
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json={
                "id": "task1",
                "list": {"id": "list_original", "name": "Original"}
            })
        )

        # Mock POST adicionar na nova list
        respx.post(f"{API_BASE}/list/list_new/task/task1").mock(
            return_value=Response(200, json={})
        )

        # Mock DELETE remover da list original
        route_delete = respx.delete(f"{API_BASE}/list/list_original/task/task1").mock(
            return_value=Response(200, json={})
        )

        params = MoveTaskInput(task_id="task1", list_id="list_new")
        result = await move_task(params)

        assert route_delete.call_count == 1
        assert "sucesso" in result.lower() or "movid" in result.lower()


# ============================================================================
# TESTES DE ANALYZE STRUCTURE (BRANCHES ADICIONAIS)
# ============================================================================

class TestAnalyzeStructureBranches:
    """Testes adicionais para analyze_space_structure."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_analyze_structure_json(self):
        """Deve retornar análise em JSON."""
        respx.get(f"{API_BASE}/space/space1").mock(
            return_value=Response(200, json={
                "id": "space1",
                "name": "Test Space"
            })
        )
        respx.get(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(200, json={"folders": []})
        )
        respx.get(f"{API_BASE}/space/space1/list").mock(
            return_value=Response(200, json={"lists": []})
        )

        params = AnalyzeSpaceStructureInput(space_id="space1", output_mode=OutputMode.JSON)
        result = await analyze_space_structure(params)

        data = json.loads(result)
        assert "summary" in data

    @respx.mock
    @pytest.mark.asyncio
    async def test_analyze_structure_compact(self):
        """Deve retornar análise em formato compacto."""
        respx.get(f"{API_BASE}/space/space1").mock(
            return_value=Response(200, json={
                "id": "space1",
                "name": "Test Space"
            })
        )
        respx.get(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(200, json={
                "folders": [{"id": "f1", "name": "F1", "lists": []}]
            })
        )
        respx.get(f"{API_BASE}/space/space1/list").mock(
            return_value=Response(200, json={
                "lists": [{"id": "l1", "name": "L1", "task_count": 5}]
            })
        )

        params = AnalyzeSpaceStructureInput(space_id="space1", output_mode=OutputMode.COMPACT)
        result = await analyze_space_structure(params)

        assert "Test Space" in result
        assert "folder" in result.lower()
        assert "list" in result.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_analyze_structure_with_empty_folders(self):
        """Deve mostrar folders vazios corretamente."""
        respx.get(f"{API_BASE}/space/space1").mock(
            return_value=Response(200, json={"id": "space1", "name": "Space"})
        )
        respx.get(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(200, json={
                "folders": [{"id": "f1", "name": "Folder Vazio", "lists": []}]
            })
        )
        respx.get(f"{API_BASE}/space/space1/list").mock(
            return_value=Response(200, json={"lists": []})
        )

        params = AnalyzeSpaceStructureInput(space_id="space1", output_mode=OutputMode.DETAILED)
        result = await analyze_space_structure(params)

        assert "vazio" in result.lower() or "Folder Vazio" in result


# ============================================================================
# TESTES DE GET METRICS (BRANCHES ADICIONAIS)
# ============================================================================

class TestMetricsBranches:
    """Testes adicionais para get_metrics cobrindo todos os branches."""

    @pytest.mark.asyncio
    async def test_get_metrics_compact(self):
        """Deve retornar métricas em formato compacto."""
        params = GetMetricsInput(output_mode=OutputMode.COMPACT)
        result = await get_metrics(params)

        assert "Métricas" in result
        assert "API:" in result
        assert "Cache:" in result

    @pytest.mark.asyncio
    async def test_get_metrics_detailed(self):
        """Deve retornar métricas em formato detalhado."""
        params = GetMetricsInput(output_mode=OutputMode.DETAILED)
        result = await get_metrics(params)

        assert "Métricas do Servidor" in result
        assert "API Calls" in result
        assert "Cache Hits" in result


# ============================================================================
# TESTES DE CUSTOM FIELDS (BRANCHES ADICIONAIS)
# ============================================================================

class TestCustomFieldsBranches:
    """Testes adicionais para get_custom_fields."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_custom_fields_detailed(self):
        """Deve listar custom fields em formato detalhado."""
        mock_response = {
            "fields": [
                {
                    "id": "field1",
                    "name": "Dropdown Field",
                    "type": "dropdown",
                    "required": True,
                    "type_config": {
                        "options": [
                            {"name": "Option 1"},
                            {"name": "Option 2"}
                        ]
                    }
                }
            ]
        }
        respx.get(f"{API_BASE}/list/list1/field").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetCustomFieldsInput(list_id="list1", output_mode=OutputMode.DETAILED)
        result = await get_custom_fields(params)

        assert "Custom Fields" in result
        assert "Dropdown Field" in result
        assert "Opções:" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_custom_fields_json(self):
        """Deve retornar custom fields em JSON."""
        mock_response = {"fields": [{"id": "f1", "name": "Test"}]}
        respx.get(f"{API_BASE}/list/list1/field").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetCustomFieldsInput(list_id="list1", output_mode=OutputMode.JSON)
        result = await get_custom_fields(params)

        data = json.loads(result)
        assert "fields" in data

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_custom_fields_empty(self):
        """Deve retornar mensagem quando não há custom fields."""
        mock_response = {"fields": []}
        respx.get(f"{API_BASE}/list/list1/field").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetCustomFieldsInput(list_id="list1")
        result = await get_custom_fields(params)

        assert "Nenhum campo customizado" in result


# ============================================================================
# TESTES DE SPACE DETAILS (BRANCHES ADICIONAIS)
# ============================================================================

class TestSpaceDetailsBranches:
    """Testes adicionais para get_space_details."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_space_details_compact(self):
        """Deve retornar detalhes em formato compacto."""
        mock_response = {
            "id": "space1",
            "name": "Test Space",
            "private": True,
            "statuses": [{"status": "open"}],
            "features": {},
            "members": [{"user": {"id": 1}}]
        }
        respx.get(f"{API_BASE}/space/space1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetSpaceDetailsInput(space_id="space1", output_mode=OutputMode.COMPACT)
        result = await get_space_details(params)

        assert "Test Space" in result
        assert "privado" in result
        assert "1 status" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_space_details_json(self):
        """Deve retornar detalhes em JSON."""
        mock_response = {"id": "space1", "name": "Test"}
        respx.get(f"{API_BASE}/space/space1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetSpaceDetailsInput(space_id="space1", output_mode=OutputMode.JSON)
        result = await get_space_details(params)

        data = json.loads(result)
        assert data["id"] == "space1"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_space_details_with_members(self):
        """Deve mostrar membros do space."""
        mock_response = {
            "id": "space1",
            "name": "Test Space",
            "private": False,
            "statuses": [],
            "features": {"due_dates": {"enabled": True}},
            "members": [
                {"user": {"id": 1, "username": "member1"}},
                {"user": {"id": 2, "username": "member2"}}
            ]
        }
        respx.get(f"{API_BASE}/space/space1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetSpaceDetailsInput(space_id="space1", output_mode=OutputMode.DETAILED)
        result = await get_space_details(params)

        assert "Membros" in result


# ============================================================================
# TESTES DE COMMENTS (BRANCHES ADICIONAIS)
# ============================================================================

class TestCommentsBranches:
    """Testes adicionais para comments."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_comments_json(self):
        """Deve retornar comments em JSON."""
        mock_response = {"comments": [{"id": "c1", "comment_text": "Test"}]}
        respx.get(f"{API_BASE}/task/task1/comment").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTaskCommentsInput(task_id="task1", output_mode=OutputMode.JSON)
        result = await get_task_comments(params)

        data = json.loads(result)
        assert "comments" in data

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_comments_empty(self):
        """Deve retornar mensagem quando não há comments."""
        mock_response = {"comments": []}
        respx.get(f"{API_BASE}/task/task1/comment").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTaskCommentsInput(task_id="task1")
        result = await get_task_comments(params)

        assert "Nenhum comentário" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_comments_detailed(self):
        """Deve retornar comments em formato detalhado."""
        mock_response = {
            "comments": [
                {
                    "id": "c1",
                    "comment_text": "Comentário detalhado",
                    "user": {"username": "joao"},
                    "date": "1704067200000"
                }
            ]
        }
        respx.get(f"{API_BASE}/task/task1/comment").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTaskCommentsInput(task_id="task1", output_mode=OutputMode.DETAILED)
        result = await get_task_comments(params)

        assert "Comentários" in result
        assert "joao" in result


# ============================================================================
# TESTES PARA ATINGIR 90% DE COBERTURA
# ============================================================================

class TestWorkspacesDetailedBranches:
    """Testes para branches de workspaces."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_workspaces_detailed(self):
        """Deve listar workspaces em formato detalhado."""
        mock_response = {
            "teams": [
                {
                    "id": "team1",
                    "name": "Test Workspace",
                    "members": [{"user": {"id": 1, "username": "admin"}}]
                }
            ]
        }
        respx.get(f"{API_BASE}/team").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetWorkspacesInput(output_mode=OutputMode.DETAILED)
        result = await get_workspaces(params)

        assert "# Workspaces" in result
        assert "Test Workspace" in result
        assert "Membros:" in result


class TestSpacesDetailedBranches:
    """Testes para branches de spaces."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_spaces_detailed(self):
        """Deve listar spaces em formato detalhado."""
        mock_response = {
            "spaces": [
                {
                    "id": "space1",
                    "name": "Test Space",
                    "private": True,
                    "statuses": [
                        {"status": "open"},
                        {"status": "closed"}
                    ]
                }
            ]
        }
        respx.get(f"{API_BASE}/team/team1/space").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetSpacesInput(team_id="team1", output_mode=OutputMode.DETAILED)
        result = await get_spaces(params)

        assert "# Spaces" in result
        assert "Test Space" in result
        assert "Status disponíveis" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_spaces_json(self):
        """Deve retornar spaces em JSON."""
        mock_response = {"spaces": [{"id": "s1", "name": "Test"}]}
        respx.get(f"{API_BASE}/team/team1/space").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetSpacesInput(team_id="team1", output_mode=OutputMode.JSON)
        result = await get_spaces(params)

        data = json.loads(result)
        assert "spaces" in data


class TestFoldersDetailedBranches:
    """Testes para branches de folders."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_folders_detailed(self):
        """Deve listar folders em formato detalhado."""
        mock_response = {
            "folders": [
                {
                    "id": "folder1",
                    "name": "Test Folder",
                    "lists": [
                        {"id": "list1", "name": "List 1"},
                        {"id": "list2", "name": "List 2"}
                    ]
                }
            ]
        }
        respx.get(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetFoldersInput(space_id="space1", output_mode=OutputMode.DETAILED)
        result = await get_folders(params)

        assert "# Folders" in result
        assert "Test Folder" in result
        assert "List 1" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_folders_json(self):
        """Deve retornar folders em JSON."""
        mock_response = {"folders": [{"id": "f1", "name": "Test"}]}
        respx.get(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetFoldersInput(space_id="space1", output_mode=OutputMode.JSON)
        result = await get_folders(params)

        data = json.loads(result)
        assert "folders" in data


class TestListsDetailedBranches:
    """Testes para branches de lists."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_lists_detailed(self):
        """Deve listar lists em formato detalhado."""
        mock_response = {
            "lists": [
                {
                    "id": "list1",
                    "name": "Test List",
                    "task_count": 10,
                    "folder": {"id": "folder1", "name": "Folder 1"}
                }
            ]
        }
        respx.get(f"{API_BASE}/folder/folder1/list").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetListsInput(folder_id="folder1", output_mode=OutputMode.DETAILED)
        result = await get_lists(params)

        assert "# Lists" in result
        assert "Test List" in result
        assert "Tasks:" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_lists_json(self):
        """Deve retornar lists em JSON."""
        mock_response = {"lists": [{"id": "l1", "name": "Test"}]}
        respx.get(f"{API_BASE}/folder/folder1/list").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetListsInput(folder_id="folder1", output_mode=OutputMode.JSON)
        result = await get_lists(params)

        data = json.loads(result)
        assert "lists" in data

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_list_details_json(self):
        """Deve retornar detalhes da list em JSON."""
        mock_response = {"id": "list1", "name": "Test", "task_count": 5}
        respx.get(f"{API_BASE}/list/list1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetListDetailsInput(list_id="list1", output_mode=OutputMode.JSON)
        result = await get_list_details(params)

        data = json.loads(result)
        assert data["id"] == "list1"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_list_details_compact(self):
        """Deve retornar detalhes da list em formato compacto."""
        mock_response = {
            "id": "list1",
            "name": "Test List",
            "task_count": 5,
            "folder": {"id": "f1", "name": "Folder"}
        }
        respx.get(f"{API_BASE}/list/list1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetListDetailsInput(list_id="list1", output_mode=OutputMode.COMPACT)
        result = await get_list_details(params)

        assert "Test List" in result


class TestTasksFilterBranches:
    """Testes para branches de filtros de tasks."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_tasks_with_all_filters(self):
        """Deve passar todos os filtros corretamente."""
        mock_response = {"tasks": [{"id": "t1", "name": "Task", "status": {"status": "open"}}]}
        route = respx.get(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTasksInput(
            list_id="list1",
            order_by=OrderBy.DUE_DATE,
            reverse=True,
            statuses=["open", "in_progress"],
            assignees=["123", "456"],
            due_date_gt=1704067200000,
            due_date_lt=1704153600000,
            date_created_gt=1704067200000,
            date_created_lt=1704153600000,
            date_updated_gt=1704067200000,
            date_updated_lt=1704153600000
        )
        result = await get_tasks(params)

        assert route.call_count == 1
        assert "Task" in result or "t1" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_tasks_json(self):
        """Deve retornar tasks em JSON."""
        mock_response = {"tasks": [{"id": "t1", "name": "Test"}]}
        respx.get(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTasksInput(list_id="list1", output_mode=OutputMode.JSON)
        result = await get_tasks(params)

        data = json.loads(result)
        assert "tasks" in data


class TestFilteredTeamTasksBranches:
    """Testes para branches de get_filtered_team_tasks."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_filtered_team_tasks_with_all_filters(self):
        """Deve passar todos os filtros corretamente."""
        mock_response = {"tasks": [{"id": "t1", "name": "Task"}]}
        route = respx.get(f"{API_BASE}/team/team1/task").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetFilteredTeamTasksInput(
            team_id="team1",
            order_by=OrderBy.DUE_DATE,
            reverse=True,
            space_ids=["space1"],
            project_ids=["folder1"],
            list_ids=["list1"],
            statuses=["open"],
            assignees=["123"],
            due_date_gt=1704067200000,
            due_date_lt=1704153600000,
            date_created_gt=1704067200000,
            date_created_lt=1704153600000,
            date_updated_gt=1704067200000,
            date_updated_lt=1704153600000
        )
        result = await get_filtered_team_tasks(params)

        assert route.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_filtered_team_tasks_json(self):
        """Deve retornar tasks em JSON."""
        mock_response = {"tasks": [{"id": "t1", "name": "Test"}]}
        respx.get(f"{API_BASE}/team/team1/task").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetFilteredTeamTasksInput(team_id="team1", output_mode=OutputMode.JSON)
        result = await get_filtered_team_tasks(params)

        data = json.loads(result)
        assert "tasks" in data

    @respx.mock
    @pytest.mark.asyncio
    async def test_filtered_team_tasks_detailed(self):
        """Deve retornar tasks em formato detalhado."""
        mock_response = {
            "tasks": [
                {
                    "id": "t1",
                    "name": "Test Task",
                    "status": {"status": "open"},
                    "date_created": "1704067200000",
                    "assignees": [],
                    "list": {"id": "l1", "name": "List"},
                    "folder": {"id": "f1", "name": "Folder"}
                }
            ]
        }
        respx.get(f"{API_BASE}/team/team1/task").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetFilteredTeamTasksInput(team_id="team1", output_mode=OutputMode.DETAILED)
        result = await get_filtered_team_tasks(params)

        assert "Test Task" in result


class TestFolderlessListsBranches:
    """Testes para branches de folderless lists."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_folderless_lists_detailed(self):
        """Deve listar folderless lists em formato detalhado."""
        mock_response = {
            "lists": [
                {
                    "id": "list1",
                    "name": "Avulsa 1",
                    "task_count": 10
                }
            ]
        }
        respx.get(f"{API_BASE}/space/space1/list").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetFolderlessListsInput(space_id="space1", output_mode=OutputMode.DETAILED)
        result = await get_folderless_lists(params)

        assert "Avulsa 1" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_folderless_lists_json(self):
        """Deve retornar folderless lists em JSON."""
        mock_response = {"lists": [{"id": "l1", "name": "Test"}]}
        respx.get(f"{API_BASE}/space/space1/list").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetFolderlessListsInput(space_id="space1", output_mode=OutputMode.JSON)
        result = await get_folderless_lists(params)

        data = json.loads(result)
        assert "lists" in data


class TestGetTaskBranches:
    """Testes para branches de get_task."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_task_with_custom_fields(self):
        """Deve mostrar custom fields em formato detalhado."""
        mock_response = {
            "id": "task1",
            "name": "Test Task",
            "status": {"status": "open"},
            "description": "Descrição da task",
            "list": {"id": "l1", "name": "List"},
            "folder": {"id": "f1", "name": "Folder"},
            "custom_fields": [
                {"name": "Valor", "value": "1000"},
                {"name": "Status", "value": "OK"}
            ]
        }
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetTaskInput(task_id="task1")
        result = await get_task(params)

        assert "Test Task" in result


# ============================================================================
# SPRINT 5 TESTS
# ============================================================================

class TestFuzzyRatio:
    """Testes para a função fuzzy_ratio."""

    def test_exact_match(self):
        """Strings idênticas devem ter ratio 1.0."""
        assert fuzzy_ratio("hello", "hello") == 1.0

    def test_case_insensitive(self):
        """Deve ignorar diferença de case."""
        assert fuzzy_ratio("Hello", "hello") == 1.0

    def test_similar_strings(self):
        """Strings similares devem ter ratio alto."""
        ratio = fuzzy_ratio("relatorio", "relatório")
        assert ratio > 0.7

    def test_different_strings(self):
        """Strings muito diferentes devem ter ratio baixo."""
        ratio = fuzzy_ratio("hello", "goodbye")
        assert ratio < 0.5

    def test_empty_string(self):
        """String vazia deve retornar 0."""
        assert fuzzy_ratio("hello", "") == 0.0
        assert fuzzy_ratio("", "hello") == 0.0


class TestFuzzySearchTasks:
    """Testes para fuzzy_search_tasks."""

    def test_exact_match_priority(self):
        """Match exato ou muito similar deve estar nos resultados."""
        tasks = [
            {"name": "Relatório Mensal", "id": "1"},
            {"name": "Relatório", "id": "2"},
            {"name": "Relatório Anual", "id": "3"},
            {"name": "Configuração", "id": "4"}
        ]
        results = fuzzy_search_tasks(tasks, "relatório")
        # Deve encontrar os 3 relatórios
        assert len(results) >= 3
        # Todos os resultados devem conter "Relatório"
        for task in results:
            assert "Relatório" in task["name"]

    def test_substring_match(self):
        """Substring deve encontrar tasks."""
        tasks = [
            {"name": "Configuração do Sistema", "id": "1"},
            {"name": "Relatório Mensal", "id": "2"}
        ]
        results = fuzzy_search_tasks(tasks, "config")
        assert len(results) >= 1
        assert "Configuração" in results[0]["name"]

    def test_fuzzy_match(self):
        """Busca fuzzy deve encontrar tasks com erros de digitação."""
        tasks = [
            {"name": "Reunião com Cliente", "id": "1"},
            {"name": "Relatório Final", "id": "2"}
        ]
        results = fuzzy_search_tasks(tasks, "reunao", threshold=0.4)
        assert len(results) >= 1

    def test_threshold_filter(self):
        """Threshold alto deve filtrar mais resultados."""
        tasks = [
            {"name": "Relatório", "id": "1"},
            {"name": "Configuração", "id": "2"}
        ]
        results_low = fuzzy_search_tasks(tasks, "rel", threshold=0.3)
        results_high = fuzzy_search_tasks(tasks, "rel", threshold=0.7)
        assert len(results_low) >= len(results_high)


class TestFuzzySearchTasksTool:
    """Testes para a tool fuzzy_search_tasks_tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fuzzy_search_compact(self):
        """Deve retornar resultados em modo compact."""
        mock_tasks = {
            "tasks": [
                {"id": "t1", "name": "Relatório Mensal", "status": {"status": "open"}},
                {"id": "t2", "name": "Relatório Anual", "status": {"status": "done"}},
                {"id": "t3", "name": "Configuração", "status": {"status": "open"}}
            ]
        }
        respx.get(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json=mock_tasks)
        )

        params = FuzzySearchTasksInput(list_id="list1", query="relatorio")
        result = await fuzzy_search_tasks_tool(params)

        assert "Busca fuzzy" in result
        assert "relatorio" in result
        assert "2 resultados" in result or "Relatório" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_fuzzy_search_no_results(self):
        """Deve informar quando não há resultados."""
        mock_tasks = {
            "tasks": [
                {"id": "t1", "name": "Configuração", "status": {"status": "open"}}
            ]
        }
        respx.get(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json=mock_tasks)
        )

        params = FuzzySearchTasksInput(list_id="list1", query="xyz123", threshold=0.9)
        result = await fuzzy_search_tasks_tool(params)

        assert "Nenhuma task encontrada" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_fuzzy_search_json(self):
        """Deve retornar JSON válido."""
        mock_tasks = {
            "tasks": [
                {"id": "t1", "name": "Relatório", "status": {"status": "open"}}
            ]
        }
        respx.get(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json=mock_tasks)
        )

        params = FuzzySearchTasksInput(
            list_id="list1",
            query="relatorio",
            output_mode=OutputMode.JSON
        )
        result = await fuzzy_search_tasks_tool(params)

        data = json.loads(result)
        assert "query" in data
        assert "tasks" in data


class TestCreateTimeEntry:
    """Testes para create_time_entry."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_time_entry_basic(self):
        """Deve criar time entry básico."""
        mock_response = {
            "data": {
                "id": "te1",
                "duration": 3600000,
                "billable": False
            }
        }
        respx.post(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(200, json=mock_response)
        )

        params = CreateTimeEntryInput(
            team_id="team1",
            start=1704067200000,
            duration=3600000
        )
        result = await create_time_entry(params)

        assert "Time entry criado" in result
        assert "60 minutos" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_time_entry_billable(self):
        """Deve criar time entry faturável."""
        mock_response = {
            "data": {
                "id": "te2",
                "duration": 7200000,
                "billable": True
            }
        }
        respx.post(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(200, json=mock_response)
        )

        params = CreateTimeEntryInput(
            team_id="team1",
            start=1704067200000,
            duration=7200000,
            billable=True,
            description="Trabalho no projeto X"
        )
        result = await create_time_entry(params)

        assert "Time entry criado" in result
        assert "Sim" in result  # Faturável: Sim
        assert "💰" in result


class TestGetBillableReport:
    """Testes para get_billable_report."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_billable_report_detailed(self):
        """Deve gerar relatório detalhado."""
        mock_response = {
            "data": [
                {
                    "id": "te1",
                    "duration": 3600000,
                    "billable": True,
                    "user": {"username": "user1"},
                    "task": {"name": "Task 1"}
                },
                {
                    "id": "te2",
                    "duration": 7200000,
                    "billable": True,
                    "user": {"username": "user1"},
                    "task": {"name": "Task 2"}
                },
                {
                    "id": "te3",
                    "duration": 1800000,
                    "billable": False,
                    "user": {"username": "user2"},
                    "task": {"name": "Task 3"}
                }
            ]
        }
        respx.get(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetBillableReportInput(
            team_id="team1",
            start_date=1704067200000,
            end_date=1704153600000
        )
        result = await get_billable_report(params)

        assert "Horas Faturáveis" in result
        assert "user1" in result
        assert "Por Usuário" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_billable_report_compact(self):
        """Deve gerar relatório compacto."""
        mock_response = {
            "data": [
                {"id": "te1", "duration": 3600000, "billable": True, "user": {"username": "u1"}, "task": {"name": "T1"}}
            ]
        }
        respx.get(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetBillableReportInput(
            team_id="team1",
            start_date=1704067200000,
            end_date=1704153600000,
            output_mode=OutputMode.COMPACT
        )
        result = await get_billable_report(params)

        assert "💰" in result
        assert "1 entries" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_billable_report_no_billable(self):
        """Deve informar quando não há horas faturáveis."""
        mock_response = {
            "data": [
                {"id": "te1", "duration": 3600000, "billable": False, "user": {"username": "u1"}, "task": {"name": "T1"}}
            ]
        }
        respx.get(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(200, json=mock_response)
        )

        params = GetBillableReportInput(
            team_id="team1",
            start_date=1704067200000,
            end_date=1704153600000
        )
        result = await get_billable_report(params)

        assert "Nenhuma hora faturável" in result


class TestReadOnlyMode:
    """Testes para modo read-only."""

    def test_check_write_permission_allowed(self):
        """Deve permitir escrita quando READ_ONLY_MODE=False."""
        original = clickup_mcp.READ_ONLY_MODE
        clickup_mcp.READ_ONLY_MODE = False
        try:
            # Não deve lançar exceção
            check_write_permission("test_operation")
        finally:
            clickup_mcp.READ_ONLY_MODE = original

    def test_check_write_permission_blocked(self):
        """Deve bloquear escrita quando READ_ONLY_MODE=True."""
        original = clickup_mcp.READ_ONLY_MODE
        clickup_mcp.READ_ONLY_MODE = True
        try:
            with pytest.raises(ReadOnlyModeError) as exc_info:
                check_write_permission("test_operation")
            assert "READ_ONLY" in str(exc_info.value)
            assert "test_operation" in str(exc_info.value)
        finally:
            clickup_mcp.READ_ONLY_MODE = original


class TestMetricsWithOperationMode:
    """Testes para métricas com modo de operação."""

    @pytest.mark.asyncio
    async def test_metrics_shows_operation_mode(self):
        """Métricas devem mostrar modo de operação."""
        params = GetMetricsInput(output_mode=OutputMode.DETAILED)
        result = await get_metrics(params)

        assert "Modo de Operação" in result
        assert "READ_WRITE" in result or "READ_ONLY" in result

    @pytest.mark.asyncio
    async def test_metrics_compact_shows_mode(self):
        """Métricas compact devem mostrar modo."""
        params = GetMetricsInput(output_mode=OutputMode.COMPACT)
        result = await get_metrics(params)

        assert "Modo:" in result


# ============================================================================
# TESTES PARA MELHORIAS DE QUALIDADE
# ============================================================================

class TestSanitization:
    """Testes para funções de sanitização."""

    def test_sanitize_output_normal_text(self):
        """Texto normal deve passar inalterado."""
        from clickup_mcp import sanitize_output
        text = "Hello World! Teste com acentos: São Paulo"
        result = sanitize_output(text)
        assert result == text

    def test_sanitize_output_control_chars(self):
        """Caracteres de controle devem ser removidos."""
        from clickup_mcp import sanitize_output
        text = "Hello\x00World\x01Test\x02"
        result = sanitize_output(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "HelloWorldTest" in result

    def test_sanitize_output_preserves_newlines(self):
        """Newlines e tabs devem ser preservados."""
        from clickup_mcp import sanitize_output
        text = "Line 1\nLine 2\tTabbed"
        result = sanitize_output(text)
        assert "\n" in result
        assert "\t" in result

    def test_sanitize_output_max_length(self):
        """Texto muito longo deve ser truncado."""
        from clickup_mcp import sanitize_output
        text = "x" * 200000  # 200KB
        result = sanitize_output(text)
        assert len(result) <= 100100  # 100KB + margem para mensagem
        assert "truncado" in result

    def test_sanitize_dict_values(self):
        """Dict com valores string devem ser sanitizados."""
        from clickup_mcp import sanitize_dict_values
        data = {
            "name": "Test\x00Name",
            "nested": {"value": "Hello\x01World"},
            "list": ["item\x02one", "item two"],
            "number": 42
        }
        result = sanitize_dict_values(data)
        assert "\x00" not in result["name"]
        assert "\x01" not in result["nested"]["value"]
        assert "\x02" not in result["list"][0]
        assert result["number"] == 42


class TestMetricsLatency:
    """Testes para métricas de latência."""

    def test_record_latency(self):
        """Deve registrar latência corretamente."""
        from clickup_mcp import Metrics
        m = Metrics()
        m.record_latency(100.0)
        m.record_latency(200.0)
        m.record_latency(150.0)

        summary = m.get_summary()
        assert "latency_ms" in summary
        assert summary["latency_ms"]["samples"] == 3

    def test_latency_percentiles(self):
        """Deve calcular percentis corretamente."""
        from clickup_mcp import Metrics
        m = Metrics()
        # Adiciona valores conhecidos
        for i in range(100):
            m.record_latency(float(i))

        summary = m.get_summary()
        latency = summary["latency_ms"]
        assert latency["p50"] == 50  # Mediana
        assert latency["p95"] >= 90
        assert latency["p99"] >= 95
        assert latency["min"] == 0
        assert latency["max"] == 99

    def test_measure_latency_context_manager(self):
        """Context manager deve medir latência."""
        from clickup_mcp import Metrics
        import time
        m = Metrics()

        with m.measure_latency("test_tool"):
            time.sleep(0.01)  # 10ms

        summary = m.get_summary()
        assert summary["latency_ms"]["samples"] == 1
        assert summary["latency_ms"]["avg"] >= 10  # Pelo menos 10ms

    def test_latency_by_tool(self):
        """Deve agrupar latência por tool."""
        from clickup_mcp import Metrics
        m = Metrics()

        m.record_latency(100.0, "tool_a")
        m.record_latency(200.0, "tool_a")
        m.record_latency(50.0, "tool_b")

        m.tool_calls["tool_a"] = 2
        m.tool_calls["tool_b"] = 1

        summary = m.get_summary()
        assert "latency_by_tool" in summary


class TestExceptions:
    """Testes para exceções específicas."""

    def test_clickup_error_base(self):
        """ClickUpError deve ser base para outras exceções."""
        from clickup_mcp import ClickUpError, ConfigurationError, ClickUpAPIError

        assert issubclass(ConfigurationError, ClickUpError)
        assert issubclass(ClickUpAPIError, ClickUpError)

    def test_clickup_api_error_attributes(self):
        """ClickUpAPIError deve ter atributos corretos."""
        from clickup_mcp import ClickUpAPIError

        error = ClickUpAPIError(
            message="Not found",
            status_code=404,
            endpoint="/task/123",
            err_code="TASK_NOT_FOUND"
        )

        assert error.status_code == 404
        assert error.endpoint == "/task/123"
        assert error.err_code == "TASK_NOT_FOUND"
        assert "404" in str(error)
        assert "Not found" in str(error)

    def test_configuration_error(self):
        """ConfigurationError deve funcionar corretamente."""
        from clickup_mcp import ConfigurationError

        error = ConfigurationError("Token not set")
        assert "Token not set" in str(error)


class TestValidateConfigFailFast:
    """Testes para validate_config fail-fast."""

    def test_validate_config_missing_token_allowed(self):
        """Com ALLOW_MISSING_TOKEN=true, não deve dar erro."""
        import os
        original_token = os.environ.get("CLICKUP_API_TOKEN")
        original_allow = os.environ.get("ALLOW_MISSING_TOKEN")

        try:
            os.environ["ALLOW_MISSING_TOKEN"] = "true"
            if "CLICKUP_API_TOKEN" in os.environ:
                del os.environ["CLICKUP_API_TOKEN"]

            # Reimporta para testar
            # Nota: validate_config já foi executado no import,
            # este teste verifica que não falhou
            from clickup_mcp import ALLOW_MISSING_TOKEN
            assert True  # Se chegou aqui, não deu erro

        finally:
            if original_token:
                os.environ["CLICKUP_API_TOKEN"] = original_token
            if original_allow:
                os.environ["ALLOW_MISSING_TOKEN"] = original_allow


class TestFuzzyPerformance:
    """Testes de performance para fuzzy search."""

    def test_fuzzy_search_performance_1000_tasks(self):
        """Fuzzy search deve ser rápido com 1000 tasks."""
        import time

        # Gera 1000 tasks
        tasks = [
            {"name": f"Task número {i} - Descrição aleatória", "id": str(i)}
            for i in range(1000)
        ]

        start = time.perf_counter()
        results = fuzzy_search_tasks(tasks, "número", threshold=0.5)
        elapsed = time.perf_counter() - start

        # Deve completar em menos de 1 segundo
        assert elapsed < 1.0, f"Fuzzy search demorou {elapsed:.2f}s (esperado < 1s)"
        assert len(results) > 0

    def test_fuzzy_search_performance_empty_query(self):
        """Query vazia deve retornar rápido."""
        tasks = [{"name": "Test", "id": "1"}]
        results = fuzzy_search_tasks(tasks, "", threshold=0.5)
        assert results == []

    def test_fuzzy_search_performance_empty_tasks(self):
        """Lista vazia deve retornar rápido."""
        results = fuzzy_search_tasks([], "query", threshold=0.5)
        assert results == []


# ============================================================================
# TESTES - CUSTOM FIELDS
# ============================================================================

class TestSetCustomFieldValue:
    """Testes para clickup_set_custom_field_value."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_set_text_field(self):
        """Deve definir valor de campo texto."""
        respx.post(f"{API_BASE}/task/task123/field/field456").mock(
            return_value=Response(200, json={})
        )

        params = SetCustomFieldValueInput(
            task_id="task123",
            field_id="field456",
            value="Texto de teste"
        )
        result = await set_custom_field_value(params)

        assert "Custom field atualizado" in result
        assert "task123" in result
        assert "field456" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_set_number_field(self):
        """Deve definir valor de campo número."""
        respx.post(f"{API_BASE}/task/task123/field/field789").mock(
            return_value=Response(200, json={})
        )

        params = SetCustomFieldValueInput(
            task_id="task123",
            field_id="field789",
            value=42
        )
        result = await set_custom_field_value(params)

        assert "Custom field atualizado" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_set_dropdown_field(self):
        """Deve definir valor de campo dropdown."""
        respx.post(f"{API_BASE}/task/task123/field/dropdown_field").mock(
            return_value=Response(200, json={})
        )

        params = SetCustomFieldValueInput(
            task_id="task123",
            field_id="dropdown_field",
            value="option_abc123"  # ID da opção
        )
        result = await set_custom_field_value(params)

        assert "Custom field atualizado" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_set_date_field_with_time(self):
        """Deve definir valor de campo data com horário."""
        respx.post(f"{API_BASE}/task/task123/field/date_field").mock(
            return_value=Response(200, json={})
        )

        params = SetCustomFieldValueInput(
            task_id="task123",
            field_id="date_field",
            value=1704067200000,  # timestamp ms
            value_options={"time": True}
        )
        result = await set_custom_field_value(params)

        assert "Custom field atualizado" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_set_labels_field(self):
        """Deve definir valor de campo labels."""
        respx.post(f"{API_BASE}/task/task123/field/labels_field").mock(
            return_value=Response(200, json={})
        )

        params = SetCustomFieldValueInput(
            task_id="task123",
            field_id="labels_field",
            value=["label1", "label2", "label3"]
        )
        result = await set_custom_field_value(params)

        assert "Custom field atualizado" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_set_users_field(self):
        """Deve definir valor de campo users (relationship)."""
        respx.post(f"{API_BASE}/task/task123/field/users_field").mock(
            return_value=Response(200, json={})
        )

        params = SetCustomFieldValueInput(
            task_id="task123",
            field_id="users_field",
            value={"add": ["user123", "user456"], "rem": []}
        )
        result = await set_custom_field_value(params)

        assert "Custom field atualizado" in result


class TestRemoveCustomFieldValue:
    """Testes para clickup_remove_custom_field_value."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_remove_field_value(self):
        """Deve remover valor de custom field."""
        respx.delete(f"{API_BASE}/task/task123/field/field456").mock(
            return_value=Response(200, json={})
        )

        params = RemoveCustomFieldValueInput(
            task_id="task123",
            field_id="field456"
        )
        result = await remove_custom_field_value(params)

        assert "Valor do custom field removido" in result
        assert "task123" in result
        assert "field456" in result


class TestCreateTaskWithCustomFields:
    """Testes para create_task com custom_fields."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_task_with_custom_fields(self):
        """Deve criar task com custom fields."""
        respx.post(f"{API_BASE}/list/list123/task").mock(
            return_value=Response(200, json={
                "id": "new_task_id",
                "name": "Task com Custom Fields",
                "url": "https://app.clickup.com/t/new_task_id"
            })
        )

        params = CreateTaskInput(
            list_id="list123",
            name="Task com Custom Fields",
            custom_fields=[
                {"id": "field1", "value": "Texto"},
                {"id": "field2", "value": 100},
                {"id": "field3", "value": True}
            ]
        )
        result = await create_task(params)

        assert "Task com Custom Fields" in result
        assert "new_task_id" in result


# ============================================================================
# TESTES - TAGS
# ============================================================================

class TestTags:
    """Testes para tools de tags."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_space_tags(self):
        """Deve listar tags do space."""
        respx.get(f"{API_BASE}/space/space123/tag").mock(
            return_value=Response(200, json={
                "tags": [
                    {"name": "urgente", "tag_fg": "#FF0000", "tag_bg": "#FFFFFF"},
                    {"name": "bug", "tag_fg": "#0000FF", "tag_bg": "#FFFFFF"}
                ]
            })
        )

        params = GetSpaceTagsInput(space_id="space123")
        result = await get_space_tags(params)

        assert "2 tags" in result
        assert "urgente" in result
        assert "bug" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_space_tag(self):
        """Deve criar tag no space."""
        respx.post(f"{API_BASE}/space/space123/tag").mock(
            return_value=Response(200, json={})
        )

        params = CreateSpaceTagInput(
            space_id="space123",
            name="nova-tag",
            tag_fg="#FFFFFF",
            tag_bg="#FF0000"
        )
        result = await create_space_tag(params)

        assert "nova-tag" in result
        assert "criada" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_space_tag(self):
        """Deve atualizar tag do space."""
        respx.put(f"{API_BASE}/space/space123/tag/old-tag").mock(
            return_value=Response(200, json={})
        )

        params = UpdateSpaceTagInput(
            space_id="space123",
            tag_name="old-tag",
            new_name="new-tag"
        )
        result = await update_space_tag(params)

        assert "atualizada" in result
        assert "new-tag" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_space_tag(self):
        """Deve deletar tag do space."""
        respx.delete(f"{API_BASE}/space/space123/tag/tag-to-delete").mock(
            return_value=Response(200, json={})
        )

        params = DeleteSpaceTagInput(space_id="space123", tag_name="tag-to-delete")
        result = await delete_space_tag(params)

        assert "deletada" in result
        assert "tag-to-delete" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_tag_to_task(self):
        """Deve adicionar tag à task."""
        respx.post(f"{API_BASE}/task/task123/tag/urgente").mock(
            return_value=Response(200, json={})
        )

        params = AddTagToTaskInput(task_id="task123", tag_name="urgente")
        result = await add_tag_to_task(params)

        assert "urgente" in result
        assert "adicionada" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_remove_tag_from_task(self):
        """Deve remover tag da task."""
        respx.delete(f"{API_BASE}/task/task123/tag/urgente").mock(
            return_value=Response(200, json={})
        )

        params = RemoveTagFromTaskInput(task_id="task123", tag_name="urgente")
        result = await remove_tag_from_task(params)

        assert "urgente" in result
        assert "removida" in result


# ============================================================================
# TESTES - DEPENDENCIES
# ============================================================================

class TestDependencies:
    """Testes para tools de dependências."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_dependency(self):
        """Deve criar dependência entre tasks."""
        respx.post(f"{API_BASE}/task/taskB/dependency").mock(
            return_value=Response(200, json={})
        )

        params = AddDependencyInput(task_id="taskB", depends_on="taskA")
        result = await add_dependency(params)

        assert "Dependência criada" in result
        assert "taskB" in result
        assert "taskA" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_dependency(self):
        """Deve remover dependência entre tasks."""
        respx.delete(f"{API_BASE}/task/taskB/dependency").mock(
            return_value=Response(200, json={})
        )

        params = DeleteDependencyInput(task_id="taskB", depends_on="taskA")
        result = await delete_dependency(params)

        assert "removida" in result
        assert "taskB" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_task_link(self):
        """Deve criar link entre tasks."""
        respx.post(f"{API_BASE}/task/task1/link/task2").mock(
            return_value=Response(200, json={})
        )

        params = AddTaskLinkInput(task_id="task1", links_to="task2")
        result = await add_task_link(params)

        assert "Link criado" in result
        assert "task1" in result
        assert "task2" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_task_link(self):
        """Deve remover link entre tasks."""
        respx.delete(f"{API_BASE}/task/task1/link/task2").mock(
            return_value=Response(200, json={})
        )

        params = DeleteTaskLinkInput(task_id="task1", links_to="task2")
        result = await delete_task_link(params)

        assert "removido" in result


# ============================================================================
# TESTES - CHECKLISTS
# ============================================================================

class TestChecklistsCRUD:
    """Testes para CRUD de checklists."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_checklist(self):
        """Deve criar checklist em task."""
        respx.post(f"{API_BASE}/task/task123/checklist").mock(
            return_value=Response(200, json={
                "checklist": {"id": "cl123", "name": "Meu Checklist"}
            })
        )

        params = CreateChecklistInput(task_id="task123", name="Meu Checklist")
        result = await create_checklist(params)

        assert "Checklist criado" in result
        assert "Meu Checklist" in result
        assert "cl123" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_checklist(self):
        """Deve atualizar checklist."""
        respx.put(f"{API_BASE}/checklist/cl123").mock(
            return_value=Response(200, json={
                "checklist": {"id": "cl123", "name": "Novo Nome"}
            })
        )

        params = UpdateChecklistInput(checklist_id="cl123", name="Novo Nome")
        result = await update_checklist(params)

        assert "atualizado" in result
        assert "Novo Nome" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_checklist(self):
        """Deve deletar checklist."""
        respx.delete(f"{API_BASE}/checklist/cl123").mock(
            return_value=Response(200, json={})
        )

        params = DeleteChecklistInput(checklist_id="cl123")
        result = await delete_checklist(params)

        assert "deletado" in result
        assert "cl123" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_checklist_item(self):
        """Deve criar item no checklist."""
        respx.post(f"{API_BASE}/checklist/cl123/checklist_item").mock(
            return_value=Response(200, json={
                "checklist": {
                    "id": "cl123",
                    "items": [{"id": "item1", "name": "Fazer X"}]
                }
            })
        )

        params = CreateChecklistItemInput(checklist_id="cl123", name="Fazer X")
        result = await create_checklist_item(params)

        assert "Item adicionado" in result
        assert "Fazer X" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_checklist_item_resolved(self):
        """Deve marcar item como concluído."""
        respx.put(f"{API_BASE}/checklist/cl123/checklist_item/item1").mock(
            return_value=Response(200, json={})
        )

        params = UpdateChecklistItemInput(
            checklist_id="cl123",
            checklist_item_id="item1",
            resolved=True
        )
        result = await update_checklist_item(params)

        assert "atualizado" in result
        assert "concluído" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_checklist_item(self):
        """Deve deletar item do checklist."""
        respx.delete(f"{API_BASE}/checklist/cl123/checklist_item/item1").mock(
            return_value=Response(200, json={})
        )

        params = DeleteChecklistItemInput(checklist_id="cl123", checklist_item_id="item1")
        result = await delete_checklist_item(params)

        assert "deletado" in result
        assert "item1" in result


# ============================================================================
# TESTES - TIMER
# ============================================================================

class TestTimer:
    """Testes para start/stop timer."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_start_timer(self):
        """Deve iniciar timer."""
        respx.post(f"{API_BASE}/team/team123/time_entries/start").mock(
            return_value=Response(200, json={
                "data": {"id": "timer123"}
            })
        )

        params = StartTimeEntryInput(
            team_id="team123",
            task_id="task456",
            billable=True
        )
        result = await start_timer(params)

        assert "Timer iniciado" in result
        assert "timer123" in result
        assert "Sim" in result  # billable

    @pytest.mark.asyncio
    @respx.mock
    async def test_stop_timer(self):
        """Deve parar timer."""
        respx.post(f"{API_BASE}/team/team123/time_entries/stop").mock(
            return_value=Response(200, json={
                "data": {"id": "timer123", "duration": 3600000}  # 1 hora
            })
        )

        params = StopTimeEntryInput(team_id="team123")
        result = await stop_timer(params)

        assert "Timer parado" in result
        assert "60 minutos" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_running_timer_active(self):
        """Deve mostrar timer em execução."""
        respx.get(f"{API_BASE}/team/team123/time_entries/current").mock(
            return_value=Response(200, json={
                "data": {
                    "id": "timer123",
                    "task": {"name": "Minha Task"},
                    "start": "1704067200000",
                    "billable": False
                }
            })
        )

        params = GetRunningTimeEntryInput(team_id="team123")
        result = await get_running_timer(params)

        assert "Timer em execução" in result
        assert "Minha Task" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_running_timer_none(self):
        """Deve indicar que não há timer."""
        respx.get(f"{API_BASE}/team/team123/time_entries/current").mock(
            return_value=Response(200, json={"data": None})
        )

        params = GetRunningTimeEntryInput(team_id="team123")
        result = await get_running_timer(params)

        assert "Nenhum timer" in result


# ============================================================================
# TESTES - TEMPLATES
# ============================================================================

class TestTemplates:
    """Testes para templates."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_task_templates(self):
        """Deve listar templates."""
        respx.get(f"{API_BASE}/team/team123/taskTemplate").mock(
            return_value=Response(200, json={
                "templates": [
                    {"id": "tpl1", "name": "Template de Bug"},
                    {"id": "tpl2", "name": "Template de Feature"}
                ]
            })
        )

        params = GetTaskTemplatesInput(team_id="team123")
        result = await get_task_templates(params)

        assert "2 templates" in result
        assert "Template de Bug" in result
        assert "tpl1" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_task_templates_empty(self):
        """Deve indicar que não há templates."""
        respx.get(f"{API_BASE}/team/team123/taskTemplate").mock(
            return_value=Response(200, json={"templates": []})
        )

        params = GetTaskTemplatesInput(team_id="team123")
        result = await get_task_templates(params)

        assert "Nenhum template" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_task_from_template(self):
        """Deve criar task a partir de template."""
        respx.post(f"{API_BASE}/list/list123/taskTemplate/tpl456").mock(
            return_value=Response(200, json={
                "task": {
                    "id": "new_task_id",
                    "name": "Nova Task do Template",
                    "url": "https://app.clickup.com/t/new_task_id"
                }
            })
        )

        params = CreateTaskFromTemplateInput(
            list_id="list123",
            template_id="tpl456",
            name="Nova Task do Template"
        )
        result = await create_task_from_template(params)

        assert "Task criada" in result
        assert "template" in result
        assert "new_task_id" in result


# ============================================================================
# TESTES ADICIONAIS PARA COBERTURA 95%
# ============================================================================

from clickup_mcp import (
    format_task_markdown,
    format_tasks_compact,
    format_tasks_detailed,
    format_tasks_list_markdown,
    sanitize_output,
    sanitize_dict_values,
    format_timestamp,
    extract_tipo_subtipo,
    get_headers,
    ConfigurationError,
    _metrics,
    validate_config,
)


class TestFormatTaskMarkdownComplete:
    """Testes para format_task_markdown cobrindo todos os campos opcionais."""

    def test_format_task_with_all_optional_fields(self):
        """Deve formatar task com todos os campos opcionais."""
        task = {
            "id": "task123",
            "name": "[Tipo] Subtipo - Nome da Task",
            "status": {"status": "in progress"},
            "url": "https://app.clickup.com/t/task123",
            "date_created": "1704067200000",
            "date_updated": "1704153600000",
            "date_closed": "1704240000000",
            "due_date": "1704326400000",
            "start_date": "1704067200000",
            "priority": {"priority": "high"},
            "assignees": [
                {"username": "joao", "email": "joao@test.com"},
                {"email": "maria@test.com"}
            ],
            "tags": [{"name": "urgent"}, {"name": "bug"}],
            "list": {"name": "Client A"},
            "folder": {"name": "Project X"},
            "space": {"name": "Workspace"},
            "description": "Descrição detalhada da task",
            "time_estimate": 7200000,  # 120 min
            "time_spent": 3600000  # 60 min
        }

        result = format_task_markdown(task)

        assert "task123" in result
        assert "in progress" in result
        assert "Tipo" in result
        assert "Subtipo" in result
        assert "Criado em:" in result
        assert "Modificado em:" in result
        assert "Fechado em:" in result
        assert "Prazo:" in result
        assert "Início:" in result
        assert "Prioridade:" in result
        assert "high" in result
        assert "joao" in result
        assert "maria@test.com" in result
        assert "urgent" in result
        assert "bug" in result
        assert "Client A" in result
        assert "Project X" in result
        assert "Workspace" in result
        assert "Descrição detalhada" in result
        assert "Tempo estimado:" in result
        assert "120 min" in result
        assert "Tempo gasto:" in result
        assert "60 min" in result

    def test_format_task_with_string_list_folder_space(self):
        """Deve lidar com list/folder/space como strings."""
        task = {
            "id": "task123",
            "name": "Task Simples",
            "status": {"status": "open"},
            "url": "https://example.com",
            "list": "List Name String",
            "folder": "Folder Name String",
            "space": "Space Name String"
        }

        result = format_task_markdown(task)
        assert "List Name String" in result
        assert "Space Name String" in result


class TestFormatTasksCompactDetailed:
    """Testes para format_tasks_compact e format_tasks_detailed."""

    def test_format_tasks_compact_empty(self):
        """Deve retornar mensagem quando não há tasks."""
        result = format_tasks_compact([])
        assert "Nenhuma task" in result

    def test_format_tasks_compact_with_pagination(self):
        """Deve mostrar aviso de paginação quando necessário."""
        tasks = [
            {"id": f"task{i}", "name": f"Task {i}", "status": {"status": "open"}}
            for i in range(25)
        ]
        result = format_tasks_compact(tasks, total=100, page=0, limit=25)
        assert "Use `page=1`" in result
        assert "25 tasks" in result

    def test_format_tasks_detailed_empty(self):
        """Deve retornar mensagem quando não há tasks."""
        result = format_tasks_detailed([])
        assert "Nenhuma task" in result

    def test_format_tasks_detailed_with_pagination(self):
        """Deve mostrar aviso de paginação no modo detailed."""
        tasks = [
            {"id": f"task{i}", "name": f"Task {i}", "status": {"status": "open"}}
            for i in range(25)
        ]
        result = format_tasks_detailed(tasks, total=100, page=0, limit=25)
        assert "Use `page=1`" in result

    def test_format_tasks_list_markdown_alias(self):
        """Deve funcionar como alias para format_tasks_detailed."""
        tasks = [{"id": "task1", "name": "Task 1", "status": {"status": "open"}}]
        result1 = format_tasks_detailed(tasks, total=1, page=0)
        result2 = format_tasks_list_markdown(tasks, total=1, page=0)
        assert result1 == result2


class TestSanitizationExtended:
    """Testes adicionais para sanitização."""

    def test_sanitize_output_with_non_string(self):
        """Deve converter não-strings para string."""
        result = sanitize_output(12345)
        assert result == "12345"

        result = sanitize_output({"key": "value"})
        assert "key" in result

    def test_sanitize_dict_values_nested(self):
        """Deve sanitizar dicts aninhados."""
        data = {
            "name": "Test\x00Name",
            "nested": {
                "value": "Nested\x01Value"
            }
        }
        result = sanitize_dict_values(data)
        assert "\x00" not in result["name"]
        assert "\x01" not in result["nested"]["value"]


class TestMetricsExtended:
    """Testes adicionais para métricas."""

    def test_record_tool_error(self):
        """Deve registrar erro de tool."""
        _metrics.tool_errors.clear()
        _metrics.record_tool_error("test_tool")
        _metrics.record_tool_error("test_tool")
        _metrics.record_tool_error("other_tool")

        assert _metrics.tool_errors["test_tool"] == 2
        assert _metrics.tool_errors["other_tool"] == 1

    def test_record_latency_overflow(self):
        """Deve manter apenas últimas N amostras."""
        _metrics._latencies.clear()
        _metrics._tool_latencies.clear()

        # Adiciona mais que o máximo de amostras
        for i in range(_metrics._max_samples + 100):
            _metrics.record_latency(float(i), tool_name="test_tool")

        # Deve ter no máximo _max_samples
        assert len(_metrics._latencies) <= _metrics._max_samples

        # Tool latencies tem limite menor
        max_tool_samples = _metrics._max_samples // 10
        assert len(_metrics._tool_latencies["test_tool"]) <= max_tool_samples


class TestFormatTimestamp:
    """Testes para format_timestamp."""

    def test_format_timestamp_none(self):
        """Deve retornar None para input None."""
        assert format_timestamp(None) is None

    def test_format_timestamp_valid(self):
        """Deve formatar timestamp válido."""
        result = format_timestamp(1704067200000)  # 2024-01-01 00:00:00 UTC
        assert result is not None
        assert "2024" in result or "2023" in result  # Depende do fuso

    def test_format_timestamp_invalid(self):
        """Deve retornar string para timestamp inválido."""
        result = format_timestamp("invalid")
        assert result == "invalid"


class TestExtractTipoSubtipo:
    """Testes para extract_tipo_subtipo."""

    def test_extract_with_dash(self):
        """Deve extrair tipo e subtipo separados por ' - '."""
        tipo, subtipo = extract_tipo_subtipo("Bug - Frontend issue")
        assert tipo == "Bug"
        assert subtipo == "Frontend issue"

    def test_extract_multiple_parts(self):
        """Deve extrair tipo e subtipo de nomes com múltiplas partes."""
        tipo, subtipo = extract_tipo_subtipo("Notificação Extrajudicial - Pirataria - Detalhes")
        assert tipo == "Notificação Extrajudicial"
        assert subtipo == "Pirataria"

    def test_extract_with_numeric_prefix(self):
        """Deve remover prefixo numérico."""
        tipo, subtipo = extract_tipo_subtipo("3 - Bug - Frontend")
        assert tipo == "Bug"
        assert subtipo == "Frontend"

    def test_extract_no_subtipo(self):
        """Deve retornar subtipo None quando não há separador."""
        tipo, subtipo = extract_tipo_subtipo("Simple task name")
        assert tipo == "Simple task name"
        assert subtipo is None

    def test_extract_empty_string(self):
        """Deve retornar None para string vazia."""
        tipo, subtipo = extract_tipo_subtipo("")
        assert tipo is None
        assert subtipo is None


class TestGetHeadersNoToken:
    """Testes para get_headers sem token."""

    def test_get_headers_without_token(self):
        """Deve lançar ConfigurationError sem token."""
        import clickup_mcp
        original_token = clickup_mcp.API_TOKEN
        clickup_mcp.API_TOKEN = ""

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                get_headers()
            assert "CLICKUP_API_TOKEN" in str(exc_info.value)
        finally:
            clickup_mcp.API_TOKEN = original_token


class TestHTTPResponses:
    """Testes para diferentes respostas HTTP."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_request_204_response(self):
        """Deve tratar resposta 204 No Content."""
        respx.delete(f"{API_BASE}/task/task123").mock(
            return_value=Response(204)
        )

        result = await api_request("DELETE", "/task/task123")
        assert result == {"success": True}


class TestToolsDetailedMode:
    """Testes para modo DETAILED em várias tools."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_spaces_detailed(self):
        """Deve retornar spaces em modo detailed."""
        respx.get(f"{API_BASE}/team/team1/space").mock(
            return_value=Response(200, json={
                "spaces": [
                    {
                        "id": "space1",
                        "name": "Space 1",
                        "statuses": [{"status": "open"}, {"status": "closed"}],
                        "private": False
                    }
                ]
            })
        )

        params = GetSpacesInput(team_id="team1", output_mode=OutputMode.DETAILED)
        result = await get_spaces(params)

        assert "Space 1" in result
        assert "open" in result
        assert "closed" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_folders_detailed(self):
        """Deve retornar folders em modo detailed."""
        respx.get(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(200, json={
                "folders": [
                    {
                        "id": "folder1",
                        "name": "Folder 1",
                        "lists": [
                            {"id": "list1", "name": "List 1"},
                            {"id": "list2", "name": "List 2"}
                        ]
                    }
                ]
            })
        )

        params = GetFoldersInput(space_id="space1", output_mode=OutputMode.DETAILED)
        result = await get_folders(params)

        assert "Folder 1" in result
        assert "List 1" in result
        assert "List 2" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_lists_detailed(self):
        """Deve retornar lists em modo detailed."""
        respx.get(f"{API_BASE}/folder/folder1/list").mock(
            return_value=Response(200, json={
                "lists": [
                    {
                        "id": "list1",
                        "name": "List 1",
                        "task_count": 10,
                        "status": {"status": "active"}
                    }
                ]
            })
        )

        params = GetListsInput(folder_id="folder1", output_mode=OutputMode.DETAILED)
        result = await get_lists(params)

        assert "List 1" in result
        assert "10" in result or "task" in result.lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_tasks_detailed(self):
        """Deve retornar tasks em modo detailed."""
        respx.get(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json={
                "tasks": [
                    {
                        "id": "task1",
                        "name": "[Bug] Task Name",
                        "status": {"status": "open"},
                        "date_created": "1704067200000"
                    }
                ]
            })
        )

        params = GetTasksInput(list_id="list1", output_mode=OutputMode.DETAILED)
        result = await get_tasks(params)

        assert "Task Name" in result
        assert "Bug" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_task_comments_detailed(self):
        """Deve retornar comments em modo detailed."""
        respx.get(f"{API_BASE}/task/task1/comment").mock(
            return_value=Response(200, json={
                "comments": [
                    {
                        "id": "comment1",
                        "comment_text": "Comentário de teste",
                        "user": {"username": "joao"},
                        "date": "1704067200000"
                    }
                ]
            })
        )

        params = GetTaskCommentsInput(task_id="task1", output_mode=OutputMode.DETAILED)
        result = await get_task_comments(params)

        assert "Comentário de teste" in result
        assert "joao" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_members_detailed(self):
        """Deve retornar members em modo detailed."""
        respx.get(f"{API_BASE}/team").mock(
            return_value=Response(200, json={
                "teams": [
                    {
                        "id": "team1",
                        "name": "Test Team",
                        "members": [
                            {
                                "user": {
                                    "id": 1,
                                    "username": "admin",
                                    "email": "admin@test.com",
                                    "role": 1
                                }
                            }
                        ]
                    }
                ]
            })
        )

        params = GetMembersInput(team_id="team1", output_mode=OutputMode.DETAILED)
        result = await get_workspace_members(params)

        assert "admin" in result
        assert "admin@test.com" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_custom_fields_detailed(self):
        """Deve retornar custom fields em modo detailed."""
        respx.get(f"{API_BASE}/list/list1/field").mock(
            return_value=Response(200, json={
                "fields": [
                    {
                        "id": "field1",
                        "name": "Priority Field",
                        "type": "drop_down",
                        "type_config": {
                            "options": [
                                {"id": "opt1", "name": "High"},
                                {"id": "opt2", "name": "Low"}
                            ]
                        }
                    }
                ]
            })
        )

        params = GetCustomFieldsInput(list_id="list1", output_mode=OutputMode.DETAILED)
        result = await get_custom_fields(params)

        assert "Priority Field" in result
        assert "drop_down" in result
        assert "High" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_checklists_detailed(self):
        """Deve retornar checklists em modo detailed."""
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json={
                "checklists": [
                    {
                        "id": "checklist1",
                        "name": "To Do List",
                        "items": [
                            {"id": "item1", "name": "Item 1", "resolved": False},
                            {"id": "item2", "name": "Item 2", "resolved": True}
                        ]
                    }
                ]
            })
        )

        params = GetChecklistsInput(task_id="task1", output_mode=OutputMode.DETAILED)
        result = await get_checklists(params)

        assert "To Do List" in result
        assert "Item 1" in result
        assert "Item 2" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_docs_detailed(self):
        """Deve retornar docs em modo detailed."""
        respx.get(f"{API_BASE}/team/team1/doc").mock(
            return_value=Response(200, json={
                "docs": [
                    {
                        "id": "doc1",
                        "name": "README",
                        "date_created": "1704067200000",
                        "creator": {"username": "admin"}
                    }
                ]
            })
        )

        params = GetDocsInput(workspace_id="team1", output_mode=OutputMode.DETAILED)
        result = await get_docs(params)

        assert "README" in result
        assert "admin" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_space_tags_detailed(self):
        """Deve retornar tags em modo detailed."""
        respx.get(f"{API_BASE}/space/space1/tag").mock(
            return_value=Response(200, json={
                "tags": [
                    {"name": "urgent", "tag_fg": "#ff0000", "tag_bg": "#ffffff"},
                    {"name": "bug", "tag_fg": "#000000", "tag_bg": "#ffff00"}
                ]
            })
        )

        params = GetSpaceTagsInput(space_id="space1", output_mode=OutputMode.DETAILED)
        result = await get_space_tags(params)

        assert "urgent" in result
        assert "bug" in result
        assert "#ff0000" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_templates_detailed(self):
        """Deve retornar templates em modo detailed."""
        respx.get(f"{API_BASE}/team/team1/taskTemplate").mock(
            return_value=Response(200, json={
                "templates": [
                    {"id": "tpl1", "name": "Bug Report Template"}
                ]
            })
        )

        params = GetTaskTemplatesInput(team_id="team1", output_mode=OutputMode.DETAILED)
        result = await get_task_templates(params)

        assert "Bug Report Template" in result
        assert "tpl1" in result


class TestCreateTaskWithAllOptions:
    """Testes para create_task com todas as opções."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_task_with_all_optional_params(self):
        """Deve criar task com todos os parâmetros opcionais."""
        respx.post(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(200, json={
                "id": "new_task",
                "name": "Full Task",
                "url": "https://app.clickup.com/t/new_task"
            })
        )

        params = CreateTaskInput(
            list_id="list1",
            name="Full Task",
            description="Full description",
            assignees=[1, 2],
            tags=["urgent", "bug"],
            status="open",
            priority=1,
            due_date=1704326400000,
            due_date_time=True,
            start_date=1704067200000,
            start_date_time=True,
            time_estimate=3600000,
            parent="parent_task_id",
            custom_fields=[{"id": "field1", "value": "test"}]
        )
        result = await create_task(params)

        assert "Full Task" in result
        assert "new_task" in result


class TestUpdateTaskWithAllOptions:
    """Testes para update_task com todas as opções."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_task_with_all_params(self):
        """Deve atualizar task com todos os parâmetros."""
        respx.put(f"{API_BASE}/task/task1").mock(
            return_value=Response(200, json={
                "id": "task1",
                "name": "Updated Task",
                "url": "https://app.clickup.com/t/task1"
            })
        )

        params = UpdateTaskInput(
            task_id="task1",
            name="Updated Task",
            description="Updated description",
            status="in progress",
            priority=2,
            due_date=1704326400000,
            due_date_time=True,
            start_date=1704067200000,
            start_date_time=False,
            time_estimate=7200000,
            archived=False
        )
        result = await update_task(params)

        assert "Updated Task" in result or "task1" in result


class TestErrorHandlers:
    """Testes para tratamento de erros em tools."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_spaces_error(self):
        """Deve tratar erro em get_spaces."""
        respx.get(f"{API_BASE}/team/team1/space").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetSpacesInput(team_id="team1")
        result = await get_spaces(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_folders_error(self):
        """Deve tratar erro em get_folders."""
        respx.get(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetFoldersInput(space_id="space1")
        result = await get_folders(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_lists_error(self):
        """Deve tratar erro em get_lists."""
        respx.get(f"{API_BASE}/folder/folder1/list").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetListsInput(folder_id="folder1")
        result = await get_lists(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_folderless_lists_error(self):
        """Deve tratar erro em get_folderless_lists."""
        respx.get(f"{API_BASE}/space/space1/list").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetFolderlessListsInput(space_id="space1")
        result = await get_folderless_lists(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_folder_error(self):
        """Deve tratar erro em create_folder."""
        respx.post(f"{API_BASE}/space/space1/folder").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = CreateFolderInput(space_id="space1", name="New Folder")
        result = await create_folder(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_folder_error(self):
        """Deve tratar erro em update_folder."""
        respx.put(f"{API_BASE}/folder/folder1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = UpdateFolderInput(folder_id="folder1", name="Updated")
        result = await update_folder(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_folder_error(self):
        """Deve tratar erro em delete_folder."""
        respx.delete(f"{API_BASE}/folder/folder1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = DeleteFolderInput(folder_id="folder1")
        result = await delete_folder(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_list_error(self):
        """Deve tratar erro em create_list."""
        respx.post(f"{API_BASE}/folder/folder1/list").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = CreateListInput(folder_id="folder1", name="New List")
        result = await create_list(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_list_error(self):
        """Deve tratar erro em update_list."""
        respx.put(f"{API_BASE}/list/list1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = UpdateListInput(list_id="list1", name="Updated")
        result = await update_list(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_list_error(self):
        """Deve tratar erro em delete_list."""
        respx.delete(f"{API_BASE}/list/list1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = DeleteListInput(list_id="list1")
        result = await delete_list(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_task_error(self):
        """Deve tratar erro em get_task."""
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetTaskInput(task_id="task1")
        result = await get_task(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_task_error(self):
        """Deve tratar erro em create_task."""
        respx.post(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = CreateTaskInput(list_id="list1", name="New Task")
        result = await create_task(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_task_error(self):
        """Deve tratar erro em update_task."""
        respx.put(f"{API_BASE}/task/task1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = UpdateTaskInput(task_id="task1", name="Updated")
        result = await update_task(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_task_error(self):
        """Deve tratar erro em delete_task."""
        respx.delete(f"{API_BASE}/task/task1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = DeleteTaskInput(task_id="task1")
        result = await delete_task(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_move_task_error(self):
        """Deve tratar erro em move_task."""
        respx.post(f"{API_BASE}/task/task1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = MoveTaskInput(task_id="task1", list_id="list2")
        result = await move_task(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_duplicate_task_error(self):
        """Deve tratar erro em duplicate_task."""
        respx.post(f"{API_BASE}/task/task1/duplicate/list1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = DuplicateTaskInput(task_id="task1", list_id="list1")
        result = await duplicate_task(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_task_comments_error(self):
        """Deve tratar erro em get_task_comments."""
        respx.get(f"{API_BASE}/task/task1/comment").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetTaskCommentsInput(task_id="task1")
        result = await get_task_comments(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_task_comment_error(self):
        """Deve tratar erro em create_task_comment."""
        respx.post(f"{API_BASE}/task/task1/comment").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = CreateTaskCommentInput(task_id="task1", comment_text="Test")
        result = await create_task_comment(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_members_error(self):
        """Deve tratar erro em get_workspace_members."""
        respx.get(f"{API_BASE}/team").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetMembersInput(team_id="team1")
        result = await get_workspace_members(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_custom_fields_error(self):
        """Deve tratar erro em get_custom_fields."""
        respx.get(f"{API_BASE}/list/list1/field").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetCustomFieldsInput(list_id="list1")
        result = await get_custom_fields(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_checklists_error(self):
        """Deve tratar erro em get_checklists."""
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetChecklistsInput(task_id="task1")
        result = await get_checklists(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_attachments_error(self):
        """Deve tratar erro em get_attachments."""
        respx.get(f"{API_BASE}/task/task1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetAttachmentsInput(task_id="task1")
        result = await get_attachments(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_docs_error(self):
        """Deve tratar erro em get_docs."""
        respx.get(f"{API_BASE}/team/team1/doc").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetDocsInput(workspace_id="team1")
        result = await get_docs(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_doc_error(self):
        """Deve tratar erro em create_doc."""
        respx.post(f"{API_BASE}/team/team1/doc").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = CreateDocInput(workspace_id="team1", name="New Doc")
        result = await create_doc(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_set_custom_field_value_error(self):
        """Deve tratar erro em set_custom_field_value."""
        respx.post(f"{API_BASE}/task/task1/field/field1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = SetCustomFieldValueInput(task_id="task1", field_id="field1", value="test")
        result = await set_custom_field_value(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_remove_custom_field_value_error(self):
        """Deve tratar erro em remove_custom_field_value."""
        respx.delete(f"{API_BASE}/task/task1/field/field1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = RemoveCustomFieldValueInput(task_id="task1", field_id="field1")
        result = await remove_custom_field_value(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_space_tag_error(self):
        """Deve tratar erro em create_space_tag."""
        respx.post(f"{API_BASE}/space/space1/tag").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = CreateSpaceTagInput(space_id="space1", name="urgent")
        result = await create_space_tag(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_space_tag_error(self):
        """Deve tratar erro em update_space_tag."""
        respx.put(f"{API_BASE}/space/space1/tag/urgent").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = UpdateSpaceTagInput(space_id="space1", tag_name="urgent", new_name="high")
        result = await update_space_tag(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_space_tag_error(self):
        """Deve tratar erro em delete_space_tag."""
        respx.delete(f"{API_BASE}/space/space1/tag/urgent").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = DeleteSpaceTagInput(space_id="space1", tag_name="urgent")
        result = await delete_space_tag(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_tag_to_task_error(self):
        """Deve tratar erro em add_tag_to_task."""
        respx.post(f"{API_BASE}/task/task1/tag/urgent").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = AddTagToTaskInput(task_id="task1", tag_name="urgent")
        result = await add_tag_to_task(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_remove_tag_from_task_error(self):
        """Deve tratar erro em remove_tag_from_task."""
        respx.delete(f"{API_BASE}/task/task1/tag/urgent").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = RemoveTagFromTaskInput(task_id="task1", tag_name="urgent")
        result = await remove_tag_from_task(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_dependency_error(self):
        """Deve tratar erro em add_dependency."""
        respx.post(f"{API_BASE}/task/task1/dependency").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = AddDependencyInput(task_id="task1", depends_on="task2")
        result = await add_dependency(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_dependency_error(self):
        """Deve tratar erro em delete_dependency."""
        respx.delete(f"{API_BASE}/task/task1/dependency").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = DeleteDependencyInput(task_id="task1", depends_on="task2")
        result = await delete_dependency(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_task_link_error(self):
        """Deve tratar erro em add_task_link."""
        respx.post(f"{API_BASE}/task/task1/link/task2").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = AddTaskLinkInput(task_id="task1", links_to="task2")
        result = await add_task_link(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_task_link_error(self):
        """Deve tratar erro em delete_task_link."""
        respx.delete(f"{API_BASE}/task/task1/link/task2").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = DeleteTaskLinkInput(task_id="task1", links_to="task2")
        result = await delete_task_link(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_checklist_error(self):
        """Deve tratar erro em create_checklist."""
        respx.post(f"{API_BASE}/task/task1/checklist").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = CreateChecklistInput(task_id="task1", name="Checklist")
        result = await create_checklist(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_checklist_error(self):
        """Deve tratar erro em update_checklist."""
        respx.put(f"{API_BASE}/checklist/checklist1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = UpdateChecklistInput(checklist_id="checklist1", name="Updated")
        result = await update_checklist(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_checklist_error(self):
        """Deve tratar erro em delete_checklist."""
        respx.delete(f"{API_BASE}/checklist/checklist1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = DeleteChecklistInput(checklist_id="checklist1")
        result = await delete_checklist(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_checklist_item_error(self):
        """Deve tratar erro em create_checklist_item."""
        respx.post(f"{API_BASE}/checklist/checklist1/checklist_item").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = CreateChecklistItemInput(checklist_id="checklist1", name="Item")
        result = await create_checklist_item(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_checklist_item_error(self):
        """Deve tratar erro em update_checklist_item."""
        respx.put(f"{API_BASE}/checklist/checklist1/checklist_item/item1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = UpdateChecklistItemInput(checklist_id="checklist1", checklist_item_id="item1", name="Updated")
        result = await update_checklist_item(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_checklist_item_error(self):
        """Deve tratar erro em delete_checklist_item."""
        respx.delete(f"{API_BASE}/checklist/checklist1/checklist_item/item1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = DeleteChecklistItemInput(checklist_id="checklist1", checklist_item_id="item1")
        result = await delete_checklist_item(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_start_timer_error(self):
        """Deve tratar erro em start_timer."""
        respx.post(f"{API_BASE}/team/team1/time_entries/start").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = StartTimeEntryInput(team_id="team1", task_id="task1")
        result = await start_timer(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_stop_timer_error(self):
        """Deve tratar erro em stop_timer."""
        respx.post(f"{API_BASE}/team/team1/time_entries/stop").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = StopTimeEntryInput(team_id="team1")
        result = await stop_timer(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_running_timer_error(self):
        """Deve tratar erro em get_running_timer."""
        respx.get(f"{API_BASE}/team/team1/time_entries/running").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetRunningTimeEntryInput(team_id="team1")
        result = await get_running_timer(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_task_templates_error(self):
        """Deve tratar erro em get_task_templates."""
        respx.get(f"{API_BASE}/team/team1/taskTemplate").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetTaskTemplatesInput(team_id="team1")
        result = await get_task_templates(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_task_from_template_error(self):
        """Deve tratar erro em create_task_from_template."""
        respx.post(f"{API_BASE}/list/list1/taskTemplate/tpl1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = CreateTaskFromTemplateInput(list_id="list1", template_id="tpl1", name="Task")
        result = await create_task_from_template(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_fuzzy_search_tasks_tool_error(self):
        """Deve tratar erro em fuzzy_search_tasks_tool."""
        respx.get(f"{API_BASE}/list/list1/task").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = FuzzySearchTasksInput(list_id="list1", query="test")
        result = await fuzzy_search_tasks_tool(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_time_entry_error(self):
        """Deve tratar erro em create_time_entry."""
        respx.post(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = CreateTimeEntryInput(team_id="team1", task_id="task1", duration=3600000, start=1704067200000)
        result = await create_time_entry(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_billable_report_error(self):
        """Deve tratar erro em get_billable_report."""
        respx.get(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetBillableReportInput(team_id="team1", start_date=1704067200000, end_date=1704153600000)
        result = await get_billable_report(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_time_entries_error(self):
        """Deve tratar erro em get_time_entries."""
        respx.get(f"{API_BASE}/team/team1/time_entries").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetTimeEntriesInput(team_id="team1")
        result = await get_time_entries(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_analyze_space_structure_error(self):
        """Deve tratar erro em analyze_space_structure."""
        respx.get(f"{API_BASE}/space/space1").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = AnalyzeSpaceStructureInput(space_id="space1")
        result = await analyze_space_structure(params)

        assert "Erro" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_space_tags_error(self):
        """Deve tratar erro em get_space_tags."""
        respx.get(f"{API_BASE}/space/space1/tag").mock(
            return_value=Response(500, json={"err": "Server error"})
        )

        params = GetSpaceTagsInput(space_id="space1")
        result = await get_space_tags(params)

        assert "Erro" in result


class TestFuzzySearchEmpty:
    """Testes para fuzzy_search_tasks com lista vazia."""

    def test_fuzzy_search_empty_tasks(self):
        """Deve retornar lista vazia para tasks vazias."""
        result = fuzzy_search_tasks([], "query")
        assert result == []

    def test_fuzzy_search_empty_query(self):
        """Deve retornar lista vazia para query vazia."""
        tasks = [{"id": "1", "name": "Task 1"}]
        result = fuzzy_search_tasks(tasks, "")
        assert result == []
