# Weekend Radar

Collects weekend ideas (free stuff, exhibitions, festivals, workshops...) from PUBLIC Telegram channels.
The same event posted in several channels is merged into one card ("Also posted in ...").

## Setup
1. Create a GitHub repo and upload everything in this folder.
2. Edit `channels.json` (public channel usernames, the part after t.me/).
3. Settings > Pages > Deploy from a branch > `main` / root.
4. Settings > Actions > General > Workflow permissions: Read and write.
5. Actions > "Crawl weekend events" > Run workflow. Then open your Pages URL.

Runs automatically at 08:00 and 18:00 Singapore time.

## Tweak
- Keywords / categories: `CATEGORIES` in `scripts/crawl.py`
- Duplicate sensitivity: `SIM_THRESHOLD` in `scripts/crawl.py` (lower = merges more)
- Schedule: `cron` in `.github/workflows/crawl.yml` (UTC)
- Days kept: `keep_days` in `channels.json`
