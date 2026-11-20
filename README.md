# Weekend Radar

A free page that collects weekend ideas (free stuff, exhibitions, festivals, workshops…) from PUBLIC Telegram channels.

## Setup (10 minutes)
1. Create a new GitHub repo and upload everything in this folder.
2. Edit `channels.json` – replace the placeholders with public channel usernames (the part after `t.me/`).
   Only channels with a web preview work (test: open `https://t.me/s/<channel>` in a browser).
3. Repo > Settings > Pages > Source: **Deploy from a branch** > `main` / `(root)`.
4. Repo > Settings > Actions > General > Workflow permissions: **Read and write**.
5. Repo > Actions > "Crawl weekend events" > **Run workflow**. Then open your Pages URL.

The crawl then runs automatically at 08:00 and 18:00 Singapore time every day.

## Tweak
- Categories / keywords: `CATEGORIES` in `scripts/crawl.py`
- Schedule: `cron` in `.github/workflows/crawl.yml` (UTC)
- Posts kept: `keep_days` in `channels.json`
