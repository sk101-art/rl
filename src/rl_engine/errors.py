class ContractError(ValueError):
    """The supplied artifact does not satisfy a frozen contract."""


class ConflictError(RuntimeError):
    """The same stable identifier was reused with different content."""


class NotEligibleError(RuntimeError):
    """A completed outcome is not safe to add to the reusable registry."""
