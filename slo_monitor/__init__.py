"""SLO & Error Budget Monitor.

A small synthetic-monitoring tool that checks public API endpoints on a schedule,
computes rolling uptime and error-budget burn against a configured SLO target, and
automatically files GitHub Issues (incidents and proactive budget warnings) so that
nobody has to notice problems manually.
"""

__version__ = "0.1.0"
