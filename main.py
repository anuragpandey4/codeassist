import argparse
import json
import os
import sys


from dotenv import load_dotenv
from openai import OpenAI

from call_functions import available_functions, call_function

system_prompt = """
You are a helpful AI coding agent.

When a user asks a question or makes a request, make a function call plan. You can perform the following operations:

- List files and directories
- Read file contents
- Execute Python files with optional arguments
- Write or overwrite files

All paths you provide should be relative to the working directory. You do not need to specify the working directory in your function calls as it is automatically injected for security reasons.
"""

def main() -> None:
    parser = argparse.ArgumentParser(description="AI Code Assistant")
    parser.add_argument("user_prompt", type=str, help="Prompt to send to the LLM")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.user_prompt},
    ]
    if args.verbose:
        print(f"User prompt: {args.user_prompt}\n")

    generate_content(client, messages, args.verbose)


def generate_content(client: OpenAI, messages: list, verbose: bool) -> None:
    for _ in range(20):
        response = client.chat.completions.create(
            model="openrouter/free",
            messages=messages,
            tools=available_functions,
        )
        if not response.usage:
            raise RuntimeError("API response appears to be malformed")

        if verbose:
            print("Prompt tokens:", response.usage.prompt_tokens)
            print("Response tokens:", response.usage.completion_tokens)

        message = response.choices[0].message
        
        # 1. Append assistant's turn to conversation history
        messages.append(message)

        # 2. Check if tools were requested
        if message.tool_calls:
            for tool_call in message.tool_calls:
                result_message = call_function(tool_call, verbose=verbose)
                if not result_message.get("content"):
                    raise RuntimeError("Function call returned empty content")
                
                # Append tool's result to conversation history
                messages.append(result_message)
                
                if verbose:
                    print(f"-> {result_message['content']}")
        else:
            # 3. No tool calls -> LLM has its final answer!
            if message.content:
                print(message.content)
            return

    # 4. If 20 iterations were exhausted without a final response
    print("Error: Reached maximum iterations (20) without a final response.")
    sys.exit(1)


if __name__ == "__main__":
    main()
