from typing import Optional, Any, Union, Iterator, AsyncIterator, List, Dict
from project_types.llm_provider import (
    LLMProvider,
    ProviderResponse,
    Message,
    MessageContent,
)
from utils.types import NotGiven, NOT_GIVEN


class LLM:
    """
    A service class for interacting with language models through standardized providers.

    This class provides an interface for invoking language models with
    customizable system prompts and streaming capabilities, with rate limiting
    and caching handled by the specific provider implementations.

    System prompts can include cache control blocks for providers that support it:
    [
        {
            "type": "text",
            "text": "You are a helpful assistant.",
        },
        {
            "type": "text",
            "text": "<large document content>",
            "cache_control": {"type": "ephemeral"}
        }
    ]
    """

    def __init__(
        self,
        provider: LLMProvider,
        system_prompts: Union[str, List[Dict[str, Any]]] = [
            {"type": "text", "text": "You are a helpful assistant."}
        ],
    ):
        """
        Initialize the LLM service.

        Args:
            provider (LLMProvider): The language model provider instance.
            system_prompts (Union[str, List[Dict[str, Any]]], optional): The default system prompt(s).
                Can be a simple string or a list of message blocks with optional cache_control.
                For Anthropic, use message blocks to enable caching of large content.
        """
        self.provider = provider
        self.system_prompts = system_prompts

    def _prepare_system_message(
        self, system_prompts: Union[str, List[Dict[str, Any]], None] = None
    ) -> Message:
        """
        Prepare system message from prompts.

        Args:
            system_prompts: Custom system prompt(s) or None to use default.

        Returns:
            Message: Formatted system message
        """
        prompts = system_prompts if system_prompts is not None else self.system_prompts

        if isinstance(prompts, str):
            return {"role": "system", "content": prompts}

        # Convert list of content blocks to MessageContent format
        content_blocks: List[MessageContent] = []
        for block in prompts:
            content_block: MessageContent = {
                "type": block.get("type", "text"),
                "text": block.get("text", ""),
            }
            if "image_url" in block:
                content_block["image_url"] = block["image_url"]
            if "cache_control" in block:
                content_block["cache_control"] = block["cache_control"]
            content_blocks.append(content_block)

        return {"role": "system", "content": content_blocks}

    def invoke(
        self,
        messages: List[Message],
        model_id: str,
        stream: bool = False,
        system_prompts: Union[str, List[Dict[str, Any]], None] = None,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: Any | NotGiven = NOT_GIVEN,
        functions: list[Any] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[dict[str, int]] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        response_format: Any | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], list[str]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Any | NotGiven = NOT_GIVEN,
        tools: list[Any] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
    ) -> Union[ProviderResponse, Iterator[str]]:
        """
        Invoke the language model with a given list of messages.

        Args:
            messages (List[Message]): List of messages to send to the model.
            model_id (str): The identifier for the model to use.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            system_prompts (Union[str, List[Dict[str, Any]]], optional): Custom system prompt(s).
                Can be a simple string or a list of message blocks with optional cache_control.
                For Anthropic, use message blocks to enable caching of large content:
                [
                    {
                        "type": "text",
                        "text": "You are a helpful assistant.",
                    },
                    {
                        "type": "text",
                        "text": "<large document content>",
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            frequency_penalty (Optional[float], optional): Penalty for token frequency.
            function_call (Any, optional): Function calling configuration.
            functions (list[Any], optional): Available functions.
            logit_bias (Optional[dict[str, int]], optional): Token biases.
            max_tokens (Optional[int], optional): Maximum tokens to generate.
            n (Optional[int], optional): Number of completions.
            presence_penalty (Optional[float], optional): Penalty for token presence.
            response_format (Any, optional): Format specification for the response.
            seed (Optional[int], optional): Random seed.
            stop (Union[Optional[str], list[str]], optional): Stop sequences.
            temperature (Optional[float], optional): Sampling temperature.
            tool_choice (Any, optional): Tool selection configuration.
            tools (list[Any], optional): Available tools.
            top_p (Optional[float], optional): Nucleus sampling parameter.
            user (str, optional): User identifier.

        Returns:
            Union[ProviderResponse, Iterator[str]]: Either a ProviderResponse for non-streaming
            requests or an iterator of string chunks for streaming requests.
        """
        # Prepend system message if system prompts are provided
        if system_prompts is not None:
            messages = [self._prepare_system_message(system_prompts)] + messages

        return self.provider.generate(
            messages=messages,
            model_id=model_id,
            stream=stream,
            frequency_penalty=frequency_penalty,
            function_call=function_call,
            functions=functions,
            logit_bias=logit_bias,
            max_tokens=max_tokens,
            n=n,
            presence_penalty=presence_penalty,
            response_format=response_format,
            seed=seed,
            stop=stop,
            temperature=temperature,
            tool_choice=tool_choice,
            tools=tools,
            top_p=top_p,
            user=user,
        )

    async def ainvoke(
        self,
        messages: List[Message],
        model_id: str,
        stream: bool = False,
        system_prompts: Union[str, List[Dict[str, Any]], None] = None,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: Any | NotGiven = NOT_GIVEN,
        functions: list[Any] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[dict[str, int]] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        response_format: Any | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], list[str]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Any | NotGiven = NOT_GIVEN,
        tools: list[Any] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
    ) -> Union[ProviderResponse, AsyncIterator[str]]:
        """
        Asynchronously invoke the language model with a given list of messages.

        Args:
            messages (List[Message]): List of messages to send to the model.
            model_id (str): The identifier for the model to use.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            system_prompts (Union[str, List[Dict[str, Any]]], optional): Custom system prompt(s).
                Can be a simple string or a list of message blocks with optional cache_control.
                For Anthropic, use message blocks to enable caching of large content:
                [
                    {
                        "type": "text",
                        "text": "You are a helpful assistant.",
                    },
                    {
                        "type": "text",
                        "text": "<large document content>",
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            frequency_penalty (Optional[float], optional): Penalty for token frequency.
            function_call (Any, optional): Function calling configuration.
            functions (list[Any], optional): Available functions.
            logit_bias (Optional[dict[str, int]], optional): Token biases.
            max_tokens (Optional[int], optional): Maximum tokens to generate.
            n (Optional[int], optional): Number of completions.
            presence_penalty (Optional[float], optional): Penalty for token presence.
            response_format (Any, optional): Format specification for the response.
            seed (Optional[int], optional): Random seed.
            stop (Union[Optional[str], list[str]], optional): Stop sequences.
            temperature (Optional[float], optional): Sampling temperature.
            tool_choice (Any, optional): Tool selection configuration.
            tools (list[Any], optional): Available tools.
            top_p (Optional[float], optional): Nucleus sampling parameter.
            user (str, optional): User identifier.

        Returns:
            Union[ProviderResponse, AsyncIterator[str]]: Either a ProviderResponse for non-streaming
            requests or an async iterator of string chunks for streaming requests.
        """
        # Prepend system message if system prompts are provided
        if system_prompts is not None:
            messages = [self._prepare_system_message(system_prompts)] + messages

        return await self.provider.agenerate(
            messages=messages,
            model_id=model_id,
            stream=stream,
            frequency_penalty=frequency_penalty,
            function_call=function_call,
            functions=functions,
            logit_bias=logit_bias,
            max_tokens=max_tokens,
            n=n,
            presence_penalty=presence_penalty,
            response_format=response_format,
            seed=seed,
            stop=stop,
            temperature=temperature,
            tool_choice=tool_choice,
            tools=tools,
            top_p=top_p,
            user=user,
        )
