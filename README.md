## Try it

It's easy to run Saturn Moonlet locally using [Docker Compose](https://docs.docker.com/compose):

```console
$ cd docker
$ docker compose --profile local up -d
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

Now everything is ready to launch Saturn Moonlet 🚀

```console
$ cd docker
$ docker compose up -d
```

Production Grafana configuration is almost similar to default except for HTTPS (see [`docker/grafana/production/grafana.ini`](docker/grafana/production/grafana.ini)).
You can override this configuration by setting [environment variables](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#override-configuration-with-environment-variables) in `docker/grafana/production/.env`.

For example, override the default admin user, password, and email:

```sh
cat << EOF > docker/grafana/production/.env
GF_SECURITY_ADMIN_USER=saturn
GF_SECURITY_ADMIN_PASSWORD=SuperSecret
GF_SECURITY_ADMIN_EMAIL=hi@example.com
EOF
```
