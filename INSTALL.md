<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# Install L30 on a Sunday Afternoon

A practical guide for librarians who want to run their own library system.
No programming required. You need a computer, an internet connection, and
about 2 hours.

## What you are setting up

L30 is a complete library management system: catalog, circulation, patron
accounts, events, reading programs, and more. It runs on a server (a
computer that stays on) and your patrons access it through a web browser.

## What you need

- A server running Ubuntu 22.04 or 24.04 (a $20/month VPS from DigitalOcean,
  Hetzner, or Linode works fine. 2 CPU, 4 GB RAM minimum.)
- A domain name pointing to your server (like yourlibrary.org)
- SSH access to your server (your VPS provider will give you this)
- About 2 hours on a quiet Sunday

Everything builds from the source code in this repository -- there is no
separate download and nothing to compile by hand. Docker does the building.

## Step 1: Connect to your server

Open Terminal (Mac) or PowerShell (Windows) and connect:

```
ssh root@your-server-ip
```

Your VPS provider gave you the IP address when you created the server.

## Step 2: Install Docker

Copy and paste these commands one at a time:

```
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

Verify it worked:

```
docker --version
```

You should see something like "Docker version 27.x.x".

## Step 3: Set up a firewall

```
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

Type "y" when it asks to confirm. This allows SSH, web traffic, and
nothing else. L30's own containers bind only to the loopback interface
(127.0.0.1), so the database and cache are never reachable from the
internet regardless.

## Step 4: Download L30

```
cd /opt
git clone https://github.com/luminarynerds/l30-library.git l30
cd l30
```

## Step 5: Configure your library

Run the setup script. It generates all your secrets automatically and asks
for your library name, domain, and contact email:

```
./setup.sh
```

You can also pass values directly:

```
./setup.sh --domain yourlibrary.org --email admin@yourlibrary.org --name "Your Library Name"
```

