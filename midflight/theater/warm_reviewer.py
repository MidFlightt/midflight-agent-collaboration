"""Persistent Codex app-server pool, with a fresh ephemeral context per inference.

The CLI owns sign-in. No credentials are extracted or copied. Each pool member
handles one call at a time; timeout discards that process, never another review.
"""

import json
import logging
import os
import queue
import shutil
import signal
import subprocess
import tempfile
import time
from contextlib import suppress
from threading import Thread

from midflight.ports import ReviewerUnavailable
from midflight.theater.hosted_reviewer import HostedReviewer, strict_schema

log = logging.getLogger(__name__)


def isolated_config():
    # CLI overrides replace these tables; do not inherit user connectors/tools.
    values = [
        "mcp_servers={}",
        "plugins={}",
        "features.shell_tool=false",
        'web_search="disabled"',
        "features.apps=false",
        "features.multi_agent=false",
        'developer_instructions=""',
    ]
    return [arg for value in values for arg in ["-c", value]]


class AppServer:
    def __init__(self):
        self.proc = None
        self.root = None
        self.messages = queue.Queue()
        self.sequence = 0

    def start(self, deadline):
        if self.proc is not None and self.proc.poll() is None:
            return
        self.close()
        executable = shutil.which("codex")
        if not executable:
            raise ReviewerUnavailable("Codex is not installed.")
        self.root = tempfile.TemporaryDirectory(prefix="midflight-warm-review-")
        self.messages = queue.Queue()
        self.proc = subprocess.Popen(
            [executable, "app-server", "--listen", "stdio://", *isolated_config()],
            cwd=self.root.name,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        Thread(target=self._read, args=(self.proc, self.messages), daemon=True).start()
        self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "midflight_reviewer",
                    "title": "MidFlight reviewer",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
            deadline,
        )
        self.send({"method": "initialized", "params": {}})

    @staticmethod
    def _read(proc, messages):
        try:
            for line in proc.stdout:
                messages.put(json.loads(line))
        except (OSError, ValueError):
            pass
        finally:
            messages.put(None)

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def receive(self, deadline):
        try:
            message = self.messages.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty as error:
            raise ReviewerUnavailable("Warm reviewer timed out.") from error
        if message is None:
            raise ReviewerUnavailable("Warm reviewer disconnected.")
        if "method" in message and "id" in message:
            # No permission requests, tools or user questions are appropriate here.
            self.send(
                {
                    "id": message["id"],
                    "error": {
                        "code": -32601,
                        "message": "Tools and approval requests are disabled for reviews.",
                    },
                }
            )
            raise ReviewerUnavailable("Reviewer requested an unsupported tool.")
        return message

    def request(self, method, params, deadline):
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        deferred = []
        while True:
            message = self.receive(deadline)
            if message.get("id") == request_id:
                for event in deferred:
                    self.messages.put(event)
                if "error" in message:
                    raise ReviewerUnavailable(f"Warm reviewer rejected {method}.")
                return message["result"]
            deferred.append(message)

    def infer(self, prompt, schema, deadline):
        self.start(deadline)
        thread = self.request(
            "thread/start",
            {
                "cwd": self.root.name,
                "ephemeral": True,
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "baseInstructions": "You are a bounded coordination reviewer. Use supplied data only. "
                "Never run tools or read files. Return the requested JSON.",
            },
            deadline,
        )["thread"]["id"]
        self.request(
            "turn/start",
            {
                "threadId": thread,
                "input": [{"type": "text", "text": prompt}],
                "effort": "low",
                "outputSchema": strict_schema(schema),
            },
            deadline,
        )
        answer = None
        while True:
            message = self.receive(deadline)
            params = message.get("params", {})
            if params.get("threadId") != thread:
                continue
            if message.get("method") == "item/completed":
                item = params.get("item", {})
                if item.get("type") == "agentMessage":
                    answer = item.get("text")
            if message.get("method") == "turn/completed":
                if params["turn"]["status"] != "completed" or answer is None:
                    raise ReviewerUnavailable("Warm reviewer turn did not complete.")
                result = json.loads(answer)
                if not isinstance(result, dict):
                    raise ReviewerUnavailable("Warm reviewer returned a non-object.")
                self.request("thread/unsubscribe", {"threadId": thread}, deadline)
                return result

    def close(self):
        if self.proc is not None:
            if self.proc.poll() is None:
                with suppress(ProcessLookupError):
                    os.killpg(self.proc.pid, signal.SIGKILL)
            self.proc.wait(timeout=5)
            for stream in [self.proc.stdin, self.proc.stdout]:
                stream.close()
            self.proc = None
        if self.root is not None:
            self.root.cleanup()
            self.root = None


class WarmReviewer(HostedReviewer):
    def __init__(self, *, size=2, **kwargs):
        super().__init__(**kwargs)
        if size < 1:
            raise ValueError("Reviewer pool cannot be empty")
        self.pool = queue.Queue()
        self.servers = [AppServer() for _ in range(size)]
        for server in self.servers:
            self.pool.put(server)

    def warm(self):
        # Initialization only: no dummy inference and no background polling.
        for server in self.servers:
            try:
                server.start(time.monotonic() + 10)
            except Exception as error:
                server.close()
                log.warning("review_warmup outcome=%s", type(error).__name__)

    def close(self):
        for server in self.servers:
            server.close()

    def _infer(self, system, task, data, tool, schema):
        deadline = min(self._deadline or float("inf"), time.monotonic() + self.call_timeout)
        try:
            server = self.pool.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty as error:
            raise ReviewerUnavailable("Reviewer pool was busy.") from error
        try:
            prompt = (
                system
                + "\n"
                + task
                + "\nReturn JSON matching the output schema.\n<data>\n"
                + json.dumps(data)
                + "\n</data>"
            )
            return server.infer(prompt, schema, deadline)
        except (OSError, ValueError, ReviewerUnavailable) as error:
            server.close()
            raise ReviewerUnavailable(f"Warm reviewer: {type(error).__name__}") from error
        finally:
            self.pool.put(server)
