from __future__ import annotations

DOMAIN = "marstek_venus_local"

CONF_LOOP_INTERVAL = "loop_interval"
CONF_ES_STATUS_INTERVAL = "es_status_interval"
CONF_BAT_STATUS_INTERVAL = "bat_status_interval"
CONF_ES_MODE_INTERVAL = "es_mode_interval"
CONF_MIN_REQUEST_GAP = "min_request_gap"
CONF_UDP_TIMEOUT = "udp_timeout"

DEFAULT_PORT = 30000

# Coordinator tick (seconds). Each tick performs at most ONE UDP request (if due).
DEFAULT_LOOP_INTERVAL = 2

# Per-method fetch intervals (seconds)
DEFAULT_ES_STATUS_INTERVAL = 30
DEFAULT_BAT_STATUS_INTERVAL = 60
DEFAULT_ES_MODE_INTERVAL = 600  # 10 minutes

# Minimum time between UDP requests (seconds)
DEFAULT_MIN_REQUEST_GAP = 2

# UDP socket timeout (seconds)
DEFAULT_UDP_TIMEOUT = 2.0
