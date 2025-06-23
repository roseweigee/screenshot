#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網頁截圖工具 - 支援自動登入版本
檔案名稱：screenshot_app_with_login.py

新增功能：
- 支援基本 HTTP 認證
- 支援表單登入
- 支援 Cookie 檔案
- 支援自定義 Headers

使用方法：
  # 基本截圖
  WebScreenshot.exe https://www.example.com
  
  # HTTP 基本認證
  WebScreenshot.exe https://site.com --username admin --password 123456
  
  # 表單登入
  WebScreenshot.exe https://site.com --form-login --username admin --password 123456 --login-url https://site.com/login
  
  # 使用 Cookie 檔案
  WebScreenshot.exe https://site.com --cookies cookies.txt
  
  # 自定義 Headers
  WebScreenshot.exe https://site.com --headers "Authorization: Bearer token123"
"""

import argparse
import sys
import os
import time
import json
import base64
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 導入原有的模組
from screenshot_app import WebScreenshotTool, safe_print

class WebScreenshotWithLogin(WebScreenshotTool):
    
    def setup_driver_with_auth(self, width=1920, height=1080, headless=True, username=None, password=None, headers=None, cookies=None):
        """設定 WebDriver 並處理認證"""
        driver = self.setup_driver(width, height, headless)
        
        if not driver:
            return None
        
        # 添加自定義 Headers
        if headers:
            for header_line in headers:
                if ':' in header_line:
                    key, value = header_line.split(':', 1)
                    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                        "userAgent": driver.execute_script("return navigator.userAgent") + f"; {key.strip()}: {value.strip()}"
                    })
        
        # 載入 Cookies
        if cookies and os.path.exists(cookies):
            try:
                with open(cookies, 'r', encoding='utf-8') as f:
                    cookies_data = json.load(f)
                    for cookie in cookies_data:
                        driver.add_cookie(cookie)
                safe_print(f"Loaded cookies from: {cookies}")
            except Exception as e:
                safe_print(f"Failed to load cookies: {e}")
        
        return driver
    
    def http_basic_auth(self, driver, url, username, password):
        """處理 HTTP 基本認證"""
        try:
            # 構建帶認證的 URL
            parsed_url = urlparse(url)
            if username and password:
                auth_url = f"{parsed_url.scheme}://{username}:{password}@{parsed_url.netloc}{parsed_url.path}"
                if parsed_url.query:
                    auth_url += f"?{parsed_url.query}"
                
                safe_print(f"Using HTTP Basic Auth for: {parsed_url.netloc}")
                driver.get(auth_url)
                return True
        except Exception as e:
            safe_print(f"HTTP Basic Auth failed: {e}")
            return False
        
        return False
    
    def form_login(self, driver, login_url, target_url, username, password, username_field='username', password_field='password'):
        """處理表單登入"""
        try:
            safe_print(f"Navigating to login page: {login_url}")
            driver.get(login_url)
            
            # 等待登入表單載入
            time.sleep(3)
            
            # 尋找用戶名欄位（嘗試多種選擇器）
            username_selectors = [
                f"input[name='{username_field}']",
                f"input[id='{username_field}']",
                "input[type='text']",
                "input[type='email']",
                "input[name='user']",
                "input[name='login']",
                "input[name='email']"
            ]
            
            username_element = None
            for selector in username_selectors:
                try:
                    username_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not username_element:
                safe_print("Could not find username field")
                return False
            
            # 尋找密碼欄位
            password_selectors = [
                f"input[name='{password_field}']",
                f"input[id='{password_field}']",
                "input[type='password']",
                "input[name='pass']",
                "input[name='pwd']"
            ]
            
            password_element = None
            for selector in password_selectors:
                try:
                    password_element = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not password_element:
                safe_print("Could not find password field")
                return False
            
            # 填入認證資訊
            safe_print("Filling login credentials...")
            username_element.clear()
            username_element.send_keys(username)
            
            password_element.clear()
            password_element.send_keys(password)
            
            # 尋找並點擊登入按鈕
            login_button_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                "button:contains('登入')",
                "button:contains('Login')",
                "button:contains('Sign in')",
                ".login-button",
                "#login-button",
                "[name='submit']"
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    if ':contains(' in selector:
                        # 使用 XPath 處理 contains
                        xpath = f"//button[contains(text(), '{selector.split(':contains(')[1].split(')')[0]}')]"
                        login_button = driver.find_element(By.XPATH, xpath)
                    else:
                        login_button = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if login_button:
                safe_print("Clicking login button...")
                login_button.click()
                
                # 等待登入完成
                time.sleep(5)
                
                # 檢查是否登入成功（可以通過 URL 變化或特定元素來判斷）
                current_url = driver.current_url
                if login_url not in current_url or 'dashboard' in current_url.lower():
                    safe_print("Login appears successful")
                    
                    # 導航到目標頁面
                    if target_url != login_url:
                        safe_print(f"Navigating to target page: {target_url}")
                        driver.get(target_url)
                        time.sleep(3)
                    
                    return True
                else:
                    safe_print("Login may have failed - still on login page")
                    return False
            else:
                safe_print("Could not find login button")
                return False
                
        except Exception as e:
            safe_print(f"Form login failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def grafana_login(self, driver, base_url, username, password):
        """專門處理 Grafana 登入 - 根據實際 HTML 結構"""
        try:
            login_url = f"{base_url.rstrip('/')}/login"
            safe_print(f"Attempting Grafana login: {login_url}")
            
            driver.get(login_url)
            time.sleep(3)
            
            # 根據你的截圖，Grafana 登入表單結構
            try:
                # 方法1：使用 placeholder 屬性尋找用戶名欄位
                safe_print("Looking for username field...")
                username_input = None
                
                # 嘗試多種選擇器來找到用戶名欄位
                username_selectors = [
                    "input[placeholder='email or username']",  # 根據你的截圖
                    "input[aria-label='Username input field']",
                    "input[name='user']",
                    "input[name='username']",
                    "input[name='email']",
                    "input[type='text']:first-of-type",
                    ".css-1x5sjso-input-inputWrapper input",  # CSS class 選擇器
                    "div[class*='css-1x5sjso'] input"
                ]
                
                for selector in username_selectors:
                    try:
                        username_input = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        safe_print(f"Found username field with selector: {selector}")
                        break
                    except:
                        continue
                
                if not username_input:
                    safe_print("Could not find username field, trying XPath...")
                    # 使用 XPath 嘗試
                    xpath_selectors = [
                        "//input[@placeholder='email or username']",
                        "//input[contains(@aria-label, 'Username')]",
                        "//input[contains(@placeholder, 'username')]",
                        "//input[contains(@placeholder, 'email')]"
                    ]
                    for xpath in xpath_selectors:
                        try:
                            username_input = driver.find_element(By.XPATH, xpath)
                            safe_print(f"Found username field with XPath: {xpath}")
                            break
                        except:
                            continue
                
                if not username_input:
                    safe_print("ERROR: Could not find username field")
                    return False
                
                # 方法2：尋找密碼欄位
                safe_print("Looking for password field...")
                password_input = None
                
                password_selectors = [
                    "input[placeholder='password']",  # 根據你的截圖
                    "input[aria-label='Password input field']",
                    "input[name='password']",
                    "input[type='password']",
                    ".css-1x5sjso-input-inputWrapper input[type='password']",
                    "div[class*='css-1x5sjso'] input[type='password']"
                ]
                
                for selector in password_selectors:
                    try:
                        password_input = driver.find_element(By.CSS_SELECTOR, selector)
                        safe_print(f"Found password field with selector: {selector}")
                        break
                    except:
                        continue
                
                if not password_input:
                    safe_print("Could not find password field, trying XPath...")
                    xpath_selectors = [
                        "//input[@placeholder='password']",
                        "//input[contains(@aria-label, 'Password')]",
                        "//input[@type='password']"
                    ]
                    for xpath in xpath_selectors:
                        try:
                            password_input = driver.find_element(By.XPATH, xpath)
                            safe_print(f"Found password field with XPath: {xpath}")
                            break
                        except:
                            continue
                
                if not password_input:
                    safe_print("ERROR: Could not find password field")
                    return False
                
                # 填入認證資訊
                safe_print("Filling login credentials...")
                
                # 清除並填入用戶名
                username_input.click()
                username_input.clear()
                time.sleep(0.5)
                username_input.send_keys(username)
                
                # 清除並填入密碼
                password_input.click()
                password_input.clear()
                time.sleep(0.5)
                password_input.send_keys(password)
                
                # 尋找登入按鈕
                safe_print("Looking for login button...")
                login_button = None
                
                login_button_selectors = [
                    "button:contains('Log in')",
                    "button[type='submit']",
                    "button[aria-label='Login button']",
                    ".css-1mhnkuh-button",  # 根據你的截圖中的 CSS class
                    "button[class*='css-1mhnkuh']",
                    "div[class*='css-1mhnkuh'] button",
                    "button:contains('登入')",
                    "input[type='submit']"
                ]
                
                for selector in login_button_selectors:
                    try:
                        if ':contains(' in selector:
                            # 使用 XPath 處理 contains
                            text = selector.split(':contains(')[1].split(')')[0].strip('"\'')
                            xpath = f"//button[contains(text(), '{text}')]"
                            login_button = driver.find_element(By.XPATH, xpath)
                        else:
                            login_button = driver.find_element(By.CSS_SELECTOR, selector)
                        safe_print(f"Found login button with selector: {selector}")
                        break
                    except:
                        continue
                
                if not login_button:
                    safe_print("Could not find login button, trying to submit form...")
                    # 嘗試按 Enter 鍵提交
                    from selenium.webdriver.common.keys import Keys
                    password_input.send_keys(Keys.RETURN)
                else:
                    safe_print("Clicking login button...")
                    login_button.click()
                
                # 等待登入完成
                safe_print("Waiting for login to complete...")
                time.sleep(5)
                
                # 檢查是否登入成功
                current_url = driver.current_url
                page_source = driver.page_source.lower()
                
                # 檢查登入成功的指標
                if (login_url not in current_url or 
                    'dashboard' in current_url.lower() or 
                    'welcome to grafana' not in page_source or
                    'log out' in page_source or
                    'logout' in page_source):
                    safe_print("✅ Grafana login appears successful!")
                    return True
                else:
                    safe_print("⚠️ Login may have failed - checking for error messages...")
                    
                    # 檢查是否有錯誤訊息
                    error_selectors = [
                        ".alert-error", ".error", ".login-error", 
                        "[data-testid='login-error']", ".css-*error*"
                    ]
                    
                    error_found = False
                    for selector in error_selectors:
                        try:
                            error_element = driver.find_element(By.CSS_SELECTOR, selector)
                            if error_element.is_displayed():
                                safe_print(f"❌ Login error found: {error_element.text}")
                                error_found = True
                                break
                        except:
                            continue
                    
                    if not error_found:
                        safe_print("⚠️ No obvious error, but still on login page")
                    
                    return False
                
            except Exception as e:
                safe_print(f"Grafana login failed with error: {e}")
                import traceback
                traceback.print_exc()
                return False
                
        except Exception as e:
            safe_print(f"Grafana login completely failed: {e}")
            return False
    
    def capture_screenshot_with_auth(self, url, output_path="screenshot.png", width=1920, height=1080, 
                                    full_page=True, wait_time=3, dpi=1.0, quality=95,
                                    username=None, password=None, login_method='auto',
                                    login_url=None, headers=None, cookies=None,
                                    username_field='username', password_field='password'):
        """帶認證的截圖功能"""
        
        # 根據 DPI 調整解析度
        actual_width = int(width * dpi)
        actual_height = int(height * dpi)
        
        driver = None
        try:
            safe_print(f"Starting Chrome browser with authentication support...")
            driver = self.setup_driver_with_auth(actual_width, actual_height, True, username, password, headers, cookies)
            
            if not driver:
                return False
            
            # 根據登入方法處理認證
            login_success = False
            
            if username and password:
                if login_method == 'auto':
                    # 自動偵測登入方式
                    parsed_url = urlparse(url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    
                    # 先嘗試 Grafana 特定登入
                    if 'grafana' in url.lower() or ':3000' in url:
                        login_success = self.grafana_login(driver, base_url, username, password)
                    
                    # 如果 Grafana 登入失敗，嘗試 HTTP 基本認證
                    if not login_success:
                        login_success = self.http_basic_auth(driver, url, username, password)
                        
                elif login_method == 'http':
                    login_success = self.http_basic_auth(driver, url, username, password)
                    
                elif login_method == 'form':
                    if not login_url:
                        parsed_url = urlparse(url)
                        login_url = f"{parsed_url.scheme}://{parsed_url.netloc}/login"
                    login_success = self.form_login(driver, login_url, url, username, password, username_field, password_field)
                    
                elif login_method == 'grafana':
                    parsed_url = urlparse(url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    login_success = self.grafana_login(driver, base_url, username, password)
            
            # 如果沒有認證資訊或認證失敗，直接存取 URL
            if not login_success:
                safe_print(f"Loading webpage: {url}")
                driver.get(url)
            
            # 智能等待頁面載入
            safe_print(f"Waiting for page to load...")
            self.wait_for_page_load(driver)
            
            # 額外等待時間
            if wait_time > 0:
                safe_print(f"Additional wait: {wait_time} seconds...")
                time.sleep(wait_time)
            
            # 檢查是否還在登入頁面
            current_url = driver.current_url
            if 'login' in current_url.lower() and username and password:
                safe_print("Warning: Still on login page. Authentication may have failed.")
            
            # 設定 DPI 縮放
            if dpi != 1.0:
                try:
                    driver.execute_script(f"document.body.style.zoom = '{dpi}';")
                    time.sleep(1)
                except:
                    pass
            
            if full_page:
                safe_print("Taking full page screenshot...")
                return self.capture_full_page(driver, output_path, quality)
            else:
                safe_print("Taking viewport screenshot...")
                screenshot = driver.get_screenshot_as_png()
                self.save_screenshot(screenshot, output_path, quality)
                safe_print(f"Screenshot saved: {output_path}")
                return True
                
        except Exception as e:
            safe_print(f"Screenshot with auth failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

def create_parser_with_auth():
    """建立支援認證的命令列參數解析器"""
    parser = argparse.ArgumentParser(
        description="Web Screenshot Tool with Authentication Support",
        epilog="""
