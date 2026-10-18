import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from midflight.communication.invites import Invites
from midflight.communication.store import Store


@pytest.mark.usefixtures("falkor_server")
def test_real_store_concurrent_redemption_and_recovery(falkor_server):
    name = "invite_test_" + uuid.uuid4().hex
    stores = [Store(name, falkor_server.port) for _ in range(2)]
    try:
        registries = [Invites(s, "k" * 32) for s in stores]
        invite = registries[0].create(1, 1, 1)

        def redeem(registry):
            return registry.redeem(invite["id"], invite["secret"], "a" * 32)

        with ThreadPoolExecutor(2) as pool:
            a, b = pool.map(redeem, registries)
        assert a == b
        stores[0].close()
        stores[0] = Store(name, falkor_server.port)
        recovered = Invites(stores[0], "k" * 32)
        assert redeem(recovered) == a
        assert recovered.authenticate(a["tokens"]["billing"])[0]["project"] == a["project"]
        recovered.revoke(invite["id"])
        assert registries[1].authenticate(a["tokens"]["billing"]) is None
    finally:
        stores[1].graph.delete()
        for store in stores:
            store.close()
