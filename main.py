import json
import os
import signal
from collections import defaultdict
from datetime import datetime

import requests
from prometheus_client import (
    GC_COLLECTOR,
    PLATFORM_COLLECTOR,
    PROCESS_COLLECTOR,
    REGISTRY,
    start_http_server,
)
from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    InfoMetricFamily,
)


def _bool_to_str(v):
    return str(v).lower()


def _str_to_timestamp(v):
    ts = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
    # Grafana expects Unix timestamps in milliseconds, not seconds.
    return ts * 1000


class NodeInfoMetric(InfoMetricFamily):
    def __init__(self):
        super().__init__("saturn_node", "")

    @staticmethod
    def _id_short(v):
        return v[:8]

    def add(self, node):
        values = {
            "id": node["id"],
            "id_short": self._id_short(node["id"]),
            "state": node["state"],
            "core": _bool_to_str(node["core"]),
            "ip_address": node["ipAddress"],
            "sunrise": _bool_to_str(node["sunrise"]),
            "cassini": _bool_to_str(node["cassini"]),
            "geoloc_region": node["geoloc"]["region"],
            "geoloc_city": node["geoloc"]["city"],
            "geoloc_country": node["geoloc"]["country"],
            "geoloc_country_code": node["geoloc"]["countryCode"],
        }

        speedtest = node.get("speedtest")
        if speedtest:
            values.update(
                {
                    "sppedtest_isp": node["speedtest"]["isp"],
                    "sppedtest_server_location": node["speedtest"]["server"][
                        "location"
                    ],
                    "sppedtest_server_country": node["speedtest"]["server"]["country"],
                }
            )

        if node["earnings"]:
            values["payout_status"] = node["earnings"]["payoutStatus"]

        self.add_metric([], values)

    def add_inactive(self, node_id):
        self.add_metric(
            [],
            {
                "id": node_id,
                "id_short": self._id_short(node_id),
                "state": "inactive",
            },
        )


class NodeVersionMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_version", "", labels=["id"])

    def add(self, node):
        version = node["version"].split("_")[0]
        self.add_metric([node["id"]], version)


class NodeWeightMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_weight", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["bias"])


class NodeBiasMetric(GaugeMetricFamily):
    _BIASES = {
        "ageBias": "age",
        "ttfbBias": "ttfb",
        "randomBias": "random",
        "uptimeBias": "uptime",
        "speedtestBias": "speedtest",
    }

    def __init__(self):
        super().__init__("saturn_node_bias", "", labels=["id", "kind"])

    def add(self, node):
        for k, v in self._BIASES.items():
            bias = node["biases"].get(k)
            if bias is not None:
                self.add_metric([node["id"], v], bias)


class NodePenaltyMetric(GaugeMetricFamily):
    _PENALTIES = {
        "speedPenalty": "speed",
        "cpuLoadPenalty": "cpu_load",
        "errorRatePenalty": "error_rate",
        "oldVersionPenalty": "old_version",
        "cacheHitRatePenalty": "cache_hit_rate",
        "healthCheckFailuresPenalty": "health_check_failures",
    }

    def __init__(self):
        super().__init__("saturn_node_penalty", "", labels=["id", "kind"])

    def add(self, node):
        for k, v in self._PENALTIES.items():
            penalty = node["biases"].get(k)
            if penalty is not None:
                self.add_metric([node["id"], v], penalty)


class NodeWeightedTTFBMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_weighted_ttfb_milliseconds", "", labels=["id"])

    def add(self, node):
        v = node["biases"].get("weightedTtfb")
        if v is not None:
            self.add_metric([node["id"]], v)


class NodeWeightedHitsRatioMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_weighted_hits_ratio", "", labels=["id"])

    def add(self, node):
        v = node["biases"].get("weightedHitsRatio")
        if v is not None:
            self.add_metric([node["id"]], v)


class NodeWeightedErrorsRatioMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_weighted_errors_ratio", "", labels=["id"])

    def add(self, node):
        v = node["biases"].get("weightedErrorsRatio")
        if v is not None:
            self.add_metric([node["id"]], v)


class NodeWeightedDupCacheMissRatioMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_weighted_dup_cache_miss_ratio", "", labels=["id"])

    def add(self, node):
        v = node["biases"].get("weightedDupCacheMissRatio")
        if v is not None:
            self.add_metric([node["id"]], v)


class NodeLastRegistrationMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_last_registration_timestamp", "", labels=["id"])

    def add(self, node):
        last_registration_ts = _str_to_timestamp(node["lastRegistration"])
        self.add_metric([node["id"]], last_registration_ts)


class NodeCreationMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_creation_timestamp", "", labels=["id"])

    def add(self, node):
        creation_ts = _str_to_timestamp(node["createdAt"])
        self.add_metric([node["id"]], creation_ts)


class NodeDiskTotalMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_disk_total_megabytes", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["diskStats"]["totalDiskMB"])


class NodeDiskUsedMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_disk_used_megabytes", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["diskStats"]["usedDiskMB"])


class NodeDiskAvailableMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_disk_available_megabytes", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["diskStats"]["availableDiskMB"])


class NodeMemoryTotalMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_memory_total_kilobytes", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["memoryStats"]["totalMemoryKB"])


class NodeMemoryFreeMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_memory_free_kilobytes", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["memoryStats"]["freeMemoryKB"])


class NodeMemoryAvailableMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_memory_available_kilobytes", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["memoryStats"]["availableMemoryKB"])


class NodeCPUNumberMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_cpu_number", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["cpuStats"]["numCPUs"])


class NodeCPULoadAvgMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_cpu_load_avg", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["cpuStats"]["loadAvgs"][0])


class NodeSentBytesTotalMetric(CounterMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_sent_bytes", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["nicStats"]["bytesSent"])


class NodeSpeedtestUploadBandwidthMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_speedtest_upload_bandwidth", "", labels=["id"])

    def add(self, node):
        speedtest = node.get("speedtest")
        if speedtest:
            self.add_metric([node["id"]], speedtest["upload"]["bandwidth"])


class NodeSpeedtestDownloadBandwidthMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_speedtest_download_bandwidth", "", labels=["id"])

    def add(self, node):
        speedtest = node.get("speedtest")
        if speedtest:
            self.add_metric([node["id"]], speedtest["download"]["bandwidth"])


class NodeSpeedtestPingLatencyMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__(
            "saturn_node_speedtest_ping_latency_milliseconds", "", labels=["id"]
        )

    def add(self, node):
        speedtest = node.get("speedtest")
        if speedtest:
            self.add_metric([node["id"]], speedtest["ping"]["latency"])


class NodeReceivedBytesTotalMetric(CounterMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_received_bytes", "", labels=["id"])

    def add(self, node):
        self.add_metric([node["id"]], node["nicStats"]["bytesReceived"])


class NodeEstimatedEarningsMetric(CounterMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_estimated_earnings_fil", "", labels=["id"])

    def add(self, node):
        fil_amount = node["earnings"].get("filAmount")
        if fil_amount is not None:
            self.add_metric([node["id"]], fil_amount)


class NodeUptimeCompletionMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_uptime_completion_ratio", "", labels=["id"])

    def add(self, node):
        uptime_completion = node["earnings"].get("uptimeCompletion")
        if uptime_completion is not None:
            self.add_metric([node["id"]], uptime_completion)


class NodeRetrievalsMetric(CounterMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_retrievals", "", labels=["id"])

    def add(self, node):
        num_requests = node["earnings"].get("numRequests")
        if num_requests is not None:
            self.add_metric([node["id"]], num_requests)


class NodeBandwidthServedMetric(CounterMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_bandwidth_served_bytes", "", labels=["id"])

    def add(self, node):
        num_bytes = node["earnings"].get("numBytes")
        if num_bytes is not None:
            self.add_metric([node["id"]], num_bytes)


class NodeResponseDurationMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__(
            "saturn_node_response_duration_milliseconds", "", labels=["id", "quantile"]
        )

    def add(self, node):
        ttfb = node.get("ttfbStats")
        if not ttfb:
            return

        for q in (0.01, 0.05, 0.5, 0.95, 0.99):
            p = int(q * 100)
            try:
                self.add_metric([node["id"], str(q)], ttfb[f"p{p}_1h"])
            except KeyError:
                return


class NodeRequestsMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_requests", "", labels=["id", "result"])

    def add(self, node):
        ttfb = node.get("ttfbStats")
        if not ttfb:
            return

        try:
            ok = ttfb["reqs_served_1h"]
            hits = ttfb["hits_1h"]
            errors = ttfb["errors_1h"]
            slow_hits = ttfb["slow_hits_1h"]
        except KeyError:
            return

        self.add_metric([node["id"], "ok"], ok)
        self.add_metric([node["id"], "ok_hit"], hits)
        self.add_metric([node["id"], "error"], errors)
        self.add_metric([node["id"], "ok_slow_hit"], slow_hits)


class NodeHealthCheckFailuresMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__(
            "saturn_node_health_check_failures", "", labels=["id", "error"]
        )

    def add(self, node):
        failures = node.get("HealthCheckFailures")
        if not failures:
            self.add_metric([node["id"]], 0)
            return

        errors = defaultdict(int)
        for f in failures:
            errors[f["error"]] += 1

        for k, v in errors.items():
            self.add_metric([node["id"], k], v)


class NodeRequirementsMinCPUCoresMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_requirements_min_cpu_cores", "")

    def add(self, requirements):
        self.add_metric([], requirements["minCPUCores"])


class NodeRequirementsMinMemoryMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_requirements_min_memory_gigabytes", "")

    def add(self, requirements):
        self.add_metric([], requirements["minMemoryGB"])


class NodeRequirementsMinUploadSpeedMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_requirements_min_upload_speed_mbps", "")

    def add(self, requirements):
        self.add_metric([], requirements["minUploadSpeedMbps"])


class NodeRequirementsMinDownloadSpeedMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_requirements_min_download_speed_mbps", "")

    def add(self, requirements):
        self.add_metric([], requirements["minDownloadSpeedMbps"])


class NodeRequirementsMinDiskMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_requirements_min_disk_gigabytes", "")

    def add(self, requirements):
        self.add_metric([], requirements["minDiskGB"])


class NodeRequirementsLastVersionMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_requirements_last_version", "")

    def add(self, requirements):
        self.add_metric([], requirements["lastVersion"])


class NodeRequirementsMinVersionMetric(GaugeMetricFamily):
    def __init__(self):
        super().__init__("saturn_node_requirements_min_version", "")

    def add(self, requirements):
        self.add_metric([], requirements["minVersion"])


class StatsCollector(object):
    def __init__(self, node_ids):
        """Collects stats for the specified node IDs.

        If node_ids is empty then collets stats for all nodes.
        """
        self._node_ids = frozenset(node_ids)
        self._earnings_start = self._utcnow_timestamp()

    @staticmethod
    def _utcnow_timestamp():
        return datetime.utcnow().timestamp() * 1000

    def _earnings_per_node(self, earnings):
        per_node = {}

        for node in earnings["perNodeMetrics"]:
            if not self._node_ids or node["nodeId"] in self._node_ids:
                per_node[node["nodeId"]] = node

        return per_node

    def _node_metrics_from_stats(self, stats, earnings):
        info = NodeInfoMetric()
        metrics = (
            info,
            NodeVersionMetric(),
            NodeWeightMetric(),
            NodeBiasMetric(),
            NodePenaltyMetric(),
            NodeWeightedTTFBMetric(),
            NodeWeightedHitsRatioMetric(),
            NodeWeightedErrorsRatioMetric(),
            NodeWeightedDupCacheMissRatioMetric(),
            NodeLastRegistrationMetric(),
            NodeCreationMetric(),
            NodeDiskTotalMetric(),
            NodeDiskUsedMetric(),
            NodeDiskAvailableMetric(),
            NodeMemoryTotalMetric(),
            NodeMemoryFreeMetric(),
            NodeMemoryAvailableMetric(),
            NodeCPUNumberMetric(),
            NodeCPULoadAvgMetric(),
            NodeResponseDurationMetric(),
            NodeRequestsMetric(),
            NodeHealthCheckFailuresMetric(),
            NodeSentBytesTotalMetric(),
            NodeReceivedBytesTotalMetric(),
            NodeSpeedtestUploadBandwidthMetric(),
            NodeSpeedtestDownloadBandwidthMetric(),
            NodeSpeedtestPingLatencyMetric(),
            NodeEstimatedEarningsMetric(),
            NodeUptimeCompletionMetric(),
            NodeRetrievalsMetric(),
            NodeBandwidthServedMetric(),
        )

        found = set()
        for node in stats:
            if self._node_ids and node["id"] not in self._node_ids:
                continue
            found.add(node["id"])

            node["earnings"] = earnings.get(node["id"], {})
            for m in metrics:
                m.add(node)

        # Every not found node considered inactive.
        for i in self._node_ids - found:
            info.add_inactive(i)

        return metrics

    def collect(self):
        r = requests.get(
            "https://uc2x7t32m6qmbscsljxoauwoae0yeipw.lambda-url.us-west-2.on.aws",
            params={
                "filAddress": "all",
                "startDate": self._earnings_start,
                "endDate": self._utcnow_timestamp(),
                "step": "day",
                "perNode": "true",
            },
        )
        earnings = r.json()
        earnings = self._earnings_per_node(earnings)

        r = requests.get(
            "https://orchestrator.strn.pl/stats",
            headers={"Accept": "application/json", "Accept-Encoding": "gzip, deflate"},
        )
        stats = r.json()

        for m in self._node_metrics_from_stats(stats["nodes"], earnings):
            yield m


class RequirementsCollector:
    @staticmethod
    def _node_requirements_metrics(requirements):
        metrics = (
            NodeRequirementsMinCPUCoresMetric(),
            NodeRequirementsMinMemoryMetric(),
            NodeRequirementsMinUploadSpeedMetric(),
            NodeRequirementsMinDownloadSpeedMetric(),
            NodeRequirementsMinDiskMetric(),
            NodeRequirementsLastVersionMetric(),
            NodeRequirementsMinVersionMetric(),
        )

        for m in metrics:
            m.add(requirements)

        return metrics

    def collect(self):
        r = requests.get("https://orchestrator.strn.pl/requirements")
        requirements = r.json()

        for m in self._node_requirements_metrics(requirements):
            yield m


if __name__ == "__main__":
    # Disable default collector metrics.
    REGISTRY.unregister(GC_COLLECTOR)
    REGISTRY.unregister(PLATFORM_COLLECTOR)
    REGISTRY.unregister(PROCESS_COLLECTOR)

    node_ids = []
    # Try reading node IDs from file set in SATURN_PROMETHEUS_EXPORTER_NODES.
    nodes_file = os.environ.get("SATURN_PROMETHEUS_EXPORTER_NODES")
    if nodes_file:
        with open(nodes_file) as f:
            node_ids = [l.strip() for l in f]

    REGISTRY.register(StatsCollector(node_ids))
    REGISTRY.register(RequirementsCollector())

    start_http_server(9000)

    signal.pause()
