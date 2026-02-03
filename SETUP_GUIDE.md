# XenFlow Mailer - Complete Setup Guide

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Requirements](#requirements)
3. [Quick Start](#quick-start)
4. [Environment Configuration](#environment-configuration)
5. [Gmail OAuth Setup](#gmail-oauth-setup)
6. [Custom SMTP Setup](#custom-smtp-setup)
7. [Adding Leads](#adding-leads)
8. [Creating Templates](#creating-templates)
9. [Follow-up Logic](#follow-up-logic)
10. [Starting & Stopping Services](#starting--stopping-services)
11. [Safety Warnings](#safety-warnings)
12. [Troubleshooting](#troubleshooting)

---

## 🎯 System Overview

XenFlow Mailer is an enterprise-grade, reputation-aware email automation system designed for safe, scalable outbound communication.

### Key Features

- ✅ **Personalized Outreach**: Dynamic templates with placeholders
- ✅ **Automated Follow-ups**: Multi-step sequences with timing control
- ✅ **Provider Agnostic**: Gmail, Outlook, or any SMTP server
- ✅ **Safety First**: Rate limiting, warmup, bounce handling
- ✅ **Full Audit Trail**: Complete email logging
- ✅ **Enterprise Dashboard**: Real-time monitoring and analytics

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    XenFlow Mailer                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Frontend (React) ──► API (FastAPI) ──► Workers (Celery)│
│       ▲                    ▲                    ▲        │
│       │                    │                    │        │
│       └────────────────────┼────────────────────┘        │
│                            │                             │
│              ┌─────────────┴─────────────┐              │
│              │                           │               │
│         PostgreSQL                    Redis              │
│         (Leads, Logs)            (Queue, Cache)          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 💻 Requirements

### System Requirements

- **Docker**: 20.10+ with Docker Compose V2
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk**: 10GB free space
- **OS**: Linux, macOS, or Windows with WSL2

### Software Dependencies (handled by Docker)

- Python 3.11
- Node.js 20
- PostgreSQL 15
- Redis 7

---

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Navigate to your project directory
cd Email_automation

# Copy environment file
cp env.example .env

# Edit .env with your settings
# IMPORTANT: Change SECRET_KEY and POSTGRES_PASSWORD
```

### 2. Start Services

```bash
# Build and start all services
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Access the Dashboard

- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/api/docs
- **Flower (Celery Monitor)**: http://localhost:5555

### 4. Initial Setup Checklist

1. ☐ Configure `.env` file
2. ☐ Add at least one sender (email account)
3. ☐ Create email templates
4. ☐ Import leads
5. ☐ Create and start a campaign

---

## ⚙️ Environment Configuration

### Essential Variables

```env
# REQUIRED: Change these!
SECRET_KEY=generate-a-random-64-character-string
POSTGRES_PASSWORD=your-secure-database-password

# Email Safety (adjust based on your needs)
MAX_EMAILS_PER_DAY=200
MAX_EMAILS_PER_HOUR=20
MAX_BOUNCE_RATE=0.05

# Send Window
SEND_WINDOW_START_HOUR=9
SEND_WINDOW_END_HOUR=17
SEND_WEEKDAYS_ONLY=true
DEFAULT_TIMEZONE=America/New_York
```

### Generating a Secure Secret Key

```bash
# On Linux/macOS
openssl rand -hex 32

# On Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
```

---

## 📧 Gmail OAuth Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable the **Gmail API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"

### Step 2: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Web application"
4. Add authorized redirect URI:
   ```
   http://localhost:8000/api/v1/auth/google/callback
   ```
5. Copy the Client ID and Client Secret

### Step 3: Configure Environment

```env
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

### Step 4: Connect Gmail Account

1. Go to Dashboard → Senders → Add Sender
2. Select "Gmail" as provider
3. Click "Connect with Google"
4. Authorize the application
5. Gmail sender is now ready!

### Important Gmail Notes

- ⚠️ Gmail has strict sending limits (500/day for regular accounts)
- ⚠️ Use Google Workspace for higher limits
- ⚠️ Enable 2-Step Verification on the Gmail account

---

## 🔧 Custom SMTP Setup

### Supported Providers

- SendGrid
- Mailgun
- Amazon SES
- Any SMTP server

### SMTP Configuration

1. Go to Dashboard → Senders → Add Sender
2. Select "Custom SMTP"
3. Enter SMTP details:

```
SMTP Host: smtp.sendgrid.net
SMTP Port: 587
SMTP Username: apikey
SMTP Password: your-api-key
Use TLS: Yes
```

### IMAP Configuration (for Reply Detection)

```
IMAP Host: imap.gmail.com
IMAP Port: 993
IMAP Username: your@email.com
IMAP Password: your-app-password
Use SSL: Yes
Folder: INBOX
```

### Provider-Specific Settings

#### SendGrid
```
SMTP Host: smtp.sendgrid.net
Port: 587 (TLS) or 465 (SSL)
Username: apikey
Password: Your SendGrid API Key
```

#### Mailgun
```
SMTP Host: smtp.mailgun.org
Port: 587
Username: your-domain-smtp-login
Password: Your Mailgun SMTP password
```

#### Amazon SES
```
SMTP Host: email-smtp.us-east-1.amazonaws.com
Port: 587
Username: Your SES SMTP username
Password: Your SES SMTP password
```

---

## 👥 Adding Leads

### Method 1: CSV Import (Recommended)

1. Prepare your CSV file with columns:
   ```csv
   email,name,company,industry,title
   john@example.com,John Smith,Acme Inc,Technology,CEO
   sarah@startup.io,Sarah Jones,Startup.io,SaaS,CTO
   ```

2. Go to Dashboard → Leads → Import CSV
3. Upload your file
4. Map columns to lead fields
5. Click "Import"

### Required CSV Columns

| Column | Required | Description |
|--------|----------|-------------|
| email | Yes | Valid email address |
| name | No | Full name |
| company | No | Company name |
| industry | No | Industry/vertical |
| title | No | Job title |

### Method 2: Manual Entry

1. Go to Dashboard → Leads → Add Lead
2. Fill in the form
3. Click "Save"

### Method 3: API Import

```bash
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "name": "John Smith",
    "company": "Acme Inc",
    "campaign_id": 1
  }'
```

---

## 📝 Creating Templates

### Template Placeholders

Available placeholders:

| Placeholder | Description | Fallback |
|------------|-------------|----------|
| `{{name}}` | First name or display name | "there" |
| `{{first_name}}` | First name | "" |
| `{{last_name}}` | Last name | "" |
| `{{company}}` | Company name | "" |
| `{{industry}}` | Industry | "" |
| `{{title}}` | Job title | "" |
| `{{custom_field}}` | Any custom field | "" |

### Example Initial Template

**Subject:**
```
Quick question about {{company}}
```

**Body:**
```html
Hi {{name}},

I noticed {{company}} is doing great work in the {{industry}} space.

I'd love to share how we've helped similar companies improve their 
[specific outcome]. Would you have 15 minutes this week for a quick call?

Best,
[Your Name]
```

### Example Follow-up Templates

**Follow-up 1 (Day 3):**
```
Subject: Re: Quick question about {{company}}

Hi {{name}},

Just floating this back to the top of your inbox. I know things get busy!

Would love to connect briefly this week if you have time.

Best,
[Your Name]
```

**Follow-up 2 (Day 7):**
```
Subject: Re: Quick question about {{company}}

Hi {{name}},

One last check-in - completely understand if now isn't the right time.

If it would help, I can send over a quick 2-minute video showing 
what I had in mind.

Let me know either way!

[Your Name]
```

### Best Practices

- ✅ Keep emails short (under 150 words)
- ✅ Use plain language, avoid jargon
- ✅ One clear call-to-action
- ✅ Personalize with placeholders
- ✅ Include signature
- ❌ Don't use excessive HTML/images
- ❌ Don't include attachments in cold outreach
- ❌ Don't use spam trigger words

---

## 🔄 Follow-up Logic

### How Follow-ups Work

1. **Initial email** is sent when campaign starts
2. **System waits** for the configured delay (default: 3 days)
3. **Checks for reply/bounce/unsubscribe**
4. If no engagement → sends next follow-up
5. Process repeats until max steps reached

### Timing Rules

```
Campaign Settings:
├── Follow-up Delay: 3 days
├── Max Follow-up Steps: 3
└── Send Window: 9 AM - 5 PM (recipient's timezone)

Timeline:
Day 0: Initial email sent
Day 3: Follow-up #1 (if no reply)
Day 6: Follow-up #2 (if no reply)
Day 9: Follow-up #3 (if no reply)
Day 9+: Sequence complete
```

### Stop Conditions

Follow-ups **automatically stop** when:

- ✅ Lead replies (detected via IMAP)
- ✅ Email bounces (hard or soft after 3 attempts)
- ✅ Lead unsubscribes
- ✅ Lead manually marked as replied
- ✅ Max follow-up steps reached
- ✅ Campaign paused/stopped

### Configuring Follow-ups

1. Go to Campaign → Follow-up Templates
2. Add template for each step
3. Configure delay (days + hours)
4. Enable/disable individual steps

---

## ▶️ Starting & Stopping Services

### Start All Services

```bash
# Start everything
docker-compose up -d

# Start specific service
docker-compose up -d backend
```

### Stop Services

```bash
# Stop all (keeps data)
docker-compose stop

# Stop and remove containers (keeps volumes)
docker-compose down

# Stop and remove EVERYTHING (including data!)
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f worker
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific
docker-compose restart worker
```

### Scale Workers

```bash
# Run 3 email workers
docker-compose up -d --scale worker=3
```

---

## ⚠️ Safety Warnings

### THIS IS NOT A SPAM TOOL

XenFlow Mailer is designed for **legitimate business outreach**, not bulk spam. Misuse will:

- ❌ Destroy your sender reputation
- ❌ Get your domain blacklisted
- ❌ Get your email accounts suspended
- ❌ Potentially violate laws (CAN-SPAM, GDPR)

### Hard Safety Limits

These limits **cannot be exceeded**:

| Limit | Value | Purpose |
|-------|-------|---------|
| Max emails/day | 500 | Protect sender reputation |
| Max emails/hour | 50 | Avoid spam triggers |
| Max bounce rate | 10% | System auto-stops |
| Max complaint rate | 0.5% | System auto-stops |
| Min send interval | 30 seconds | Human-like behavior |

### Warmup is Non-Negotiable

New email accounts MUST be warmed up:

| Day | Daily Limit |
|-----|-------------|
| 1-3 | 10 emails |
| 4-7 | 25 emails |
| 8-14 | 50 emails |
| 15-21 | 75 emails |
| 22-28 | 100 emails |
| 29+ | Full limit |

### Email Best Practices

1. **Clean your list** - Remove invalid emails before importing
2. **Get permission** - Only email people who expect to hear from you
3. **Provide value** - Don't just sell, offer something useful
4. **Include unsubscribe** - Always honor opt-outs immediately
5. **Monitor metrics** - Stop if bounce rate exceeds 5%

---

## 🔧 Troubleshooting

### Common Issues

#### Container won't start
```bash
# Check logs
docker-compose logs backend

# Rebuild
docker-compose build --no-cache backend
docker-compose up -d
```

#### Database connection failed
```bash
# Check database is running
docker-compose ps db

# Check logs
docker-compose logs db

# Restart database
docker-compose restart db
```

#### Emails not sending
1. Check worker logs: `docker-compose logs worker`
2. Verify sender credentials
3. Check rate limits in dashboard
4. Ensure campaign is "active"

#### IMAP not detecting replies
1. Check IMAP worker: `docker-compose logs worker_imap`
2. Verify IMAP credentials
3. Check IMAP folder settings (usually "INBOX")
4. For Gmail, ensure "Less secure apps" or use App Password

#### Gmail OAuth errors
1. Verify Client ID and Secret
2. Check redirect URI matches exactly
3. Ensure Gmail API is enabled
4. Try re-authorizing the account

### Getting Help

1. Check logs: `docker-compose logs -f`
2. Check API health: `curl http://localhost:8000/health`
3. Check worker status: http://localhost:5555 (Flower)
4. Review this guide thoroughly

---

## 📊 Quick Reference

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/campaigns` | GET/POST | List/create campaigns |
| `/api/v1/leads` | GET/POST | List/create leads |
| `/api/v1/leads/import` | POST | Import CSV |
| `/api/v1/templates` | GET/POST | List/create templates |
| `/api/v1/senders` | GET/POST | List/create senders |
| `/api/v1/analytics/dashboard` | GET | Dashboard stats |

### Ports

| Service | Port | URL |
|---------|------|-----|
| Dashboard | 3000 | http://localhost:3000 |
| API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/api/docs |
| Flower | 5555 | http://localhost:5555 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |

### Key Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f [service]

# Restart
docker-compose restart [service]

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

---

**XenFlow Mailer v1.0** - Built for deliverability, designed for scale.

For V2 features (AI replies, calendar booking), stay tuned!


docker-compose up -d
Rebuild and restart services:
docker-compose build && docker-compose up -d
Or rebuild specific services (backend and frontend):
docker-compose build backend frontend && docker-compose up -d
Or rebuild without cache (if needed):
docker-compose build --no-cache backend frontend && docker-compose up -d
View logs after building:
docker-compose logs -f backend frontend
