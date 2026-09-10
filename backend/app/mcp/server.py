"""MCP server: MCPServer instance + describe_image / ocr_image tool registration.

Tools are thin (Architecture §12/§16): parse args → VisionService.run → string.
Auth user identity comes from the McpAuthMiddleware contextvar (never an argument).
Stable errors (Decision #5/#10) surface as MCP tool errors with the exact message.
create_mcp_server() builds a fresh instance because the SDK's session manager is
single-use (one run() per instance) — apps built twice (tests) need their own.
"""

import uuid

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ImageContent

from app.auth.mcp_auth import current_mcp_user_id

# set by create_app: the session-factory provider shared by middleware and tools.
# Plain module global (not a contextvar): the MCP app runs in the server thread,
# which starts with a fresh context — contextvars set in the main thread don't
# propagate, but module state does.
_session_factory_fn_global: list = []  # single-slot holder


def set_session_factory_fn(fn) -> None:
    _session_factory_fn_global.clear()
    _session_factory_fn_global.append(fn)


def _session_factory_fn():
    if _session_factory_fn_global:
        return _session_factory_fn_global[0]
    from app.services.vision_service import _CachedSessionFactory

    return _CachedSessionFactory()


def _require_user() -> uuid.UUID:
    user_id = current_mcp_user_id.get()
    if user_id is None:
        raise RuntimeError("MCP request is not authenticated")
    return user_id


def create_mcp_server() -> MCPServer:
    mcp = MCPServer("vision")

    @mcp.tool()
    async def describe_image(image: ImageContent, prompt: str) -> str:
        """Analyze/describe the contents of an image. Use for general visual
        understanding, screenshots, diagrams, UI review, etc."""
        return await _run_tool("describe", image, prompt)

    @mcp.tool()
    async def ocr_image(image: ImageContent, prompt: str) -> str:
        """Extract text from an image via OCR. Use when you need the literal
        text content of an image (error messages, code, documents)."""
        return await _run_tool("ocr", image, prompt)

    return mcp


async def _run_tool(mode: str, image: ImageContent, prompt: str) -> str:
    from app.services.image_validator import ImageValidationError
    from app.services.vision_service import VisionService, VisionServiceError

    user_id = _require_user()
    try:
        service = VisionService(session_factory_fn=_session_factory_fn())
        return await service.run(user_id=user_id, mode=mode, image=image, prompt=prompt)
    except (VisionServiceError, ImageValidationError) as exc:
        # stable application-level message → MCP tool error (never internals)
        raise ToolError(str(exc)) from exc
