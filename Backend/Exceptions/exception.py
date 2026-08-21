"""
Application-specific exception hierarchy for the AI Travel Planner.

Rules:

- Never use exceptions as workflow state.
- Log the exception at the boundary where it occurs.
- Raise specific exceptions instead of generic Exception where possible.
- Preserve the original exception using ``raise ... from exc``.
"""


class TravelPlannerError(Exception):
    """Base exception for the entire application."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ==========================================================
# Configuration
# ==========================================================

class ConfigurationError(TravelPlannerError):
    """Raised when application configuration is invalid."""

    pass


# ==========================================================
# LLM
# ==========================================================

class LLMError(TravelPlannerError):
    """Base exception for LLM-related failures."""

    pass


class LLMConnectionError(LLMError):
    """Raised when the LLM provider cannot be reached."""

    pass


class LLMResponseError(LLMError):
    """Raised when the LLM returns an invalid or unusable response."""

    pass


class LLMRateLimitError(LLMError):
    """Raised when the LLM provider rate limit is exceeded."""

    pass


class LLMAuthenticationError(LLMError):
    """Raised when LLM authentication fails."""

    pass


class LLMTimeoutError(LLMError):
    """Raised when an LLM request times out."""

    pass


# ==========================================================
# Tool
# ==========================================================

class ToolError(TravelPlannerError):
    """Base exception for application tool failures."""

    pass


class FlightToolError(ToolError):
    """Raised when the flight tool fails."""

    pass


class HotelToolError(ToolError):
    """Raised when the hotel tool fails."""

    pass


class ActivityToolError(ToolError):
    """Raised when the activity tool fails."""

    pass


class WeatherToolError(ToolError):
    """Raised when the weather tool fails."""

    pass


class CurrencyToolError(ToolError):
    """Raised when the currency tool fails."""

    pass


class PlacesToolError(ToolError):
    """Raised when a places lookup tool fails."""

    pass


# ==========================================================
# External API
# ==========================================================

class APIError(TravelPlannerError):
    """Base exception for external API failures."""

    pass


class AuthenticationError(APIError):
    """Raised when an external API authentication fails."""

    pass


class RateLimitError(APIError):
    """Raised when an external API rate limit is exceeded."""

    pass


class ServiceUnavailableError(APIError):
    """Raised when an external service is unavailable."""

    pass


class TimeoutError(APIError):
    """Raised when an external API request times out."""

    pass


class WeatherAPIError(APIError):
    """Raised when the weather API request fails."""

    pass


class ActivityAPIError(APIError):
    """Raised when the activity API request fails."""

    pass


class CurrencyAPIError(APIError):
    """Raised when the currency API request fails."""

    pass


class FlightAPIError(APIError):
    """Raised when the flight API request fails."""

    pass


class HotelAPIError(APIError):
    """Raised when the hotel API request fails."""

    pass


# ==========================================================
# Validation
# ==========================================================

class ValidationError(TravelPlannerError):
    """Raised when application or user input validation fails."""

    pass


class TravelPlanValidationError(ValidationError):
    """Raised when a TravelPlan is invalid or incomplete."""

    pass


class InvalidDateError(ValidationError):
    """Raised when travel dates are invalid."""

    pass


class InvalidLocationError(ValidationError):
    """Raised when a travel location cannot be resolved safely."""

    pass


# ==========================================================
# Database
# ==========================================================

class DatabaseError(TravelPlannerError):
    """Base exception for database-related failures."""

    pass


# ==========================================================
# Graph / Workflow
# ==========================================================

class GraphExecutionError(TravelPlannerError):
    """Raised when LangGraph execution fails."""

    pass


class GraphStateError(GraphExecutionError):
    """Raised when required graph state is missing or invalid."""

    pass


class RoutingError(GraphExecutionError):
    """Raised when graph routing cannot determine a valid destination."""

    pass


class ClarificationError(GraphExecutionError):
    """Raised when clarification handling fails."""

    pass