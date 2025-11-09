# Copyright (c) Microsoft. All rights reserved.

import os, httpx, asyncio, re


import logging

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.ollama import OllamaTextCompletion, OllamaChatCompletion
from semantic_kernel.functions import KernelArguments
from semantic_kernel.prompt_template import PromptTemplateConfig
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread

SHORT_FORM_TEMPLATE = """Generate a short-form social media post based on this brief:

Brief: {{brief}}

Requirements:
- Maximum 280 characters
- Engaging and attention-grabbing
- Include relevant hashtags if appropriate
- Clear call-to-action
- Optimized for social media engagement

{{#if brand_tone}}
Brand Tone: {{brand_tone}}
{{/if}}

{{#if context}}
Context: {{context}}
{{/if}}"""


logger = logging.getLogger(__name__)


"""
The following sample demonstrates how to create a chat completion agent that
answers user questions using the Azure Chat Completion service. The Chat Completion
Service is first added to the kernel, and the kernel is passed in to the
ChatCompletionAgent constructor. This sample demonstrates the basic steps to
create an agent and simulate a conversation with the agent.

Note: if both a service and a kernel are provided, the service will be used.

The interaction with the agent is via the `get_response` method, which sends a
user input to the agent and receives a response from the agent. The conversation
history needs to be maintained by the caller in the chat history object.
"""

# Simulate a conversation with the agent
USER_INPUTS = [
    "Hello, I am John Doe.",
    "What is your name?",
    "What is my name?",
]


async def main():
    # Automatically detect Windows host URL when running from WSL
    ollama_url = "http://localhost:11435"
    print(f"Connecting to Ollama at: {ollama_url}")
    try:
        print(httpx.get(ollama_url, timeout=3).text)
        print("Successfully connected to Ollama")
    except Exception as e:
        print(f"Error: {e}")

    kernel = Kernel()

    ollama_service = OllamaChatCompletion(host=ollama_url, ai_model_id="llama3.2:3b")
    kernel.add_service(ollama_service)

    prompt_config = PromptTemplateConfig(
        template_format="handlebars",
    )
    short_form_func = kernel.add_function(
        function_name="generate_short_form",
        plugin_name="ContentGeneration",
        prompt=SHORT_FORM_TEMPLATE,
        prompt_template_config=prompt_config,
    )
    # 2. Create the agent
    agent = ChatCompletionAgent(
        kernel=kernel,
        name="Assistant",
        instructions="Answer the user's questions.",
    )

    # 3. Create a thread to hold the conversation
    # If no thread is provided, a new thread will be
    # created and returned with the initial response
    thread: ChatHistoryAgentThread = None

    for user_input in USER_INPUTS:
        print(f"# User: {user_input}")
        # 4. Invoke the agent for a response
        response = await agent.get_response(
            messages=user_input,
            thread=thread,
        )
        print(f"# {response.name}: {response}")
        thread = response.thread

        args = KernelArguments(
            brief="pet product",
            brand_tone="energetic",
            context="dogs",
        )

        result_func_invoke = await kernel.invoke(
            short_form_func,
            args,
        )
        print(f"# Result function invoke: {result_func_invoke}")
        print(f"# Result function invoke type: {type(result_func_invoke)}")
        print(f"# Result function invoke value: {result_func_invoke.value}")
        print(f"# Result function invoke value type: {type(result_func_invoke.value)}")
        print(f"# Result function invoke value length: {len(result_func_invoke.value)}")
        print(f"# Result function invoke value first item: {result_func_invoke.value[0]}")
        print(f"# Result function invoke value first item type: {type(result_func_invoke.value[0])}")
        print(f"# Result function invoke value first item content: {result_func_invoke.value[0].content}")

    # 4. Cleanup: Clear the thread
    await thread.delete() if thread else None

    """
    Sample output:
    # User: Hello, I am John Doe.
    # Assistant: Hello, John Doe! How can I assist you today?
    # User: What is your name?
    # Assistant: I don't have a personal name like a human does, but you can call me Assistant.?
    # User: What is my name?
    # Assistant: You mentioned that your name is John Doe. How can I assist you further, John?
    """


if __name__ == "__main__":
    asyncio.run(main())
