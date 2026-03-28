"""Re-exports domain models for backward compatibility."""

from backend.domain.prospect import Prospect, ProspectStatus

__all__ = ["Prospect", "ProspectStatus"]
