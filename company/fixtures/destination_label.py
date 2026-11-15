"""Synthetic, non-production public travel label fixture for the AI department."""


def destination_label(title):
    """Normalize whitespace in a synthetic public destination label."""
    return " ".join(title.split())
