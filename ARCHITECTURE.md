# XenFlow Mailer - System Architecture (V1)

## 📊 Architecture Diagram (Textual)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              XENFLOW MAILER V1                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        FRONTEND DASHBOARD                                │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │   │
│  │  │  Campaigns  │ │   Leads     │ │  Analytics  │ │  Settings   │       │   │
│  │  │   Overview  │ │  Management │ │   Metrics   │ │   Panel     │       │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │   │
│  │                     React + Framer Motion (Red/Black Theme)              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                          API GATEWAY (FastAPI)                           │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │   │
│  │  │  Campaign   │ │    Lead     │ │  Template   │ │   Sender    │       │   │
│  │  │  Endpoints  │ │  Endpoints  │ │  Endpoints  │ │  Endpoints  │       │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    SAFETY MIDDLEWARE                              │   │   │
│  │  │  • Rate Limit Guard  • Reputation Monitor  • Threshold Checks    │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                    ┌─────────────────┼─────────────────┐                       │
│                    ▼                 ▼                 ▼                        │
│  ┌─────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐          │
│  │   PostgreSQL DB     │ │   Redis Queue   │ │   Email Services    │          │
│  │  ┌───────────────┐  │ │  ┌───────────┐  │ │  ┌───────────────┐  │          │
│  │  │    leads      │  │ │  │  outbound │  │ │  │ SMTP Provider │  │          │
│  │  │   campaigns   │  │ │  │   queue   │  │ │  │  Abstraction  │  │          │
│  │  │   templates   │  │ │  ├───────────┤  │ │  ├───────────────┤  │          │
│  │  │  email_logs   │  │ │  │ follow-up │  │ │  │  Gmail OAuth  │  │          │
│  │  │   senders     │  │ │  │   queue   │  │ │  │  Outlook      │  │          │
│  │  │ suppressions  │  │ │  ├───────────┤  │ │  │  Custom SMTP  │  │          │
│  │  └───────────────┘  │ │  │  warmup   │  │ │  └───────────────┘  │          │
│  └─────────────────────┘ │  │   queue   │  │ │  ┌───────────────┐  │          │
│                          │  └───────────┘  │ │  │ IMAP Listener │  │          │
│                          └─────────────────┘ │  │  (Replies &   │  │          │
│                                              │  │   Bounces)    │  │          │
│                                              │  └───────────────┘  │          │
│                                              └─────────────────────┘          │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         BACKGROUND WORKERS                               │   │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐           │   │
│  │  │  Email Worker   │ │ Follow-up Worker│ │  IMAP Monitor   │           │   │
│  │  │  • Send emails  │ │ • Check timing  │ │ • Reply detect  │           │   │
│  │  │  • Rate limit   │ │ • Queue next    │ │ • Bounce detect │           │   │
│  │  │  • Log results  │ │ • Stop on reply │ │ • Auto-suppress │           │   │
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘           │   │
│  │                                                                          │   │
│  │  ┌─────────────────┐ ┌─────────────────┐                                │   │
│  │  │  Warmup Worker  │ │ Scheduler Worker│                                │   │
│  │  │  • Gradual ramp │ │ • Time windows  │                                │   │
│  │  │  • Daily limits │ │ • Timezone aware│                                │   │
│  │  │  • Safety caps  │ │ • Weekday logic │                                │   │
│  │  └─────────────────┘ └─────────────────┘                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

## 🔄 Data Flow

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Import  │───▶│  Queue   │───▶│  Rate    │───▶│  Send    │───▶│  Log     │
│  Leads   │    │  Email   │    │  Limit   │    │  Email   │    │  Result  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                                      │
                     ┌────────────────────────────────────────────────┘
                     ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  IMAP    │───▶│  Detect  │───▶│  Update  │───▶│  Stop/   │
│  Monitor │    │  Reply   │    │  Lead    │    │  Continue│
└──────────┘    └──────────┘    └──────────┘    └──────────┘

## 🛡️ Safety Architecture

```
                    ┌─────────────────────────────────────┐
                    │         SAFETY LAYER                 │
                    ├─────────────────────────────────────┤
                    │                                      │
                    │  ┌─────────────────────────────┐    │
                    │  │    THRESHOLD GUARDS          │    │
                    │  │  • Max emails/day: 50-200   │    │
                    │  │  • Max emails/hour: 10-20   │    │
                    │  │  • Bounce rate < 5%         │    │
                    │  │  • Complaint rate < 0.1%    │    │
                    │  └─────────────────────────────┘    │
                    │                                      │
                    │  ┌─────────────────────────────┐    │
                    │  │    AUTO-SUPPRESSION          │    │
                    │  │  • Hard bounces → block     │    │
                    │  │  • Unsubscribes → block     │    │
                    │  │  • Complaints → block       │    │
                    │  │  • 3+ soft bounces → block  │    │
                    │  └─────────────────────────────┘    │
                    │                                      │
                    │  ┌─────────────────────────────┐    │
                    │  │    WARMUP PROTECTION         │    │
                    │  │  Day 1-3:  10 emails/day    │    │
                    │  │  Day 4-7:  25 emails/day    │    │
                    │  │  Day 8-14: 50 emails/day    │    │
                    │  │  Day 15+:  100 emails/day   │    │
                    │  └─────────────────────────────┘    │
                    │                                      │
                    └─────────────────────────────────────┘
```

