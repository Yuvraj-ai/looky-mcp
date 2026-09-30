#!/usr/bin/env python3
"""Looky MCP End-to-End Verification Script

Tests live connection to Looky MCP endpoint:
- Auth validation (rejection of unauthenticated / invalid requests)
- MCP initialize handshake and session initialization
- Tool discovery (describe_image, ocr_image)
- Real image description and OCR execution
"""

import base64
import io
import os
import sys

import httpx
from PIL import Image, ImageDraw


def run_verification(url: str, key: str) -> bool:
    print("=" * 60)
    print("   LOOKY MCP LIVE PRODUCTION VERIFICATION SUITE")
    print("=" * 60)
    print(f"Target URL:     {url}")
    print(f"MCP Key Prefix: {key[:8]}...{key[-4:] if len(key) >= 12 else ''}")
    print("-" * 60)

    # 1. Unauthenticated rejection
    r_noauth = httpx.post(
        url,
        json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
        timeout=15.0,
    )
    if r_noauth.status_code != 401:
        print(f"❌ FAIL: Unauthenticated request returned {r_noauth.status_code}, expected 401")
        return False
    print("✓ Test 1: Unauthenticated request rejected with 401 Unauthorized")

    # 2. Invalid bearer rejection
    r_badauth = httpx.post(
        url,
        headers={"Authorization": "Bearer mcp_invalid_token_12345"},
        json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
        timeout=15.0,
    )
    if r_badauth.status_code != 401:
        print(f"❌ FAIL: Invalid bearer key returned {r_badauth.status_code}, expected 401")
        return False
    print("✓ Test 2: Invalid bearer token rejected with 401 Unauthorized")

    # 3. Initialize handshake
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    init_payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 10,
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "looky-verifier", "version": "1.0"},
        },
    }

    with httpx.Client(timeout=45.0) as client:
        r_init = client.post(url, headers=headers, json=init_payload)
        if r_init.status_code != 200:
            print(f"❌ FAIL: Initialize handshake returned {r_init.status_code}: {r_init.text}")
            return False

        session_id = r_init.headers.get("mcp-session-id")
        print(f"✓ Test 3: Initialize handshake successful (Session ID: {session_id})")
        if session_id:
            headers["mcp-session-id"] = session_id

        # Initialized notification
        client.post(
            url,
            headers=headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )

        # 4. Tool Discovery
        r_tools = client.post(
            url,
            headers=headers,
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 20, "params": {}},
        )
        if r_tools.status_code != 200:
            print(f"❌ FAIL: Tool discovery returned {r_tools.status_code}")
            return False

        body = r_tools.text
        if "describe_image" not in body or "ocr_image" not in body:
            print("❌ FAIL: Expected tools describe_image and ocr_image not found in tools/list")
            return False
        print("✓ Test 4: Tool discovery successful (Found: describe_image, ocr_image)")

        # 5. describe_image tool execution
        img_color = Image.new("RGB", (100, 100), color=(0, 150, 255))
        buf = io.BytesIO()
        img_color.save(buf, format="PNG")
        b64_color = base64.b64encode(buf.getvalue()).decode()

        r_desc = client.post(
            url,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": 30,
                "params": {
                    "name": "describe_image",
                    "arguments": {
                        "image": f"data:image/png;base64,{b64_color}",
                        "prompt": "What color is this image and what does it display?",
                    },
                },
            },
        )
        if r_desc.status_code != 200 or "isError\":true" in r_desc.text:
            print(f"❌ FAIL: describe_image call failed: {r_desc.text}")
            return False
        print("✓ Test 5: describe_image executed successfully")

        # 6. ocr_image tool execution
        test_text = "LOOKY MCP LIVE TEST 2026"
        img_text = Image.new("RGB", (320, 60), color=(255, 255, 255))
        draw = ImageDraw.Draw(img_text)
        draw.text((10, 20), test_text, fill=(0, 0, 0))
        buf2 = io.BytesIO()
        img_text.save(buf2, format="PNG")
        b64_ocr = base64.b64encode(buf2.getvalue()).decode()

        r_ocr = client.post(
            url,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": 40,
                "params": {
                    "name": "ocr_image",
                    "arguments": {
                        "image": f"data:image/png;base64,{b64_ocr}",
                        "prompt": "Extract the exact text visible.",
                    },
                },
            },
        )
        if r_ocr.status_code != 200 or "isError\":true" in r_ocr.text:
            print(f"❌ FAIL: ocr_image call failed: {r_ocr.text}")
            return False
        print("✓ Test 6: ocr_image executed successfully")

    print("-" * 60)
    print("🎉 ALL TESTS PASSED! Looky MCP is completely operational and ready for use.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://looky-mcp.onrender.com/mcp"
    mcp_key = (
        sys.argv[2]
        if len(sys.argv) > 2
        else os.getenv("VISION_MCP_KEY", "mcp_vcJoI4GsbKcwsDVjnC30otRBJrWpsxmihJhWjDm9yem")
    )
    success = run_verification(target_url, mcp_key)
    sys.exit(0 if success else 1)
