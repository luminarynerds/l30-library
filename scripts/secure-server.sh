#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# L30 Server Security Setup
# Run this ONCE on a fresh Ubuntu server before installing L30.
# Usage: sudo bash scripts/secure-server.sh
# ==============================================================================

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: run this as root (sudo bash $0)"
    exit 1
fi

echo ""
echo "L30 Server Security Setup"
echo "========================="
echo ""

# --- Preflight: make sure SSH key exists ---
if [ ! -f /root/.ssh/authorized_keys ] || [ ! -s /root/.ssh/authorized_keys ]; then
    echo "ERROR: No SSH key found in /root/.ssh/authorized_keys"
    echo "Add your SSH key FIRST, or you will be locked out."
    echo "Aborting."
    exit 1
fi

echo "[1/7] Updating system packages..."
apt update -qq && apt upgrade -y -qq

echo "[2/7] Hardening SSH..."
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config
grep -q '^MaxAuthTries' /etc/ssh/sshd_config || echo "MaxAuthTries 3" >> /etc/ssh/sshd_config
grep -q '^AllowAgentForwarding' /etc/ssh/sshd_config || echo "AllowAgentForwarding no" >> /etc/ssh/sshd_config
# Fix cloud-init overrides
find /etc/ssh/sshd_config.d/ -name '*.conf' -exec sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' {} \; 2>/dev/null
systemctl restart ssh

echo "[3/7] Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable

echo "[4/7] Installing fail2ban..."
apt install -y -qq fail2ban
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 3
banaction = ufw

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
backend = pyinotify
maxretry = 3
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban

echo "[5/7] Enabling automatic security updates..."
apt install -y -qq unattended-upgrades
echo 'Unattended-Upgrade::Automatic-Reboot "false";' > /etc/apt/apt.conf.d/51auto-upgrades

echo "[6/7] Disabling unnecessary services..."
snap disable cups 2>/dev/null || true
systemctl disable --now avahi-daemon 2>/dev/null || true

echo "[7/7] Applying kernel hardening..."
cat > /etc/sysctl.d/99-hardening.conf << 'EOF'
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.rp_filter = 1
net.ipv4.tcp_syncookies = 1
EOF
sysctl --system > /dev/null 2>&1

echo ""
echo "========================="
echo "Server security setup complete."
echo ""
echo "Summary:"
echo "  - SSH: key-only, no passwords, max 3 attempts"
echo "  - Firewall: only ports 22, 80, 443 open"
echo "  - fail2ban: active, banning after 3 failures"
echo "  - Auto-updates: enabled"
echo "  - Kernel: network hardening applied"
echo ""
echo "Next steps:"
echo "  1. Install L30 (see README.md)"
echo "  2. Make sure docker-compose.yml ports use 127.0.0.1"
echo "  3. Set .env files to chmod 600"
echo "========================="
