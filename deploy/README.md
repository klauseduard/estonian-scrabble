# Deploying Estonian Scrabble

This directory contains deployment notes, ideas, and instructions.
It is gitignored — nothing here gets committed.

## Quick Start (local sharing)

The fastest way to let friends play without any server setup:

```bash
source .venv/bin/activate
pip install -r requirements-server.txt  # first time only
python -m uvicorn server.app:app --host 0.0.0.0 --port 8765
```

Then share access via:
- **Same network:** `http://<your-local-ip>:8765`
- **Over internet (temporary):** `ngrok http 8765` or `tailscale serve 8765`

---

## Option A: Hetzner VPS

**Cost:** ~4 EUR/month (CX22: 2 vCPU, 4 GB RAM — far more than needed)
**Pros:** Full control, cheapest long-term, no WebSocket limitations
**Cons:** You manage the server (updates, SSL, etc.)

### Our server

- IPv4: `89.167.100.76`
- IPv6: `2a01:4f9:c014:f6e0::/64`
- Game URL: `http://89.167.100.76/scrabble/`
- Admin: `http://89.167.100.76/scrabble/admin`

### Steps

1. **Create a VPS** at https://console.hetzner.cloud
   - Location: Helsinki (hel1) for lowest latency to Estonia
   - Image: Ubuntu 24.04
   - Type: CX22 (cheapest, plenty for this)
   - Add your SSH public key (`~/.ssh/id_ed25519.pub` or `~/.ssh/id_rsa.pub`)
     — the key must be selected during server creation, adding it later
     won't inject it into the server

2. **SSH in as root** (Hetzner only creates the root user):
   ```bash
   ssh root@89.167.100.76
   ```
   If you have multiple SSH keys, specify which one:
   ```bash
   ssh -i ~/.ssh/id_ed25519 root@89.167.100.76
   ```

3. **Install Docker and Caddy:**
   ```bash
   apt update && apt install -y docker.io docker-compose-v2 caddy
   ```

4. **Clone and build:**
   ```bash
   git clone https://github.com/klauseduard/estonian-scrabble.git
   cd estonian-scrabble
   docker build -t scrabble .
   docker run -d --restart unless-stopped -p 8080:8080 --name scrabble scrabble
   ```
   The container runs on port 8080 internally. Caddy exposes it on port 80.

5. **Set up Caddy** as reverse proxy on port 80:

   Edit `/etc/caddy/Caddyfile`:
   ```
   klauseduard.duckdns.org {
       handle_path /scrabble/* {
           reverse_proxy localhost:8080
       }

       # SEO: robots.txt and sitemap at domain root
       handle /robots.txt {
           respond "User-agent: *
Allow: /scrabble/
Sitemap: https://klauseduard.duckdns.org/sitemap.xml"
       }
       handle /sitemap.xml {
           respond `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://klauseduard.duckdns.org/scrabble/</loc></url>
</urlset>` 200 {
               header Content-Type "application/xml"
           }
       }

       # Add other services here later, e.g.:
       # handle_path /other-app/* {
       #     reverse_proxy localhost:9090
       # }
   }
   ```

   ```bash
   systemctl restart caddy
   ```

   The game is now at `http://89.167.100.76/scrabble/`
   (WebSocket connects to `ws://89.167.100.76/scrabble/ws` automatically)

6. **With a domain** (adds HTTPS automatically):

   Change the Caddyfile to:
   ```
   yourdomain.com {
       handle_path /scrabble/* {
           reverse_proxy localhost:8080
       }
   }
   ```
   Point your DNS A record to `89.167.100.76`. Caddy gets a Let's Encrypt
   certificate automatically.

### Updating

```bash
cd estonian-scrabble
git pull
docker build -t scrabble .
docker stop scrabble && docker rm scrabble
docker run -d --restart unless-stopped -p 8080:8080 --name scrabble scrabble
```

### Monitoring

- Admin dashboard: `http://89.167.100.76:8080/admin`
- Server stats API: `http://89.167.100.76:8080/stats`
- Docker logs: `docker logs -f scrabble`

---

## Option B: Heroku

