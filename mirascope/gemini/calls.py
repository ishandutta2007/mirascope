"""A module for calling Google's Gemini Chat API."""
import datetime
import logging
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    ClassVar,
    Generator,
    Optional,
)

from google.generativeai import GenerativeModel, configure  # type: ignore
from google.generativeai.types import ContentsType  # type: ignore
from pydantic import AfterValidator

from ..base import BaseCall, BasePrompt
from .tools import GeminiTool
from .types import (
    GeminiCallParams,
    GeminiCallResponse,
    GeminiCallResponseChunk,
)

logger = logging.getLogger("mirascope")


class GeminiCall(
    BaseCall[GeminiCallResponse, GeminiCallResponseChunk, GeminiTool], BasePrompt
):
    '''A class for prompting Google's Gemini Chat API.

    This prompt supports the message types: USER, MODEL, TOOL

    Example:

    ```python
    from google.generativeai import configure  # type: ignore
    from mirascope.gemini import GeminiPrompt

    configure(api_key="YOUR_API_KEY")


    class BookRecommender(GeminiPrompt):
        template = """
        USER: You're the world's greatest librarian.
        MODEL: Ok, I understand I'm the world's greatest librarian. How can I help?
        USER: Please recommend some {genre} books.

        genre: str


    response = BookRecommender(genre="fantasy").call()
    print(response.call())
    #> As the world's greatest librarian, I am delighted to recommend...
    ```
    '''

    api_key: Annotated[
        Optional[str],
        AfterValidator(lambda key: configure(api_key=key) if key is not None else None),
    ] = None

    call_params: ClassVar[GeminiCallParams] = GeminiCallParams(
        model="gemini-1.0-pro",
        generation_config={"candidate_count": 1},
    )

    @property
    def messages(self) -> ContentsType:
        """Returns the `ContentsType` messages for Gemini `generate_content`.

        Raises:
            ValueError: if the docstring contains an unknown role.
        """
        return self._parse_messages(["model", "user", "tool"])

    def call(self, **kwargs: Any) -> GeminiCallResponse:
        """Makes an call to the model using this `GeminiCall` instance.

        Args:
            **kwargs: Additional keyword arguments that will be used for generating the
                response. These will override any existing argument settings in call
                params.

        Returns:
            A `GeminiCallResponse` instance.
        """
        kwargs, tool_types = self._setup(kwargs, GeminiTool)
        gemini_pro_model = GenerativeModel(kwargs.pop("model"))
        start_time = datetime.datetime.now().timestamp() * 1000
        response = gemini_pro_model.generate_content(
            self.messages,
            stream=False,
            tools=kwargs.pop("tools") if "tools" in kwargs else None,
            **kwargs,
        )
        return GeminiCallResponse(
            response=response,
            tool_types=tool_types,
            start_time=start_time,
            end_time=datetime.datetime.now().timestamp() * 1000,
        )

    async def call_async(self, **kwargs: Any) -> GeminiCallResponse:
        """Makes an asynchronous call to the model using this `GeminiCall` instance.

        Args:
            **kwargs: Additional keyword arguments that will be used for generating the
                response. These will override any existing argument settings in call
                params.

        Returns:
            A `GeminiCallResponse` instance.
        """
        kwargs, tool_types = self._setup(kwargs, GeminiTool)
        gemini_pro_model = GenerativeModel(kwargs.pop("model"))
        start_time = datetime.datetime.now().timestamp() * 1000
        response = await gemini_pro_model.generate_content_async(
            self.messages,
            stream=False,
            tools=kwargs.pop("tools") if "tools" in kwargs else None,
            **kwargs,
        )
        return GeminiCallResponse(
            response=response,
            tool_types=tool_types,
            start_time=start_time,
            end_time=datetime.datetime.now().timestamp() * 1000,
        )

    def stream(self, **kwargs: Any) -> Generator[GeminiCallResponseChunk, None, None]:
        """Streams the response for a call using this `GeminiCall`.

        Args:
            **kwargs: Additional keyword arguments parameters to pass to the call. These
                will override any existing arguments in `call_params`.

        Yields:
            A `GeminiCallResponseChunk` for each chunk of the response.
        """
        kwargs, tool_types = self._setup(kwargs, GeminiTool)
        gemini_pro_model = GenerativeModel(kwargs.pop("model"))
        stream = gemini_pro_model.generate_content(
            self.messages,
            stream=True,
            tools=kwargs.pop("tools") if "tools" in kwargs else None,
            **kwargs,
        )
        for chunk in stream:
            yield GeminiCallResponseChunk(chunk=chunk, tool_types=tool_types)

    async def stream_async(
        self, **kwargs: Any
    ) -> AsyncGenerator[GeminiCallResponseChunk, None]:
        """Streams the response asynchronously for a call using this `GeminiCall`.

        Args:
            **kwargs: Additional keyword arguments parameters to pass to the call. These
                will override any existing arguments in `call_params`.

        Yields:
            A `GeminiCallResponseChunk` for each chunk of the response.
        """
        kwargs, tool_types = self._setup(kwargs, GeminiTool)
        gemini_pro_model = GenerativeModel(kwargs.pop("model"))
        stream = await gemini_pro_model.generate_content_async(
            self.messages,
            stream=True,
            tools=kwargs.pop("tools") if "tools" in kwargs else None,
            **kwargs,
        )
        async for chunk in stream:
            yield GeminiCallResponseChunk(chunk=chunk, tool_types=tool_types)
