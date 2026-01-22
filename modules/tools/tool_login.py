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
    host="http://192.168.1.2:3012/login",
    username="",
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
        target_text = convert_command.get(style, "Lịch sử")
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

    return output
