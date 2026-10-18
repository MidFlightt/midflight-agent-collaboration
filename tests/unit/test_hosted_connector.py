"""The hosted connector: self-serve projects, join codes and agents on different computers.

Driven by an MCP client as different signed-in people against in-memory storage. Real
sign-in over HTTP is in tests/integration/test_hosted_connector_http.py.
"""

import json

import pytest
from mcp import Client

from midflight.communication.hosted import Services, build_hosted_server, hosted_instructions
from midflight.communication.hosted_registry import MemoryAuth, Registry, normalized_code
from midflight.communication.memory_store import MemoryStore
from midflight.communication.service import Service
from midflight.ports import GitHubAccount

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Team:
    """One hosted server, and a switch for who is calling it."""

    def __init__(self):
        self.registry = Registry(MemoryStore(), MemoryAuth())
        self.services = Services(lambda _graph: MemoryStore())
        self.users = {
            login: self.registry.sign_in(GitHubAccount(github_id, login)).id
            for github_id, login in [(101, "somesh"), (202, "frederik"), (303, "stranger")]
        }
        self.caller = "somesh"
        self.server = build_hosted_server(
            self.registry,
            self.services,
            current_user_id=lambda: self.users.get(self.caller),
        )

    async def call(self, client, who, tool, **args):
        self.caller = who
        result = await client.call_tool(tool, args)
        assert not result.is_error, result.content
        return json.loads(result.content[0].text)

    async def refused(self, client, who, tool, **args):
        self.caller = who
        result = await client.call_tool(tool, args)
        assert result.is_error, result.content
        return result.content[0].text


async def test_exact_tool_surface():
    team = Team()
    async with Client(team.server) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
    assert names == {
        "create_project",
        "join_project",
        "my_projects",
        "join",
        "send",
        "check_in",
        "objection",
        "assign_owner",
        "rotate_join_code",
        "remove_member",
    }


async def test_two_people_create_join_and_coordinate():
    team = Team()
    async with Client(team.server) as client:
        created = await team.call(client, "somesh", "create_project", name="Food app")
        assert created["role"] == "lead"
        code = created["join_code"]
        assert code in created["next"]

        # A teammate types the code however they like.
        sloppy = code.lower().replace("-", "")[2:]
        joined = await team.call(client, "frederik", "join_project", join_code=sloppy)
        assert joined["project_id"] == created["project_id"]
        assert joined["members"] == ["frederik", "somesh"]

        assert (await team.call(client, "stranger", "my_projects")) == {"projects": []}
        assert "aren't in a project" in await team.refused(
            client, "stranger", "join", name="spy", task="x", request_id="j"
        )

        deps = ["order-record", "refund-policy"]
        orders = await team.call(
            client,
            "somesh",
            "join",
            name="orders",
            task="Orders",
            request_id="j",
            dependencies=deps,
        )
        assert orders["project"] == "Food app"
        assert "session context returned" in orders["activity"]
        payments = await team.call(
            client,
            "frederik",
            "join",
            name="payments",
            task="Payments",
            request_id="j",
            dependencies=deps,
        )
        # One person, several agents.
        menu = await team.call(
            client,
            "somesh",
            "join",
            name="menu",
            task="Menu",
            request_id="j",
            dependencies=["menu-item"],
        )
        so, sp, sm = orders["session_id"], payments["session_id"], menu["session_id"]

        # Nobody else can speak as an agent another member joined with.
        assert "belongs to somesh" in await team.refused(
            client, "frederik", "join", name="orders", task="x", request_id="steal"
        )
        assert "Unknown session" in await team.refused(
            client, "frederik", "check_in", session_id=so
        )
        assert "another agent or project" in await team.refused(
            client, "somesh", "join", name="menu", task="x", request_id="r", session_id=so
        )

        # First publisher on an unowned topic becomes its owner; subscribers receive it.
        published = await team.call(
            client,
            "somesh",
            "send",
            session_id=so,
            kind="interface",
            topic="order-record",
            body="{id, items[], total_cents}",
            request_id="p1",
            expected_revision=0,
        )
        assert published["claimed_ownership"] is True
        assert published["recipients"] == ["orders", "payments"]

        update = await team.call(client, "frederik", "check_in", session_id=sp)
        [interface] = update["interfaces"]
        assert (interface["topic"], interface["revision"], interface["owner"]) == (
            "order-record",
            1,
            "orders",
        )
        assert (
            "only the interface owner"
            in (
                await team.refused(
                    client,
                    "frederik",
                    "send",
                    session_id=sp,
                    kind="interface",
                    topic="order-record",
                    body="mine",
                    request_id="p2",
                    expected_revision=1,
                )
            ).lower()
        )

        objected = await team.call(
            client,
            "frederik",
            "objection",
            session_id=sp,
            publication_id=published["event_id"],
            revision=1,
            problem="No customer email",
            affects="Receipts are emailed",
            request_id="o1",
        )
        context = await team.call(client, "somesh", "check_in", session_id=so)
        assert [o["id"] for o in context["open_objections"]] == [objected["objection_id"]]

        # A business rule reaches only its subscribers: not the Menu agent.
        policy = await team.call(
            client,
            "somesh",
            "send",
            session_id=so,
            kind="policy",
            topic="refund-policy",
            body="Refunds after 10 minutes keep a $1 fee",
            source="keep a $1 fee after 10 min",
            request_id="pol",
        )
        assert policy["recipients"] == ["orders", "payments"]
        menu_view = await team.call(client, "somesh", "check_in", session_id=sm)
        assert menu_view["messages"] == [] and menu_view["unapplied_policies"] == []
        payments_view = await team.call(client, "frederik", "check_in", session_id=sp)
        assert [p["id"] for p in payments_view["unapplied_policies"]] == [policy["event_id"]]

        [project] = (await team.call(client, "frederik", "my_projects"))["projects"]
        assert project["role"] == "member"
        assert project["agents"] == {"menu": "somesh", "orders": "somesh", "payments": "frederik"}
        assert project["owners"] == {"order-record": "orders"}


