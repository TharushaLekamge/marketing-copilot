"""Pytest fixtures for Ollama provider tests."""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
import pytest


class MockStreamResponse:
    """
    Emulates the response object returned from client.stream(...)
    - raise_for_status() is available
    - aiter_lines() is an async generator yielding lines (strings)
    """

    def __init__(self, lines: List[str]):
        # `lines` should be an iterable of strings
        self._lines = lines
        self._closed = False

    def raise_for_status(self) -> None:
        """No-op for success case."""
        return None

    async def aiter_lines(self):
        """Emulate streaming line-by-line."""
        for line in self._lines:
            # simulate small delay between chunks like a real stream
            await asyncio.sleep(0)
            yield line

    async def aclose(self) -> None:
        """Close the stream."""
        self._closed = True


class MockStreamContext:
    """
    Async context manager returned by MockClient.stream
    """

    def __init__(self, response: MockStreamResponse, raise_on_enter: Optional[Exception] = None):
        self._response = response
        self._raise_on_enter = raise_on_enter

    async def __aenter__(self) -> MockStreamResponse:
        """Enter the context manager."""
        if self._raise_on_enter:
            raise self._raise_on_enter
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        """Exit the context manager."""
        # close/cleanup if needed
        if hasattr(self._response, "aclose"):
            await self._response.aclose()
        return False  # don't swallow exceptions


class MockAsyncResponse:
    """
    Mock response for async POST calls.
    """

    def __init__(self, json_data: Dict[str, Any], raise_on_status: Optional[Exception] = None):
        self._json_data = json_data
        self._raise_on_status = raise_on_status
        self.status_code = 200

    def raise_for_status(self) -> None:
        """Raise error if configured."""
        if self._raise_on_status:
            raise self._raise_on_status

    def json(self) -> Dict[str, Any]:
        """Return JSON data."""
        return self._json_data


class MockClient:
    """
    Mock client that supports both .stream() and .post() methods.
    """

    def __init__(
        self,
        *,
        response_lines: Optional[List[str]] = None,
        raise_on_enter: Optional[Exception] = None,
        post_response: Optional[Dict[str, Any]] = None,
        post_error: Optional[Exception] = None,
    ):
        self.response_lines = response_lines or []
        self.raise_on_enter = raise_on_enter
        self.post_response = post_response
        self.post_error = post_error
        self.last_stream_args: Optional[tuple] = None  # capture stream call args
        self.last_post_args: Optional[tuple] = None  # capture post call args

    def stream(self, method: str, path: str, **kwargs):
        """Mock stream method that returns an async context manager."""
        # capture call
        self.last_stream_args = (method, path, kwargs)
        response = MockStreamResponse(self.response_lines)
        return MockStreamContext(response, raise_on_enter=self.raise_on_enter)

    async def post(self, path: str, **kwargs):
        """Mock async POST method."""
        # capture call
        self.last_post_args = (path, kwargs)
        
        # Raise error if configured
        if self.post_error:
            raise self.post_error
        
        # Return mock response with JSON data
        return MockAsyncResponse(self.post_response or {}, raise_on_status=None)


@pytest.fixture
def mock_client_factory():
    """Factory fixture for creating MockClient instances.
    
    Returns:
        A function that creates MockClient instances with specified parameters.
        
    Example:
        ```python
        # For streaming tests
        mock_client = mock_client_factory(response_lines=["line1", "line2"])
        
        # For async POST tests
        mock_client = mock_client_factory(
            post_response={"response": "Hello", "done": True}
        )
        
        # For error cases
        mock_client = mock_client_factory(
            post_error=httpx.HTTPError("Connection error")
        )
        ```
    """

    def _create_mock_client(
        response_lines: Optional[List[str]] = None,
        raise_on_enter: Optional[Exception] = None,
        post_response: Optional[Dict[str, Any]] = None,
        post_error: Optional[Exception] = None,
    ) -> MockClient:
        """Create a MockClient instance.
        
        Args:
            response_lines: List of strings to return from stream
            raise_on_enter: Exception to raise when entering stream context manager
            post_response: JSON data to return from async POST calls
            post_error: Exception to raise from async POST calls
            
        Returns:
            MockClient instance
        """
        return MockClient(
            response_lines=response_lines,
            raise_on_enter=raise_on_enter,
            post_response=post_response,
            post_error=post_error,
        )
    
    return _create_mock_client
