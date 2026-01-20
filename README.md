# 🚀 XenFlow Mailer

> Enterprise-grade email automation system with reputation protection

[![Version](https://img.shields.io/badge/version-1.0.0-red.svg)](https://github.com/xenflow/mailer)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](docker-compose.yml)

---

## ✨ Features

- **Personalized Outreach** - Dynamic templates with `{{placeholders}}`
- **Automated Follow-ups** - Multi-step sequences with smart timing
- **Provider Agnostic** - Gmail OAuth, Outlook, or any SMTP server
- **Safety First** - Rate limiting, warmup, bounce handling
- **Reply Detection** - IMAP monitoring with auto-suppression
- **Enterprise Dashboard** - Real-time analytics with dark theme
- **Docker Ready** - One-command deployment

## 🛡️ Safety by Design

XenFlow Mailer is built with deliverability protection as a core feature:

| Protection | Limit | Purpose |
|------------|-------|---------|
| Daily Cap | 500 max | Protect reputation |
| Hourly Cap | 50 max | Avoid triggers |
| Bounce Rate | 10% stops | Auto-protection |
| Warmup | 28 days | Gradual ramp |
| Send Window | 9-5 weekdays | Human-like |

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone <repo-url> && cd xenflow-mailer

# 2. Configure environment
cp env.example .env
# Edit .env with your settings

# 3. Start services
docker-compose up -d

# 4. Access dashboard
open http://localhost:3000
```

## 📚 Documentation

- [**Complete Setup Guide**](SETUP_GUIDE.md) - Full installation instructions
- [**Architecture**](ARCHITECTURE.md) - System design and tech stack
- [**API Documentation**](http://localhost:8000/api/docs) - Interactive API docs

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│              XenFlow Mailer                  │
├─────────────────────────────────────────────┤
│                                              │
│   Dashboard ──► API ──► Celery Workers      │
│   (React)      (FastAPI)  (Email/IMAP)      │
│                    │                         │
│         ┌─────────┴─────────┐               │
│         │                   │                │
│    PostgreSQL            Redis               │
│                                              │
└─────────────────────────────────────────────┘
```

## 📦 Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11 + FastAPI |
| Frontend | React 18 + TypeScript |
| Database | PostgreSQL 15 |
| Queue | Redis + Celery |
| Email | SMTP + IMAP abstraction |
| Container | Docker + Docker Compose |

## 🎨 Dashboard Preview

The enterprise dashboard features:

- 🔴 Red & Black theme for professional appearance
- ✨ Smooth animations with Framer Motion
- 📊 Real-time charts with Recharts
- 🛡️ Safety status indicators
- 📱 Responsive design

## 🔧 Configuration

Key environment variables:

```env
# Safety thresholds
MAX_EMAILS_PER_DAY=200
MAX_EMAILS_PER_HOUR=20
MAX_BOUNCE_RATE=0.05

# Send window
SEND_WINDOW_START_HOUR=9
SEND_WINDOW_END_HOUR=17
DEFAULT_TIMEZONE=America/New_York

# Gmail OAuth (optional)
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-secret
```

## 📧 Supported Providers

- ✅ Gmail (OAuth 2.0)
- ✅ Outlook/Office 365
- ✅ SendGrid
- ✅ Mailgun
- ✅ Amazon SES
- ✅ Any SMTP server

## 🔮 Roadmap (V2)

- [ ] AI-powered reply generation (self-hosted LLM)
- [ ] Intent detection from replies
- [ ] Calendar booking integration
- [ ] CRM synchronization
- [ ] A/B testing for templates

## ⚠️ Important Notes

1. **This is NOT a spam tool** - Use only for legitimate business outreach
2. **Warmup is required** - New accounts must be warmed up gradually
3. **Monitor metrics** - Stop if bounce rate exceeds 5%
4. **Respect unsubscribes** - Always honor opt-out requests immediately

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

Built with ❤️ for deliverability

