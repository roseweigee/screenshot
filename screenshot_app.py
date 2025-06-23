#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網頁截圖工具 - 離線環境 Chrome 129 相容版本
檔案名稱：screenshot_app.py

相容版本：
- Chrome: 129.0.6668.90
- ChromeDriver: 需要 129.x 版本
- Selenium: 4.15.0+

安裝依賴：
  pip install selenium>=4.15.0 pillow

使用方法：
  WebScreenshot.exe https://www.example.com
  WebScreenshot.exe https://www.example.com --output my_screenshot.png
  WebScreenshot.exe https://www.example.com --width 1920 --height 1080
  WebScreenshot.exe --help

建立 EXE 方法：
  pyinstaller --onefile --console --name="WebScreenshot" screenshot_app.py
"""

import argparse
import sys
import os
import time
import locale
import io
from urllib.parse import urlparse

# 修正 Windows 控制台編碼問題
if sys.platform.startswith('win'):
    try:
        # 設定控制台為 UTF-8
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        # 如果 reconfigure 不可用，使用替代方法
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
        # 如果仍有編碼問題，轉換為 ASCII
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
            chrome_options.add_argument("--headless=new")  # 使用新的 headless 模式
        
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
        
        # 設定用戶代理 - 使用 Chrome 129 對應的版本
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
        
        # 移除自動化檢測標誌
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 效能優化設定
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        
        # 離線模式設定（如果需要）
        chrome_options.add_argument("--aggressive-cache-discard")
        chrome_options.add_argument("--disable-background-networking")
        
        # 忽略證書錯誤
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--ignore-certificate-errors-spki-list")
        
        try:
            if self.chromedriver_path and os.path.exists(self.chromedriver_path):
                safe_print(f"Using local ChromeDriver: {self.chromedriver_path}")
                
                # 檢查 ChromeDriver 版本
                try:
                    import subprocess
                    result = subprocess.run([self.chromedriver_path, "--version"], 
                                          capture_output=True, text=True, timeout=10)
                    version_info = result.stdout.strip()
                    safe_print(f"ChromeDriver version: {version_info}")
                    
                    # 檢查版本匹配
                    if "114." in version_info:
                        safe_print("WARNING: ChromeDriver 114 detected, but Chrome 129 is installed")
                        safe_print("This may cause compatibility issues")
                        safe_print("Recommended: Download ChromeDriver 129.x from:")
                        safe_print("https://googlechromelabs.github.io/chrome-for-testing/")
                        
                        # 嘗試使用相容性模式
                        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
                        chrome_options.add_argument("--disable-gpu-sandbox")
                        
                except Exception as e:
                    safe_print(f"Cannot check ChromeDriver version: {e}")
                
                service = Service(executable_path=self.chromedriver_path)
                
                # 對於舊版 ChromeDriver，使用舊的語法
                try:
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                except Exception as e:
                    if "executable_path" in str(e):
                        # 嘗試舊的語法（適用於更舊的 Selenium 版本）
                        driver = webdriver.Chrome(executable_path=self.chromedriver_path, 
                                                chrome_options=chrome_options)
                    else:
                        raise e
            else:
                safe_print("Using system ChromeDriver")
                driver = webdriver.Chrome(options=chrome_options)
            
            # 移除 webdriver 屬性（避免檢測）
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except:
                pass  # 如果執行失敗，繼續
            
            return driver
            
        except Exception as e:
            safe_print(f"Error: Unable to start Chrome browser")
            safe_print(f"Details: {e}")
            safe_print("\nPossible solutions:")
            safe_print("1. Download ChromeDriver 129.x compatible with Chrome 129:")
            safe_print("   https://googlechromelabs.github.io/chrome-for-testing/")
            safe_print("2. Or downgrade Chrome to version 114 to match your ChromeDriver")
            safe_print("3. Update Selenium: pip install selenium>=4.15.0")
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
            # 等待 document ready state
            WebDriverWait(driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # 額外等待 JavaScript 執行
            time.sleep(2)
            
            # 檢查是否有 jQuery，如果有則等待它完成
            try:
                if driver.execute_script("return typeof jQuery !== 'undefined'"):
                    WebDriverWait(driver, 10).until(
                        lambda driver: driver.execute_script("return jQuery.active == 0")
                    )
            except:
                pass  # 沒有 jQuery 或執行失敗，繼續
                
        except Exception as e:
            safe_print(f"Page load timeout: {e}")
    
    def capture_screenshot(self, url, output_path="screenshot.png", width=1920, height=1080, full_page=True, wait_time=3, dpi=1.0, quality=95):
        """截取網頁截圖"""
        
        # 驗證 URL
        if not self.validate_url(url):
            safe_print(f"Error: Invalid URL format: {url}")
            return False
        
        # 確保 URL 有協議
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # 確保輸出檔案有副檔名
        if not output_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            output_path += '.png'
        
        # 根據 DPI 調整解析度
        actual_width = int(width * dpi)
        actual_height = int(height * dpi)
        
        driver = None
        try:
            safe_print(f"Starting Chrome browser...")
            driver = self.setup_driver(actual_width, actual_height)
            
            if not driver:
                return False
            
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
    
    def save_screenshot(self, screenshot_data, output_path, quality=95):
        """保存截圖並優化品質"""
        try:
            # 如果是 PNG，直接保存
            if output_path.lower().endswith('.png'):
                with open(output_path, 'wb') as file:
                    file.write(screenshot_data)
            else:
                # 如果是 JPEG，轉換並設定品質
                image = Image.open(io.BytesIO(screenshot_data))
                # 轉換為 RGB（JPEG 不支援透明度）
                if image.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = background
                
                image.save(output_path, 'JPEG', quality=quality, optimize=True)
        except Exception as e:
            safe_print(f"Save screenshot failed: {e}")
            raise
    
    def capture_full_page(self, driver, output_path, quality=95):
        """截取完整頁面（包含滾動區域）- 相容 Chrome 129"""
        try:
            # 獲取當前視窗尺寸
            original_size = driver.get_window_size()
            
            # 獲取頁面完整尺寸 - 使用更可靠的方法
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
                safe_print(f"Failed to get page dimensions, using viewport size: {e}")
                total_width = original_size['width']
                total_height = original_size['height']
            
            safe_print(f"Full page dimensions: {total_width} x {total_height}")
            
            # 限制最大尺寸（避免記憶體問題）
            max_width = 7680  # 8K 寬度
            max_height = 20000  # 20K 高度
            
            if total_width > max_width:
                safe_print(f"Width exceeds limit, adjusting to {max_width}px")
                total_width = max_width
                
            if total_height > max_height:
                safe_print(f"Height exceeds limit, adjusting to {max_height}px")
                total_height = max_height
            
            # 滾動到頂部
            try:
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except:
                pass
            
            # 設定瀏覽器視窗大小為頁面完整尺寸
            try:
                driver.set_window_size(total_width, total_height)
                time.sleep(3)  # 給更多時間讓頁面調整
            except Exception as e:
                safe_print(f"Failed to resize window: {e}")
                # 如果無法調整視窗大小，使用原始大小
            
            # 再次滾動到頂部確保正確位置
            try:
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except:
                pass
            
            # 截圖
            screenshot = driver.get_screenshot_as_png()
            self.save_screenshot(screenshot, output_path, quality)
            
            # 恢復原始視窗大小
            try:
                driver.set_window_size(original_size['width'], original_size['height'])
            except:
                pass
            
            safe_print(f"Full page screenshot saved: {output_path}")
            return True
            
        except Exception as e:
            safe_print(f"Full page screenshot failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def create_parser():
    """建立命令列參數解析器"""
    parser = argparse.ArgumentParser(
        description="Web Screenshot Tool - Compatible with Chrome 129",
        epilog="""
