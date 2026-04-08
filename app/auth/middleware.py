"""Authorization middleware for consistent security enforcement.

Provides middleware components and decorators to enforce authorization
policies consistently across all API endpoints. Implements request-level
authorization checks before route handlers execute.

The middleware intercepts requests to protected resources and validates
permissions based on resource type (team, pulse, trend analysis) and
user context. This ensures uniform security policy enforcement without
repeating authorization logic in every route.
"""

from typing import Callable, Optional
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce authorization on protected routes.
    
    Intercepts requests to routes matching protected patterns and verifies
    user has appropriate permissions before forwarding to route handler.
    Supports team-level, pulse-level, and admin-level authorization.
    
    Protected route patterns:
        - /api/v1/teams/{team_id}/* - requires team access
        - /api/v1/pulses/{pulse_id}/* - requires pulse access
        - /api/v1/trends/* - requires team access via query param
        - /api/v1/admin/* - requires admin role
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and enforce authorization rules.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler in chain
            
        Returns:
            Response from downstream handler if authorized
            
        Raises:
            HTTPException: If authorization check fails
        """
        path = request.url.path
        
        # Skip authorization for public endpoints
        if self._is_public_endpoint(path):
            return await call_next(request)
        
        # Extract resource identifiers from path
        team_id = self._extract_team_id(request)
        pulse_id = self._extract_pulse_id(request)
        
        # Verify authorization based on resource type
        # TODO: Implement actual checks when user context available in Task 3
        if team_id or pulse_id:
            # For now, pass through - full implementation in Task 3
            pass
        
        response = await call_next(request)
        return response
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public and doesn't require authorization.
        
        Args:
            path: Request URL path
            
        Returns:
            bool: True if endpoint is public
        """
        public_patterns = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register"
        ]
        return any(path.startswith(pattern) for pattern in public_patterns)
    
    def _extract_team_id(self, request: Request) -> Optional[int]:
        """Extract team_id from request path or query parameters.
        
        Args:
            request: Incoming HTTP request
            
        Returns:
            Optional[int]: Team ID if present, None otherwise
        """
        # Check path parameters
        if "team_id" in request.path_params:
            return int(request.path_params["team_id"])
        
        # Check query parameters for trend/analysis endpoints
        team_id = request.query_params.get("team_id")
        if team_id:
            return int(team_id)
        
        return None
    
    def _extract_pulse_id(self, request: Request) -> Optional[int]:
        """Extract pulse_id from request path parameters.
        
        Args:
            request: Incoming HTTP request
            
        Returns:
            Optional[int]: Pulse ID if present, None otherwise
        """
        if "pulse_id" in request.path_params:
            return int(request.path_params["pulse_id"])
        return None
