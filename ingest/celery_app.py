"""
ingest/celery_app.py
Celery / Temporal Schedule Configuration for EPFO Ingestion & Self-Updating Pipeline.
Coordinates the autonomous daily clock:
- Every 5-15 mins: Conditional 304 probes (ETag / If-Modified-Since)
- 06:00 IST: Full daily Tier 1–4 sweep & scheduled_future rule activations
- 06:15 IST: Stage 4 dual-extractor consensus & shadow-DB auto-promotion
- 06:30 IST: Stage 2 Redis cache refresh & Tier 4 confidence decay
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any

# Mock/standalone Celery schedule dictionary for direct Python & Celery worker consumption
CELERY_BEAT_SCHEDULE = {
    # 1. 5-minute lightweight conditional probes (zero-waste 304 checks)
    "conditional-304-probes": {
        "task": "ingest.tasks.probe_tier1_sources",
        "schedule": 300.0,  # 5 minutes
    },
    # 2. 06:00 IST Daily Full Sweep (00:30 UTC)
    "daily-0600-ist-sweep": {
        "task": "ingest.tasks.run_daily_full_sweep",
        "schedule": "crontab(minute=30, hour=0)",  # 00:30 UTC = 06:00 IST
    },
    # 3. 06:15 IST Auto-Promotion Gate (00:45 UTC)
    "daily-0615-ist-gate": {
        "task": "gate.tasks.run_confidence_gate",
        "schedule": "crontab(minute=45, hour=0)",  # 00:45 UTC = 06:15 IST
    },
    # 4. 06:30 IST Cache Refresh & Decay (01:00 UTC)
    "daily-0630-ist-refresh": {
        "task": "engines.tasks.refresh_caches_and_decay",
        "schedule": "crontab(minute=0, hour=1)",  # 01:00 UTC = 06:30 IST
    },
}


def get_schedule_status() -> Dict[str, Any]:
    """
    Returns the current active autonomous schedule contract.
    """
    return {
        "configured_tasks": list(CELERY_BEAT_SCHEDULE.keys()),
        "daily_sweep_ist": "06:00 IST",
        "gate_auto_promotion_ist": "06:15 IST",
        "engine_refresh_decay_ist": "06:30 IST",
        "conditional_probe_interval_seconds": 300,
        "clock_timezone": "Asia/Kolkata (UTC+05:30)",
    }