Examples:
  %(prog)s https://www.google.com
  %(prog)s www.example.com --output example.png
  %(prog)s https://github.com --width 1920 --height 1080 --no-full-page
  %(prog)s https://www.apple.com --wait 5 --output apple_screenshot.jpg
  %(prog)s https://www.site.com --uhd --quality 95
  %(prog)s https://www.site.com --mobile
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 必要參數
    parser.add_argument(
        'url',
        help='Target webpage URL (supports http://, https:// or direct domain)'
    )
    
    # 可選參數
    parser.add_argument(
        '-o', '--output',
        default='screenshot.png',
        help='Output filename (default: screenshot.png)'
    )
    
    parser.add_argument(
        '-w', '--width',
        type=int,
        default=1920,
        help='Browser window width (default: 1920)'
    )
    
    parser.add_argument(
        '--height',
        type=int,
        default=1080,
        help='Browser window height (default: 1080)'
    )
    
    # 預設解析度選項
    parser.add_argument(
        '--mobile',
        action='store_true',
        help='Use mobile resolution (375x812)'
    )
    
    parser.add_argument(
        '--tablet',
        action='store_true',
        help='Use tablet resolution (768x1024)'
    )
    
    parser.add_argument(
        '--hd',
        action='store_true',
        help='Use HD resolution (1366x768)'
    )
    
    parser.add_argument(
        '--fhd',
        action='store_true',
        help='Use Full HD resolution (1920x1080)'
    )
    
    parser.add_argument(
        '--qhd',
        action='store_true',
        help='Use QHD resolution (2560x1440)'
    )
    
    parser.add_argument(
        '--uhd',
        action='store_true',
        help='Use 4K resolution (3840x2160)'
    )
    
    parser.add_argument(
        '--no-full-page',
        action='store_true',
        help='Capture viewport only, not full page'
    )
    
    parser.add_argument(
        '--wait',
        type=int,
        default=3,
        help='Page load wait time in seconds (default: 3)'
    )
    
    parser.add_argument(
        '--dpi',
        type=float,
        default=1.0,
        help='DPI scaling factor (default: 1.0, use 2.0 for high-DPI)'
    )
    
    parser.add_argument(
        '--quality',
        type=int,
        default=95,
        choices=range(1, 101),
        help='JPEG quality 1-100 (default: 95, only for .jpg/.jpeg)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='WebScreenshot 2.0.0 (Chrome 129 Compatible, Offline Ready)'
    )
    
    return parser