## 📦 Tech Stack Justification

### Backend: Python + FastAPI
- **Why**: Async-native, excellent performance, automatic OpenAPI docs
- **V2 Ready**: Easy integration with Python ML/LLM libraries
- **Battle-tested**: Used by Microsoft, Netflix, Uber for high-throughput APIs

### Database: PostgreSQL
- **Why**: ACID compliance, excellent for relational lead data
- **V2 Ready**: Supports JSON columns for flexible AI metadata
- **Scalability**: Handles millions of leads with proper indexing

### Queue: Redis + Celery
- **Why**: Proven distributed task queue, retry logic, scheduling
- **V2 Ready**: Can handle AI inference queues
- **Reliability**: Persistent tasks, graceful failure handling

### Email: Custom Abstraction Layer
- **Why**: Provider-agnostic design supports Gmail, Outlook, any SMTP
- **Safety**: Centralized rate limiting, header management
- **Flexibility**: Easy to add new providers

### Frontend: React + Framer Motion
- **Why**: Component-based, excellent animation support
- **V2 Ready**: Easy to add AI dashboards, real-time updates
- **Enterprise**: Professional UI libraries available

### Containerization: Docker Compose
- **Why**: One-command deployment, isolated services
- **Production**: Same setup works locally and in cloud
- **Scalability**: Easy to scale individual services

## 🔮 V2 Extension Points (Design Only)

```
┌─────────────────────────────────────────────────────────────────┐
│                    V2 EXTENSION HOOKS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  AI REPLY SYSTEM (V2)                                    │   │
│  │  • Interface: AIReplyGenerator                           │   │
│  │  • Hook: on_reply_detected(email, context) → response    │   │
│  │  • Queue: ai_reply_queue (Redis)                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  INTENT DETECTION (V2)                                   │   │
│  │  • Interface: IntentClassifier                           │   │
│  │  • Hook: classify_intent(email_body) → intent_type       │   │
│  │  • Types: interested, not_interested, question, booking  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  CALENDAR BOOKING (V2)                                   │   │
│  │  • Interface: CalendarIntegration                        │   │
│  │  • Hook: check_availability(datetime_range) → slots      │   │
│  │  • Hook: create_booking(slot, lead) → confirmation       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  CRM SYNC (V2)                                           │   │
│  │  • Interface: CRMConnector                               │   │
│  │  • Hook: sync_lead(lead_data) → crm_id                   │   │
│  │  • Hook: update_crm_status(crm_id, status)               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
xenflow-mailer/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application
│   │   ├── config.py               # Environment configuration
│   │   ├── database.py             # Database connection
│   │   │
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── lead.py
│   │   │   ├── campaign.py
│   │   │   ├── template.py
│   │   │   ├── sender.py
│   │   │   ├── email_log.py
│   │   │   └── suppression.py
│   │   │
│   │   ├── schemas/                # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── lead.py
│   │   │   ├── campaign.py
│   │   │   ├── template.py
│   │   │   └── analytics.py
│   │   │
│   │   ├── api/                    # API routes
│   │   │   ├── __init__.py
│   │   │   ├── leads.py
│   │   │   ├── campaigns.py
│   │   │   ├── templates.py
│   │   │   ├── senders.py
│   │   │   └── analytics.py
│   │   │
│   │   ├── services/               # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── email_service.py    # Email abstraction layer
│   │   │   ├── rate_limiter.py     # Rate limiting engine
│   │   │   ├── warmup_engine.py    # Warmup logic
│   │   │   ├── followup_engine.py  # Follow-up scheduler
│   │   │   ├── reply_detector.py   # IMAP reply detection
│   │   │   ├── bounce_handler.py   # Bounce classification
│   │   │   └── suppression.py      # Auto-suppression
│   │   │
│   │   ├── workers/                # Celery workers
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py
│   │   │   ├── email_worker.py
│   │   │   ├── followup_worker.py
│   │   │   ├── imap_worker.py
│   │   │   └── warmup_worker.py
│   │   │
│   │   ├── providers/              # Email providers
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Abstract base provider
│   │   │   ├── gmail.py            # Gmail OAuth + SMTP
│   │   │   ├── outlook.py          # Outlook provider
│   │   │   └── smtp.py             # Generic SMTP
│   │   │
│   │   └── utils/                  # Utilities
│   │       ├── __init__.py
│   │       ├── template_renderer.py
│   │       ├── csv_importer.py
│   │       └── logger.py
│   │
│   ├── tests/
│   ├── alembic/                    # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── styles/
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
├── SETUP_GUIDE.md
└── README.md
```

---
**XenFlow Mailer V1** - Built for deliverability, designed for scale.

