from selenium import webdriver
import time
import tempfile
import os, shutil
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Cấu hình command
convert_command = {
    "cc": "Chấm công",
    "ls": "Lịch sử"
}

def login_and_click(
    host="http://10.0.99.101:3012/login",
    username="0867660302",
    password="aipt2024",
    output="downloads/cache/screenshot.png",
    style="ls"
):
    mobile_emulation = {"deviceName": "Pixel 2"}

    options = Options()
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")  # chạy ẩn
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--headless=new")

    # Tạo thư mục user-data-dir tạm (tránh lỗi trùng session)
    user_data_dir = tempfile.mkdtemp()
    
    # Dọn dẹp các thư mục tạm cũ nếu hệ thống vừa crash/tắt đột ngột
    try:
        temp_root = tempfile.gettempdir()
        for item in os.listdir(temp_root):
            if item.startswith("tmpxxxx"): # Có thể tinh chỉnh pattern
                pass # Logic dọn dẹp bổ sung nếu cần
    except:
        pass

    options.add_argument(f"--user-data-dir={user_data_dir}")

    # Nếu bạn dùng google-chrome bản deb:
    options.binary_location = "/usr/bin/google-chrome"
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(host)
        wait = WebDriverWait(driver, 10)

        # Điền username + password
        username_input = wait.until(EC.presence_of_element_located((By.ID, "login-form_username")))
        password_input = driver.find_element(By.ID, "login-form_password")
        username_input.send_keys(username)
        password_input.send_keys(password)

        # Click nút Đăng nhập
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Đăng nhập']]")))
        old_url = driver.current_url
        login_button.click()

        wait.until(EC.url_changes(old_url))
        print("Đăng nhập thành công, URL:", driver.current_url)

        # Chọn chức năng theo style, kiểm tra nút đã hiển thị trước khi click
        target_text = convert_command.get("ls", "Lịch sử")
        print("Chờ nút xuất hiện:", target_text)
        
        xpath = f"//button[span[text()='{target_text}']]"
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                # Chờ nút xuất hiện
                button = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                print(f"✓ Nút '{target_text}' đã xuất hiện")
                
                # Chờ nút hiển thị (visible)
                button = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
                print(f"✓ Nút '{target_text}' đã hiển thị")
                
                # Chờ nút có thể click
                button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                print(f"✓ Nút '{target_text}' đã sẵn sàng click")
                
                # Scroll vào view
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(1)  # Chờ animation scroll xong
                
                # Click
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
        
        # Check if already clocked in today
        today_str = time.strftime("%d-%m-%Y") # e.g. 25-02-2026
        rows = driver.find_elements(By.CSS_SELECTOR, "tr.ant-table-row")
        already_clocked_in = False
        already_clocked_out = False
        
        print(f"➜ Kiểm tra trạng thái chấm công cho ngày {today_str}...")
        
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 5:
                # Cấu trúc bảng: 0=Lần, 1=Thời gian, 2=PVR, 3=Kiểu, 4=Trạng thái
                time_info = cells[1].text
                status_info = cells[4].text.strip()
                if today_str in time_info:
                    if "Vào" in status_info:
                        already_clocked_in = True
                        print(f"✓ Đã chấm công vào lúc: {time_info}")
                    elif "Ra" in status_info:
                        already_clocked_out = True
                        print(f"✓ Đã chấm công ra lúc: {time_info}")
        
        current_hour = int(time.strftime("%H"))
        status_report = ""

        # Logic báo cáo 8h tối (20h)
        if current_hour >= 20:
            if not already_clocked_out:
                status_report = f"⚠️ Cảnh báo: Đã {current_hour}h tối nhưng chưa thấy dữ liệu chấm công RA cho ngày {today_str}!"
                print(status_report)
            # Nếu đã có dữ liệu ra rồi thì không gán status_report để không báo gì cả

        if already_clocked_in:
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
            try:
                back_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Quay lại']]")))
                back_button.click()
                print("✓ Đã click nút 'Quay lại' thành công")
                time.sleep(3)
            except Exception as e:
                print(f"⚠️ Cảnh báo: Không thể click nút 'Quay lại', dùng driver.back(): {e}")
                driver.back()
                time.sleep(3)
            
            # Click nút Chấm công
            cc_text = convert_command.get(style, "Lịch sử")
            cc_xpath = f"//button[span[text()='{cc_text}']]"
            try:
                cc_button = wait.until(EC.element_to_be_clickable((By.XPATH, cc_xpath)))
                # Scroll vào view cho chắc chắn
                driver.execute_script("arguments[0].scrollIntoView(true);", cc_button)
                time.sleep(1)
                cc_button.click()
                print(f"✓ Đã click nút '{cc_text}' thành công.")
                time.sleep(2)
            except Exception as e:
                print(f"❌ Không thể click nút '{cc_text}': {e}")

        driver.save_screenshot(output)
        print("Đã thao tác xong và lưu screenshot:", output)

    finally:
        driver.quit()
        if user_data_dir and os.path.exists(user_data_dir):
            try:
                # shutil.rmtree xóa thư mục và tất cả nội dung đệ quy
                shutil.rmtree(user_data_dir)
                print(f"Đã dọn dẹp thư mục tạm: {user_data_dir}")
            except Exception as e:
                # Nếu không thể xóa (vì lý do nào đó), in ra cảnh báo
                print(f"CẢNH BÁO: Không thể xóa thư mục tạm {user_data_dir}. Lỗi: {e}")

    # Trả về screenshot kèm theo tin nhắn báo cáo nếu có
    if 'status_report' in locals() and status_report:
        return {"screenshot": output, "message": status_report}
    return output
