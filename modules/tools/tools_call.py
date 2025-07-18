from duckduckgo_search import DDGS
from langchain_community.document_loaders import WebBaseLoader
from duckduckgo_search.exceptions import DuckDuckGoSearchException


# def add(a, b): return int(a) + int(b)


# def substract(a, b): return int(a) - int(b)


# subtract_tool = {
#     'type': 'function',
#     'function': {
#         'name': 'subtract_tool',
#         'description': 'Subtract two numbers',
#         'parameters': {
#             'type': 'object',
#             'required': ['a', 'b'],
#             'properties': {
#                 'a': {'type': 'number', 'description': 'The first number'},
#                 'b': {'type': 'number', 'description': 'The second number'},
#             },
#         },
#     },
# }
# add_tool = {
#     'type': 'function',
#     'function': {
#         'name': 'add_tool',
#         'description': 'Add two numbers',
#         'parameters': {
#             'type': 'object',
#             'required': ['a', 'b'],
#             'properties': {
#                 'a': {'type': 'number', 'description': 'The first number'},
#                 'b': {'type': 'number', 'description': 'The second number'},
#             },
#         },
#     },
# }

search_web_tool = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Tìm kiếm thông tin mới nhất từ internet. Dùng cho các câu hỏi yêu cầu dữ liệu cập nhật hoặc không có trong kiến thức hiện tại.",
        "parameters": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi/từ khóa cần tìm kiếm (ví dụ: 'thời tiết Hà Nội hôm nay', 'giá iPhone 15 mới nhất')",
                    "minLength": 3  # Đảm bảo query không quá ngắn
                }
            }
        }
    }
}




def search_with_ddgs(query, max_results=5):
    try:
        with DDGS() as ddgs:
            return ddgs.text(query, region="vn-vi", max_results=max_results)
    except DuckDuckGoSearchException as e:
        print(f"Lỗi: {e}")
# Ví dụ


def web_search(query, max_results=5):
    # loader = WebBaseLoader(query, max_results=max_results)
    # return loader.load()
    results = []
    text = ""
    for result in search_with_ddgs(query, max_results=max_results):
        results.append({
            "title": result['title'],
            "url": result['href'],
            "description": result['body']
        })
        text += f"Title: {result['title']}\nURL: {result['href']}\nDescription: {result['body']}\n\n"
    return results, text

url_search_tool = {
    'type': 'function',
    'function': {
        'name': 'url_search',
        'description': 'Tìm kiếm thông tin từ một URL cụ thể được cung cấp',
        'parameters': {
            'type': 'object',
            'required': ['url'],
            'properties': {
                'url': {
                    'type': 'string',
                    'format': 'uri',
                    'description': 'Danh sách URL để tìm kiếm thông tin',
                }
            }
        }
    }
}

def web_crawl_data(url_doc):
    if isinstance(url_doc, str):
        url_doc = [url_doc]
    loader = WebBaseLoader(
        web_paths=url_doc,
        requests_kwargs={
            'timeout': 10,  # 10 seconds timeout
        })

    document_to_compare = loader.load()
    return document_to_compare

calculus_tool = {
    "type": "function",
    "function": {
        "name": "calculus_calculator",
        "description": "Tính toán biểu thức toán học, bao gồm đạo hàm, tích phân và tính giá trị số. Hỗ trợ symbolic và numerical computation.",
        "parameters": {
            "type": "object",
            "required": ["expression", "operation"],
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Biểu thức toán học đơn vị góc là radian (ví dụ: 'x^2 + 3*x', 'sin(3/8) + 12*100 - 20/5', 'exp(-x^2)')"
                },
                "operation": {
                    "type": "string",
                    "enum": ["derivative", "integral", "calculate"],
                    "description": "Loại phép toán: derivative (đạo hàm), integral (tích phân), hoặc calculate (tính giá trị số)"
                },
                "variable": {
                    "type": "string",
                    "default": "x",
                    "description": "Biến cần tính (chỉ dùng cho derivative/integral, mặc định: 'x')"
                },
                "lower_bound": {
                    "type": "number",
                    "description": "Cận dưới cho tích phân (chỉ dùng khi operation='integral')"
                },
                "upper_bound": {
                    "type": "number",
                    "description": "Cận trên cho tích phân (chỉ dùng khi operation='integral')"
                },
                "evaluate": {
                    "type": "boolean",
                    "default": True,
                    "description": "Trả về giá trị số nếu True, giữ dạng symbolic nếu False (chỉ dùng khi operation='calculate')"
                }
            }
        }
    }
}

from sympy import symbols, diff, integrate, sin, cos, exp, sqrt, N
from sympy.parsing.sympy_parser import parse_expr

def calculus_calculator(
    expression: str,
    operation: str = "calculate",  # Thêm tùy chọn mặc định
    variable: str = "x",
    lower_bound: float = None,
    upper_bound: float = None,
    evaluate: bool = True  # Cho phép tính ra số cụ thể
):
    """
    Tính toán biểu thức toán học, bao gồm:
    - Đạo hàm (derivative)
    - Tích phân (integral)
    - Tính giá trị số (calculate)
    """
    try:
        # Chuẩn hóa biểu thức (thay ^ thành **)
        expr_str = expression.replace("^", "**")
        
        # Xử lý theo loại phép toán
        if operation == "derivative":
            x = symbols(variable)
            expr = parse_expr(expr_str)
            result = diff(expr, x)
        elif operation == "integral":
            x = symbols(variable)
            expr = parse_expr(expr_str)
            if lower_bound is not None and upper_bound is not None:
                result = integrate(expr, (x, lower_bound, upper_bound))
            else:
                result = integrate(expr, x)
        elif operation == "calculate":
            expr = parse_expr(expr_str)
            result = N(expr) if evaluate else expr  # Tính ra số hoặc giữ symbolic
        else:
            return "Lỗi: Phép toán không hỗ trợ. Chọn 'derivative', 'integral', hoặc 'calculate'"

        return str(result) if evaluate else f"Biểu thức: {result}"
    
    except Exception as e:
        return f"Lỗi: {str(e)}"