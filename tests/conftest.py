"""
Fixtures para testes do MCP ClickUp.
"""
import pytest


@pytest.fixture
def mock_task():
    """Task de exemplo para testes."""
    return {
        "id": "abc123",
        "name": "Notificação Extrajudicial - Pirataria - Cliente X",
        "status": {"status": "Em andamento"},
        "date_created": "1704067200000",
        "date_updated": "1704153600000",
        "due_date": "1704240000000",
        "assignees": [{"username": "joao"}],
        "list": {"id": "list1", "name": "Cliente X"},
        "folder": {"id": "folder1", "name": "Plano Premium"},
        "space": {"id": "space1"},
        "url": "https://app.clickup.com/t/abc123",
        "description": "Descrição da task"
    }


@pytest.fixture
def mock_tasks(mock_task):
    """Lista de tasks para testes."""
    return [mock_task for _ in range(10)]


@pytest.fixture
def mock_workspace():
    """Workspace de exemplo."""
    return {
        "id": "team1",
        "name": "Helper Consultoria",
        "members": [
            {"user": {"id": 1, "username": "admin", "email": "admin@example.com"}}
        ]
    }


@pytest.fixture
def mock_space():
    """Space de exemplo."""
    return {
        "id": "space1",
        "name": "Consultoria",
        "private": False,
        "statuses": [
            {"status": "Aberto"},
            {"status": "Em andamento"},
            {"status": "Concluído"}
        ]
    }


@pytest.fixture
def mock_folder():
    """Folder de exemplo."""
    return {
        "id": "folder1",
        "name": "Plano Premium",
        "lists": [
            {"id": "list1", "name": "Cliente X"},
            {"id": "list2", "name": "Cliente Y"}
        ]
    }


@pytest.fixture
def mock_custom_field():
    """Custom field de exemplo."""
    return {
        "id": "field1",
        "name": "Valor do Contrato",
        "type": "currency",
        "required": True
    }
