"""Domain exception hierarchy. Every service raises these directly —
the REST layer's exception_handlers.py maps them to HTTP status codes
so no router needs a try/except block."""
from __future__ import annotations


class PerfPlatformError(Exception):
    pass


# -- common ---------------------------------------------------------------------------------------------

class NotFoundError(PerfPlatformError):
    pass


class ValidationError(PerfPlatformError):
    pass


class ConflictError(PerfPlatformError):
    pass


class ConcurrentModificationError(PerfPlatformError):
    pass


class AuthorizationError(PerfPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class TenantIsolationError(AuthorizationError):
    pass


class InvalidTransitionError(PerfPlatformError):
    pass


# -- cache platform ---------------------------------------------------------------------------------------

class CacheError(PerfPlatformError):
    pass


class UnsupportedCacheLayerError(CacheError):
    pass


class CacheEntryNotFoundError(CacheError):
    pass


# -- model routing / LLM cost intelligence -----------------------------------------------------------------

class RoutingError(PerfPlatformError):
    pass


class UnsupportedModelTierError(RoutingError):
    pass


class UnsupportedTaskComplexityError(RoutingError):
    pass


class RoutingPolicyNotFoundError(RoutingError):
    pass


class NoEligibleModelTierError(RoutingError):
    pass


# -- cost intelligence engine -------------------------------------------------------------------------------

class CostError(PerfPlatformError):
    pass


class UnsupportedCostCategoryError(CostError):
    pass


class UnsupportedCostEntityTypeError(CostError):
    pass


class BudgetNotFoundError(CostError):
    pass


class BudgetExceededError(CostError):
    pass


# -- auto-optimization engine -------------------------------------------------------------------------------

class OptimizationError(PerfPlatformError):
    pass


class RecommendationNotFoundError(OptimizationError):
    pass


class UnsupportedRecommendationCategoryError(OptimizationError):
    pass


# -- observability & benchmarking ----------------------------------------------------------------------------

class ObservabilityError(PerfPlatformError):
    pass


class MetricSampleInvalidError(ObservabilityError):
    pass


class BenchmarkNotFoundError(ObservabilityError):
    pass


# -- scalability & GPU efficiency ------------------------------------------------------------------------------

class ScalabilityError(PerfPlatformError):
    pass


class UnsupportedGpuPoolTypeError(ScalabilityError):
    pass


class GpuPoolNotFoundError(ScalabilityError):
    pass
