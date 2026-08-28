#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  printf '%s\n' 'Run this installer as root from a validated release.' >&2
  exit 1
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ops_group=lanseir-ops

if ! getent group "$ops_group" >/dev/null; then
  groupadd --system "$ops_group"
fi
if ! getent group lanseir-audit >/dev/null; then
  groupadd --system lanseir-audit
fi

create_service_user() {
  local user=$1
  if ! id "$user" >/dev/null 2>&1; then
    useradd --system --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin "$user"
  fi
  usermod -a -G "$ops_group" "$user"
}

for service_user in \
  lanseir-mission-control \
  lanseir-arc \
  lanseir-invictus \
  lanseir-porter \
  lanseir-griot \
  lanseir-sentinel; do
  create_service_user "$service_user"
done

if ! id lanseir-deploy >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash lanseir-deploy
  passwd -l lanseir-deploy >/dev/null
fi
usermod -a -G "$ops_group" lanseir-deploy
usermod -a -G lanseir-audit lanseir-griot

install -d -o root -g root -m 0755 \
  /opt/lanseir \
  /opt/lanseir/apps \
  /opt/lanseir/apps/cadre \
  /opt/lanseir/cadre \
  /opt/lanseir/cadre/mission-control \
  /opt/lanseir/cadre/agents \
  /opt/lanseir/cadre/orchestration \
  /opt/lanseir/cadre/jobs \
  /opt/lanseir/cadre/policies \
  /opt/lanseir/infrastructure \
  /opt/lanseir/infrastructure/proxy \
  /opt/lanseir/infrastructure/docker \
  /opt/lanseir/infrastructure/monitoring \
  /opt/lanseir/infrastructure/security \
  /opt/lanseir/shared \
  /opt/lanseir/scripts \
  /opt/lanseir/libexec

install -d -o root -g root -m 0755 /opt/lanseir/cadre/state
install -d -o root -g root -m 0750 /opt/lanseir/releases /opt/lanseir/backups
install -d -o root -g lanseir-audit -m 0750 /opt/lanseir/logs/audit /opt/lanseir/logs/security
install -d -o root -g root -m 0700 /opt/lanseir/secrets
install -d -o root -g "$ops_group" -m 0750 /etc/lanseir/operations

install -o root -g root -m 0755 "$repo_root/ops/cadre_ops.py" /opt/lanseir/libexec/cadre_ops.py
install -o root -g "$ops_group" -m 0640 "$repo_root/ops/config/roles.json" /etc/lanseir/operations/roles.json
install -o root -g "$ops_group" -m 0640 "$repo_root/ops/config/actors.json" /etc/lanseir/operations/actors.json
install -o root -g "$ops_group" -m 0640 "$repo_root/ops/config/services.json" /etc/lanseir/operations/services.json
install -o root -g "$ops_group" -m 0640 "$repo_root/ops/config/limits.json" /etc/lanseir/operations/limits.json
install -o root -g "$ops_group" -m 0640 "$repo_root/ops/config/repository.json" /etc/lanseir/operations/repository.json
install -o root -g "$ops_group" -m 0640 "$repo_root/ops/config/docker-compose.prod.yml" /etc/lanseir/operations/docker-compose.prod.yml
install -o root -g "$ops_group" -m 0640 "$repo_root/ops/config/Dockerfile.prod" /etc/lanseir/operations/Dockerfile.prod
install -o root -g "$ops_group" -m 0640 "$repo_root/ops/config/Caddyfile" /etc/lanseir/operations/Caddyfile

temp_sudoers=$(mktemp)
trap 'rm -f "$temp_sudoers"' EXIT
install -m 0440 "$repo_root/ops/config/lanseir-cadre-ops.sudoers" "$temp_sudoers"
visudo -cf "$temp_sudoers"
install -o root -g root -m 0440 "$temp_sudoers" /etc/sudoers.d/lanseir-cadre-ops

install -o root -g root -m 0755 "$repo_root/ops/config/cadre-ops-root" /opt/lanseir/scripts/cadre-ops

for unit in lanseir-sentinel.service lanseir-sentinel.timer lanseir-backup.service lanseir-backup.timer; do
  install -o root -g root -m 0644 "$repo_root/ops/systemd/$unit" "/etc/systemd/system/$unit"
done

if [[ ! -f /opt/lanseir/secrets/cadre.env ]]; then
  install -o root -g root -m 0600 "$repo_root/ops/config/cadre.env.example" /opt/lanseir/secrets/cadre.env
  printf '%s\n' 'Created /opt/lanseir/secrets/cadre.env from the non-secret template; populate it before deployment.'
fi

systemctl daemon-reload
systemctl enable lanseir-sentinel.timer lanseir-backup.timer

sudo -u lanseir-sentinel sudo /opt/lanseir/scripts/cadre-ops release-current >/dev/null
printf '%s\n' 'LANSEIR/CADRE governed operations layer installed.'
