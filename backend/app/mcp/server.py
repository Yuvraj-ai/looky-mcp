"""MCP server: MCPServer instance + describe_image / ocr_image tool registration.

Tools are thin (Architecture §12/§16): parse args → VisionService.run → string.
Auth user identity comes from the McpAuthMiddleware contextvar (never an argument).

create_mcp_server() builds a fresh instance because the SDK's session manager is
single-use (one run() per instance) — apps built twice (tests) need their own.
"""

import uuid

from mcp.server import MCPServer
from mcp.types import ImageContent

from app.auth.mcp_auth import current_mcp_user_id


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
        from app.services.vision_service import VisionService

        user_id = _require_user()
        service = VisionService()
        return await service.run(user_id=user_id, mode="describe", image=image, prompt=prompt)

    @mcp.tool()
    async def ocr_image(image: ImageContent, prompt: str) -> str:
        """Extract text from an image via OCR. Use when you need the literal
        text content of an image (error messages, code, documents)."""
        from app.services.vision_service import VisionService

        user_id = _require_user()
        service = VisionService()
        return await service.run(user_id=user_id, mode="ocr", image=image, prompt=prompt)

    return mcp
