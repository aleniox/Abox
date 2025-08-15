import time
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
import dotenv
import os

dotenv.load_dotenv()

def call_api_gennerate_image(args, output_image='data/cache/gemini-native-image.png'):

    contents = args.get("prompt", None)
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


    # contents = ('Tạo cho tôi một con người béo cao tên là Minh đang khóc')

    response = client.models.generate_content(
        model="gemini-2.0-flash-preview-image-generation",
        contents=contents,
        config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
        )
    )

    for part in response.candidates[0].content.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = Image.open(BytesIO((part.inline_data.data)))
            image.save(output_image)
            # image.show()
    return output_image
# call_api_gennerate_image({'user_query': "tạo cho tôi một con dán đứng như con người nhìn bản thân mình trong chiếc gương"})