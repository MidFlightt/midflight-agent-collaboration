"""In-memory stand-in for `Store`: same CAS and routing contract, nothing persisted.

For tests and local runs of the hosted connector. Routing matches the FalkorDB graph:
an agent subscribed to topic T receives a change to topic C when T == C or T depends on
C through declared topic prerequisites (up to 32 edges).
"""

import copy
import threading


class MemoryStore:
    def __init__(self):
        self.revision = 0
        self.state = dict(agents={}, sessions={}, events=[], requests={}, dependencies={})
        self.lock = threading.Lock()

    def read(self):
        with self.lock:
            return self.revision, copy.deepcopy(self.state)

    def commit(self, revision, state):
        with self.lock:
            if revision != self.revision:
                return False
            self.state = copy.deepcopy(state)
            self.revision += 1
            return True

    def recipients(self, revision, topics):
        with self.lock:
            agents = copy.deepcopy(self.state["agents"])
            prerequisites = copy.deepcopy(self.state["dependencies"])
        changed = set(topics)

        def reaches(topic):
            seen, frontier = set(), [(topic, 0)]
            while frontier:
                node, depth = frontier.pop()
                if node in changed:
                    return True
                if node in seen or depth >= 32:
                    continue
                seen.add(node)
                frontier.extend((p, depth + 1) for p in prerequisites.get(node, []))
            return False

        return sorted(
            name
            for name, agent in agents.items()
            if any(reaches(t) for t in agent.get("dependencies", []))
        )

    def close(self):
        pass
