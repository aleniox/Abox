import requests
import logging
import modules.config.config as config
from transformers import AutoTokenizer


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
                  host=config.LLM_API_CHAT):
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {
            "num_ctx": max_token,
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 64,
        },
        "tools": tools,
    }
    response = requests.post(host, json=payload, stream=stream)
    response.raise_for_status()
    return response.json()


def get_tokenizer():
    return AutoTokenizer.from_pretrained(config.TOKENIZE)


def compute_tokenize(context):
    tokenizer = get_tokenizer()
    tokens = tokenizer.tokenize(context)
    print(f"Char count: {len(context)}")
    print(f"Word count: {len(context.split())}")
    print(f"Token count: {len(tokens)}")

    return len(context), len(context.split()), len(tokens)