Authentication Examples:
  %(prog)s https://site.com --username admin --password 123456
  %(prog)s https://grafana.com --username admin --password 123456 --login-method grafana
  %(prog)s https://site.com --form-login --login-url https://site.com/login --username user --password pass
  %(prog)s https://site.com --cookies session.json
  %(prog)s https://site.com --headers "Authorization: Bearer token123"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 基本參數
    parser.add_argument('url', help='Target webpage URL')
    parser.add_argument('-o', '--output', default='screenshot.png', help='Output filename')
    parser.add_argument('-w', '--width', type=int, default=1920, help='Browser window width')
    parser.add_argument('--height', type=int, default=1080, help='Browser window height')
    
    # 認證參數
    auth_group = parser.add_argument_group('Authentication Options')
    auth_group.add_argument('--username', help='Username for authentication')
    auth_group.add_argument('--password', help='Password for authentication')
    auth_group.add_argument('--login-method', choices=['auto', 'http', 'form', 'grafana'], 
                           default='auto', help='Login method (default: auto)')
    auth_group.add_argument('--login-url', help='Login page URL (for form login)')
    auth_group.add_argument('--username-field', default='username', help='Username field name (default: username)')
    auth_group.add_argument('--password-field', default='password', help='Password field name (default: password)')
    auth_group.add_argument('--cookies', help='Path to cookies JSON file')
    auth_group.add_argument('--headers', action='append', help='Custom headers (can be used multiple times)')
    
    # 其他參數
    parser.add_argument('--no-full-page', action='store_true', help='Capture viewport only')
    parser.add_argument('--wait', type=int, default=3, help='Page load wait time in seconds')
    parser.add_argument('--quality', type=int, default=95, choices=range(1, 101), help='JPEG quality')
    parser.add_argument('--version', action='version', version='WebScreenshot with Auth 2.1.0')
    
    return parser

def main():
    """主函數"""
    parser = create_parser_with_auth()
    args = parser.parse_args()
    
    # 建立帶認證的截圖工具
    tool = WebScreenshotWithLogin()
    
    # 執行截圖
    safe_print(f"=== Web Screenshot Tool with Auth v2.1.0 ===")
    safe_print(f"Target URL: {args.url}")
    safe_print(f"Output file: {args.output}")
    safe_print(f"Window size: {args.width} x {args.height}")
    if args.username:
        safe_print(f"Username: {args.username}")
        safe_print(f"Login method: {args.login_method}")
    safe_print("-" * 60)
    
    success = tool.capture_screenshot_with_auth(
        url=args.url,
        output_path=args.output,
        width=args.width,
        height=args.height,
        full_page=not args.no_full_page,
        wait_time=args.wait,
        quality=args.quality,
        username=args.username,
        password=args.password,
        login_method=args.login_method,
        login_url=args.login_url,
        headers=args.headers,
        cookies=args.cookies,
        username_field=args.username_field,
        password_field=args.password_field
    )
    
    if success:
        safe_print("Screenshot with authentication completed successfully!")
        return 0
    else:
        safe_print("Screenshot with authentication failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
