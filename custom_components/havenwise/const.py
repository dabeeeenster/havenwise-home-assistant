"""Constants for the Havenwise integration."""

from datetime import timedelta

DOMAIN = "havenwise"

PLATFORMS = [
    "climate",
    "water_heater",
    "sensor",
    "switch",
    "binary_sensor",
]

SCAN_INTERVAL = timedelta(minutes=5)

MANUFACTURER = "Havenwise"