async def test_lead_tools_rotate_reassign_and_remove():
    team = Team()
    async with Client(team.server) as client:
        created = await team.call(client, "somesh", "create_project", name="Shop")
        pid, old_code = created["project_id"], created["join_code"]
        await team.call(client, "frederik", "join_project", join_code=old_code)
        so = (
            await team.call(
                client,
                "somesh",
                "join",
                name="orders",
                task="Orders",
                request_id="j",
                dependencies=["order-record"],
            )
        )["session_id"]
        sp = (
            await team.call(
                client,
                "frederik",
                "join",
                name="payments",
                task="Payments",
                request_id="j",
                dependencies=["order-record"],
            )
        )["session_id"]
        await team.call(
            client,
            "somesh",
            "send",
            session_id=so,
            kind="interface",
            topic="order-record",
            body="r1",
            request_id="p1",
            expected_revision=0,
        )

        assert "Only the project's lead" in await team.refused(
            client, "frederik", "rotate_join_code", project_id=pid
        )
        rotated = await team.call(client, "somesh", "rotate_join_code", project_id=pid)
        assert rotated["join_code"] != old_code
        assert "No project has that join code" in await team.refused(
            client, "stranger", "join_project", join_code=old_code
        )

        assert "Only the project's lead" in await team.refused(
            client,
            "frederik",
            "assign_owner",
            project_id=pid,
            topic="order-record",
            agent="payments",
        )
        assigned = await team.call(
            client,
            "somesh",
            "assign_owner",
            project_id=pid,
            topic="order-record",
            agent="payments",
        )
        assert (assigned["owner"], assigned["revision"]) == ("payments", 2)
        notice = await team.call(client, "frederik", "check_in", session_id=sp)
        assert any(
            m["kind"] == "transfer" and m["author"] == "lead:somesh" for m in notice["messages"]
        )
        republished = await team.call(
            client,
            "frederik",
            "send",
            session_id=sp,
            kind="interface",
            topic="order-record",
            body="r2 with email",
            request_id="p2",
            expected_revision=1,
        )
        assert republished["revision"] == 2

        removed = await team.call(
            client, "somesh", "remove_member", project_id=pid, login="Frederik"
        )
        assert removed["released_agents"] == ["payments"]
        assert "aren't a member" in await team.refused(
            client, "frederik", "check_in", session_id=sp
        )

        # Whoever takes over the component can now use the released name.
        await team.call(client, "stranger", "join_project", join_code=rotated["join_code"])
        takeover = await team.call(
            client, "stranger", "join", name="payments", task="Payments", request_id="j2"
        )
        assert takeover["updates"]["agent"] == "payments"
        assert "can't remove themselves" in await team.refused(
            client, "somesh", "remove_member", project_id=pid, login="somesh"
        )


