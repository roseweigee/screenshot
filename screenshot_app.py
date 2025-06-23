#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網頁截圖工具 - 增強版，支援 Grafana 登入
檔案名稱：screenshot_app.py

功能：
- 基本網頁截圖
- Grafana 自動登入
- 完整頁面截圖
- 高品質圖片輸出

新增使用方法：
  # 基本截圖（原功能）
  WebScreenshot.exe https://www.example.com
  
  # Grafana 登入截圖（新功能）
  WebScreenshot.exe https://grafana.com/dashboard --username admin --password 123456
  
  # 完整參數範例
  WebScreenshot.exe https://grafana.com/dashboard --username admin --password 123456 --wait 5 --output dashboard.png
"""

import argparse
import sys
import os
import time
import io
from urllib.parse import urlparse

# 修正 Windows 控制台編碼問題
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
except ImportError as e:
    print("Error: Missing required packages. Please install:")
    print("pip install selenium>=4.15.0")
    sys.exit(1)

try:
    from PIL import Image
except ImportError as e:
    print("Error: Missing Pillow package. Please install:")
    print("pip install pillow")
    sys.exit(1)

def safe_print(message):
    """安全的 print 函數，處理編碼問題"""
    try:
        print(message)
    except UnicodeEncodeError:
        ascii_message = message.encode('ascii', 'replace').decode('ascii')
        print(ascii_message)

class WebScreenshotTool:
    def __init__(self, chromedriver_path=None):
        self.chromedriver_path = chromedriver_path or self.find_chromedriver()
    
    def find_chromedriver(self):
        """尋找 ChromeDriver 執行檔"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(current_dir, "chromedriver.exe"),
            os.path.join(current_dir, "chromedriver"),
            "chromedriver.exe",
            "chromedriver"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def setup_driver(self, width=1920, height=1080, headless=True, high_res=False, scale_factor=2.0):
        """設定 WebDriver - 相容 Chrome 129，支援高解析度"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        # 高解析度模式的特殊設定
        if high_res:
            safe_print(f"🔥 配置高解析度模式 ({scale_factor}x)")
            # 啟用高 DPI 支援
            chrome_options.add_argument("--force-device-scale-factor={}".format(scale_factor))
            chrome_options.add_argument("--high-dpi-support=1")
            chrome_options.add_argument("--device-scale-factor={}".format(scale_factor))
        
        # Chrome 129 相容的參數設定
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_argument(f"--window-size={width},{height}")
        
        # 高解析度模式的額外設定
        if high_res:
            # 增加記憶體限制以處理高解析度
            chrome_options.add_argument("--max_old_space_size=8192")
            chrome_options.add_argument("--memory-pressure-off")
            # 啟用硬體加速（在高解析度下有幫助）
            chrome_options.add_argument("--enable-accelerated-2d-canvas")
            chrome_options.add_argument("--enable-accelerated-jpeg-decoding")
        else:
            chrome_options.add_argument("--memory-pressure-off")
            chrome_options.add_argument("--max_old_space_size=4096")
        
        # 設定用戶代理
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
        
        # 移除自動化檢測標誌
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 忽略證書錯誤
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--ignore-certificate-errors-spki-list")
        
        try:
            if self.chromedriver_path and os.path.exists(self.chromedriver_path):
                safe_print(f"Using local ChromeDriver: {self.chromedriver_path}")
                service = Service(executable_path=self.chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                safe_print("Using system ChromeDriver")
                driver = webdriver.Chrome(options=chrome_options)
            
            # 移除 webdriver 屬性
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except:
                pass
            
            # 高解析度模式的額外設定
            if high_res:
                try:
                    # 設定設備像素比
                    driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                        'width': width,
                        'height': height,
                        'deviceScaleFactor': scale_factor,
                        'mobile': False
                    })
                    safe_print(f"✅ 高解析度設定完成 - 設備縮放: {scale_factor}x")
                except Exception as e:
                    safe_print(f"⚠️ 高解析度 CDP 設定失敗: {e}")
            
            return driver
            
        except Exception as e:
            safe_print(f"Error: Unable to start Chrome browser")
            safe_print(f"Details: {e}")
            return None
    
    def validate_url(self, url):
        """驗證 URL 格式"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def wait_for_page_load(self, driver, timeout=30):
        """等待頁面完全載入"""
        try:
            WebDriverWait(driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)
            
            try:
                if driver.execute_script("return typeof jQuery !== 'undefined'"):
                    WebDriverWait(driver, 10).until(
                        lambda driver: driver.execute_script("return jQuery.active == 0")
                    )
            except:
                pass
                
        except Exception as e:
            safe_print(f"Page load timeout: {e}")
    
    def openshift_login(self, driver, base_url, username, password):
        """OpenShift 專用登入處理"""
        try:
            login_url = f"{base_url.rstrip('/')}/login"
            safe_print(f"正在存取 OpenShift 登入頁面: {login_url}")
            
            driver.get(login_url)
            time.sleep(3)
            
            # 檢查是否有多個登入選項（OAuth providers）
            try:
                # 尋找登入選項
                oauth_buttons = driver.find_elements(By.CSS_SELECTOR, "a[href*='oauth'], button[id*='oauth'], .pf-c-login__main a")
                if oauth_buttons:
                    safe_print("發現 OAuth 登入選項，點擊第一個...")
                    oauth_buttons[0].click()
                    time.sleep(3)
            except:
                safe_print("未發現 OAuth 選項，繼續直接登入...")
            
            # 尋找用戶名欄位
            safe_print("尋找用戶名輸入欄位...")
            username_input = None
            
            username_selectors = [
                "input[name='inputUsername']",  # 根據你的截圖
                "input[id='inputUsername']",
                "input[placeholder*='用戶']",
                "input[placeholder*='username']",
                "input[placeholder*='User']",
                "input[name='username']",
                "input[name='user']",
                "input[type='text']",
                ".pf-c-form-control[type='text']"
            ]
            
            for selector in username_selectors:
                try:
                    username_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    safe_print(f"找到用戶名欄位: {selector}")
                    break
                except:
                    continue
            
            if not username_input:
                safe_print("❌ 找不到用戶名輸入欄位")
                return False
            
            # 尋找密碼欄位
            safe_print("尋找密碼輸入欄位...")
            password_input = None
            
            password_selectors = [
                "input[name='inputPassword']",  # 根據你的截圖
                "input[id='inputPassword']",
                "input[placeholder*='密碼']",
                "input[placeholder*='password']",
                "input[placeholder*='Password']",
                "input[type='password']",
                "input[name='password']",
                ".pf-c-form-control[type='password']"
            ]
            
            for selector in password_selectors:
                try:
                    password_input = driver.find_element(By.CSS_SELECTOR, selector)
                    safe_print(f"找到密碼欄位: {selector}")
                    break
                except:
                    continue
            
            if not password_input:
                safe_print("❌ 找不到密碼輸入欄位")
                return False
            
            # 填入登入資訊
            safe_print("填入登入認證...")
            username_input.click()
            username_input.clear()
            time.sleep(0.5)
            username_input.send_keys(username)
            
            password_input.click()
            password_input.clear()
            time.sleep(0.5)
            password_input.send_keys(password)
            
            # 尋找並點擊登入按鈕
            safe_print("尋找登入按鈕...")
            login_button = None
            
            button_selectors = [
                "button:contains('登录')",  # 根據你的截圖
                "button:contains('登錄')",
                "button:contains('Login')",
                "button:contains('Log in')",
                "button[type='submit']",
                "input[type='submit']",
                "button[id*='login']",
                ".pf-c-button.pf-m-primary",
                "button.btn-primary"
            ]
            
            for selector in button_selectors:
                try:
                    if ':contains(' in selector:
                        # 使用 XPath 處理 contains
                        text = selector.split(':contains(')[1].split(')')[0].strip('"\'')
                        xpath = f"//button[contains(text(), '{text}')]"
                        login_button = driver.find_element(By.XPATH, xpath)
                    else:
                        login_button = driver.find_element(By.CSS_SELECTOR, selector)
                    safe_print(f"找到登入按鈕: {selector}")
                    break
                except:
                    continue
            
            if login_button:
                safe_print("點擊登入按鈕...")
                login_button.click()
            else:
                safe_print("找不到登入按鈕，嘗試按 Enter 鍵...")
                password_input.send_keys(Keys.RETURN)
            
            # 等待登入完成
            safe_print("等待登入完成...")
            time.sleep(8)  # OpenShift 可能需要更長時間
            
            # 檢查登入結果
            current_url = driver.current_url
            page_source = driver.page_source.lower()
            
            # OpenShift 登入成功的指標
            login_success = False
            
            success_indicators = [
                'console' in current_url.lower(),
                'dashboard' in current_url.lower(),
                'overview' in current_url.lower(),
                'projects' in page_source,
                'logout' in page_source,
                'sign out' in page_source,
                'openshift console' in page_source
            ]
            
            if any(success_indicators) or 'login' not in current_url.lower():
                safe_print("✅ OpenShift 登入成功！")
                login_success = True
            else:
                # 檢查是否有錯誤訊息
                error_indicators = ['invalid', 'error', 'incorrect', 'failed', 'unauthorized']
                if any(indicator in page_source for indicator in error_indicators):
                    safe_print("❌ 登入失敗：發現錯誤訊息")
                    return False
                else:
                    safe_print("⚠️ 登入狀態不明確，嘗試繼續...")
                    login_success = True
            
            return login_success
                
        except Exception as e:
            safe_print(f"❌ OpenShift 登入失敗: {e}")
            return False
    
    def auto_detect_login_type(self, driver, base_url, username, password):
        """自動偵測登入類型並處理"""
        try:
            # 先存取首頁或登入頁面來偵測類型
            test_url = f"{base_url.rstrip('/')}/login"
            driver.get(test_url)
            time.sleep(3)
            
            page_source = driver.page_source.lower()
            current_url = driver.current_url.lower()
            
            # 偵測是否為 Grafana
            if ('grafana' in page_source or 
                'grafana' in current_url or 
                'welcome to grafana' in page_source):
                safe_print("🔍 偵測到 Grafana 系統")
                return self.grafana_login(driver, base_url, username, password)
            
            # 偵測是否為 OpenShift
            elif ('openshift' in page_source or 
                  'red hat' in page_source or 
                  'openshift' in current_url or
                  'console-openshift' in current_url):
                safe_print("🔍 偵測到 OpenShift 系統")
                return self.openshift_login(driver, base_url, username, password)
            
            # 通用登入處理
            else:
                safe_print("🔍 使用通用登入處理")
                return self.generic_login(driver, base_url, username, password)
                
        except Exception as e:
            safe_print(f"❌ 自動偵測登入失敗: {e}")
            return False
    
    def generic_login(self, driver, base_url, username, password):
        """通用登入處理"""
        try:
            safe_print("嘗試通用表單登入...")
            
            # 尋找用戶名欄位
            username_selectors = [
                "input[name='username']", "input[name='user']", "input[name='email']",
                "input[type='text']", "input[type='email']", 
                "input[placeholder*='user']", "input[placeholder*='email']"
            ]
            
            username_input = None
            for selector in username_selectors:
                try:
                    username_input = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            # 尋找密碼欄位
            password_input = None
            try:
                password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            except:
                pass
            
            if username_input and password_input:
                username_input.clear()
                username_input.send_keys(username)
                password_input.clear()
                password_input.send_keys(password)
                
                # 尋找提交按鈕
                try:
                    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
                    submit_button.click()
                except:
                    password_input.send_keys(Keys.RETURN)
                
                time.sleep(5)
                return True
            
            return False
            
        except Exception as e:
            safe_print(f"通用登入失敗: {e}")
            return False
        """Grafana 專用登入處理"""
        try:
            login_url = f"{base_url.rstrip('/')}/login"
            safe_print(f"正在存取 Grafana 登入頁面: {login_url}")
            
            driver.get(login_url)
            time.sleep(3)
            
            # 尋找用戶名欄位
            safe_print("尋找用戶名輸入欄位...")
            username_input = None
            
            username_selectors = [
                "input[placeholder='email or username']",
                "input[aria-label='Username input field']",
                "input[name='user']",
                "input[name='username']",
                "input[type='text']"
            ]
            
            for selector in username_selectors:
                try:
                    username_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    safe_print(f"找到用戶名欄位: {selector}")
                    break
                except:
                    continue
            
            if not username_input:
                safe_print("❌ 找不到用戶名輸入欄位")
                return False
            
            # 尋找密碼欄位
            safe_print("尋找密碼輸入欄位...")
            password_input = None
            
            password_selectors = [
                "input[placeholder='password']",
                "input[type='password']",
                "input[name='password']"
            ]
            
            for selector in password_selectors:
                try:
                    password_input = driver.find_element(By.CSS_SELECTOR, selector)
                    safe_print(f"找到密碼欄位: {selector}")
                    break
                except:
                    continue
            
            if not password_input:
                safe_print("❌ 找不到密碼輸入欄位")
                return False
            
            # 填入登入資訊
            safe_print("填入登入認證...")
            username_input.click()
            username_input.clear()
            username_input.send_keys(username)
            
            password_input.click()
            password_input.clear()
            password_input.send_keys(password)
            
            # 尋找並點擊登入按鈕
            safe_print("尋找登入按鈕...")
            login_button = None
            
            button_selectors = [
                "button[type='submit']",
                "button[aria-label='Login button']",
                "input[type='submit']"
            ]
            
            for selector in button_selectors:
                try:
                    login_button = driver.find_element(By.CSS_SELECTOR, selector)
                    safe_print(f"找到登入按鈕: {selector}")
                    break
                except:
                    continue
            
            if login_button:
                safe_print("點擊登入按鈕...")
                login_button.click()
            else:
                safe_print("找不到登入按鈕，嘗試按 Enter 鍵...")
                password_input.send_keys(Keys.RETURN)
            
            # 等待登入完成
            safe_print("等待登入完成...")
            time.sleep(5)
            
            # 檢查登入結果
            current_url = driver.current_url
            page_source = driver.page_source.lower()
            
            # 檢查是否登入成功（多種指標）
            login_success = False
            
            if (login_url not in current_url or 
                'welcome to grafana' in page_source or
                'dashboard' in current_url.lower() or
                'home' in current_url.lower()):
                safe_print("✅ Grafana 登入成功！")
                login_success = True
            else:
                # 檢查是否有錯誤訊息
                error_indicators = ['invalid', 'error', 'incorrect', 'failed']
                if any(indicator in page_source for indicator in error_indicators):
                    safe_print("❌ 登入失敗：發現錯誤訊息")
                    return False
                else:
                    safe_print("⚠️ 登入狀態不明確，嘗試繼續...")
                    login_success = True
            
            return login_success
                
        except Exception as e:
            safe_print(f"❌ Grafana 登入失敗: {e}")
            return False
    
    def save_screenshot(self, screenshot_data, output_path, quality=95):
        """保存截圖並優化品質"""
        try:
            if output_path.lower().endswith('.png'):
                with open(output_path, 'wb') as file:
                    file.write(screenshot_data)
            else:
                image = Image.open(io.BytesIO(screenshot_data))
                if image.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = background
                
                image.save(output_path, 'JPEG', quality=quality, optimize=True)
        except Exception as e:
            safe_print(f"Save screenshot failed: {e}")
            raise
    
    def capture_full_page(self, driver, output_path, quality=95, start_height=0):
        """截取完整頁面 - 支援指定起始高度"""
        try:
            original_size = driver.get_window_size()
            
            try:
                total_width = driver.execute_script("""
                    return Math.max(
                        document.body.scrollWidth,
                        document.documentElement.scrollWidth,
                        document.body.offsetWidth,
                        document.documentElement.offsetWidth,
                        document.body.clientWidth,
                        document.documentElement.clientWidth
                    );
                """)
                
                total_height = driver.execute_script("""
                    return Math.max(
                        document.body.scrollHeight,
                        document.documentElement.scrollHeight,
                        document.body.offsetHeight,
                        document.documentElement.offsetHeight,
                        document.body.clientHeight,
                        document.documentElement.clientHeight
                    );
                """)
            except Exception as e:
                safe_print(f"Failed to get page dimensions: {e}")
                total_width = original_size['width']
                total_height = original_size['height']
            
            # 處理起始高度
            if start_height > 0:
                if start_height >= total_height:
                    safe_print(f"Warning: Start height ({start_height}) is greater than page height ({total_height}). Using 0.")
                    start_height = 0
                else:
                    safe_print(f"截圖起始高度: {start_height}px")
                    total_height = total_height - start_height
            
            safe_print(f"Full page dimensions: {total_width} x {total_height} (starting from {start_height}px)")
            
            max_width = 7680
            max_height = 20000
            
            if total_width > max_width:
                total_width = max_width
            if total_height > max_height:
                total_height = max_height
            
            try:
                # 滾動到指定的起始位置
                if start_height > 0:
                    safe_print(f"滾動到起始位置: {start_height}px")
                    driver.execute_script(f"window.scrollTo(0, {start_height});")
                    time.sleep(1)
                else:
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(1)
                
                # 設定瀏覽器視窗大小（包含起始位置的調整）
                adjusted_height = total_height + (original_size['height'] if start_height > 0 else 0)
                driver.set_window_size(total_width, adjusted_height)
                time.sleep(3)
                
                # 再次滾動到正確位置
                if start_height > 0:
                    driver.execute_script(f"window.scrollTo(0, {start_height});")
                else:
                    driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except:
                pass
            
            # 截圖
            screenshot = driver.get_screenshot_as_png()
            
            # 如果有起始高度，需要裁切圖片
            if start_height > 0:
                try:
                    from PIL import Image
                    import io
                    
                    # 載入截圖
                    image = Image.open(io.BytesIO(screenshot))
                    
                    # 計算裁切區域（從起始高度開始）
                    # 這裡需要根據實際的螢幕比例來計算
                    viewport_height = original_size['height']
                    crop_top = 0  # 因為我們已經滾動到正確位置，所以從頂部開始
                    crop_bottom = image.height
                    
                    # 裁切圖片
                    cropped_image = image.crop((0, crop_top, image.width, crop_bottom))
                    
                    # 儲存裁切後的圖片
                    buffer = io.BytesIO()
                    cropped_image.save(buffer, format='PNG')
                    screenshot = buffer.getvalue()
                    
                    safe_print(f"已裁切圖片，從高度 {start_height}px 開始")
                    
                except Exception as e:
                    safe_print(f"圖片裁切失敗，使用原始截圖: {e}")
            
            self.save_screenshot(screenshot, output_path, quality)
            
            try:
                driver.set_window_size(original_size['width'], original_size['height'])
            except:
                pass
            
            safe_print(f"Full page screenshot saved: {output_path}")
            return True
            
        except Exception as e:
            safe_print(f"Full page screenshot failed: {e}")
            return False
    
    def capture_viewport_from_height(self, driver, output_path, start_height=0, quality=95):
        """從指定高度截取視窗截圖"""
        try:
            if start_height > 0:
                safe_print(f"滾動到指定高度: {start_height}px")
                driver.execute_script(f"window.scrollTo(0, {start_height});")
                time.sleep(2)
            
            screenshot = driver.get_screenshot_as_png()
            self.save_screenshot(screenshot, output_path, quality)
            safe_print(f"Viewport screenshot from height {start_height}px saved: {output_path}")
            return True
            
        except Exception as e:
            safe_print(f"Viewport screenshot failed: {e}")
            return False
    
    def capture_screenshot(self, url, output_path="screenshot.png", width=1920, height=1080, 
                          full_page=True, wait_time=3, dpi=1.0, quality=95,
                          username=None, password=None, start_height=0, high_res=False, scale_factor=2.0):
        """主要截圖功能 - 支援 Grafana 登入、起始高度、高解析度"""
        
        # 處理高解析度設定
        if high_res:
            safe_print(f"🔥 啟用高解析度模式，縮放倍數: {scale_factor}x")
            actual_width = int(width * scale_factor)
            actual_height = int(height * scale_factor)
            # 高解析度模式下，DPI 也需要相應調整
            effective_dpi = dpi * scale_factor
        else:
            # 根據 DPI 調整解析度（原有邏輯）
            actual_width = int(width * dpi)
            actual_height = int(height * dpi)
            effective_dpi = dpi
        
        driver = None
        try:
            safe_print(f"Starting Chrome browser...")
            driver = self.setup_driver(actual_width, actual_height, True, high_res, scale_factor)
            
            if not driver:
                return False
            
            # 檢查是否需要 Grafana 登入
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            need_login = username and password
            
            if need_login:
                # 執行自動偵測登入
                safe_print(f"檢測到登入認證，自動偵測系統類型...")
                login_success = self.auto_detect_login_type(driver, base_url, username, password)
                
                if login_success:
                    safe_print(f"✅ 登入成功！正在導航到目標頁面...")
                    safe_print(f"Target URL: {url}")
                    driver.get(url)
                    
                    # 等待頁面載入完成
                    safe_print("等待儀表板載入...")
                    time.sleep(5)
                    
                    # 嘗試等待 Grafana 圖表載入完成
                    try:
                        WebDriverWait(driver, 10).until_not(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".loading, .spinner, [data-testid='loading']"))
                        )
                        safe_print("載入指示器已消失")
                    except:
                        safe_print("未發現載入指示器或已載入完成")
                    
                    # 再等待一些時間確保圖表完全渲染
                    safe_print("等待圖表完全渲染...")
                    time.sleep(3)
                else:
                    safe_print("❌ 登入失敗，嘗試直接存取 URL...")
                    driver.get(url)
            else:
                # 直接存取 URL（原有功能）
                safe_print(f"Loading webpage: {url}")
                driver.get(url)
            
            # 智能等待頁面載入
            safe_print(f"Waiting for page to load...")
            self.wait_for_page_load(driver)
            
            # 額外等待時間
            if wait_time > 0:
                safe_print(f"Additional wait: {wait_time} seconds...")
                time.sleep(wait_time)
            
            # 設定 DPI 縮放
            if effective_dpi != 1.0:
                try:
                    safe_print(f"設定頁面縮放: {effective_dpi}")
                    driver.execute_script(f"document.body.style.zoom = '{effective_dpi}';")
                    time.sleep(2)  # 高解析度需要更多時間渲染
                except:
                    pass
            
            if full_page:
                safe_print("Taking full page screenshot...")
                success = self.capture_full_page(driver, output_path, quality, start_height)
            else:
                safe_print("Taking viewport screenshot...")
                success = self.capture_viewport_from_height(driver, output_path, start_height, quality)
            
            # 高解析度模式的後處理
            if success and high_res:
                safe_print(f"✨ 高解析度截圖完成！解析度: {actual_width}x{actual_height}")
                try:
                    # 顯示檔案大小資訊
                    file_size = os.path.getsize(output_path)
                    size_mb = file_size / (1024 * 1024)
                    safe_print(f"📁 檔案大小: {size_mb:.2f} MB")
                except:
                    pass
            
            return success
                
        except Exception as e:
            safe_print(f"Screenshot failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

def create_parser():
    """建立命令列參數解析器"""
    parser = argparse.ArgumentParser(
        description="Web Screenshot Tool v2.1.0 (Chrome 129 Compatible) with Auto-Login Support",
        epilog="""
Examples:
  %(prog)s https://www.example.com
  %(prog)s https://grafana.com/dashboard --username admin --password 123456
  %(prog)s https://openshift-console.apps.cluster.com --username admin --password 123456
  %(prog)s https://example.com --width 1920 --height 1080 --output screenshot.png
  %(prog)s https://example.com --start-height 500 --output partial.png
  %(prog)s https://example.com --high-res --scale-factor 2.0 --output hd_screenshot.png
  %(prog)s https://example.com --preset 4k --output 4k_screenshot.png
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 必要參數
    parser.add_argument('url', help='Target webpage URL')
    
    # 可選參數
    parser.add_argument('-o', '--output', default='screenshot.png', help='Output filename (default: screenshot.png)')
    parser.add_argument('-w', '--width', type=int, default=1920, help='Browser window width (default: 1920)')
    parser.add_argument('--height', type=int, default=1080, help='Browser window height (default: 1080)')
    parser.add_argument('--no-full-page', action='store_true', help='Capture viewport only instead of full page')
    parser.add_argument('--wait', type=int, default=3, help='Wait time in seconds after page load (default: 3)')
    parser.add_argument('--dpi', type=float, default=1.0, help='DPI scaling factor (default: 1.0)')
    parser.add_argument('--quality', type=int, default=95, choices=range(1, 101), help='JPEG quality 1-100 (default: 95)')
    
    # Authentication Options (for Grafana, OpenShift, etc.)
    auth_group.add_argument('--username', help='Username for login (supports Grafana, OpenShift, etc.)')
    auth_group.add_argument('--password', help='Password for login (supports Grafana, OpenShift, etc.)')
    
    parser.add_argument('--version', action='version', version='WebScreenshot v2.1.0 (Chrome 129 Compatible)')
    
    return parser

def main():
    """主函數"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 處理高解析度預設值
    if args.preset:
        args.high_res = True
        if args.preset == '2k':
            args.width = 3840
            args.height = 2160
            args.scale_factor = 1.5
        elif args.preset == '4k':
            args.width = 7680
            args.height = 4320
            args.scale_factor = 2.0
        elif args.preset == '8k':
            args.width = 15360
            args.height = 8640
            args.scale_factor = 2.5
        safe_print(f"🔥 使用 {args.preset.upper()} 預設值: {args.width}x{args.height}, 縮放: {args.scale_factor}x")
    
    # 驗證 URL
    tool = WebScreenshotTool()
    if not tool.validate_url(args.url):
        safe_print(f"Error: Invalid URL format: {args.url}")
        return 1
    
    # 確保 URL 有協定
    if not args.url.startswith(('http://', 'https://')):
        args.url = 'https://' + args.url
    
    # 輸出基本資訊
    safe_print(f"=== Web Screenshot Tool v2.1.0 (Chrome 129 Compatible) ===")
    safe_print(f"Target URL: {args.url}")
    safe_print(f"Output file: {args.output}")
    safe_print(f"Window size: {args.width} x {args.height}")
    safe_print(f"Full page: {not args.no_full_page}")
    safe_print(f"Wait time: {args.wait} seconds")
    if args.start_height > 0:
        safe_print(f"Start height: {args.start_height}px")
    if args.high_res:
        safe_print(f"High resolution: {args.scale_factor}x scaling")
    if args.username:
        safe_print(f"Username: {args.username}")
        safe_print("Authentication: Enabled (Auto-detect mode)")
    safe_print("-" * 60)
    
    # 執行截圖
    success = tool.capture_screenshot(
        url=args.url,
        output_path=args.output,
        width=args.width,
        height=args.height,
        full_page=not args.no_full_page,
        wait_time=args.wait,
        dpi=args.dpi,
        quality=args.quality,
        username=args.username,
        password=args.password,
        start_height=args.start_height,
        high_res=args.high_res,
        scale_factor=args.scale_factor
    )
    
    if success:
        safe_print("Screenshot completed successfully!")
        return 0
    else:
        safe_print("Screenshot failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
