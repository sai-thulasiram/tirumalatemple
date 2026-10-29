# Tirumala Darshan Planner

An independent planner for visiting Sri Venkateswara Swamy Temple, Tirumala. It turns TTD's public daily bulletins into:

- a **date checker** that estimates the crowd for any dates you pick
- upcoming **festivals compared with the same festival last year**
- **weekday patterns** and a day-by-day calendar of the free Sarva Darshan queue
- **TTD quota release dates** (₹300 Special Entry Darshan, rooms, sevas)

Data comes from TTD's daily bulletins on news.tirumala.org and can be missing or wrong. The site is not affiliated with TTD.

## How it works

```
GitHub Actions (daily, 09:15 and 12:15 IST)
  └─ scripts/scrape.py   reads TTD's bulletins → docs/data/bulletins.json
  └─ scripts/build.py    writes docs/index.html with the latest figures, robots.txt, sitemap.xml, CNAME
  └─ commits docs/       → GitHub Pages serves docs/ on your domain
```

No server, no database and no paid services. Python standard library only.

| Path | What it is |
|---|---|
| `src/index.template.html` | The page. Edit this, not `docs/index.html`. |
| `docs/data/bulletins.json` | Every daily bulletin, one record per day |
| `docs/data/plan.json` | Festival dates, Ekadasi/Pournami dates and the quota release pattern. Edit by hand. |
| `scripts/parse.py` | Turns bulletin text into a record. Tests in `tests/test_parse.py`. |
| `site.config.json` | Your domain and Google verification code |

## One-time setup

### 1. Publish on GitHub Pages
1. Push this folder to `github.com/sai-thulasiram/tirumalatemple`. The repo must be **public** for free GitHub Pages.
2. Repo **Settings → Pages**: Source **Deploy from a branch**, branch **main**, folder **/docs**. Save.
3. Repo **Settings → Actions → General → Workflow permissions**: choose **Read and write permissions**. Save.

### 2. Point your GoDaddy domain at it
1. In `site.config.json` set `"siteUrl": "https://yourdomain.in"` and push. The workflow rebuilds and writes `docs/CNAME`.
2. GoDaddy → **My Products → your domain → DNS → Manage DNS**. Delete any existing **A** record for `@` (often a "Parked" record), then add:

   | Type | Name | Value |
   |---|---|---|
   | A | @ | 185.199.108.153 |
   | A | @ | 185.199.109.153 |
   | A | @ | 185.199.110.153 |
   | A | @ | 185.199.111.153 |
   | CNAME | www | sai-thulasiram.github.io |

3. Back in **Settings → Pages**, enter the domain under **Custom domain**, wait for the DNS check (minutes to a few hours), then tick **Enforce HTTPS**.

### 3. Get it into Google
1. Open [Google Search Console](https://search.google.com/search-console) → **Add property → Domain** → enter your domain.
2. Google gives a TXT record. Add it in GoDaddy DNS (Type **TXT**, Name **@**). Click **Verify**.
   *Alternative:* choose **URL prefix**, pick the **HTML tag** method, paste the `content="…"` code into `googleSiteVerification` in `site.config.json` and push.
3. **Sitemaps** → submit `sitemap.xml`. Then **URL inspection** → your home page → **Request indexing**.

New sites usually take a few days to a few weeks to appear in results.

## Everyday use

- **Run an update now:** Actions → *Update bulletins* → **Run workflow**.
- **Backfill older years:** same button, set *pages* to e.g. `20` (50 bulletins per page).
- **Update festival dates or the quota pattern:** edit `docs/data/plan.json` and push.
- **Test the parser:** `python tests/test_parse.py`
- **Preview locally:** `python scripts/build.py && cd docs && python -m http.server` then open http://localhost:8000

## What is in the page head for search

Title and description, canonical URL, Open Graph and Twitter cards (with `og.png`), favicon and Apple touch icon, `lang="en-IN"`, and JSON-LD for `WebSite`, `WebApplication` and `Dataset` (eligible for Google Dataset Search). The latest queue, status and the last 60 bulletins are written into the HTML at build time, so search engines see real content without running JavaScript.
