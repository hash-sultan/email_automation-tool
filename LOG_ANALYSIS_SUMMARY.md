# Log Analysis Summary – Campaign Stuck & Senders Inactive

**Date:** 2026-02-04  
**Checked:** Worker logs, Beat schedule, email_service and warmup_worker behavior.

---

## 1. Why the campaign is stuck (no emails sending)

From the **worker logs**:

- **Gmail daily sending limit exceeded** for the senders used by the campaign.
- **xenflowtech@gmail.com** (sender id 10) and **saad.ai.solutions@gmail.com** (sender id 3) are **paused** because Gmail returns:
  - `550 5.4.5 Daily user sending limit exceeded`
- The campaign has **8 senders in rotation**. In the logs we see:
  - Both xenflowtech and saad.ai.solutions are **skipped** as “Skipping paused sender”.
  - Then **“Sender daily limit reached: 200/200”** and **“Rate limited, wait 25794s”** (~7.2 hours).
- So in practice **no sender is eligible**: either paused (Gmail limit) or at app daily limit (200/200). The worker keeps retrying with “Retry in 3600s” and the campaign appears stuck.

**Conclusion:** The campaign is stuck because **all rotation senders are either paused (Gmail limit) or at their app daily limit**, so every send attempt is rate-limited and retried every hour until the next day.

---

## 2. Why xenflowtech@gmail.com and saad.ai.solutions@gmail.com “become inactive again and again”

They are not broken; they are **intentionally paused** when they hit Gmail’s daily limit:

1. **When limit is hit:**  
   In `email_service.py`, when Gmail returns the “Daily user sending limit exceeded” error, the code sets:
   - `sender.status = SenderStatus.PAUSED`
   - and logs: `"Pausing sender X (email) due to Gmail daily limit"`.

2. **Why it repeats:**  
   - Next **midnight (UTC)**, the Celery Beat task **`update_warmup_task`** runs.  
   - In `warmup_worker.py`, that task **reactivates all PAUSED senders** and resets daily stats:
     - `if sender.status == SenderStatus.PAUSED: sender.status = SenderStatus.ACTIVE`
   - So the next day they send again until they hit Gmail’s limit → they get **paused again** → same cycle.

So “inactive again and again” = **paused by design when Gmail’s daily limit is reached**, then **automatically reactivated at midnight**. It’s a repeating loop: send → hit limit → pause → midnight reactivation → send again.

---

## 3. What you can do

### A. Stay under Gmail’s limit (recommended)

- Gmail (consumer) is often **500 emails/day**; Google Workspace can be **2000/day** (or lower per account).
- Your app allows up to **200/day per sender** (`Sender daily limit reached: 200/200`). If you’re also sending from the same accounts elsewhere, or if Gmail’s actual limit is lower, you’ll hit the 550 error and get paused.
- **Action:**  
  - Lower **per-sender daily limits** in the app (e.g. to **150–180**) so you pause *before* Gmail does.  
  - Or add more sender accounts and spread volume so no single account hits Gmail’s limit.

### B. Confirm midnight reactivation

- Beat runs **`update_warmup_task`** at **00:05 UTC** (see `celery_app.py`: `crontab(hour=0, minute=5)`).
- That task resets daily stats and sets all **PAUSED** senders back to **ACTIVE**.
- If your “inactive” senders are **PAUSED** (not DISCONNECTED), they should become active again after that run. You can check worker logs around midnight UTC for:  
  `"Reactivated sender X (email) after daily reset"`.

### C. Manual reactivation (one-off)

- If you need xenflowtech or saad.ai.solutions active **before** midnight:  
  - In the app, open the sender and set status back to **Active** (or use the “Test connection” / “Reactivate” flow if your UI has it).  
  - Be aware they will only send until they hit Gmail’s limit again, then get paused again.

### D. Reduce pointless retries (optional code change)

- Right now, when **no sender is available** (all paused or at limit), each task **retries every 3600s** for hours. You could change behavior so that when the rate limiter returns “no eligible sender” (and it’s a global limit, not a temporary wait), the task **fails** (or retries only once much later) instead of retrying every hour. That would reduce queue load and make “campaign stuck” easier to see in the UI.

---

## 4. Quick reference from logs

| Log message | Meaning |
|-------------|--------|
| `Pausing sender X (xenflowtech@gmail.com) due to Gmail daily limit` | That sender hit Gmail’s daily limit and was set to PAUSED. |
| `Skipping paused sender 10 (xenflowtech@gmail.com)` | Sender is PAUSED so not used for this send. |
| `Sender daily limit reached: 200/200` | Some sender in rotation has reached the app’s daily cap (200). |
| `Rate limited, wait 25926s (rotation: 8 senders)` | No eligible sender; system says wait ~7.2 hours (until next day). |
| `Retry in 3600s` | Celery is retrying the send task in 1 hour. |

---

## 5. Commands used to inspect

```powershell
# Worker logs (where send attempts and pauses appear)
docker compose logs worker --tail=300

# Beat schedule (when wake and warmup run)
docker compose logs beat --tail=150
```

Relevant code:

- **Pause on Gmail limit:** `backend/app/services/email_service.py` (e.g. around 628–644).  
- **Reactivate at midnight:** `backend/app/workers/warmup_worker.py` – `update_warmup_task` (e.g. 39–45).  
- **Sender selection (skipping paused):** `backend/app/services/email_service.py` – `_choose_sender_for_campaign` (e.g. 729–736).