async def test_signed_out_calls_are_refused():
    team = Team()
    team.users = {}
    async with Client(team.server) as client:
        assert "aren't signed in" in await team.refused(client, "nobody", "my_projects")


def test_several_projects_need_an_explicit_project_id():
    team = Team()
    uid = team.users["somesh"]
    a = team.registry.create_project(uid, "A")
    team.registry.create_project(uid, "B")
    with pytest.raises(ValueError, match="several projects"):
        team.registry.project_for(uid)
    assert team.registry.project_for(uid, a["project_id"])["name"] == "A"
    with pytest.raises(ValueError, match="aren't a member"):
        team.registry.project_for(team.users["frederik"], a["project_id"])


def test_registry_survives_restart_and_tracks_renames():
    store = MemoryStore()
    registry = Registry(store, MemoryAuth())
    uid = registry.sign_in(GitHubAccount(101, "somesh")).id
    created = registry.create_project(uid, "Food app")
    again = Registry(store, MemoryAuth())
    assert again.sign_in(GitHubAccount(101, "somesh-renamed")).id == uid
    [view] = again.projects_of(uid)
    assert (view["join_code"], view["lead"]) == (created["join_code"], "somesh-renamed")


def test_join_codes_normalize_and_reject_garbage():
    assert normalized_code(" mf-abcd-efgh ") == "MF-ABCD-EFGH"
    assert normalized_code("abcdefgh") == "MF-ABCD-EFGH"
    for bad in ("", "MF-0000-0000", "hello", "MF-ABCD-EFG"):
        with pytest.raises(ValueError, match="join code"):
            normalized_code(bad)


def test_claiming_unowned_topics_is_opt_in_and_atomic():
    def joined(service):
        sid = service.join("a", "task", "j", dependencies=["t"])["session_id"]
        service.join("b", "task", "j", dependencies=["t"])
        return sid

    roster = Service(MemoryStore())
    sid = joined(roster)
    with pytest.raises(ValueError, match="No assigned owner"):
        roster.send(sid, "interface", "body", "p", topic="t", expected_revision=0)

    hosted = Service(MemoryStore(), claim_unowned=True)
    sid = joined(hosted)
    with pytest.raises(ValueError, match="Stale interface"):
        hosted.send(sid, "interface", "body", "stale", topic="t", expected_revision=3)
    assert hosted.status()["owners"] == {}  # a rejected publication claims nothing
    with pytest.raises(ValueError, match="No assigned owner"):
        hosted.send(sid, "transfer", "x", "tr", topic="t", new_owner="b", expected_revision=1)
    claim = hosted.send(sid, "interface", "body", "p", topic="t", expected_revision=0)
    assert claim["claimed_ownership"] and claim["revision"] == 1
    assert hosted.status()["owners"]["t"] == {"name": "a", "revision": 1}
    # A retry is the same publication, not a second claim.
    again = hosted.send(sid, "interface", "body", "p", topic="t", expected_revision=0)
    assert again["duplicate"] and again["event_id"] == claim["event_id"]
    second = hosted.send(sid, "interface", "body2", "p2", topic="t", expected_revision=1)
    assert "claimed_ownership" not in second


def test_lead_reassignment_requires_a_joined_agent():
    service = Service(MemoryStore(), claim_unowned=True)
    service.join("a", "task", "j", dependencies=["t"])
    with pytest.raises(ValueError, match="No agent named ghost"):
        service.assign_owner("t", "ghost", "lead:somesh")
    first = service.assign_owner("t", "a", "lead:somesh")
    assert (first["owner"], first["revision"]) == ("a", 1)
    assert service.assign_owner("t", "a", "lead:somesh")["revision"] == 1  # no-op


def test_hosted_instructions_replace_roster_and_identity_rules():
    text = hosted_instructions()
    assert "create_project" in text and "join_project" in text
    assert "ask the human to assign ownership" not in text
    assert "trusted local prototype" not in text
    assert "first agent to\npublish kind=interface" in text


def test_memory_routing_follows_topic_prerequisites():
    service = Service(MemoryStore(), claim_unowned=True)
    sid = service.join("checkout", "task", "j", dependencies=["order"])["session_id"]
    service.join("reporting", "task", "j", dependencies=["report"])
    service.join("notifications", "task", "j", dependencies=["email"])
    service.send(sid, "dependency", "report uses order", "d", topic="report", depends_on=["order"])
    sent = service.send(sid, "policy", "price change", "p", topic="order", source="human said so")
    assert sent["recipients"] == ["checkout", "reporting"]
