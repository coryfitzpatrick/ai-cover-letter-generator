"""Logging configuration for the cover letter generator."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name: Name of the module (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"cover_letter_generator.{name}")
