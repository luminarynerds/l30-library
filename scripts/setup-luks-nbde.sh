#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# L30 Library System - One-shot LUKS2 + Tang/Clevis (NBDE) provisioner
#
# Provisions an encrypted block volume for L30 secure data:
#   1. LUKS2-formats the target device (argon2id KDF)
#   2. Adds a recovery passphrase to slot 0 (operator-supplied, stdin)
#   3. Binds an automatic-unlock keyslot to a Tang server (Clevis)
#   4. Formats the unlocked mapper as ext4
#   5. Writes /etc/crypttab + /etc/fstab entries (commented out by default;
#      operator uncomments after the first manual unlock + smoke test)
#
# This script does NOT mount the volume, copy data, or change Docker. Those
# steps belong in the maintenance-window runbook (see docs/security/disk-encryption.md).
#
# Run as root, on the L30 production host, ONCE per encrypted volume.
#
# Usage:
#   sudo ./setup-luks-nbde.sh --device /dev/sdb --tang-url https://tang.example.org
#
# Required:
#   --device     Block device to format (must be empty / disposable)
#   --tang-url   Tang server URL (https recommended)
#
# Optional:
#   --name       LUKS mapper name (default: l30_secure)
#   --label      ext4 filesystem label (default: l30-secure)

set -euo pipefail

MAPPER_NAME="l30_secure"
FS_LABEL="l30-secure"
DEVICE=""
TANG_URL=""

while [ $# -gt 0 ]; do
    case "$1" in
        --device)    DEVICE="$2"; shift 2 ;;
        --tang-url)  TANG_URL="$2"; shift 2 ;;
        --name)      MAPPER_NAME="$2"; shift 2 ;;
        --label)     FS_LABEL="$2"; shift 2 ;;
        -h|--help)   sed -n '2,40p' "$0"; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done

die() { echo "ERROR: $*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "Must run as root"
[ -n "$DEVICE" ]    || die "--device is required"
[ -n "$TANG_URL" ]  || die "--tang-url is required"
[ -b "$DEVICE" ]    || die "$DEVICE is not a block device"

for bin in cryptsetup clevis clevis-luks-bind mkfs.ext4 lsblk blkid; do
    command -v "$bin" >/dev/null 2>&1 || die "Required tool missing: $bin (install cryptsetup, clevis, clevis-luks)"
done

# Refuse to clobber a device that already holds a filesystem or LUKS header.
if blkid -p "$DEVICE" >/dev/null 2>&1; then
    EXISTING=$(blkid -p -o value -s TYPE "$DEVICE" 2>/dev/null || true)
    die "$DEVICE already has signature: '$EXISTING'. Refusing to overwrite. Wipe manually with \`wipefs -a $DEVICE\` only if you are certain."
fi

# Refuse if the device is mounted or is the root disk.
if findmnt -nr -S "$DEVICE" >/dev/null 2>&1; then
    die "$DEVICE is currently mounted"
fi
ROOT_SRC=$(findmnt -nr -o SOURCE / | sed 's/\[.*\]//')
ROOT_PARENT=$(lsblk -no PKNAME "$ROOT_SRC" 2>/dev/null | head -1 || true)
if [ -n "$ROOT_PARENT" ] && [ "/dev/$ROOT_PARENT" = "$DEVICE" ]; then
    die "$DEVICE is the parent of the root filesystem. Refusing."
fi

cat <<EOF

About to LUKS2-format and provision NBDE on:
  device:    $DEVICE
  size:      $(lsblk -nbdo SIZE "$DEVICE" | numfmt --to=iec)
  mapper:    /dev/mapper/$MAPPER_NAME
  fs label:  $FS_LABEL
  tang url:  $TANG_URL

This will DESTROY all data on $DEVICE.
EOF

read -r -p "Type the device path to confirm ($DEVICE): " CONFIRM
[ "$CONFIRM" = "$DEVICE" ] || die "Confirmation did not match. Aborting."

echo
echo "==> Step 1/4: LUKS2 format (argon2id)"
echo "    You will be prompted for a RECOVERY passphrase. Store it in the"
echo "    team password manager. It is the break-glass for Tang outage."
cryptsetup luksFormat \
    --type luks2 \
    --pbkdf argon2id \
    --cipher aes-xts-plain64 \
    --key-size 512 \
    --hash sha512 \
    --label "$FS_LABEL" \
    "$DEVICE"

echo
echo "==> Step 2/4: Open volume to verify passphrase works"
cryptsetup open "$DEVICE" "$MAPPER_NAME"

echo
echo "==> Step 3/4: Bind a Clevis keyslot to Tang at $TANG_URL"
echo "    This adds an UNATTENDED unlock keyslot. The recovery passphrase"
echo "    from step 1 is preserved in slot 0."
echo "    Tang advertisement fingerprint will be shown — verify it out-of-band"
echo "    against the Tang server before accepting."
clevis luks bind -d "$DEVICE" tang "{\"url\":\"$TANG_URL\"}"

echo
echo "==> Step 4/4: Create ext4 on /dev/mapper/$MAPPER_NAME"
mkfs.ext4 -L "$FS_LABEL" "/dev/mapper/$MAPPER_NAME"

UUID=$(blkid -s UUID -o value "$DEVICE")
[ -n "$UUID" ] || die "Could not read LUKS UUID from $DEVICE"

echo
cat <<EOF
=========================================================================
DONE. The encrypted volume is provisioned and currently OPEN.

Next steps (do these manually, NOT in this script):

1. Verify the volume mounts cleanly:
     mkdir -p /opt/l30/secure
     mount /dev/mapper/$MAPPER_NAME /opt/l30/secure
     touch /opt/l30/secure/.write-test && rm /opt/l30/secure/.write-test

2. Add to /etc/crypttab (auto-unlock via clevis at boot):
     $MAPPER_NAME UUID=$UUID none _netdev,nofail

3. Add to /etc/fstab:
     /dev/mapper/$MAPPER_NAME /opt/l30/secure ext4 defaults,nofail,_netdev 0 2

4. Enable the clevis-luks-askpass unit so initramfs/systemd asks Tang:
     systemctl enable clevis-luks-askpass.path

5. Reboot to confirm unattended unlock works. If Tang is unreachable, the
   recovery passphrase from step 1 is your fallback at the console.

6. Then proceed with the data migration in:
     docs/security/disk-encryption.md
=========================================================================
EOF
