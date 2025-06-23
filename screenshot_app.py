#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網頁截圖工具 - 相容 ChromeDriver 114 版本
檔案名稱：screenshot_app.py

安裝依賴：
  pip install selenium==4.10.0 pillow

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
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import io
from urllib.parse import urlparse

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
        """設定 WebDriver - 相容 ChromeDriver 114"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")
        
        # ChromeDriver 114 相容的參數設定
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # 加快載入速度
        chrome_options.add_argument(f"--window-size={width},{height}")
        
        # 設定用戶代理 - 使用 Chrome 114 對應的版本
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        
        # 移除自動化檢測標誌
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 效能優化設定
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        
        try:
            if self.chromedriver_path and os.path.exists(self.chromedriver_path):
                print(f"🔧 使用本地 ChromeDriver：{self.chromedriver_path}")
                service = Service(executable_path=self.chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                print("🔧 使用系統路徑中的 ChromeDriver")
                driver = webdriver.Chrome(options=chrome_options)
            
            # 移除 webdriver 屬性（避免檢測）
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
            
        except Exception as e:
            print(f"❌ 錯誤：無法啟動 Chrome 瀏覽器")
            print(f"詳細錯誤：{e}")
            print("\n🔧 請確認：")
            print("1. 已安裝 Chrome 114.x 版本瀏覽器")
            print("2. ChromeDriver 114 版本位於正確位置")
            print("3. Selenium 版本：pip install selenium==4.10.0")
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
            print(f"⚠️  頁面載入等待超時：{e}")
    
    def capture_screenshot(self, url, output_path="screenshot.png", width=1920, height=1080, full_page=True, wait_time=3, dpi=1.0, quality=95):
        """截取網頁截圖"""
        
        # 驗證 URL
        if not self.validate_url(url):
            print(f"❌ 錯誤：無效的 URL 格式：{url}")
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
            print(f"🚀 正在啟動 Chrome 瀏覽器...")
            driver = self.setup_driver(actual_width, actual_height)
            
            if not driver:
                return False
            
            print(f"🌐 正在載入網頁：{url}")
            driver.get(url)
            
            # 智能等待頁面載入
            print(f"⏳ 等待頁面載入...")
            self.wait_for_page_load(driver)
            
            # 額外等待時間
            if wait_time > 0:
                print(f"⏳ 額外等待 {wait_time} 秒...")
                time.sleep(wait_time)
            
            # 設定 DPI 縮放
            if dpi != 1.0:
                driver.execute_script(f"document.body.style.zoom = '{dpi}';")
                time.sleep(1)
            
            if full_page:
                print("📸 正在截取完整頁面...")
                return self.capture_full_page(driver, output_path, quality)
            else:
                print("📸 正在截取可視區域...")
                screenshot = driver.get_screenshot_as_png()
                self.save_screenshot(screenshot, output_path, quality)
                print(f"✅ 截圖已保存：{output_path}")
                return True
                
        except Exception as e:
            print(f"❌ 截圖失敗：{e}")
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
            print(f"❌ 保存截圖失敗：{e}")
            raise
    
    def capture_full_page(self, driver, output_path, quality=95):
        """截取完整頁面（包含滾動區域）- 相容 Chrome 114"""
        try:
            # 獲取當前視窗尺寸
            original_size = driver.get_window_size()
            
            # 獲取頁面完整尺寸
            total_width = driver.execute_script("return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth, document.body.offsetWidth, document.documentElement.offsetWidth, document.body.clientWidth, document.documentElement.clientWidth)")
            total_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, document.body.offsetHeight, document.documentElement.offsetHeight, document.body.clientHeight, document.documentElement.clientHeight)")
            
            print(f"📏 頁面完整尺寸：{total_width} x {total_height}")
            
            # 限制最大尺寸（避免記憶體問題）
            max_width = 7680  # 8K 寬度
            max_height = 20000  # 20K 高度
            
            if total_width > max_width:
                print(f"⚠️  頁面寬度超過限制，調整為 {max_width}px")
                total_width = max_width
                
            if total_height > max_height:
                print(f"⚠️  頁面高度超過限制，調整為 {max_height}px")
                total_height = max_height
            
            # 滾動到頂部
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # 設定瀏覽器視窗大小為頁面完整尺寸
            driver.set_window_size(total_width, total_height)
            time.sleep(3)  # 給更多時間讓頁面調整
            
            # 再次滾動到頂部確保正確位置
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # 截圖
            screenshot = driver.get_screenshot_as_png()
            self.save_screenshot(screenshot, output_path, quality)
            
            # 恢復原始視窗大小
            driver.set_window_size(original_size['width'], original_size['height'])
            
            print(f"✅ 完整頁面截圖已保存：{output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 完整頁面截圖失敗：{e}")
            import traceback
            traceback.print_exc()
            return False

def create_parser():
    """建立命令列參數解析器"""
    parser = argparse.ArgumentParser(
        description="網頁截圖工具 - 相容 ChromeDriver 114 版本",
        epilog="""
