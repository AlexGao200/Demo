from typing import Union, Literal, TypeVar, override, Any
from dataclasses import dataclass

_T = TypeVar("_T")


@dataclass
class ProviderResponse:
    """Standardized response across providers"""

    content: str
    total_tokens: int
    input_tokens: int = 0  # Track input tokens for billing
    output_tokens: int = 0  # Track output tokens for billing
    raw_response: Any = None


# Sentinel class used until PEP 0661 is accepted
class NotGiven:
    """
    A sentinel singleton class used to distinguish omitted keyword arguments
    from those passed in with the value None (which may have different behavior).

    For example:

    ```py
    def get(timeout: Union[int, NotGiven, None] = NotGiven()) -> Response: ...

    get(timeout=1) # 1s timeout
    get(timeout=None) # No timeout
    get() # Default timeout behavior, which may not be statically known at the method definition.
    ```
    """

    def __bool__(self) -> Literal[False]:
        return False

    @override
    def __repr__(self) -> str:
        return "NOT_GIVEN"


NotGivenOr = Union[_T, NotGiven]
NOT_GIVEN = NotGiven()
