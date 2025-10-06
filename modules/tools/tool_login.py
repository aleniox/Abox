from selenium import webdriver
import time
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

        # Chọn chức năng theo style
        target_text = convert_command.get(style, "Lịch sử")
        print("Click vào:", target_text)

        button = wait.until(EC.element_to_be_clickable((By.XPATH, f"//button[span[text()='{target_text}']]")))
        driver.execute_script("arguments[0].scrollIntoView(true);", button)
        button.click()

        time.sleep(2)
        driver.save_screenshot(output)
        print("Đã thao tác xong và lưu screenshot:", output)

    finally:
        driver.quit()

    return output
