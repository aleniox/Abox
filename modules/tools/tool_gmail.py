# Lưu ý: Code dưới đây cần được chạy trong dự án có file credentials.json

import os.path
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Phạm vi truy cập (chỉ đọc email)
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def tool_gmail():
    creds = None
    # Kiểm tra token đã lưu chưa
    if os.path.exists('storage/cache/token.json'):
        creds = Credentials.from_authorized_user_file('storage/cache/token.json', SCOPES)
    
    # Nếu không có token hợp lệ, đăng nhập lại
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'storage/cache/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Lưu token cho lần sau
        with open('storage/cache/token.json', 'w') as token:
            token.write(creds.to_json())

    # Kết nối Gmail API và lấy 5 email
    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = results.get('messages', [])

    email_data = []
    for msg in messages:
        # Lấy chi tiết từng email
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_data['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        body = get_email_body(msg_data['payload'])
        email_data.append({
            'subject': subject,
            'from': sender,
            'date': next((h['value'] for h in headers if h['name'] == 'Date'), ''),
            'snippet': msg_data.get('snippet', ''),
            'body': body,
            'id': msg['id']
        })
    
    # Lưu ra file JSON
    with open('emails.json', 'w', encoding='utf-8') as f:
        json.dump(email_data, f, ensure_ascii=False, indent=4)
    
    print("Đã lưu dữ liệu email vào emails.json")


def get_email_body(payload):
    """Giải mã nội dung email từ payload của Gmail API"""
    import base64
    
    # Trường hợp đơn giản: body có sẵn data
    if 'body' in payload and 'data' in payload['body']:
        data = payload['body']['data']
        return base64.urlsafe_b64decode(data).decode('utf-8')
    
    # Trường hợp multipart: lặp qua các phần
    if 'parts' in payload:
        for part in payload['parts']:
            # Ưu tiên lấy plain text
            if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            # Nếu có phần con, đệ quy
            elif 'parts' in part:
                result = get_email_body(part)
                if result:
                    return result
    return ''

if __name__ == '__main__':
    tool_gmail()