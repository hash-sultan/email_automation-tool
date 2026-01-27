# Campaign Limits Guide

## Overview

Each campaign has configurable rate limits that help you:
- **Control sending speed** for warmup of new email accounts
- **Customize per campaign** based on your sender's reputation
- **Reach your goals** (e.g., 200/day = 1000 emails in 5 days)

## Default Settings (New Campaigns)

When you create a new campaign, the defaults are:

- **Daily Limit**: 200 emails/day
- **Hourly Limit**: 25 emails/hour
- **Send Window**: 24/7 (00:00 - 23:59)
- **Weekdays Only**: Disabled (sends on weekends too)

### Why 200/day?

- **1000 emails in 5 days**: 200 × 5 = 1000 emails
- **Safe for warmup**: Good starting point for new email accounts
- **Within provider limits**: Gmail free accounts allow 500/day

## Campaign Limits Explained

### Daily Limit
- **Range**: 1 - 500 emails/day
- **Default**: 200 emails/day
- **Purpose**: Maximum emails this campaign can send per day
- **Calculation**: 200/day = ~8.3 emails/hour (24/7) or ~25 emails/hour (8-hour window)

### Hourly Limit
- **Range**: 1 - 100 emails/hour
- **Default**: 25 emails/hour
- **Purpose**: Maximum emails this campaign can send per hour
- **Note**: Must be less than or equal to daily_limit ÷ 24

### Send Window
- **Default**: 00:00 - 23:59 (24/7)
- **Customizable**: Set start and end times
- **Purpose**: Only send emails during these hours
- **Example**: 9 AM - 5 PM for business hours

### Weekdays Only
- **Default**: Disabled (sends on weekends)
- **When enabled**: Only sends Monday-Friday
- **When disabled**: Sends 7 days a week

## Recommended Settings by Scenario

### New Email Account (Warmup)
```
Daily Limit: 50-100 emails/day
Hourly Limit: 5-10 emails/hour
Send Window: 9 AM - 5 PM
Weekdays Only: Enabled
```
**Why**: Gradual warmup protects sender reputation

### Established Account (Normal)
```
Daily Limit: 200 emails/day
Hourly Limit: 25 emails/hour
Send Window: 24/7 (00:00 - 23:59)
Weekdays Only: Disabled
```
**Why**: Balanced speed and safety

### High-Volume Campaign
```
Daily Limit: 400-500 emails/day
Hourly Limit: 50-100 emails/hour
Send Window: 24/7 (00:00 - 23:59)
Weekdays Only: Disabled
```
**Why**: Maximum throughput (requires good sender reputation)

## How Limits Work Together

1. **Daily limit** is checked first - if reached, no more emails today
2. **Hourly limit** is checked second - if reached, wait until next hour
3. **Send window** restricts when emails can be sent
4. **Weekdays only** skips weekends if enabled

### Example Calculation

**Campaign with 200/day, 25/hour, 24/7 window:**
- Can send 25 emails in hour 1
- Can send 25 emails in hour 2
- ...continues for 8 hours = 200 emails
- Then stops until next day (daily limit reached)

## Global Limits (System-Wide)

These are hard limits that cannot be exceeded:

- **Absolute Maximum Daily**: 500 emails/day per sender
- **Absolute Maximum Hourly**: 50 emails/hour per sender
- **Minimum Interval**: 30 seconds between emails (hard limit)

## Multiple Campaigns

If you run multiple campaigns with the same sender:

- **Shared daily limit**: All campaigns share the sender's daily limit
- **Example**: Sender limit = 500/day
  - Campaign 1: 200/day
  - Campaign 2: 200/day
  - Campaign 3: 100/day
  - Total: 500/day (matches sender limit)

## Tips for Success

1. **Start conservative**: Use lower limits for new accounts
2. **Monitor bounce rates**: If bounces increase, lower limits
3. **Gradual increase**: Increase limits over time as reputation improves
4. **Different limits per campaign**: Use lower limits for warmup campaigns
5. **Respect provider limits**: Gmail = 500/day, Outlook = 10,000/day

## Time to Send 1000 Emails

| Daily Limit | Days Needed | Notes |
|-------------|-------------|-------|
| 50/day | 20 days | Very conservative (warmup) |
| 100/day | 10 days | Conservative |
| 200/day | 5 days | **Default** - Balanced |
| 300/day | 3.3 days | Aggressive |
| 500/day | 2 days | Maximum (Gmail limit) |

## FAQ

**Q: Can I change limits after creating a campaign?**
A: Yes, you can update campaign settings, but be careful not to exceed provider limits.

**Q: What happens if I set daily limit to 500 but sender limit is 200?**
A: The campaign will be limited to 200/day (the sender's limit).

**Q: Can I send faster than 30 seconds between emails?**
A: No, 30 seconds is a hard minimum for safety.

**Q: Do limits reset at midnight?**
A: Yes, daily limits reset at midnight in the campaign's timezone.

**Q: What if I have multiple campaigns with the same sender?**
A: They share the sender's daily limit. Plan accordingly.

