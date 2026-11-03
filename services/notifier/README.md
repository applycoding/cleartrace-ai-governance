# ClearTrace notifier

Alerts, signed CloudEvents webhooks (HMAC, retry with exponential backoff, max seven attempts), ticket deduplication, dead-letter queue entries for permanent webhook failures, and EN/FR digests.

Mount routes from the core API when integrated:

```python
from cleartrace_notifier.router import register_notifier_routes

register_notifier_routes(app)
```
