## Try it

It's easy to run Saturn Moonlet locally using [Docker Compose](https://docs.docker.com/compose):

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
