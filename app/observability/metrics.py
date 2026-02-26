from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "rm_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "rm_request_latency_seconds",
    "HTTP request latency in seconds",
    ["path"],
)
CACHE_HITS = Counter(
    "rm_cache_hits_total",
    "Total cache hits",
    ["cache"],
)
CACHE_MISSES = Counter(
    "rm_cache_misses_total",
    "Total cache misses",
    ["cache"],
)
UPSTREAM_ERRORS = Counter(
    "rm_upstream_errors_total",
    "Upstream API errors",
    ["status"],
)
CHARACTERS_PROCESSED = Counter(
    "rm_characters_processed_total",
    "Characters processed from upstream API",
)
