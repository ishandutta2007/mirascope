"""This module contains the type definition for the base call keyword arguments."""

from mirascope.core.base.call_kwargs import BaseCallKwargs
from mirascope.core.gemini import GeminiCallParams, GeminiTool


class GeminiCallKwargs(GeminiCallParams, BaseCallKwargs[GeminiTool]): ...
