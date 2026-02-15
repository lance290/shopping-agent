"""Shared constants for sourcing module."""

# Sources that don't provide price data or have dynamic pricing
# These are exempt from strict price filtering
NON_SHOPPING_SOURCES = {
    "google_cse",
    "vendor_directory",
    "wattdata",  # Service provider mock
}

# Service providers that specifically don't have fixed prices
SERVICE_SOURCES = {
    "wattdata",
    "vendor_directory",
}
