#!/bin/sh
set -eu
printf '"motorloop" "%s"\n' "$POSTGRES_PASSWORD" > /tmp/users.txt
cat > /tmp/pgbouncer.ini <<EOF
[databases]
motorloop = host=postgres port=5432 dbname=motorloop
[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = plain
auth_file = /tmp/users.txt
pool_mode = transaction
max_client_conn = 200
default_pool_size = 20
reserve_pool_size = 5
max_db_connections = 50
ignore_startup_parameters = extra_float_digits
pidfile = /tmp/pgbouncer.pid
logfile = /tmp/pgbouncer.log
EOF
chmod 644 /tmp/users.txt /tmp/pgbouncer.ini
exec pgbouncer -u nobody /tmp/pgbouncer.ini
