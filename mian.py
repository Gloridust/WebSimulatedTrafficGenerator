from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
from tqdm import tqdm
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import tempfile
import psutil
import logging
from datetime import datetime

class ResourceMonitor:
    def __init__(self, max_cpu_percent=70):
        self.max_cpu_percent = max_cpu_percent
        self.lock = threading.Lock()
        self._should_pause = False
        self._monitor_thread = None
    
    def start_monitoring(self):
        self._monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_resources(self):
        while True:
            cpu_percent = psutil.cpu_percent(interval=1)
            with self.lock:
                self._should_pause = cpu_percent > self.max_cpu_percent
            time.sleep(2)
    
    def should_pause(self):
        with self.lock:
            return self._should_pause

class VisitCounter:
    def __init__(self):
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
    
    def increment_success(self):
        with self.lock:
            self.success_count += 1
    
    def increment_fail(self):
        with self.lock:
            self.fail_count += 1
    
    def get_counts(self):
        return self.success_count, self.fail_count
    
    def get_stats(self):
        elapsed_time = time.time() - self.start_time
        visits_per_minute = (self.success_count / elapsed_time) * 60 if elapsed_time > 0 else 0
        return {
            'success': self.success_count,
            'fail': self.fail_count,
            'visits_per_minute': visits_per_minute
        }

def create_driver(user_agent):
    """创建一个配置好的 Chrome driver"""
    chrome_options = Options()
    
    # 基本配置
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument('--headless=new')  # 使用新的无头模式
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # 内存和CPU优化
    chrome_options.add_argument('--js-flags=--expose-gc,--max-old-space-size=128')
    chrome_options.add_argument('--single-process')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--disable-sync')
    
    # 禁用不必要的功能
    prefs = {
        'profile.managed_default_content_settings.images': 2,  # 禁用图片
        'profile.managed_default_content_settings.javascript': 2,  # 禁用JavaScript
        'profile.managed_default_content_settings.cookies': 2,  # 禁用Cookie
        'profile.managed_default_content_settings.plugins': 2,  # 禁用插件
        'profile.managed_default_content_settings.popups': 2,  # 禁用弹窗
        'profile.managed_default_content_settings.geolocation': 2,  # 禁用地理位置
        'profile.managed_default_content_settings.media_stream': 2,  # 禁用媒体流
    }
    chrome_options.add_experimental_option('prefs', prefs)
    
    return webdriver.Chrome(options=chrome_options)

def natural_scroll(driver):
    """自然的滚动行为"""
    try:
        # 获取页面高度
        total_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        
        # 计算需要滚动的次数
        scroll_times = min(3, max(1, total_height // viewport_height))
        
        for _ in range(scroll_times):
            # 随机滚动位置
            scroll_y = random.randint(viewport_height // 2, viewport_height)
            driver.execute_script(f"window.scrollBy(0, {scroll_y});")
            # 模拟阅读时间
            time.sleep(random.uniform(1.5, 3.0))
    
    except Exception as e:
        logging.warning(f"滚动过程出错: {str(e)}")

def visit_once(url, pbar, ua, counter, resource_monitor, max_retries=2):
    """单次访问函数"""
    driver = None
    for retry in range(max_retries):
        # 检查CPU使用率
        while resource_monitor.should_pause():
            time.sleep(1)
        
        try:
            random_ua = ua.random
            driver = create_driver(random_ua)
            
            start_time = time.time()
            driver.get(url)
            
            # 模拟真实浏览行为
            natural_scroll(driver)
            
            # 记录成功
            counter.increment_success()
            stats = counter.get_stats()
            
            visit_time = time.time() - start_time
            pbar.write(
                f'访问成功 [耗时: {visit_time:.1f}秒] '
                f'[成功: {stats["success"]}] '
                f'[失败: {stats["fail"]}] '
                f'[速率: {stats["visits_per_minute"]:.1f}/分钟]'
            )
            pbar.update(1)
            break
            
        except Exception as e:
            if retry == max_retries - 1:
                counter.increment_fail()
                pbar.write(f'访问失败 (重试 {retry + 1}/{max_retries}): {str(e)}')
        finally:
            if driver:
                driver.quit()
                del driver  # 确保释放内存

def visit_url(url, times, max_workers=5):
    """多线程访问指定URL指定次数"""
    ua = UserAgent()
    counter = VisitCounter()
    resource_monitor = ResourceMonitor(max_cpu_percent=70)
    resource_monitor.start_monitoring()
    
    with tqdm(total=times, desc="访问进度") as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(visit_once, url, pbar, ua, counter, resource_monitor)
                for _ in range(times)
            ]
            for future in futures:
                future.result()
    
    # 显示最终统计
    stats = counter.get_stats()
    print(f"\n访问统计:")
    print(f"成功次数: {stats['success']}")
    print(f"失败次数: {stats['fail']}")
    print(f"成功率: {(stats['success']/times*100):.1f}%")
    print(f"平均访问速度: {stats['visits_per_minute']:.1f} 次/分钟")

def main():
    print("欢迎使用网页访问量刷新工具（多线程版）")
    url = input("请输入要访问的网址: ")
    
    while True:
        try:
            times = int(input("请输入要访问的次数: "))
            if times > 0:
                break
            print("请输入大于0的数字")
        except ValueError:
            print("请输入有效的数字")
    
    while True:
        try:
            threads = int(input("请输入并行线程数(建议1-10): "))
            if 1 <= threads <= 20:
                break
            print("请输入1-20之间的数字")
        except ValueError:
            print("请输入有效的数字")
    
    print(f"\n开始访问 {url}...")
    print(f"使用 {threads} 个并行线程")
    visit_url(url, times, max_workers=threads)
    print("\n访问完成！")

if __name__ == "__main__":
    main()