**Cost:** $7/month (Basic plan — needed for WebSocket support)
**Pros:** Zero server management, easy deploys via git push
**Cons:** More expensive than Hetzner, WebSocket needs Basic plan (not Eco)

### Steps

1. **Install Heroku CLI:** https://devcenter.heroku.com/articles/heroku-cli

2. **Login and create app:**
   ```bash
   heroku login
   heroku create estonian-scrabble
   heroku stack:set container
   ```

3. **Deploy:**
   ```bash
   git push heroku main
   ```

4. **Open:**
   ```bash
   heroku open
   ```

### Important notes

- Heroku's Eco/Mini plans do NOT support WebSockets properly.
  You need the **Basic** plan ($7/month) for reliable WebSocket connections.
- Heroku provides HTTPS automatically on `*.herokuapp.com` domains.
- The `PORT` env var is set automatically by Heroku; the Dockerfile handles it.

### Custom domain

```bash
heroku domains:add scrabble.yourdomain.com
```
Then point your DNS CNAME to the Heroku app.

---

## Option C: Fly.io

**Cost:** Free tier available (3 shared VMs, 256 MB each)
**Pros:** Free for low traffic, good WebSocket support, European regions
**Cons:** Free tier has cold starts (first request slow after idle)

### Steps

1. **Install flyctl:** https://fly.io/docs/hands-on/install-flyctl/

2. **Deploy** (fly.toml already exists in the repo):
   ```bash
   fly auth login
   fly launch          # first time — confirms settings from fly.toml
   fly deploy          # subsequent deploys
   ```

3. **Open:**
   ```bash
   fly open
   ```

The `fly.toml` in the repo is pre-configured for:
- Region: `arn` (Stockholm — close to Estonia)
- Auto-stop/start machines to save costs
- Health check on `/health`

---

## Option D: Railway

**Cost:** Usage-based, ~$5/month for light use
**Pros:** Simple GitHub integration, auto-deploys on push
**Cons:** Usage-based pricing can surprise you

### Steps

1. Go to https://railway.app
2. "New Project" -> "Deploy from GitHub Repo"
3. Select `klauseduard/estonian-scrabble`
4. Railway detects the Dockerfile automatically
5. Set environment variable: `PORT=8080` (if not auto-detected)

---

## Comparison

| | Hetzner | Heroku | Fly.io | Railway |
|---|---------|--------|--------|---------|
| Monthly cost | ~4 EUR | $7 | Free* | ~$5 |
| WebSocket support | Yes | Basic+ plan | Yes | Yes |
| Custom domain | Manual (Caddy) | Built-in | Built-in | Built-in |
| HTTPS | Caddy/nginx | Automatic | Automatic | Automatic |
| Cold starts | No | No | Yes (free tier) | No |
| Server management | You | None | None | None |
| European region | Helsinki | EU (Ireland) | Stockholm | EU |
| Best for | Long-term, control | Quick deploy | Free hobby | Auto-deploy |

*Fly.io free tier: 3 machines, 256 MB RAM each. Enough for this game.

---

## Pre-deployment checklist

- [x] Dockerfile builds and runs correctly
- [x] Health check endpoint (`/health`) exists
- [x] Static files served from same server
- [x] Dictionary pre-downloaded at build time
- [x] `$PORT` env var respected
- [x] WebSocket URL is relative (no hardcoded localhost)
- [x] Admin/stats endpoints available
- [ ] Choose a domain name (optional)
- [ ] Test with 2+ players from different devices

---

## Security considerations

These are fine for a hobby game among friends:

- No authentication — anyone with the room code can join
- `/admin` and `/stats` are public (show only room codes and counts)
- No persistent data — everything is in-memory
- Chat messages limited to 200 chars, no HTML

If you ever make this truly public (strangers playing):
- Add rate limiting (prevent room creation spam)
- Consider adding a simple PIN/password per room
- Put `/admin` behind basic auth
- Add CORS headers if needed

---

## Domain ideas

- scrabble.yourdomain.com
- sonasport.ee (sõnasport = word sport)
- tahemang.ee (tähemäng = letter game)
- eestiscrabble.eu
