"""FalkorDB atomic CAS state and graph routing projection.

One project per graph. Each mutation commits state, durable receipts and dependency
edges in one query. A failed CAS retries from a fresh snapshot. No leased lock can
expire under a writer. JSON state is intentionally bounded to small demo projects.
"""

import json

from falkordb import FalkorDB
from redis.backoff import NoBackoff
from redis.exceptions import ResponseError
from redis.retry import Retry


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Store:
    def __init__(self, graph_name, port=6379):
        self.client = FalkorDB(
            host="127.0.0.1",
            port=port,
            socket_timeout=15,
            socket_connect_timeout=5,
            retry=Retry(NoBackoff(), 0),
        )
        self.graph = self.client.select_graph(graph_name)
        for label in ("CState", "CAgent", "CTopic"):
            try:
                self.graph.query(f"CREATE INDEX ON :{label}(name)")
            except ResponseError as exc:
                if "already indexed" not in str(exc):
                    raise
        self.graph.query(
            "MERGE (s:CState {name:'state'}) ON CREATE SET s.revision=0, s.payload=$state",
            {
                "state": encoded(
                    {
                        "agents": {},
                        "sessions": {},
                        "events": [],
                        "requests": {},
                        "dependencies": {},
                    }
                )
            },
        )

    def read(self):
        row = self.graph.query(
            "MATCH (s:CState {name:'state'}) RETURN s.revision,s.payload"
        ).result_set[0]
        return row[0], json.loads(row[1])

    def recipients(self, revision, topics):
        # An agent subscribes to a topic; topic edges point toward prerequisites.
        rows = self.graph.query(
            "MATCH (a:CAgent)-[r:DEPENDS_ON]->(t:CTopic) "
            "WHERE r.revision=$revision "
            "OPTIONAL MATCH p=(t)-[:DEPENDS_ON*0..32]->(changed:CTopic) "
            "WHERE changed.name IN $topics "
            "RETURN a.name, changed.name",
            {"revision": revision, "topics": topics},
        ).result_set
        return sorted({name for name, topic in rows if topic is not None})

    def commit(self, revision, state):
        agents = [
            {"name": name, "topics": agent["dependencies"]}
            for name, agent in state["agents"].items()
        ]
        dependencies = [
            {"name": name, "topics": topics} for name, topics in state["dependencies"].items()
        ]
        rows = self.graph.query(
            "MATCH (s:CState {name:'state'}) WHERE s.revision=$revision "
            "SET s.revision=s.revision+1,s.payload=$payload "
            "WITH s OPTIONAL MATCH ()-[old:DEPENDS_ON]->() "
            "DELETE old WITH DISTINCT s "
            "FOREACH (agent IN $agents | MERGE (a:CAgent {name:agent.name}) "
            "FOREACH (topic IN agent.topics | MERGE (t:CTopic {name:topic}) "
            "CREATE (a)-[:DEPENDS_ON {revision:s.revision}]->(t))) "
            "FOREACH (dep IN $dependencies | MERGE (t:CTopic {name:dep.name}) "
            "FOREACH (topic IN dep.topics | MERGE (p:CTopic {name:topic}) "
            "CREATE (t)-[:DEPENDS_ON {revision:s.revision}]->(p))) "
            "RETURN s.revision",
            {
                "revision": revision,
                "payload": encoded(state),
                "agents": agents,
                "dependencies": dependencies,
            },
        ).result_set
        return bool(rows)

    def close(self):
        self.client.connection.close()
