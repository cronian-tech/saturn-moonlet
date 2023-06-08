import json
import signal

import requests
from prometheus_client import (
    GC_COLLECTOR,
    PLATFORM_COLLECTOR,
    PROCESS_COLLECTOR,
    REGISTRY,
    start_http_server,
)
from prometheus_client.core import InfoMetricFamily


def _bool_to_str(v):
    return str(v).lower()


class StatsCollector(object):
    def __init__(self, node_ids):
        """Collects stats for the specified node IDs.

        If node_ids is empty then collets stats for all nodes.
        """
        self._node_ids = frozenset(node_ids)

    def _node_info_from_stats(self, stats):
        m = InfoMetricFamily("saturn_node", "")

        for node in stats:
            if self._node_ids and node["id"] not in self._node_ids:
                continue

            m.add_metric(
                [],
                {
                    "id": node["id"],
                    "core": _bool_to_str(node["core"]),
                    "ip_address": node["ipAddress"],
                    "sunrise": _bool_to_str(node["sunrise"]),
                    "cassini": _bool_to_str(node["cassini"]),
                    "version": _bool_to_str(node["version"]),
                    "geoloc_region": node["geoloc"]["region"],
                    "geoloc_city": node["geoloc"]["city"],
                    "geoloc_country": node["geoloc"]["country"],
                    "geoloc_country_code": node["geoloc"]["countryCode"],
                },
            )

        return m

    def collect(self):
        # Do not query orchestrator if "stats.json" is present.
        # Useful for development and testing.
        try:
            with open("stats.json") as f:
                stats = json.loads(f.read())
        except FileNotFoundError:
            r = requests.get(
                "https://orchestrator.strn.pl/stats",
                headers={"Accept": "application/json"},
            )
            stats = r.json()

        yield self._node_info_from_stats(stats["nodes"])


if __name__ == "__main__":
    # Disable default collector metrics.
    REGISTRY.unregister(GC_COLLECTOR)
    REGISTRY.unregister(PLATFORM_COLLECTOR)
    REGISTRY.unregister(PROCESS_COLLECTOR)

    # Try reading node IDs from "nodes.txt".
    try:
        with open("nodes.txt") as f:
            node_ids = [l.strip() for l in f]
    except FileNotFoundError:
        node_ids = []

    REGISTRY.register(StatsCollector(node_ids))

    start_http_server(9000)

    signal.pause()