The script creates two files: `.env` (secrets and settings -- keep it
private) and `branding.json` (your library's name, contact info, and
colors). (`.env.example` is a stub, not a working config -- don't use it.)

If you want to tweak the branding now, edit it with:

```
nano branding.json
```

You can also change branding later from the setup wizard and the admin
dashboard.

## Step 6: Start the system

```
docker compose -f docker-compose.dist.yml up -d --build
```

The first run builds everything from source and takes 10-15 minutes.
Later restarts take seconds.

Check that all containers are running:

```
docker compose -f docker-compose.dist.yml ps
```

You should see 5 services: database, redis, l30-backend, frontend, nginx.
Wait until all show "healthy" (this can take 2-3 minutes after the build
finishes), then confirm the system answers:

```
curl http://127.0.0.1:8081/api/v1/health
```

The app listens only on 127.0.0.1:8081 for now -- it becomes reachable
from the outside in the next step, behind HTTPS.

## Step 7: Set up SSL (HTTPS)

Get a free certificate first, while port 80 is still free:

```
apt install -y certbot
certbot certonly --standalone -d yourlibrary.org
```

Follow the prompts. It will ask for your email (for renewal notices).

Then set up a host nginx to terminate SSL and proxy to L30:

```
apt install -y nginx
```

Create the site config:

```
nano /etc/nginx/sites-available/l30
```

Paste this (replace yourlibrary.org with your domain):

```
server {
    listen 80;
    server_name yourlibrary.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourlibrary.org;

    ssl_certificate /etc/letsencrypt/live/yourlibrary.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourlibrary.org/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site and restart nginx:

```
ln -s /etc/nginx/sites-available/l30 /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

## Step 8: First boot -- explore the demo or set up your library

Visit https://yourlibrary.org in your browser. On first boot L30 shows a
landing page with two choices; the system stays locked until you finish
one of them.

**Explore Demo** loads a complete fictional library (Little Schitt Creek:
about 2,000 catalog items, patrons, staff, events, active checkouts) and
unlocks the site immediately, so you can try everything before
configuring anything. See "Demo logins" below for the accounts to use.
To switch from demo to a real install afterwards, wipe the stack and
start over: `docker compose -f docker-compose.dist.yml down -v` destroys
all demo data, and the next `up -d` boots fresh.

**Set Up My Library** starts the real setup wizard, which walks you
through:

1. **Library name and your admin account** -- the founding administrator.
   This form is only open while no admin exists; once you've created yours,
   it closes.
2. **Feature preset** -- see below.
3. **Colors and branding** -- pre-filled from your `branding.json`.
4. **Homepage welcome text.**
5. **Review and finish.**

When you finish, the site unlocks for patrons and you're logged in as admin.

### Demo logins

Demo accounts use per-role passwords in the form `demo-2026-<role>`. The
seeded staff roster is fixed, so these work on any fresh demo:

| Try out | Log in as | Password |
|---------|-----------|----------|
| A patron | `marcus.fitzgerald1@example.org` | `demo-2026-patron` |
| Front-desk staff | `priya.nakamura@littleschittcreek.example.org` | `demo-2026-staff` |
| A library admin | `helena.vogt@littleschittcreek.example.org` | `demo-2026-admin` |
| The director | `derek.whitfield@littleschittcreek.example.org` | `demo-2026-director` |

The other seeded patrons (about 60) use the same `demo-2026-patron`
password (`demo-2026-kid` for under-13 accounts); browse the patrons list
from any staff account to see them.

Two optional env vars adjust this. Both live in `.env` and are read when
the backend starts, so set them before `up -d` (or recreate the backend
after changing them):

- `DEMO_LOGIN_PASSWORD` replaces the `demo-2026` base with your own
  value. **Do this on any internet-facing demo** -- the passwords above
  are public knowledge, straight from this file.
- `DEMO_SUPERADMIN_PASSWORD` opts in to a full-access super-admin demo
  account (`avery.sinclair@littleschittcreek.example.org`). Without it,
  no super-admin demo login exists at all -- secure by default.

## Feature presets

Partway through the setup wizard you'll be asked to pick a feature preset.
This turns whole feature areas on or off at once so you aren't starting from
a blank, everything-disabled system (or an overwhelming one with every
module lit up). You can change individual features later from the admin
dashboard — the preset is just a starting point.

| Preset | What it turns on | Best for |
|--------|-------------------|----------|
| `barebones` | The minimum to run circulation: front desk, print hold slips, hold trap cards, email notifications. Everything else (events, community features, gamification, processing queue, etc.) stays off. | Testing a fork, or a very small operation that only needs check-in/checkout. |
| `small_library` | Front desk, collection management, community features, events, email + in-app notifications, processing queue, print hold slips, hold trap cards. | Most single-branch public libraries — circulation plus the day-to-day extras, without the full admin surface area. |
| `full` | Every feature flag in the system. | Libraries that want everything available immediately and will disable what they don't use. |

The exact field-by-field definitions live in
`backend/app/api/v1/organization_features.py` (`PRESETS`).

## Step 9: Set up automatic SSL renewal

Certbot's standalone renewal needs port 80, which the host nginx now owns,
so the renewal briefly stops nginx (a few seconds at 3 AM):

```
crontab -e
```

Add this line at the bottom:

```
0 3 * * * certbot renew --quiet --pre-hook "systemctl stop nginx" --post-hook "systemctl start nginx"
```

Save and exit.

## You are done

Your library system is live at https://yourlibrary.org.

### What to do next

- Explore the admin dashboard
- Add your catalog items (or import from another system)
- Set up your library hours and branch information
- Invite staff members
- Tell your patrons about the new system

### If something goes wrong

Check the logs:

```
# Backend logs
docker compose -f docker-compose.dist.yml logs l30-backend --tail 50

# All logs
docker compose -f docker-compose.dist.yml logs --tail 50
```

Restart everything:

```
docker compose -f docker-compose.dist.yml restart
```

### Getting help

- Technical docs: see SELF_HOSTING.md in this directory
- Working on the code itself: see DEVELOPER_SETUP.md
- API documentation: visit https://yourlibrary.org/docs (disabled by
  default in production -- set API_DOCS_ENABLED=true in `.env`)
