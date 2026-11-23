# Keeping the backend awake (Render free plan), v4.12.0

## What we want

| India time | Server |
|---|---|
| 06:00 – about 01:00 | Awake: no waiting for students (they chat late at night) |
| about 01:00 – 06:00 | Allowed to sleep (about 5 hours). A student who writes then waits up to a minute for it to wake |

Render's free plan stops a web service after **15 minutes without requests** and gives each workspace **750 free
instance hours a month**. Awake about 19 hours a day uses about **595 hours** in a 31-day month, well inside the
limit. **Only this one service should be kept awake.** A second free service kept awake in the same workspace
would use up the hours, and Render then suspends the free services until the 1st of next month.

## The endpoint to ping: `/ping`

`GET /ping` (or `HEAD /ping`) returns `{"status": "ok"}` and touches nothing: no database, Redis or search index.
Do **not** ping `/health` for keep-awake: it queries the database, Redis and ChromaDB on every call, which would also
keep the database awake all day. `/health` stays for real monitoring.

## Main pinger: cron-job.org (free)

1. Sign up at https://cron-job.org and choose **Create cronjob**.
2. **URL:** `https://university-ai-luwe.onrender.com/ping` (or your backend URL), method GET.
3. **Schedule → Custom:**
   - **Time zone:** Asia/Kolkata
   - **Minutes:** every 5 minutes (0, 5, 10 … 55)
   - **Hours:** 0 and 6 to 23 (that is, every hour except 1, 2, 3, 4 and 5)
   - **Days / months / weekdays:** every
   This pings from 06:00 to 00:55, so the server sleeps from about 01:10 to 06:00.
4. Optional: turn on failure e-mails so you hear if the backend is down.

## Backup pinger: GitHub Action

`.github/workflows/keep-backend-awake.yml` pings `/ping` every 10 minutes over the same hours (06:00–00:50 India
time; the schedule is written in UTC in the file). GitHub sometimes starts scheduled runs late, so it is only the
backup. GitHub also pauses scheduled workflows in a repository with no activity for 60 days.

## Switching it off (for example after moving to the paid plan)

A paid Render instance (such as Standard, $25/month) does not sleep, so the pinging is no longer needed. **No code
change is needed:**
1. cron-job.org: disable the job.
2. GitHub: Settings → Secrets and variables → Actions → **Variables** → add `KEEP_AWAKE` = `off`.

Leaving them on is harmless (a few thousand tiny requests a month).

## What pinging cannot prevent

- Render may restart a free service at any time, and every deploy restarts it (about a minute to start).
- Files written on the server (such as the local search index in `chroma_data/`) are lost on restart and rebuilt.
