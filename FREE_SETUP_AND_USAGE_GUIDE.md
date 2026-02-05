## XenFlow Mailer – Free Setup & Usage Guide

This guide shows you how to run XenFlow Mailer **100% locally** using free tools (Docker, free Gmail / free SMTP), and how to use it to send safe outbound campaigns.

---

## 1. What You Get For Free

- **Backend + Frontend**: Run inside free Docker containers on your machine.
- **Database & Queue**: PostgreSQL and Redis run locally in Docker (no paid cloud DB).
- **Email Sending**:
  - Free **Gmail** accounts (respecting Google’s daily limits), or
  - Any **free-tier SMTP** provider (SendGrid/Mailgun/SES trial, etc.).
- **Monitoring**: Free Celery dashboard (Flower) and FastAPI docs, all local.

You only need:
- A computer with **Docker Desktop** installed.
- One or more email accounts (Gmail, Outlook, or SMTP provider).

---

## 2. Prerequisites (All Free)

1. **Install Docker Desktop**
   - Windows: Install Docker Desktop and **enable WSL2**.
   - macOS/Linux: Install Docker from the official site.

2. **Clone or open this project**
   - Make sure you are in the project root folder:
     - Example: `c:\Users\abdmo\OneDrive\Desktop\Email_automation`

3. **Basic terminal**
   - On Windows, you can use **PowerShell** or **Windows Terminal**.

---

## 3. One-Time Environment Setup

1. **Create `.env` file (from example)**

   ```bash
   # From the project root
   cp env.example .env
   ```

   On Windows PowerShell (if `cp` is not available):

   ```powershell
   Copy-Item env.example .env
   ```

2. **Edit `.env`**

   Open `.env` in your editor and at minimum change:

   - `SECRET_KEY` – set to a long random string.
   - `POSTGRES_PASSWORD` – any strong password.

   Keep everything else as default to stay on free/local resources.

---

## 4. Start Everything With Docker (Free Local Stack)

From the project root, run:

```powershell
docker compose up -d --build
```

Then check that services are running:

```powershell
docker compose ps
```

Useful URLs (all local, no external cost):

- **Dashboard (frontend)**: `http://localhost:3000`
- **API docs (backend)**: `http://localhost:8000/api/docs`
- **Task monitor (Flower)**: `http://localhost:5555`

If something fails, see `SETUP_GUIDE.md` → **Troubleshooting**, or run:

```powershell
docker compose logs -f
```

---

## 5. Connect Free Email Accounts

You can use **Gmail**, **Outlook**, or any **SMTP** account. For free setup:

### Option A – Free Gmail (fastest to test)

1. In browser, go to `http://localhost:3000`.
2. Open **Senders** → **Add Sender**.
3. Choose **Gmail** (OAuth).
4. Follow the Google login flow and accept permissions.

Notes:
- Free Gmail typically allows around **500 emails/day** but can be lower.
- XenFlow will **pause** a Gmail sender if Google reports “daily limit exceeded”, and automatically **reactivate** it after the daily reset.

### Option B – Free SMTP Provider (safer for scale)

Use a free-tier SMTP (e.g. SendGrid / Mailgun / SES trial):

1. Create a free account with the provider.
2. Generate an SMTP username & password (usually an API key).
3. In the dashboard: **Senders** → **Add Sender** → **Custom SMTP**.
4. Fill in:
   - SMTP host & port (from provider docs).
   - Username & password (or API key).
   - Enable TLS if recommended.
5. (Optional) Add IMAP details if you want automatic reply detection.

All of this runs against local Docker containers, so you pay **zero** for hosting.

---

## 6. Add Leads for Free (CSV or Manual)

### A. CSV Import

1. Prepare a CSV file like:

   ```csv
   email,name,company,industry,title
   john@example.com,John Smith,Acme Inc,Technology,CEO
   ```

2. Go to **Leads** → **Import CSV**.
3. Upload the CSV, map columns, and import.

### B. Manual Leads

1. Go to **Leads** → **Add Lead**.
2. Enter email, name, and any extra fields.
3. Save.

All data is stored in your **local PostgreSQL** in Docker (no external DB cost).

---

## 7. Create Templates (Personalized But Simple)

1. Go to **Templates** in the dashboard.
2. Click **New Template**.
3. Use placeholders (merged from lead data), for example:

   - **Subject**:
     ```text
     Quick question about {{company}}
     ```
   - **Body** (plain or HTML):
     ```text
     Hi {{name}},

     I noticed {{company}} is doing great work in the {{industry}} space.

     I'd love to share how we've helped similar teams get [specific outcome].
     Would you be open to a 15‑minute call this week?

     Best,
     [Your Name]
     ```

4. Save initial and follow‑up templates as needed.

No extra services are needed; template rendering happens inside your local backend.

---

## 8. Launch a Campaign (End‑to‑End Flow)

1. **Create a campaign**
   - Go to **Campaigns** → **New Campaign**.
   - Choose a connected **Sender** (Gmail/SMTP) or enable **sender rotation** across multiple accounts.
   - Select your **templates** and set **follow‑up steps**.

2. **Attach leads**
   - Assign an existing lead list / segment to the campaign.

3. **Set safety limits**
   - Keep default values OR **lower** daily/hourly caps to stay under Gmail/free provider limits.

4. **Start campaign**
   - Change status to **Active**.
   - The system will:
     - Queue initial emails,
     - Respect send windows & limits,
     - Auto‑stop on reply, bounce, unsubscribe.

Everything runs on your machine only: PostgreSQL, Redis, workers, and UI via Docker.

---

## 9. Monitor & Stay Within Free Limits

- **Dashboard → Analytics**: See sends, opens, replies.
- **Flower (`http://localhost:5555`)**: Inspect tasks and failures.
- **Logs**:
  - `docker compose logs worker` – email sending and rate‑limit logs.
  - `docker compose logs backend` – API errors.

To avoid Gmail suspension / provider issues:
- Keep **daily sends per sender** conservative (e.g. 100–150, not max).
- Add **more senders** instead of pushing a single free Gmail too hard.

---

## 10. Stopping & Restarting (Local Only)

Stop all services (keeps data):

```powershell
docker compose down
```

Restart later:

```powershell
docker compose up -d
```

Data persists in Docker volumes on your machine, so you don’t pay for any cloud storage.

---

You now have a **fully local, free** XenFlow Mailer stack: send safer outbound campaigns using Docker + free email accounts, with full control over limits and deliverability.

