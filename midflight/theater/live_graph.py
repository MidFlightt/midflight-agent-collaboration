"""Read a semantic collaboration view from the current FalkorDB run.

Claims remain the source of truth: a file edge means declared ownership, not that
we observed a filesystem write. No edges are inferred from fixture task names.
"""


def snapshot(live):
    store = live.theater.server.services.store
    project = live.theater.project
    arrivals = store.graph.query(
        "MATCH (a:MFPeerPresence {project:$project}) RETURN a.id, a.connected_at",
        {"project": project},
    ).result_set
    nodes, edges = {}, {}

    def node(key, kind, label, **details):
        nodes[key] = {**nodes.get(key, {}), "id": key, "kind": kind, "label": label, **details}

    def edge(source, target, kind, **details):
        key = f"{source}|{kind}|{target}"
        edges[key] = {"id": key, "source": source, "target": target, "kind": kind, **details}

    for name, connected in arrivals:
        node(f"agent:{name}", "agent", name, connected_at=connected)
    latest = {}
    for claim in store.list_claims(project):
        old = latest.get(claim.id)
        if old is None or claim.revision > old.revision:
            latest[claim.id] = claim
    for claim in latest.values():
        agent = f"agent:{claim.agent_id}"
        node(agent, "agent", claim.agent_id)
        key = f"claim:{claim.id}"
        node(
            key,
            "claim",
            f"{claim.id} · r{claim.revision}",
            state=claim.state.value,
            task=claim.task_id,
            plan_version=claim.plan_version,
            acceptance_criteria=claim.acceptance_criteria,
        )
        edge(agent, key, "claims")
        for path in claim.files:
            file_key = f"file:{claim.task_id}:{path}"
            node(file_key, "file", path, meaning="File declared in this claim", task=claim.task_id)
            edge(key, file_key, "declares")
        for kind, uses in (("provides", claim.provides), ("consumes", claim.consumes)):
            for use in uses:
                contract = f"interface:{use.contract_id}"
                node(contract, "interface", use.contract_id)
                edge(key, contract, kind, fields={k: v.value for k, v in use.fields.items()})
    for directive in store.list_directives(project):
        key = f"directive:{directive.id}"
        node(key, "directive", directive.id, **directive.model_dump(mode="json", exclude={"id"}))
        edge(key, f"agent:{directive.task_id}", "notifies")
    return {
        "project": project,
        "plan_version": live.version,
        "started": bool(live.panes),
        "source": "FalkorDB · persisted session arrivals and claims",
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
    }
