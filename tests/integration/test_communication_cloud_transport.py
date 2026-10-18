"""Two real stdio MCP processes over TLS to a restartable shared server."""

import asyncio
import hashlib
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import time
import uuid
from contextlib import AsyncExitStack, asynccontextmanager

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from midflight.communication.store import Store


def test_independent_mcp_clients_over_https_and_server_restart(falkor_server, tmp_path):
    if not shutil.which("openssl"):
        pytest.skip("TLS fixture requires openssl")
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=IP:127.0.0.1,DNS:localhost",
        ],
        check=True,
        capture_output=True,
    )
    project = "transport_" + uuid.uuid4().hex
    config = {
        "projects": {project: {"agents": {"billing": ["fee"], "delivery": ["fee"]}}},
        "credentials": {
            hashlib.sha256(t.encode()).hexdigest(): {"project": project, "agent": a}
            for t, a in [("test-billing", "billing"), ("test-delivery", "delivery")]
        },
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"https://127.0.0.1:{port}"
    env = os.environ | {
        "MIDFLIGHT_CONFIG": str(config_file),
        "MIDFLIGHT_DB_PORT": str(falkor_server.port),
        "MIDFLIGHT_DB_HOST": "127.0.0.1",
    }
    processes = []

    def start():
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "midflight.communication.cloud:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--ssl-certfile",
                str(cert),
                "--ssl-keyfile",
                str(key),
                "--no-access-log",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(process)
        with httpx.Client(
            verify=ssl.create_default_context(cafile=cert), timeout=1, trust_env=False
        ) as client:
            for _ in range(100):
                assert process.poll() is None, "HTTPS backend exited during startup"
                try:
                    if client.get(url + "/healthz").status_code == 200:
                        return process
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
        raise AssertionError("HTTPS backend did not become healthy")

    @asynccontextmanager
    async def connect(token):
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "midflight.communication.mcp"],
            env={"MIDFLIGHT_URL": url, "MIDFLIGHT_TOKEN": token, "SSL_CERT_FILE": str(cert)},
        )
        async with stdio_client(parameters) as (read, write), ClientSession(read, write) as client:
            await client.initialize()
            yield client

    async def call(client, tool, **args):
        response = await client.call_tool(tool, args)
        assert not response.is_error, response.content
        return json.loads(response.content[0].text)

    async def scenario():
        process = start()
        async with AsyncExitStack() as stack:
            a = await stack.enter_async_context(connect("test-billing"))
            b = await stack.enter_async_context(connect("test-delivery"))
            assert {t.name for t in (await a.list_tools()).tools} == {
                "join",
                "send",
                "check_in",
                "objection",
            }
            ja, jb = await asyncio.gather(
                call(a, "join", name="billing", task="Billing", request_id="j"),
                call(b, "join", name="delivery", task="Delivery", request_id="j"),
            )
            args = dict(
                session_id=jb["session_id"],
                kind="policy",
                topic="fee",
                body="Keep four",
                source="Keep four",
                request_id="fee",
                expected_revision=0,
            )
            sent = await call(b, "send", **args)
            process.kill()  # Simulate abrupt server loss; durable writes must survive.
            process.wait(timeout=10)
            start()
            replay = await call(b, "send", **args)
            assert replay["duplicate"] and replay["event_id"] == sent["event_id"]
            received = await call(a, "check_in", session_id=ja["session_id"])
            assert received["unapplied_policies"][0]["id"] == sent["event_id"]
            assert list(received)[-1] == "activity"
            assert (await call(a, "check_in", session_id=ja["session_id"]))["messages"] == []

    try:
        asyncio.run(scenario())
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
        store = Store("shared_" + project, falkor_server.port)
        store.graph.delete()
        store.close()
