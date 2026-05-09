"""Shared runtime error types for LTC."""


class FatalRuntimeError(RuntimeError):
    """Errors that should stop the current run immediately."""


class ProductionModelRequiredError(FatalRuntimeError):
    """Raised when a production-only run is attempted with a smoke model."""
