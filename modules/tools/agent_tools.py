import modules.config as config
import modules.tools.tool_generate as tool_generate
import modules.tools.tool_expense as tool_expense
import modules.core.call_api_llm as call_api_llm
import json

def clean_excessive_newlines(text):
    """
    Xóa các dòng trống thừa trong văn bản, chỉ giữ lại tối đa 1 dòng trống giữa các đoạn.
    """
    import re
    # Thay thế 2+ dòng trống liên tiếp bằng 1 dòng trống
    cleaned_text = re.sub(r'\n{3,}', '\n\n', text.strip())
    return cleaned_text

def smart_agent_decision(user_message: str):
    import modules.tools.tools_call as tool_call
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_prompt = f"Thời gian hiện tại: {current_time}. Căn cứ vào ngữ cảnh cũng như là yêu cầu của người dùng để chọn tools phù hợp"
    message = [{'role': 'system', 'content': system_prompt},
               {'role': 'user', 'content': user_message['content']}]
    tools = call_api_llm.call_chat_api(model=config.MODEL_NAME_G, messages=message, tools=[tool_call.calculus_tool, 
                                                                                           tool_call.search_web_tool, 
                                                                                           tool_call.url_search_tool, 
                                                                                           tool_call.generate_image_tools, 
                                                                                           tool_expense.expense_tool_def])
    tools = tools.json()['choices'][0]
    if 'tool_calls' in tools['message']:
        print(tools['message']['tool_calls'])
        for tool in tools['message']['tool_calls']:
            if tool['function']['name'] == 'calculus_calculator':
                args = tool['function']['arguments']
                context_ = tool_call.calculus_calculator(expression=args.get('expression'),
                                                        operation=args.get('operation'),
                                                        evaluate=args.get('evaluate'),
                                                        variable=args.get('variable'),
                                                        lower_bound=args.get('lower_bound'),
                                                        upper_bound=args.get('upper_bound'))
            elif tool['function']['name'] == 'search_web':
                args = json.loads(tool['function']['arguments'])
                contexts = tool_call.web_search(query=args['query'])
                context_ = contexts[1]
            elif tool['function']['name'] == 'url_search':
                contexts = tool_call.web_crawl_data(url_doc=tool['function']['arguments']['url'])
                context_ = '\n'.join([f"Source: {doc.metadata.get('source')}, Title: {doc.metadata.get('title')}, Language: {doc.metadata.get('language', 'None')}, Page_content: {clean_excessive_newlines(doc.page_content)}" for doc in contexts])
            elif tool['function']['name'] == 'generate_image':
                return tool_generate.call_api_gennerate_image(tool['function']['arguments'])
            elif tool['function']['name'] == 'expense_tracker':
                args = json.loads(tool['function']['arguments'])
                context_ = tool_expense.handle_expense_tool(
                    args=args
                )
        
        user_message = [{"role": "assistant", "content": f"Kết quả sau khi dùng tools: {context_}"}, user_message]
        
        return user_message
        
    return [user_message]
# Ví dụ sử dụng
# if __name__ == "__main__":
#     user_message = {"role": "user", "content": "Tôi muốn nghe bài hát The Night"}
#     response = smart_agent(user_message)
#     print(response)