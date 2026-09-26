"""MCP credential routes (Decision #7, Architecture §11):
status / generate (plaintext returned ONCE) / revoke."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_user_id
from app.config import settings
from app.crypto import generate_mcp_key, hash_mcp_key
from app.db.session import get_db
from app.repositories.mcp_credentials import McpCredentialRepository

router = APIRouter(prefix="/api/mcp-credential", tags=["mcp-credential"])


class McpCredentialStatus(BaseModel):
    configured: bool
    created_at: str | None = None


class McpCredentialGenerated(BaseModel):
    key: str  # plaintext — shown exactly once (Decision #7)


def _repo(db: AsyncSession = Depends(get_db)) -> McpCredentialRepository:
    return McpCredentialRepository(db)


@router.get("", response_model=McpCredentialStatus)
async def status(
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: McpCredentialRepository = Depends(_repo),
) -> McpCredentialStatus:
    cred = await repo.get_for_user(user_id)
    if cred is None:
        return McpCredentialStatus(configured=False)
    return McpCredentialStatus(configured=True, created_at=cred.created_at.isoformat())


@router.post("/generate", response_model=McpCredentialGenerated)
async def generate(
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: McpCredentialRepository = Depends(_repo),
) -> McpCredentialGenerated:
    raw_key = generate_mcp_key()
    await repo.upsert(user_id, hash_mcp_key(raw_key))
    return McpCredentialGenerated(key=raw_key)


@router.post("/revoke", status_code=204)
async def revoke(
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: McpCredentialRepository = Depends(_repo),
) -> None:
    cred = await repo.get_for_user(user_id)
    if cred is not None:
        await repo.revoke(cred)


class OpenCodeSnippet(BaseModel):
    snippet: str


class ConfigSnippets(BaseModel):
    opencode: str
    claude_code_cli: str
    claude_code_json: str
    codex_toml: str


@router.get("/opencode-snippet", response_model=OpenCodeSnippet)
async def opencode_snippet(
    _: uuid.UUID = Depends(get_current_user_id),
) -> OpenCodeSnippet:
    """Ready-to-copy OpenCode config; key is intentionally omitted and referenced
    via {env:VISION_MCP_KEY} instead (Decision #7)."""
    snippet = (
        "{\n"
        '  "mcp": {\n'
        '    "vision": {\n'
        '      "type": "remote",\n'
        f'      "url": "{settings.PUBLIC_BASE_URL}/mcp",\n'
        '      "oauth": false,\n'
        '      "headers": {\n'
        '        "Authorization": "Bearer {env:VISION_MCP_KEY}"\n'
        "      }\n"
        "    }\n"
        "  }\n"
        "}"
    )
    return OpenCodeSnippet(snippet=snippet)


@router.get("/config-snippets", response_model=ConfigSnippets)
async def config_snippets(
    _: uuid.UUID = Depends(get_current_user_id),
) -> ConfigSnippets:
    """Ready-to-copy configuration snippets for OpenCode, Claude Code, and Codex."""
    url = f"{settings.PUBLIC_BASE_URL}/mcp"
    opencode = (
        "{\n"
        '  "mcp": {\n'
        '    "vision": {\n'
        '      "type": "remote",\n'
        f'      "url": "{url}",\n'
        '      "oauth": false,\n'
        '      "headers": {\n'
        '        "Authorization": "Bearer {env:VISION_MCP_KEY}"\n'
        "      }\n"
        "    }\n"
        "  }\n"
        "}"
    )
    claude_cli = (
        f'claude mcp add --transport http vision "{url}" '
        '--header "Authorization: Bearer $VISION_MCP_KEY"'
    )
    claude_json = (
        "{\n"
        '  "mcpServers": {\n'
        '    "vision": {\n'
        '      "type": "http",\n'
        f'      "url": "{url}",\n'
        '      "headers": {\n'
        '        "Authorization": "Bearer ${VISION_MCP_KEY}"\n'
        "      }\n"
        "    }\n"
        "  }\n"
        "}"
    )
    codex_toml = (
        "[mcp_servers.vision]\n"
        f'url = "{url}"\n'
        'http_headers = { "Authorization" = "Bearer ${VISION_MCP_KEY}" }\n'
    )
    return ConfigSnippets(
        opencode=opencode,
        claude_code_cli=claude_cli,
        claude_code_json=claude_json,
        codex_toml=codex_toml,
    )
