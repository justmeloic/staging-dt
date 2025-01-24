from google import genai
from google.genai import types
from typing import Optional
import functools
import time
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("GEMINI_MODEL_LOCATION")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

# Only run this block for Vertex AI API
client = genai.Client(
    vertexai=True, project=PROJECT_ID, location=LOCATION
)

def generate(prompt, model=MODEL_NAME, include_search: bool=False, response_schema = None, custom_tools=None, max_remote_calls=None):
    
    contents = [
        types.Content(
        role="user",
        parts=[
            types.Part.from_text(prompt)
        ]
        )
    ]

    generate_content_config = {  # Use a dictionary for easier modification
        "temperature": 1,
        "top_p": 0.95,
        "max_output_tokens": 8192,
        "response_modalities": ["TEXT"],
        "safety_settings": [
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT", threshold="OFF"
            ),
        ],
    }

    if include_search:
        tools = [types.Tool(google_search=types.GoogleSearch())]
        generate_content_config["tools"] = tools

    if response_schema:
        generate_content_config["response_schema"] = response_schema
        generate_content_config["response_mime_type"]="application/json"

    if custom_tools:
        generate_content_config["tools"] = custom_tools
        if max_remote_calls and (max_remote_calls != 10):
            print("setting max remote calls")
            generate_content_config["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(
                maximum_remote_calls=max_remote_calls)        


    generate_content_config = types.GenerateContentConfig(
        **generate_content_config
    )

    responses = client.models.generate_content(
    model = model,
    contents = contents,
    config = generate_content_config,
    )
    if responses.text:
        return responses.text
    else:
        return responses.candidates[0].finish_reason + "\n\n" + responses.candidates[0].finish_message


# print(generate("(answer as the infamous dialogue in a popular movie) \n hello there"))

# print(generate("what is the latest version of gemini available?", include_search=True))



def retry(
    exceptions=genai.errors.ClientError,
    retries=3,
    delay=5,
    backoff=2,
    logger=print,
):
    """
    Retry decorator with exponential backoff.

    Args:
        exceptions: Exception or tuple of exceptions to retry on.
        retries: Maximum number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff: Backoff multiplier (e.g., value of 2 will double the delay each retry).
        logger: Logger to use (default is the print function).
    """

    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper_retry(*args, **kwargs):
            mtries, mdelay = retries, delay
            while mtries > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if isinstance(e, genai.errors.ClientError) and e.response is not None and e.response.status_code != 429:
                        raise  # Re-raise if it's not a 429 error
                    if logger:
                        if isinstance(e, genai.errors.ClientError) and e.response is not None and e.response.status_code == 429:
                            logger(
                                f"Rate limit exceeded. Retrying in {mdelay} seconds..."
                            )
                        else:
                            logger(f"Error: {e}. Retrying in {mdelay} seconds...")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return func(*args, **kwargs)

        return wrapper_retry

    return decorator_retry


def get_data(data_type: str,) -> list[dict]:
    """Reads the data from the database and returns it.


    Args:
        data_type: The name of the table to read data from
    """
    from data_manager import DataManager
    data_manager = DataManager()
    res = data_manager.read_all(data_type=data_type)
    return res

# response = client.models.generate_content(
#     model='gemini-2.0-flash-exp',
#     contents="What is the weather like in Boston?",
#     config=types.GenerateContentConfig(tools=[get_current_weather],)
# )

# print(response.text)