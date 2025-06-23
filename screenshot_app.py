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
    
    def setup_driver(self, width=1920, height=1080, headless=True):
        """設定 WebDriver - 相容 Chrome 129"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
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
        
        # 設定用戶代理
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
        
        # 移除自動化檢測標誌
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 效能優化設定
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        
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
    
    def grafana_login(self, driver, base_url, username, password):
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
    
    def capture_full_page(self, driver, output_path, quality=95):
        """截取完整頁面"""
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
            
            safe_print(f"Full page dimensions: {total_width} x {total_height}")
            
            max_width = 7680
            max_height = 20000
            
            if total_width > max_width:
                total_width = max_width
            if total_height > max_height:
                total_height = max_height
            
            try:
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                driver.set_window_size(total_width, total_height)
                time.sleep(3)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except:
                pass
            
            screenshot = driver.get_screenshot_as_png()
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
    
    def capture_screenshot(self, url, output_path="screenshot.png", width=1920, height=1080, 
                          full_page=True, wait_time=3, dpi=1.0, quality=95,
                          username=None, password=None):
        """主要截圖功能 - 支援 Grafana 登入"""
        
        # 根據 DPI 調整解析度
        actual_width = int(width * dpi)
        actual_height = int(height * dpi)
        
        driver = None
        try:
            safe_print(f"Starting Chrome browser...")
            driver = self.setup_driver(actual_width, actual_height, True)
            
            if not driver:
                return False
            
            # 檢查是否需要 Grafana 登入
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            need_login = username and password
            
            if need_login:
                # 執行 Grafana 登入
                safe_print(f"檢測到登入認證，嘗試 Grafana 登入...")
                login_success = self.grafana_login(driver, base_url, username, password)
                
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
        description="Web Screenshot Tool v2.1.0 (Chrome 129 Compatible) with Grafana Login Support",
        epilog="""
Examples:
  %(prog)s https://www.example.com
  %(prog)s https://grafana.com/dashboard --username admin --password 123456
  %(prog)s https://example.com --width 1920 --height 1080 --output screenshot.png
  %(prog)s https://example.com --no-full-page --wait 5 --quality 90
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
    
    # Grafana 登入參數（新增）
    auth_group = parser.add_argument_group('Authentication Options (for Grafana)')
    auth_group.add_argument('--username', help='Username for Grafana login')
    auth_group.add_argument('--password', help='Password for Grafana login')
    
    parser.add_argument('--version', action='version', version='WebScreenshot v2.1.0 (Chrome 129 Compatible)')
    
    return parser

def main():
    """主函數"""
    parser = create_parser()
    args = parser.parse_args()
    
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
    if args.username:
        safe_print(f"Username: {args.username}")
        safe_print("Authentication: Enabled (Grafana mode)")
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
        password=args.password
    )
    
    if success:
        safe_print("Screenshot completed successfully!")
        return 0
    else:
        safe_print("Screenshot failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