def main():
    """主函數"""
    # 檢查 Python 版本
    if sys.version_info < (3, 7):
        safe_print("Error: Python 3.7 or newer required")
        return 1
    
    # 如果沒有參數，顯示互動式介面
    if len(sys.argv) == 1:
        safe_print("=== Web Screenshot Tool (Chrome 129 Compatible) ===")
        safe_print("Enter target webpage URL:")
        try:
            url = input("URL: ").strip()
        except (EOFError, KeyboardInterrupt):
            safe_print("\nOperation cancelled")
            return 1
        
        if not url:
            safe_print("Error: Please provide a valid URL")
            return 1
        
        try:
            output_name = input("Output filename (press Enter for default): ").strip()
        except (EOFError, KeyboardInterrupt):
            output_name = ""
        
        if not output_name:
            output_name = "screenshot.png"
        
        tool = WebScreenshotTool()
        success = tool.capture_screenshot(url, output_name)
        return 0 if success else 1
    
    # 解析命令列參數
    parser = create_parser()
    args = parser.parse_args()
    
    # 處理預設解析度選項
    width, height = args.width, args.height
    
    if args.mobile:
        width, height = 375, 812
        safe_print("Using mobile resolution: 375x812")
    elif args.tablet:
        width, height = 768, 1024
        safe_print("Using tablet resolution: 768x1024")
    elif args.hd:
        width, height = 1366, 768
        safe_print("Using HD resolution: 1366x768")
    elif args.fhd:
        width, height = 1920, 1080
        safe_print("Using Full HD resolution: 1920x1080")
    elif args.qhd:
        width, height = 2560, 1440
        safe_print("Using QHD resolution: 2560x1440")
    elif args.uhd:
        width, height = 3840, 2160
        safe_print("Using 4K resolution: 3840x2160")
    
    # 建立截圖工具
    tool = WebScreenshotTool()
    
    # 執行截圖
    safe_print(f"=== Web Screenshot Tool v2.0.0 (Chrome 129 Compatible) ===")
    safe_print(f"Target URL: {args.url}")
    safe_print(f"Output file: {args.output}")
    safe_print(f"Window size: {width} x {height}")
    if args.dpi != 1.0:
        safe_print(f"DPI scaling: {args.dpi}x (actual: {int(width*args.dpi)} x {int(height*args.dpi)})")
    safe_print(f"Full page: {'No' if args.no_full_page else 'Yes'}")
    safe_print(f"Wait time: {args.wait} seconds")
    if args.output.lower().endswith(('.jpg', '.jpeg')):
        safe_print(f"JPEG quality: {args.quality}%")
    safe_print("-" * 60)
    
    success = tool.capture_screenshot(
        url=args.url,
        output_path=args.output,
        width=width,
        height=height,
        full_page=not args.no_full_page,
        wait_time=args.wait,
        dpi=args.dpi,
        quality=args.quality
    )
    
    if success:
        safe_print("Screenshot completed successfully!")
        return 0
    else:
        safe_print("Screenshot failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
