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
from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily


def _bool_to_str(v):
    return str(v).lower()


class StatsCollector(object):
    def __init__(self, node_ids):
        """Collects stats for the specified node IDs.

        If node_ids is empty then collets stats for all nodes.
        """
        self._node_ids = frozenset(node_ids)

    def _node_metrics_from_stats(self, stats):
        info = InfoMetricFamily("saturn_node", "")
        bias = GaugeMetricFamily("saturn_node_bias", "", labels=["id"])

        found = set()

        for node in stats:
            if self._node_ids and node["id"] not in self._node_ids:
                continue

            found.add(node["id"])

            info.add_metric(
                [],
                {
                    "id": node["id"],
                    "state": node["state"],
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
            bias.add_metric([node["id"]], node["bias"])

        # Every not found node considered inactive.
        for i in self._node_ids - found:
            info.add_metric(
                [],
                {
                    "id": i,
                    "state": "inactive",
                },
            )

        return (info, bias)

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

        for m in self._node_metrics_from_stats(stats["nodes"]):
            yield m


if __name__ == "__main__":
    # Disable default collector metrics.
    REGISTRY.unregister(GC_COLLECTOR)
    REGISTRY.unregister(PLATFORM_COLLECTOR)
    REGISTRY.unregister(PROCESS_COLLECTOR)

    # Try reading node IDs from "conf/nodes.txt".
    try:
        with open("conf/nodes.txt") as f:
            node_ids = [l.strip() for l in f]
    except FileNotFoundError:
        node_ids = []

    REGISTRY.register(StatsCollector(node_ids))

    start_http_server(9000)

    signal.pause()
