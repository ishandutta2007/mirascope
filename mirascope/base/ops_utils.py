import inspect
from collections.abc import Callable
from contextlib import AbstractContextManager
from functools import wraps
from typing import Any, Optional, TypeVar, Union

from pydantic import BaseModel

from mirascope.rag.embedders import BaseEmbedder

from .calls import BaseCall


def get_class_vars(cls: BaseModel) -> dict[str, Any]:
    """Get the class variables of a `BaseModel` removing any dangerous variables."""
    class_vars = {}
    for classvars in cls.__class_vars__:
        if not classvars == "api_key":
            class_vars[classvars] = getattr(cls.__class__, classvars)
    return class_vars


T = TypeVar("T")


def get_wrapped_async_client(client: T, self: Union[BaseCall, BaseEmbedder]) -> T:
    """Get a wrapped async client."""
    if self.configuration.client_wrappers:
        for op in self.configuration.client_wrappers:
            if op == "langfuse":
                from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI

                client = LangfuseAsyncOpenAI(
                    api_key=self.api_key, base_url=self.base_url
                )
            elif op == "logfire":
                import logfire

                logfire.instrument_openai(client)  # type: ignore
            if callable(op):
                client = op(client)
    return client


def get_wrapped_client(client: T, self: Union[BaseCall, BaseEmbedder]) -> T:
    """Get a wrapped client."""
    if self.configuration.client_wrappers:
        for op in self.configuration.client_wrappers:
            if op == "langfuse":
                from langfuse.openai import OpenAI as LangfuseOpenAI

                client = LangfuseOpenAI(api_key=self.api_key, base_url=self.base_url)
            elif op == "logfire":
                import logfire

                logfire.instrument_openai(client)  # type: ignore
            if callable(op):
                client = op(client)
    return client


C = TypeVar("C")


def get_wrapped_call(call: C, self: Union[BaseCall, BaseEmbedder], **kwargs) -> C:
    """Wrap a call to add the `llm_ops` parameter if it exists."""

    if self.configuration.llm_ops:
        wrapped_call = call
        for op in self.configuration.llm_ops:
            if op == "weave":
                import weave

                wrapped_call = weave.op()(wrapped_call)
            elif callable(op):
                wrapped_call = op(
                    wrapped_call,
                    self._provider,
                    **kwargs,
                )
        return wrapped_call
    return call


def mirascope_span(
    fn: Callable,
    handle_before_call: Optional[Callable] = None,
    handle_after_call: Optional[Callable] = None,
    **custom_kwargs,
):
    """Wraps a pydantic class method."""

    @wraps(fn)
    def wrapper(self: BaseModel, *args, **kwargs):
        """Wraps a pydantic class method that returns a value."""
        before_call = (
            handle_before_call(self, fn, **kwargs, **custom_kwargs)
            if handle_before_call is not None
            else None
        )
        if isinstance(before_call, AbstractContextManager):
            with before_call as result_before_call:
                result = fn(self, *args, **kwargs)
                if handle_after_call is not None:
                    handle_after_call(
                        self, fn, result, result_before_call, **kwargs, **custom_kwargs
                    )
                return result
        else:
            result = fn(self, *args, **kwargs)
            if handle_after_call is not None:
                handle_after_call(
                    self, fn, result, before_call, **kwargs, **custom_kwargs
                )
            return result

    @wraps(fn)
    async def wrapper_async(self: BaseModel, *args, **kwargs):
        """Wraps a pydantic async class method that returns a value."""
        before_call = (
            handle_before_call(self, fn, **kwargs, **custom_kwargs)
            if handle_before_call is not None
            else None
        )
        if isinstance(before_call, AbstractContextManager):
            with before_call as result_before_call:
                result = await fn(self, *args, **kwargs)
                if handle_after_call is not None:
                    handle_after_call(
                        self, fn, result, result_before_call, **kwargs, **custom_kwargs
                    )
                return result
        else:
            result = await fn(self, *args, **kwargs)
            if handle_after_call is not None:
                handle_after_call(
                    self, fn, result, before_call, **kwargs, **custom_kwargs
                )
            return result

    @wraps(fn)
    def wrapper_generator(self: BaseModel, *args, **kwargs):
        """Wraps a pydantic class method that returns a generator."""
        before_call = (
            handle_before_call(self, fn, **kwargs, **custom_kwargs)
            if handle_before_call is not None
            else None
        )
        if isinstance(before_call, AbstractContextManager):
            with before_call as result_before_call:
                result = fn(self, *args, **kwargs)
                output = []
                for value in result:
                    output.append(value)
                    yield value
                if handle_after_call is not None:
                    handle_after_call(
                        self, fn, output, result_before_call, **kwargs, **custom_kwargs
                    )
        else:
            result = fn(self, *args, **kwargs)

            output = []
            for value in result:
                output.append(value)
                yield value
            if handle_after_call is not None:
                handle_after_call(
                    self, fn, output, before_call, **kwargs, **custom_kwargs
                )

    @wraps(fn)
    async def wrapper_generator_async(self: BaseModel, *args, **kwargs):
        """Wraps a pydantic async class method that returns a generator."""
        before_call = (
            handle_before_call(self, fn, **kwargs, **custom_kwargs)
            if handle_before_call is not None
            else None
        )
        if isinstance(before_call, AbstractContextManager):
            with before_call as result_before_call:
                result = fn(self, *args, **kwargs)
                output = []
                async for value in result:
                    output.append(value)
                    yield value
                if handle_after_call is not None:
                    handle_after_call(
                        self, fn, output, result_before_call, **kwargs, **custom_kwargs
                    )
        else:
            result = fn(self, *args, **kwargs)
            output = []
            async for value in result:
                output.append(value)
                yield value
            if handle_after_call is not None:
                handle_after_call(
                    self, fn, output, before_call, **kwargs, **custom_kwargs
                )

    if inspect.isasyncgenfunction(fn):
        return wrapper_generator_async
    elif inspect.iscoroutinefunction(fn):
        return wrapper_async
    elif inspect.isgeneratorfunction(fn):
        return wrapper_generator
    return wrapper


def wrap_mirascope_class_functions(
    cls: type[BaseModel],
    handle_before_call: Optional[
        Callable[[BaseModel, Callable[..., Any], dict[str, Any]], Any]
    ] = None,
    handle_after_call: Optional[
        Callable[[BaseModel, Callable[..., Any], Any, Any, dict[str, Any]], Any]
    ] = None,
    **custom_kwargs: Any,
):
    """Wraps Mirascope class functions with a decorator.

    Args:
        cls: The Mirascope class to wrap.
        handle_before_call: A function to call before the call to the wrapped function.
        handle_after_call: A function to call after the call to the wrapped function.
        custom_kwargs: Additional keyword arguments to pass to the decorator.
    """

    ignore_functions = [
        "copy",
        "dict",
        "dump",
        "json",
        "messages",
        "model_copy",
        "model_dump",
        "model_dump_json",
        "model_post_init",
    ]

    for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith("_") and name not in ignore_functions:
            setattr(
                cls,
                name,
                mirascope_span(
                    getattr(cls, name),
                    handle_before_call,
                    handle_after_call,
                    **custom_kwargs,
                ),
            )
    return cls
