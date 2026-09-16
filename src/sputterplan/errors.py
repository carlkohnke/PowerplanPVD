"""Domain-specific exceptions with actionable messages."""


class SputterPlanError(Exception):
    """Base error for invalid inputs or infeasible plans."""


class ConfigurationError(SputterPlanError):
    """Raised when a configuration is incomplete or inconsistent."""


class ProfileError(SputterPlanError):
    """Raised when a composition profile cannot be parsed or validated."""


class PlanningError(SputterPlanError):
    """Raised when no plan can satisfy the requested settings."""


class OutputError(SputterPlanError):
    """Raised when run outputs cannot be written safely."""
