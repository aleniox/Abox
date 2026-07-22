import requests
import logging
import modules.config.config as config
# from transformers import AutoTokenizer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def call_chat_api(messages,
                  model=config.MODEL_NAME,
                  stream=False,
                  tools=None,
                  max_token=config.MAX_TOKEN_CHAT,
                  host=config.LLM_API_CHAT,
                  resonning=False):
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {
            "num_ctx": max_token,
            "temperature": 0.0,
            "top_p": 0.95,
            "top_k": 64,
        },
        "tools": tools,
        "chat_template_kwargs": {"enable_thinking": resonning},
    }
    response = requests.post(host, json=payload, stream=stream)
    response.raise_for_status()
    return response.json()
