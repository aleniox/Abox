from selenium import webdriver
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Cấu hình Chrome giả lập Mobile

def login_and_click(host = "http://192.168.1.2:3012/login", username = "0867660302", password="aipt2024", output="downloads/temp/screenshot.png"):
    mobile_emulation = {
    "deviceName": "Pixel 2"
    }

    options = Options()
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")  # nếu bạn muốn chạy không mở cửa sổ trình duyệt
    options.add_argument('--ignore-ssl-errors')
    # Tạo driver Chrome
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(host)

        wait = WebDriverWait(driver, 10)
        # page_source = driver.page_source
        # print(page_source)
        wait.until(EC.presence_of_element_located((By.ID, "login-form_username")))

        # Tìm 2 trường input bằng id
        username_input = driver.find_element(By.ID, "login-form_username")
        password_input = driver.find_element(By.ID, "login-form_password")

        # Nhập tài khoản và mật khẩu
        username_input.send_keys(username)  # Thay bằng email thật
        password_input.send_keys(password)
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Đăng nhập']]")))
        login_button.click()
        print(driver.current_url)
        wait.until(EC.url_changes(driver.current_url))
        # html_source = driver.page_source
        # print(driver.current_url)
        # print(html_source)
        button_chamcong = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[span[text()='Lịch sử']]")))
        button_chamcong.click()
        # wait.until(EC.url_changes(driver.current_url))
        print(driver.current_url)
        # driver.save_screenshot("screenshot.png")
        time.sleep(1)
        print(driver.current_url)
        driver.save_screenshot(output)
        print("Đã chấm công!")

    finally:
        driver.quit()
    
    return output
