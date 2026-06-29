import json
import re
from datetime import datetime
from typing import Tuple, Optional

import modules.config.config as config
import modules.tools.tools_call as tool_call
import modules.tools.tool_searchs as tool_searchs
import modules.tools.tool_generate as tool_generate
import modules.tools.tool_expense as tool_expense
import modules.core.call_api_llm as call_api_llm


def clean_excessive_newlines(text):
    cleaned_text = re.sub(r'\n{3,}', '\n\n', text.strip())
    return cleaned_text


def smart_agent_decision(user_message: str) -> Tuple[list, Optional[str]]:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_prompt = f"Thời gian hiện tại: {current_time}. Căn cứ vào ngữ cảnh cũng như là yêu cầu của người dùng để chọn tools phù hợp"
    message = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_message['content']}
    ]
    tools = call_api_llm.call_chat_api(
        model=config.MODEL_NAME,
        messages=message,
        tools=[
            tool_call.calculus_tool,
            tool_call.search_web_tool,
            tool_call.url_search_tool,
            tool_call.generate_image_tools,
            tool_call.generate_voice_tools,
            tool_expense.expense_tool_def
        ]
    )
    choice = tools.get('choices', [{}])[0] if 'choices' in tools else tools

    if 'tool_calls' not in choice.get('message', {}):
        return [user_message], None

    context_parts = []
    generated_image = None

    for tool in choice['message']['tool_calls']:
        fn = tool['function']
        name = fn['name']
        raw_args = fn.get('arguments', '{}')
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

        try:
            if name == 'calculus_calculator':
                result = tool_call.calculus_calculator(
                    expression=args.get('expression'),
                    operation=args.get('operation'),
                    evaluate=args.get('evaluate'),
                    variable=args.get('variable'),
                    lower_bound=args.get('lower_bound'),
                    upper_bound=args.get('upper_bound')
                )
            elif name == 'search_web':
                contexts = tool_searchs.web_search(query=args['query'])
                result = contexts[1]
            elif name == 'url_search':
                contexts = tool_searchs.web_crawl_data(url_doc=args['url'])
                result = '\n'.join(
                    f"Source: {doc.metadata.get('source')}, Title: {doc.metadata.get('title')}, "
                    f"Language: {doc.metadata.get('language', 'None')}, "
                    f"Page_content: {clean_excessive_newlines(doc.page_content)}"
                    for doc in contexts
                )
            elif name == 'generate_image':
                image_path = tool_generate.call_api_generate_image(args)
                generated_image = image_path
                result = f"Đã tạo ảnh và lưu tại {image_path}"
            elif name == 'generate_voice':
                result = f"Đã tạo giọng nói cho: {args.get('text', '')}"
            elif name == 'expense_tracker':
                result = tool_expense.handle_expense_tool(args=args)
            else:
                result = f"Tool không hỗ trợ: {name}"

            context_parts.append(f"Kết quả từ {name}: {result}")
        except Exception as e:
            context_parts.append(f"Lỗi khi chạy tool {name}: {str(e)}")

    context_str = '\n'.join(context_parts)
    return [{"role": "assistant", "content": f"Kết quả sau khi dùng tools: {context_str}"}, user_message], generated_image