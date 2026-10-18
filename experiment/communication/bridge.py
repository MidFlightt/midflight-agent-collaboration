"""Observe this pilot's four-tool bridge without changing service behavior."""

import json
import os
import time
from pathlib import Path

from experiment.communication.context import CompactResponses
from midflight.communication.cloud import RemoteService
from midflight.communication.mcp import build_server


class ObservedRemote(RemoteService):
    def __getattr__(self, operation):
        invoke = super().__getattr__(operation)

        def call(*args, **kwargs):
            started = time.time()
            record = {
                "operation": operation,
                "args": args,
                "kwargs": kwargs,
                "started_at_unix": started,
            }
            try:
                result = invoke(*args, **kwargs)
                record["response"] = result
                return result
            except Exception as error:
                record["error_type"] = type(error).__name__
                raise
            finally:
                record["finished_at_unix"] = time.time()
                with open(os.environ["PIGEONPOST_TRACE"], "a") as output:
                    output.write(json.dumps(record) + "\n")

        call.__name__ = operation
        return call


if __name__ == "__main__":
    remote = ObservedRemote(
        os.environ["MIDFLIGHT_URL"], Path(os.environ["MIDFLIGHT_TOKEN_FILE"]).read_text().strip()
    )
    try:
        server = build_server(remote, remote=True)
        if os.environ.get("PIGEONPOST_RESPONSE_FORMAT") == "compact-v1":
            server.middleware.append(CompactResponses())
        server.run("stdio")
    finally:
        remote.close()
