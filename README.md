## 🚀 XenFlow Mailer

> Enterprise-grade, reputation-safe email automation you can run 100% locally for free.

[![Version](https://img.shields.io/badge/version-1.0.0-red.svg)](https://github.com/xenflow/mailer)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](docker-compose.yml)

> **⚠ This repository is private and licensed. Access is granted only to verified buyers.**

---

## ✨ What XenFlow Mailer Does

- **Personalized outbound at scale** – Dynamic templates with `{{placeholders}}` for name, company, industry, and custom fields.
- **Automated follow-ups** – Multi-step sequences with smart delays and send windows so you never forget to follow up.
- **Multi-provider support** – Gmail OAuth, Outlook, SendGrid, Mailgun, Amazon SES, or any custom SMTP server.
- **Deliverability & safety first** – Built-in warmup, rate limiting, bounce handling, and complaint safeguards.
- **Reply-aware campaigns** – IMAP-based reply detection that automatically stops sequences on reply, bounce, or unsubscribe.
- **Enterprise analytics** – Real-time dashboard with send/open/reply metrics and safety indicators.
- **Fully containerized** – One-command Docker stack (backend, frontend, workers, PostgreSQL, Redis, Flower).

---

## 🛡️ Safety & Limits (How It Protects You)

XenFlow Mailer is designed to protect your domain and inbox reputation, not to blast spam.

**Core protections:**

| Protection | Default | Purpose |
|-----------|---------|---------|
| Max emails/day (per sender) | 200 (hard-capped below 500) | Stay under Gmail / provider limits |
| Max emails/hour | 20–50 | Avoid spam spikes and throttling |
| Max bounce rate | 5–10% | Auto-stop risky campaigns |
| Complaint rate guard | 0.5% | Protect reputation |
| Warmup schedule | ~28 days | Gradual ramp-up for new inboxes |
| Send window | 9–17, weekdays | Human-like sending behavior |

When Gmail returns **“Daily user sending limit exceeded”** (for example on `xenflowtech@gmail.com` or `saad.ai.solutions@gmail.com`):

- The sender is **automatically paused** for the rest of the day.
- A nightly warmup task **reactivates** it after the daily reset.
- Campaigns will **skip paused or maxed-out senders**, so if all senders in rotation are exhausted, the campaign will appear “stuck” until limits reset or you add more capacity.

For details, see `LOG_ANALYSIS_SUMMARY.md` and `CAMPAIGN_LIMITS.md`.

---

## 🚀 Quick Start (Local & Free)

Run the entire stack locally using Docker (no paid cloud services required).

```bash
# 1. Clone the repository and enter the folder
git clone <repo-url>
cd Email_automation

# 2. Copy environment file
cp env.example .env
# On Windows PowerShell:
# Copy-Item env.example .env

# 3. Edit .env (at least SECRET_KEY and POSTGRES_PASSWORD)

# 4. Build and start all services
docker compose up -d --build

# 5. Check services
docker compose ps

# 6. Access the app
# Dashboard
open http://localhost:3000
# API docs
open http://localhost:8000/api/docs
# Flower (task monitor)
open http://localhost:5555
```

For a step-by-step, non-technical walkthrough of the **100% free local setup**, read `FREE_SETUP_AND_USAGE_GUIDE.md`.

---

## 📚 Documentation

- **Free Setup & Usage Guide** – `FREE_SETUP_AND_USAGE_GUIDE.md` (run locally for free and send your first campaign).
- **Complete Setup Guide** – `SETUP_GUIDE.md` (environment, Gmail OAuth, SMTP, follow-ups, scaling, troubleshooting).
- **Architecture Overview** – `ARCHITECTURE.md` (system design and internals).
- **Campaign Limits & Safety** – `CAMPAIGN_LIMITS.md` (how sending caps, warmup, and protections work).
- **Log Analysis Summary** – `LOG_ANALYSIS_SUMMARY.md` (why campaigns can appear “stuck” and senders become inactive).
- **API Documentation** – `http://localhost:8000/api/docs` (interactive OpenAPI docs).

---

## 🏗️ Architecture (High Level)

```
┌─────────────────────────────────────────────────────────┐
│                    XenFlow Mailer                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Frontend (React/TypeScript) ──► API (FastAPI)         │
│            │                     │                     │
│            ▼                     ▼                     │
│         Users       ◄── Celery Workers (email/IMAP)    │
│                          │                             │
│              ┌───────────┴───────────┐                 │
│              │                       │                 │
│         PostgreSQL               Redis                 │
│       (leads, logs,          (queue, cache,           │
│        campaigns)              rate limits)           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Tech Stack

| Component | Technology |
|----------|------------|
| Backend | Python 3.11 + FastAPI |
| Frontend | React 18 + TypeScript |
| Database | PostgreSQL 15 |
| Queue/Workers | Redis + Celery |
| Email Providers | Gmail, Outlook, SendGrid, Mailgun, SES, any SMTP |
| Infrastructure | Docker + Docker Compose |

---

## 🎨 Dashboard Highlights

- Modern **red & black** dark theme.
- **Smooth animations** using Framer Motion.
- **Live charts & stats** (sends, opens, replies, bounces).
- **Sender health indicators** (paused, warmup, at limit).
- **Responsive layout** for laptops and desktops.

---

## 🔧 Key Configuration (Environment)

Minimal important variables (see `SETUP_GUIDE.md` for the full list):

```env
# Safety thresholds
MAX_EMAILS_PER_DAY=200
MAX_EMAILS_PER_HOUR=20
MAX_BOUNCE_RATE=0.05

# Send window
SEND_WINDOW_START_HOUR=9
SEND_WINDOW_END_HOUR=17
SEND_WEEKDAYS_ONLY=true
DEFAULT_TIMEZONE=America/New_York

# Gmail OAuth (optional)
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-secret
GMAIL_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

---

## 📧 Supported Providers

- ✅ Gmail (OAuth 2.0)
- ✅ Outlook / Office 365
- ✅ SendGrid
- ✅ Mailgun
- ✅ Amazon SES
- ✅ Any custom SMTP server

See `SETUP_GUIDE.md` → **Gmail OAuth Setup** and **Custom SMTP Setup** for detailed steps.

---

## 🔮 Roadmap (V2 Ideas)

- [ ] AI-powered reply suggestions / drafting (self-hosted LLM).
- [ ] Intent detection from replies (demo vs not interested vs referral).
- [ ] Calendar booking integration (Google Calendar / Calendly).
- [ ] CRM synchronization (HubSpot, Pipedrive, custom webhooks).
- [ ] A/B testing for subject lines and templates.

---

## ⚠️ Important Usage Notes

1. **Not a spam tool** – Use XenFlow Mailer only for legitimate, permission-based business outreach.
2. **Warmup is mandatory** – New inboxes must be warmed up gradually; do not jump to full volume on day one.
3. **Respect provider limits** – Stay under Gmail/SMTP caps to avoid auto-pauses and account flags.
4. **Honor unsubscribes** – Always respect opt-outs and data privacy laws (CAN-SPAM, GDPR, etc.).
5. **Monitor metrics** – Watch bounce/complaint rates and pause campaigns if they trend high.

---

## 📄 License

MIT License – see `LICENSE` for details.

---

Built with ❤️ for deliverability and long-term inbox health.

