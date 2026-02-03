Email sending limits and delays (OPTIMIZED FOR SENDER ROTATION)

1. Hourly limits
Status: Configured but not enforced by the rate limiter
Campaign level: Each campaign has an hourly_limit (default: 50/hour)
Database check: The Campaign.can_send_now property checks hourly limits
Rate limiter: The Redis rate limiter ignores hourly limits (MAX_EMAILS_PER_HOUR = 999999)
Reset: Hourly counters reset every hour via Celery task reset_hourly_counters_task
Current behavior:
Campaigns track emails_this_hour, but the Redis rate limiter only enforces daily limits
Hourly limits are checked in the campaign model but not strictly enforced by the rate limiter

2. Adaptive delays between emails (OPTIMIZED)
The system uses adaptive delays and batch pauses based on the number of senders in rotation:

Single Sender (no rotation):
- Minimum interval: 10 seconds between emails
- Batch size: 50 emails before pause
- Batch pause: 10 minutes
- Pattern: Email 1 → Wait 10s → Email 2 → ... → Email 50 → Wait 10min → Email 51...

Two Senders (rotation):
- Minimum interval: 7 seconds between emails (per sender)
- Batch size: 75 emails before pause (per sender)
- Batch pause: 7 minutes (per sender)
- Pattern: Sender 1 sends 75 emails → pauses 7min, while Sender 2 continues sending

Three+ Senders (rotation):
- Minimum interval: 5 seconds between emails (per sender)
- Batch size: 100 emails before pause (per sender)
- Batch pause: 5 minutes (per sender)
- Pattern: If Sender 1 pauses after 100 emails, Senders 2 and 3 continue independently

Key Features:
- Per-sender batch pause: Each sender has independent batch tracking
- If one sender pauses, other senders in rotation continue sending
- Adaptive settings automatically adjust based on rotation count
- Enforcement: Redis rate limiter tracks per-sender:
  * last_send_time — ensures adaptive minimum interval (per sender)
  * batch_count — counts emails in current batch (per sender)
  * batch_pause_end — timestamp when pause ends (per sender)
3. Daily limits
Sender daily limit: Max 500/day per sender (hard cap in SafetyLimits.ABSOLUTE_MAX_EMAILS_PER_DAY)
Campaign daily limit: Configurable per campaign (default: 200/day)
Warmup adjustment: If warmup is enabled, sender's current_daily_limit is adjusted based on warmup day
Enforcement: Redis rate limiter enforces both sender and campaign daily limits

With sender rotation:
- Total daily capacity = number of senders × 500/day
- Example: 3 senders = 1,500 emails/day potential capacity
- Each sender independently tracks their daily limit
Warmup feature
How it works:
Gradually increases sending capacity over 28+ days to protect sender reputation.
Warmup schedule:
Day 1-3:   10 emails/dayDay 4-7:   25 emails/dayDay 8-14:  50 emails/dayDay 15-21: 75 emails/dayDay 22-28: 100 emails/dayDay 29+:   150 emails/day (or base_daily_limit, whichever is lower)
How warmup is applied:
When enabled: When a sender is created/activated with warmup_enabled=True
Start date: warmup_start_date is set to today
Daily updates: Celery Beat task update_warmup_task runs at midnight to:
Calculate current warmup day
Update current_daily_limit based on schedule
Mark warmup complete after day 29 if limit reaches base_daily_limit
Limit usage: The sender’s current_daily_limit (not base_daily_limit) is used by the rate limiter
Warmup states:
warmup_enabled = True + warmup_start_date = None: Pending (not started)
warmup_enabled = True + warmup_start_date = Date: In progress
warmup_enabled = False: Completed or skipped
Warmup controls:
Start: Automatically starts when sender is activated (if enabled)
Skip: skip_warmup_task — immediately uses base_daily_limit (use with caution)
Reset: reset_warmup_task — restarts from day 1
How everything works together
Sending flow (with adaptive rotation):
1. Email task queued → send_email_task
2. Calculate rotation count → Number of senders in campaign rotation
3. Rate limiter check → RateLimiter.check_rate_limit():
   - Uses adaptive minimum interval based on rotation (5s/7s/10s)
   - Checks per-sender batch pause (if batch size reached for that sender)
   - Checks sender daily limit (uses current_daily_limit if warmup enabled)
   - Checks campaign daily limit
4. If allowed: Email sent, counters updated with adaptive batch tracking
5. If rate limited: Task retries after calculated wait time

Example scenario (3 senders rotating):
- Sender 1: current_daily_limit = 200, warmup Day 10
- Sender 2: current_daily_limit = 200, warmup Day 8
- Sender 3: current_daily_limit = 150, warmup Day 5
- Campaign daily_limit = 500
- Rotation count: 3

Sending attempt (using Sender 1):
1. Check: 5 seconds since last email from Sender 1? ✓ (adaptive: 3 senders = 5s)
2. Check: Sender 1 in batch pause? (if 100 emails sent from Sender 1) ✓
3. Check: Sender 1 daily < 200? ✓
4. Check: Campaign daily < 500? ✓
5. Send email → Record in Redis → Increment Sender 1's batch count
6. If Sender 1 reaches 100 emails → Sender 1 pauses 5min, Senders 2 & 3 continue

Important notes
✅ Adaptive delays: Automatically adjust based on rotation count (5s/7s/10s)
✅ Per-sender batch pause: Each sender pauses independently, others continue
✅ Adaptive batch sizes: 50/75/100 emails based on rotation count
✅ Adaptive pause duration: 5min/7min/10min based on rotation count
✅ Hourly limits: Tracked but not enforced by the rate limiter. Only daily limits are enforced.
✅ Warmup: Automatically adjusts current_daily_limit daily. The rate limiter uses this adjusted limit.
✅ Hard caps: 500/day per sender (cannot be exceeded even if warmup allows more).
✅ Rotation benefits: With 3 senders, ~12 emails/minute vs ~6 emails/minute with 1 sender