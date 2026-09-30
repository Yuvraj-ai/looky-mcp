from fastapi.testclient import TestClient

from app.main import app, create_app


def test_health() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_spa_serving() -> None:
    with TestClient(create_app()) as client:
        # Root and frontend client routes should serve the HTML app
        root_resp = client.get("/")
        assert root_resp.status_code == 200
        assert "text/html" in root_resp.headers.get("content-type", "")

        login_resp = client.get("/login")
        assert login_resp.status_code == 200
        assert "text/html" in login_resp.headers.get("content-type", "")

        # Static assets
        favicon_resp = client.get("/favicon.svg")
        assert favicon_resp.status_code == 200

        # MCP non-mcp route without authorization should be handled properly
        mcp_resp = client.post("/mcp")
        assert mcp_resp.status_code == 401
