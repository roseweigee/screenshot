#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網頁截圖工具 - 增強版，支援範圍截圖功能
"""

import argparse
import sys
import os
import time
import io
from urllib.parse import urlparse

# Windows 編碼修正
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
except ImportError:
    print("Error: Missing required packages. Please install:")
    print("pip install selenium>=4.15.0")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Missing Pillow package. Please install:")
    print("pip install pillow")
    sys.exit(1)

def safe_print(message):
    """安全的 print 函數"""
    try:
        print(message)
    except UnicodeEncodeError:
        ascii_message = message.encode('ascii', 'replace').decode('ascii')
        print(ascii_message)

class WebScreenshotTool:
    def __init__(self, chromedriver_path=None):
        self.chromedriver_path = chromedriver_path or self.find_chromedriver()
    
    def find_chromedriver(self):
        """尋找 ChromeDriver"""
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
        """設定 WebDriver"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument(f"--window-size={width},{height}")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        
        try:
            if self.chromedriver_path and os.path.exists(self.chromedriver_path):
                safe_print(f"Using local ChromeDriver: {self.chromedriver_path}")
                service = Service(executable_path=self.chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                safe_print("Using system ChromeDriver")
                driver = webdriver.Chrome(options=chrome_options)
            
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except:
                pass
            
            return driver
            
        except Exception as e:
            safe_print(f"Error: Unable to start Chrome browser: {e}")
            return None
    
    def validate_url(self, url):
        """驗證 URL"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def wait_for_page_load(self, driver, timeout=30):
        """等待頁面載入"""
        try:
            WebDriverWait(driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)
        except Exception as e:
            safe_print(f"Page load timeout: {e}")
    
    def save_screenshot(self, screenshot_data, output_path, quality=95):
        """保存截圖"""
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
    
    def capture_range_screenshot(self, driver, output_path, start_height=0, end_height=None, quality=95):
        """截取範圍截圖"""
        try:
            original_size = driver.get_window_size()
            
            # 獲取頁面總高度
            try:
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
                total_height = original_size['height']
            
            # 驗證範圍參數
            if end_height is None:
                end_height = total_height
                safe_print(f"未指定結束高度，使用頁面總高度: {end_height}px")
            
            if start_height < 0:
                start_height = 0
            
            if end_height > total_height:
                end_height = total_height
            
            if start_height >= end_height:
                safe_print(f"錯誤: 起始高度必須小於結束高度")
                return False
            
            range_height = end_height - start_height
            safe_print(f"截圖範圍: {start_height}px → {end_height}px (高度: {range_height}px)")
            
            # 滾動到起始位置
            driver.execute_script(f"window.scrollTo(0, {start_height});")
            time.sleep(2)
            
            viewport_height = original_size['height']
            
            if range_height <= viewport_height:
                # 單次截圖
                safe_print("範圍高度適合單次截圖")
                screenshot = driver.get_screenshot_as_png()
                
                if range_height < viewport_height:
                    try:
                        image = Image.open(io.BytesIO(screenshot))
                        crop_bottom = int((range_height / viewport_height) * image.height)
                        cropped_image = image.crop((0, 0, image.width, crop_bottom))
                        
                        buffer = io.BytesIO()
                        cropped_image.save(buffer, format='PNG')
                        screenshot = buffer.getvalue()
                        safe_print("已裁切圖片至指定範圍")
                    except Exception as e:
                        safe_print(f"圖片裁切失敗，使用原始截圖: {e}")
                
                self.save_screenshot(screenshot, output_path, quality)
                return True
            else:
                # 分段截圖
                return self.capture_range_by_segments(driver, output_path, start_height, end_height, quality, original_size)
                
        except Exception as e:
            safe_print(f"範圍截圖失敗: {e}")
            return False
    
    def capture_range_by_segments(self, driver, output_path, start_height, end_height, quality, original_size):
        """分段截圖並拼接"""
        try:
            safe_print("使用分段截圖方法...")
            
            viewport_height = original_size['height']
            segments = []
            current_pos = start_height
            segment_count = 0
            
            while current_pos < end_height:
                segment_end = min(current_pos + viewport_height, end_height)
                actual_height = segment_end - current_pos
                
                safe_print(f"截圖段 {segment_count + 1}: {current_pos}px → {segment_end}px")
                
                driver.execute_script(f"window.scrollTo(0, {current_pos});")
                time.sleep(1)
                
                screenshot = driver.get_screenshot_as_png()
                image = Image.open(io.BytesIO(screenshot))
                
                if actual_height < viewport_height:
                    crop_height = int((actual_height / viewport_height) * image.height)
                    image = image.crop((0, 0, image.width, crop_height))
                
                segments.append(image)
                current_pos = segment_end
                segment_count += 1
            
            if segments:
                total_width = segments[0].width
                total_height = sum(img.height for img in segments)
                
                safe_print(f"拼接 {len(segments)} 個截圖段，總尺寸: {total_width}x{total_height}")
                
                final_image = Image.new('RGB', (total_width, total_height), (255, 255, 255))
                
                y_offset = 0
                for img in segments:
                    final_image.paste(img, (0, y_offset))
                    y_offset += img.height
                
                if output_path.lower().endswith('.png'):
                    final_image.save(output_path, 'PNG')
                else:
                    final_image.save(output_path, 'JPEG', quality=quality, optimize=True)
                
                safe_print(f"分段截圖拼接完成: {output_path}")
                return True
            
            return False
            
        except Exception as e:
            safe_print(f"分段截圖失敗: {e}")
            return False
    
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
    
    def capture_viewport(self, driver, output_path, quality=95):
        """截取視窗截圖"""
        try:
            screenshot = driver.get_screenshot_as_png()
            self.save_screenshot(screenshot, output_path, quality)
            safe_print(f"Viewport screenshot saved: {output_path}")
            return True
        except Exception as e:
            safe_print(f"Viewport screenshot failed: {e}")
            return False
    
    def capture_screenshot(self, url, output_path="screenshot.png", width=1920, height=1080, 
                          full_page=True, wait_time=3, quality=95,
                          start_height=0, end_height=None):
        """主要截圖功能"""
        driver = None
        try:
            safe_print("Starting Chrome browser...")
            driver = self.setup_driver(width, height, True)
            
            if not driver:
                return False
            
            safe_print(f"Loading webpage: {url}")
            driver.get(url)
            
            safe_print("Waiting for page to load...")
            self.wait_for_page_load(driver)
            
            if wait_time > 0:
                safe_print(f"Additional wait: {wait_time} seconds...")
                time.sleep(wait_time)
            
            # 決定截圖模式
            if end_height is not None:
                safe_print("執行範圍截圖...")
                success = self.capture_range_screenshot(driver, output_path, start_height, end_height, quality)
            elif full_page:
                safe_print("Taking full page screenshot...")
                success = self.capture_full_page(driver, output_path, quality)
            else:
                safe_print("Taking viewport screenshot...")
                success = self.capture_viewport(driver, output_path, quality)
            
            return success
                
        except Exception as e:
            safe_print(f"Screenshot failed: {e}")
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
        description="Web Screenshot Tool v2.2.0 with Range Screenshot Support",
        epilog="""
Examples:
  %(prog)s https://www.example.com
  %(prog)s https://example.com --start-height 300 --end-height 1200 --output range.png
  %(prog)s https://example.com --width 1920 --height 1080 --output screenshot.png
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('url', help='Target webpage URL')
    parser.add_argument('-o', '--output', default='screenshot.png', help='Output filename (default: screenshot.png)')
    parser.add_argument('-w', '--width', type=int, default=1920, help='Browser window width (default: 1920)')
    parser.add_argument('--height', type=int, default=1080, help='Browser window height (default: 1080)')
    parser.add_argument('--no-full-page', action='store_true', help='Capture viewport only instead of full page')
    parser.add_argument('--wait', type=int, default=3, help='Wait time in seconds after page load (default: 3)')
    parser.add_argument('--quality', type=int, default=95, choices=range(1, 101), help='JPEG quality 1-100 (default: 95)')
    
    # Range Screenshot Options
    range_group = parser.add_argument_group('Range Screenshot Options')
    range_group.add_argument('--start-height', type=int, default=0, 
                            help='Start height in pixels for range screenshot (default: 0)')
    range_group.add_argument('--end-height', type=int, 
                            help='End height in pixels for range screenshot (if not specified, captures to page end)')
    
    parser.add_argument('--version', action='version', version='WebScreenshot v2.2.0')
    
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
    
    # 驗證範圍參數
    if args.end_height is not None and args.start_height >= args.end_height:
        safe_print(f"Error: Start height ({args.start_height}) must be less than end height ({args.end_height})")
        return 1
    
    # 輸出基本資訊
    safe_print(f"=== Web Screenshot Tool v2.2.0 ===")
    safe_print(f"Target URL: {args.url}")
    safe_print(f"Output file: {args.output}")
    safe_print(f"Window size: {args.width} x {args.height}")
    
    # 顯示截圖模式
    if args.end_height is not None:
        safe_print(f"Screenshot mode: Range ({args.start_height}px → {args.end_height}px)")
    elif args.no_full_page:
        safe_print("Screenshot mode: Viewport")
    else:
        safe_print("Screenshot mode: Full page")
    
    safe_print(f"Wait time: {args.wait} seconds")
    safe_print("-" * 60)
    
    # 執行截圖
    success = tool.capture_screenshot(
        url=args.url,
        output_path=args.output,
        width=args.width,
        height=args.height,
        full_page=not args.no_full_page,
        wait_time=args.wait,
        quality=args.quality,
        start_height=args.start_height,
        end_height=args.end_height
    )
    
    if success:
        safe_print("Screenshot completed successfully!")
        return 0
    else:
        safe_print("Screenshot failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
