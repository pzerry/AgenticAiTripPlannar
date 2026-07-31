"""
Custom exception hierarchy for the AI Travel Planner.

All application-specific exceptions should inherit from
TravelPlannerError.
"""


class TravelPlannerError(Exception):
    """
    Base exception for the entire application.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ==========================================================
# Configuration
# ==========================================================

class ConfigurationError(TravelPlannerError):
    """
    Raised when application configuration is invalid.
    """
    pass


# ==========================================================
# LLM
# ==========================================================

class LLMError(TravelPlannerError):
    """
    Base exception for LLM-related errors.
    """
    pass


class LLMConnectionError(LLMError):
    """
    Raised when the LLM provider cannot be reached.
    """
    pass


class LLMResponseError(LLMError):
    """
    Raised when the LLM returns an invalid response.
    """
    pass


# ==========================================================
# Tool Exceptions
# ==========================================================

class ToolError(TravelPlannerError):
    """
    Base exception for all tool-related failures.
    """
    pass


class FlightToolError(ToolError):
    """Raised when flight search fails."""
    pass


class HotelToolError(ToolError):
    """Raised when hotel search fails."""
    pass


class ActivityToolError(ToolError):
    """Raised when activity search fails."""
    pass


class WeatherToolError(ToolError):
    """Raised when weather lookup fails."""
    pass


class CurrencyToolError(ToolError):
    """Raised when currency conversion fails."""
    pass


class PlacesToolError(ToolError):
    """Raised when Google Places or Foursquare lookup fails."""
    pass


# ==========================================================
# External API
# ==========================================================
class APIError(TravelPlannerError):
    """
    Base exception for all tool-related failures.
    """
    pass

class WeatherAPIError(APIError):
    """Raised when the OpenWeather API request fails."""
    pass

class ActivityAPIError(APIError):
    """Raised when the TripAdvisor Activity API request fails."""
    pass

class CurrencyAPIError(APIError):
    """Raised when the Currency API request fails."""
    pass

class FlightAPIError(APIError):
    """Raised when the Flight API request fails."""
    pass

class HotelAPIError(APIError):
    """Raised when the Hotel API request fails."""
    pass

class AuthenticationError(APIError):
    """
    Raised when authentication with an external API fails.
    """
    pass


class RateLimitError(APIError):
    """
    Raised when an API rate limit is exceeded.
    """
    pass


class ServiceUnavailableError(APIError):
    """
    Raised when an external service is unavailable.
    """
    pass


# ==========================================================
# Validation
# ==========================================================

class ValidationError(TravelPlannerError):
    """
    Raised when user input validation fails.
    """
    pass


# ==========================================================
# Database
# ==========================================================

class DatabaseError(TravelPlannerError):
    """
    Raised for database-related failures.
    """
    pass


# ==========================================================
# Graph / Workflow
# ==========================================================

class GraphExecutionError(TravelPlannerError):
    """
    Raised when LangGraph execution fails.
    """
    pass