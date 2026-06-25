try:
    from playwright.sync_api import sync_playwright
except ImportError:
    import subprocess
    import sys
    print("Không tìm thấy thư viện playwright. Đang tiến hành cài đặt...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        print("Đang cài đặt trình duyệt Chromium cho Playwright...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"Lỗi khi tự động cài đặt playwright: {e}")
        raise e
import time
import os
from datetime import datetime
import pytz

# Cấu hình command
convert_command = {
    "cc": "Chấm công",
    "ls": "Lịch sử"
}

def login_and_click(
    host="http://10.0.99.101:3012/login",
    username="0867660302",
    password="aipt2024",
    output="storage/downloads/screenshot.png",
    style="ls"
):
    # Đảm bảo thư mục đầu ra tồn tại
    output_dir = os.path.dirname(output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    status_report = ""

    with sync_playwright() as p:
        # Sử dụng cấu hình giả lập Pixel 2
        pixel_2 = p.devices["Pixel 2"]
        
        # Khởi chạy trình duyệt chromium
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        
        # Tạo context mới với cấu hình mobile emulation và bỏ qua lỗi SSL
        context = browser.new_context(
            **pixel_2,
            ignore_https_errors=True
        )
        
        page = context.new_page()
        
        try:
            print(f"➜ Đang truy cập host: {host}")
            page.goto(host)
            
            # Điền username + password
            page.wait_for_selector("#login-form_username", state="visible", timeout=10000)
            page.fill("#login-form_username", username)
            page.fill("#login-form_password", password)
            
            # Click nút Đăng nhập
            login_xpath = "//button[span[text()='Đăng nhập']]"
            page.wait_for_selector(login_xpath, state="visible", timeout=10000)
            
            old_url = page.url
            page.click(login_xpath)
            
            # Chờ chuyển trang
            try:
                page.wait_for_function(f'window.location.href !== "{old_url}"', timeout=10000)
            except Exception as e:
                print(f"⚠️ Chờ đổi URL gặp lỗi (hoặc không đổi URL): {e}")
                
            print("Đăng nhập thành công, URL:", page.url)
            
            # Chọn chức năng theo style (mặc định là 'Lịch sử' để check trạng thái)
            target_text = convert_command.get("ls", "Lịch sử")
            print("Chờ nút xuất hiện:", target_text)
            
            xpath = f"//button[span[text()='{target_text}']]"
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    page.wait_for_selector(xpath, state="visible", timeout=5000)
                    print(f"✓ Nút '{target_text}' đã hiển thị")
                    
                    button = page.locator(xpath)
                    print(f"✓ Nút '{target_text}' đã sẵn sàng click")
                    
                    # Scroll vào view
                    button.scroll_into_view_if_needed()
                    time.sleep(1)  # Chờ animation scroll xong
                    
                    button.click()
                    print(f"✓ Đã click nút '{target_text}'")
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"⚠️ Lần {retry_count} thất bại: {type(e).__name__}. Thử lại...")
                        time.sleep(2)
                    else:
                        print(f"❌ Sau {max_retries} lần thử, nút '{target_text}' vẫn không hiển thị")
                        raise Exception(f"Không thể tìm hoặc click nút '{target_text}'") from e
            
            time.sleep(2)
            print(f"\nMã nguồn của trang '{target_text}':\n")
            
            # Kiểm tra xem hôm nay đã chấm công chưa
            tz = pytz.timezone('Asia/Ho_Chi_Minh')
            now = datetime.now(tz)
            today_str = now.strftime("%d-%m-%Y") # e.g. 25-02-2026
            
            # Chờ bảng dữ liệu hiển thị
            try:
                page.wait_for_selector("tr.ant-table-row", timeout=10000)
            except Exception as e:
                print(f"⚠️ Không tìm thấy dòng tr.ant-table-row nào: {e}")
                
            rows = page.locator("tr.ant-table-row").all()
            already_clocked_in = False
            already_clocked_out = False
            
            print(f"➜ Kiểm tra trạng thái chấm công cho ngày {today_str}...")
            
            for row in rows:
                cells = row.locator("td").all()
                if len(cells) >= 5:
                    # Cấu trúc bảng: 0=Lần, 1=Thời gian, 2=PVR, 3=Kiểu, 4=Trạng thái
                    time_info = cells[1].inner_text()
                    status_info = cells[4].inner_text().strip()
                    if today_str in time_info:
                        if "Vào" in status_info:
                            already_clocked_in = True
                            print(f"✓ Đã chấm công vào lúc: {time_info}")
                        elif "Ra" in status_info:
                            already_clocked_out = True
                            print(f"✓ Đã chấm công ra lúc: {time_info}")
            
            current_hour = now.hour
            
            # Logic báo cáo 8h tối (20h)
            if current_hour >= 20:
                if not already_clocked_out:
                    status_report = f"⚠️ Cảnh báo: Đã {current_hour}h tối nhưng chưa thấy dữ liệu chấm công RA cho ngày {today_str}!"
                    print(status_report)
            
            if already_clocked_out:
                print("➜ Hôm nay đã có bản ghi chấm công ra. Kết thúc quá trình.")
                should_click_clock_in = False
            elif already_clocked_in:
                print("➜ Đã tìm thấy bản ghi chấm công vào.")
                if current_hour < 12:
                    print(f"➜ Thời gian hiện tại ({current_hour}h) trước 12h trưa. Không click nữa. Kết thúc quá trình.")
                    should_click_clock_in = False
                else:
                    print(f"➜ Thời gian hiện tại ({current_hour}h) sau 12h trưa. Tiếp tục click chấm công...")
                    should_click_clock_in = True
            else:
                print("➜ Chưa tìm thấy bản ghi chấm công vào. Đang quay lại để chấm công...")
                should_click_clock_in = True
            
            if should_click_clock_in:
                # Click nút Quay lại
                back_xpath = "//button[span[text()='Quay lại']]"
                try:
                    page.wait_for_selector(back_xpath, state="visible", timeout=5000)
                    page.click(back_xpath)
                    print("✓ Đã click nút 'Quay lại' thành công")
                    time.sleep(3)
                except Exception as e:
                    print(f"⚠️ Cảnh báo: Không thể click nút 'Quay lại', dùng page.go_back(): {e}")
                    page.go_back()
                    time.sleep(3)
                
                # Click nút Chấm công hoặc Lịch sử dựa trên style
                cc_text = convert_command.get(style, "Lịch sử")
                cc_xpath = f"//button[span[text()='{cc_text}']]"
                try:
                    page.wait_for_selector(cc_xpath, state="visible", timeout=5000)
                    cc_button = page.locator(cc_xpath)
                    cc_button.scroll_into_view_if_needed()
                    time.sleep(1)
                    cc_button.click()
                    print(f"✓ Đã click nút '{cc_text}' thành công.")
                    time.sleep(2)
                except Exception as e:
                    print(f"❌ Không thể click nút '{cc_text}': {e}")
            
            # Lưu ảnh chụp màn hình
            page.screenshot(path=output)
            print("Đã thao tác xong và lưu screenshot:", output)
            
        finally:
            context.close()
            browser.close()
            
    # Trả về screenshot kèm theo tin nhắn báo cáo nếu có
    if status_report:
        return {"screenshot": output, "message": status_report}
    return output
