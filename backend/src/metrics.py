from prometheus_client import Counter, Gauge


PIXELS_PLACED = Counter(
    "pixel_canvas_pixels_placed_total",
    "Total number of pixels placed on the canvas",
    ["color"]
)

SNAPSHOTS_TAKEN = Counter(
    "pixel_canvas_snapshots_taken_total",
    "Total number of snapshots taken of the canvas"
)

ACTIVE_CONNECTIONS = Gauge(
    "pixel_canvas_active_connections",
    "Current number of active WebSocket connections"
)
