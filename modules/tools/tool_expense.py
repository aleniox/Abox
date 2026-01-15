import json
import os
from datetime import datetime

EXPENSE_FILE = "data/expenses.json"

def load_expenses():
    if not os.path.exists(EXPENSE_FILE):
        return []
    try:
        with open(EXPENSE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_expenses(expenses):
    os.makedirs(os.path.dirname(EXPENSE_FILE), exist_ok=True)
    with open(EXPENSE_FILE, 'w', encoding='utf-8') as f:
        json.dump(expenses, f, ensure_ascii=False, indent=2)

def add_expense(amount, category, description, date=None):
    expenses = load_expenses()
    if not date:
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        amount = float(amount)
    except ValueError:
        return "Số tiền không hợp lệ."

    expense = {
        "amount": amount,
        "category": category,
        "description": description,
        "date": date
    }
    expenses.append(expense)
    save_expenses(expenses)
    return f"Đã thêm chi tiêu: {amount:,.0f} đ vào mục {category} ({description}) ngày {date}"

def get_expenses_report(filter_date=None, filter_category=None):
    expenses = load_expenses()
    report = "📊 **Báo cáo chi tiêu:**\n"
    total = 0
    filtered_expenses = []

    for exp in expenses:
        # Simple string matching for filter
        if filter_date and filter_date not in exp['date']:
            continue
        if filter_category and filter_category.lower() not in exp['category'].lower():
            continue
        filtered_expenses.append(exp)
        try:
            total += float(exp['amount'])
        except:
            pass
        report += f"- {exp['date']}: {float(exp['amount']):,.0f} đ ({exp['category']}) - {exp['description']}\n"
    
    report += f"\n💰 **Tổng cộng:** {total:,.0f} đ"
    if not filtered_expenses:
        return "Không tìm thấy chi tiêu nào phù hợp."
    return report

expense_tool_def = {
    "type": "function",
    "function": {
        "name": "expense_tracker",
        "description": "Quản lý chi tiêu cá nhân: thêm khoản chi hoặc xem thống kê chi tiêu.",
        "parameters": {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "report"],
                    "description": "Hành động: 'add' để thêm khoản chi mới, 'report' để xem thống kê/báo cáo"
                },
                "amount": {
                    "type": "number",
                    "description": "Số tiền chi tiêu (bắt buộc khi action='add')"
                },
                "category": {
                    "type": "string",
                    "description": "Danh mục (VD: Ăn uống, Đi lại...) (dùng cho add hoặc filter report)"
                },
                "description": {
                    "type": "string",
                    "description": "Mô tả chi tiết (dùng cho add)"
                },
                "date": {
                    "type": "string",
                    "description": "Thời gian (dùng để lọc báo cáo hoặc ghi nhận ngày chi tiêu cũ)"
                }
            }
        }
    }
}

def handle_expense_tool(args):
    action=args.get('action'),
    amount=args.get('amount'),
    category=args.get('category'),
    description=args.get('description'),
    date=args.get('date')
    if action == "add":
        if amount is None:
            return "Vui lòng cung cấp số tiền."
        return add_expense(amount, category or "Khác", description or "", date)
    elif action == "report":
        return get_expenses_report(date, category)
    return "Hành động không hợp lệ"
