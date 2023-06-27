# Saturn Moonlet

🚧 **This project is under active development. Things may break** 🚧

[Filecoin Saturn](https://saturn.tech) monitoring for node operators.
More powerful and insightful alternative to [Saturn Node Dashboard](https://dashboard.saturn.tech/stats) that anyone can run.

Saturn Moonlet provides a node operator with the following:

* Real-time and historical metrics about node stats and earnings.
* Ability to run arbitrary PromQL queries against node metrics.
* Ability to build custom dashboards.
* Alerts based on metrics.
* Anything else that [Grafana](https://grafana.com) and [Prometheus](https://prometheus.io) can do 😉

It does not require installing any additional software on a Saturn node.
You only need [Docker Compose](https://docs.docker.com/compose) to run it locally or on your server.

If you're interested, you can see [how it's made](#how-its-made).

This project is neither affiliated with the [Filecoin Saturn](https://github.com/filecoin-saturn) project nor the [Protocol Labs](https://protocol.ai) organization.
Although, it was built during the [HackFS 2023](https://ethglobal.com/showcase/saturn-moonlet-c4583) hackaton and was nominated for the "Best use of Filecoin Saturn" prize 🥇

## Try it

Live demo is available at [https://demo.moonlet.zanko.dev](https://demo.moonlet.zanko.dev).

![demo](https://github.com/31z4/saturn-moonlet/assets/3657959/a71feac1-ac79-4513-be12-797103546ab7)

Note that the demo offers limited features allowing you only to evaluate and test Saturn Moonlet. Demo is not an end product and provided **"AS IS"**.

### Run locally

It's easy to run Saturn Moonlet locally using Docker Compose:

```sh
# Create empty environment files, so that you can customize service configuration if needed.
touch docker/prometheus-exporter/.env
touch docker/grafana/local/.env

# Run services in the background.
docker compose --profile local up -d
```

This command will start Prometheus Exporter, Prometheus, and Grafana services listening on `localhost` with persistent storage in Docker volumes.

Go to [http://localhost:3000](http://localhost:3000) and check out the dashboard 🌖

## Run in production

For production, Grafana is configured to use HTTPS for secure web traffic.
It's up to you how to obtain an SSL certificate and a key for encryption.
For example, check [Grafana documentation](https://grafana.com/docs/grafana/latest/setup-grafana/set-up-https/#set-up-grafana-https-for-secure-web-traffic) for possible options.

Once you've got a certificate and a key, you must place it to `docker/grafana/ssl` under the following names:

```console
$ ls docker/grafana/ssl
grafana.crt grafana.key
```

Production Grafana configuration is almost similar to default except for HTTPS (see [`docker/grafana/production/grafana.ini`](docker/grafana/production/grafana.ini)).
You can override this configuration by setting [environment variables](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#override-configuration-with-environment-variables) in `docker/grafana/production/.env`.

For example, override the default admin user, password, and email:

```sh
cat << EOF > docker/grafana/production/.env
GF_SECURITY_ADMIN_USER=saturn
GF_SECURITY_ADMIN_PASSWORD=SuperSecret
GF_SECURITY_ADMIN_EMAIL=example@email.com
EOF
```

If you don't want to override anything, simply create an empty environment file for Grafana:

```sh
touch docker/grafana/production/.env
```

By default Prometheus Exporter observes all nodes in the network.
If that's what you need, just create and empty environment file for Prometheus Exporter, and you're ready to go.

```sh
touch docker/prometheus-exporter/.env
```

Otherwise, list specific node IDs in a file and point Prometheus Exporter to that file:

```sh
# Create conf directory if does not exist.
mkdir -p docker/prometheus-exporter/conf

# Specify node IDs.
cat << EOF > docker/prometheus-exporter/conf/nodes.txt
9b7c3402-e90f-4d12-833d-ccb50a3c261d
2aadfe2c-2111-4602-9bf9-1b38884b02e7
EOF

# Tell Prometheus Exporter to observe specific node IDs.
# Note that path to the file is within a Docker container.
echo SATURN_PROMETHEUS_EXPORTER_NODES=/conf/nodes.txt > docker/prometheus-exporter/.env
```

Now everything is ready to launch Saturn Moonlet 🚀

```sh
docker compose --profile production up -d
```

## How it's made

Saturn Moonlet consists of thee main components.

* **Prometheus Exporter** is a Python service that fetches node stats and earnings via the same public HTTP APIs that Saturn Node Dashboard uses.
It exposes this info in a simple [text-based](https://prometheus.io/docs/instrumenting/exposition_formats/#text-based-format) format.
* **Prometheus** periodically scrapes metrics exposed by Prometheus Exporter and persists these metrics in a local on-disk time series database.
Prometheus stores historical data about node stats and earnings.
* **Grafana** uses Prometheus as a data source and provides a node operator with powerfull web interface to query and visualize node metrics.
It comes with two pre-defined dashboards to overview nodes in the network and see details about a particular node.
It also allows to configure alerts.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
