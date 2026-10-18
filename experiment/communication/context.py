"""Lossless, response-local text sharing; never caches delivery or coordination state."""

import copy
import json
from collections import Counter

from mcp.types import CallToolResult, TextContent

FORMAT = "midflight-text-table-v1"
GUIDE = (
    'Self-contained response. Each {"$text":"tN"} means the exact string in '
    "text_by_id[tN] in THIS response. Expand references when reading body/source fields. "
    "All IDs, revisions, statuses and list memberships are unchanged. "
    "No reference depends on an earlier response; delivery does not mean read or applied."
)


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def encode(response):
    counts = Counter()

    def count(value):
        if isinstance(value, str) and len(value) >= 120:
            counts[value] += 1
        elif isinstance(value, dict):
            for item in value.values():
                count(item)
        elif isinstance(value, list):
            for item in value:
                count(item)

    count(response)
    texts = {f"t{n}": value for n, (value, count) in enumerate(counts.items()) if count > 1}
    identifiers = {value: key for key, value in texts.items()}

    def pack(value):
        if isinstance(value, str) and value in identifiers:
            return {"$text": identifiers[value]}
        if isinstance(value, dict):
            # Escape literal marker-shaped objects, including arbitrary peer data.
            if set(value) in ({"$text"}, {"$literal"}):
                return {"$literal": [[key, pack(item)] for key, item in value.items()]}
            return {key: pack(item) for key, item in value.items()}
        if isinstance(value, list):
            return [pack(item) for item in value]
        return value

    envelope = {"encoding": FORMAT, "guide": GUIDE, "text_by_id": texts, "response": pack(response)}
    # Plain compact JSON is preferable when the table itself would cost more bytes.
    if texts and len(dumps(envelope).encode()) < len(dumps(response).encode()):
        assert decode(envelope) == response
        return envelope
    return copy.deepcopy(response)


def decode(value):
    if not isinstance(value, dict) or value.get("encoding") != FORMAT:
        return copy.deepcopy(value)
    texts = value["text_by_id"]

    def expand(item):
        if isinstance(item, dict):
            if set(item) == {"$text"}:
                return texts[item["$text"]]
            if set(item) == {"$literal"}:
                return {key: expand(val) for key, val in item["$literal"]}
            return {key: expand(val) for key, val in item.items()}
        if isinstance(item, list):
            return [expand(val) for val in item]
        return item

    return expand(value["response"])


class CompactResponses:
    """MCP presentation middleware; inputs, errors and backend responses stay unchanged."""

    async def __call__(self, ctx, call_next):
        result = await call_next(ctx)
        wire_result = result if isinstance(result, dict) else None
        if ctx.method == "tools/call" and wire_result is not None:
            try:
                result = CallToolResult.model_validate(wire_result)
            except ValueError:
                return wire_result
        if ctx.method != "tools/call" or not isinstance(result, CallToolResult) or result.is_error:
            return result
        if len(result.content) != 1 or not isinstance(result.content[0], TextContent):
            return result
        try:
            original = json.loads(result.content[0].text)
        except ValueError:
            return result
        if not isinstance(original, dict):
            return result
        # Fail closed if text/structured outputs differ; never discard unique evidence.
        if result.structured_content is not None and result.structured_content != original:
            return result
        packed = encode(original)
        content = result.content[0].model_copy(update={"text": dumps(packed)})
        if wire_result is not None:
            output = copy.deepcopy(wire_result)
            output["content"][0]["text"] = content.text
            if output.get("structuredContent") is not None:
                output["structuredContent"] = packed
            return output
        return result.model_copy(
            update={
                "content": [content],
                "structured_content": packed if result.structured_content is not None else None,
            }
        )
