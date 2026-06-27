import requests
import logging
# from openai import OpenAI
import modules.config.config as config
from transformers import AutoTokenizer
# from langchain_ollama import OllamaEmbeddings


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
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 64,
        },
        "tools": tools,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    response = requests.post(host,
                             json=payload, stream=stream)

    return response

def get_tokenizer():
    return AutoTokenizer.from_pretrained(config.TOKENIZE)


# def get_embeddings():
#     """Create and return embedding model with consistent settings"""
#     return OllamaEmbeddings(
#         model=config.MODEL_NAME_EMBED,
#         base_url=config.OLLAMA_API_EMBEDD.replace("/api/chat", "")
#     )


def compute_tokenize(context):
    tokenizer = get_tokenizer()
    tokens = tokenizer.tokenize(context)
    print(f"Char count: {len(context)}")
    print(f"Word count: {len(context.split())}")
    print(f"Token count: {len(tokens)}")

    return len(context), len(context.split()), len(tokens)