使用範例：
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
        help='要截圖的網頁 URL（支援 http://、https:// 或直接輸入網域名稱）'
    )
    
    # 可選參數
    parser.add_argument(
        '-o', '--output',
        default='screenshot.png',
        help='輸出檔案名稱（預設：screenshot.png）'
    )
    
    parser.add_argument(
        '-w', '--width',
        type=int,
        default=1920,
        help='瀏覽器視窗寬度（預設：1920）'
    )
    
    parser.add_argument(
        '--height',
        type=int,
        default=1080,
        help='瀏覽器視窗高度（預設：1080）'
    )
    
    # 預設解析度選項
    parser.add_argument(
        '--mobile',
        action='store_true',
        help='使用手機解析度（375x812）'
    )
    
    parser.add_argument(
        '--tablet',
        action='store_true',
        help='使用平板解析度（768x1024）'
    )
    
    parser.add_argument(
        '--hd',
        action='store_true',
        help='使用HD解析度（1366x768）'
    )
    
    parser.add_argument(
        '--fhd',
        action='store_true',
        help='使用Full HD解析度（1920x1080）'
    )
    
    parser.add_argument(
        '--qhd',
        action='store_true',
        help='使用QHD解析度（2560x1440）'
    )
    
    parser.add_argument(
        '--uhd',
        action='store_true',
        help='使用4K解析度（3840x2160）'
    )
    
    parser.add_argument(
        '--no-full-page',
        action='store_true',
        help='只截取可視區域，不截取完整頁面'
    )
    
    parser.add_argument(
        '--wait',
        type=int,
        default=3,
        help='頁面載入等待時間（秒，預設：3）'
    )
    
    parser.add_argument(
        '--dpi',
        type=float,
        default=1.0,
        help='螢幕縮放比例/DPI（預設：1.0，高解析度螢幕可用 2.0）'
    )
    
    parser.add_argument(
        '--quality',
        type=int,
        default=95,
        choices=range(1, 101),
        help='JPEG 圖片品質 1-100（預設：95，僅對 .jpg/.jpeg 有效）'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='WebScreenshot 1.0.2 (ChromeDriver 114 Compatible)'
    )
    
    return parser

def main():
    """主函數"""
    # 檢查 Python 版本
    if sys.version_info < (3, 7):
        print("❌ 錯誤：需要 Python 3.7 或更新版本")
        return 1
    
    # 如果沒有參數，顯示互動式介面
    if len(sys.argv) == 1:
        print("=== 🖼️  網頁截圖工具 (ChromeDriver 114) ===")
        print("請輸入要截圖的網頁 URL：")
        url = input("URL: ").strip()
        
        if not url:
            print("❌ 錯誤：請提供有效的 URL")
            return 1
        
        output_name = input("輸出檔名（直接按 Enter 使用預設）: ").strip()
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
        print("📱 使用手機解析度：375x812")
    elif args.tablet:
        width, height = 768, 1024
        print("📱 使用平板解析度：768x1024")
    elif args.hd:
        width, height = 1366, 768
        print("🖥️ 使用HD解析度：1366x768")
    elif args.fhd:
        width, height = 1920, 1080
        print("🖥️ 使用Full HD解析度：1920x1080")
    elif args.qhd:
        width, height = 2560, 1440
        print("🖥️ 使用QHD解析度：2560x1440")
    elif args.uhd:
        width, height = 3840, 2160
        print("🖥️ 使用4K解析度：3840x2160")
    
    # 建立截圖工具
    tool = WebScreenshotTool()
    
    # 執行截圖
    print(f"=== 🖼️  網頁截圖工具 v1.0.2 (ChromeDriver 114) ===")
    print(f"🎯 目標 URL：{args.url}")
    print(f"📁 輸出檔案：{args.output}")
    print(f"📐 視窗尺寸：{width} x {height}")
    if args.dpi != 1.0:
        print(f"🔍 DPI 縮放：{args.dpi}x（實際：{int(width*args.dpi)} x {int(height*args.dpi)}）")
    print(f"📄 完整頁面：{'否' if args.no_full_page else '是'}")
    print(f"⏱️  等待時間：{args.wait} 秒")
    if args.output.lower().endswith(('.jpg', '.jpeg')):
        print(f"🎨 JPEG 品質：{args.quality}%")
    print("-" * 60)
    
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
        print("✅ 截圖完成！")
        return 0
    else:
        print("❌ 截圖失敗！")
        return 1

if __name__ == "__main__":
    sys.exit(main())
