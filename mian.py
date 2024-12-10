from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
from tqdm import tqdm
import time
import random
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import os
import tempfile
import requests
from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool
import urllib3

# 增加连接池最大数量
urllib3.PoolManager(maxsize=100)
HTTPConnection.default_socket_options = (
    HTTPConnection.default_socket_options + [
        ('TCP_NODELAY', 1),
        ('SO_KEEPALIVE', 1),
    ]
)

class VisitCounter:
    def __init__(self):
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
    
    def increment_success(self):
        with self.lock:
            self.success_count += 1
    
    def increment_fail(self):
        with self.lock:
            self.fail_count += 1
    
    def get_counts(self):
        return self.success_count, self.fail_count

def get_cache_dir():
    """获取或创建缓存目录"""
    cache_dir = os.path.join(tempfile.gettempdir(), 'chrome_cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return cache_dir

def create_driver(user_agent):
    """创建一个配置好的 Chrome driver"""
    chrome_options = Options()
    
    # 基本配置
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--disable-web-security')
    
    # 缓存和性能优化配置
    cache_dir = get_cache_dir()
    chrome_options.add_argument(f'--disk-cache-dir={cache_dir}')
    chrome_options.add_argument('--disk-cache-size=104857600')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-translate')
    chrome_options.add_argument('--disable-features=TranslateUI')
    chrome_options.add_argument('--disable-sync')
    chrome_options.add_argument('--disable-background-networking')
    
    # 内存优化
    chrome_options.add_argument('--js-flags=--expose-gc')
    chrome_options.add_argument('--single-process')
    chrome_options.add_argument('--no-zygote')
    chrome_options.add_argument('--no-first-run')
    
    prefs = {
        'profile.default_content_settings.popups': 0,
        'profile.default_content_setting_values.notifications': 2,
        'disk-cache-size': 104857600,
        'profile.default_content_setting_values.cookies': 1,
        'profile.cookie_controls_mode': 0,
        'profile.managed_default_content_settings.images': 2,  # 禁用图片加载
    }
    chrome_options.add_experimental_option('prefs', prefs)
    
    return webdriver.Chrome(options=chrome_options)

def scroll_page(driver):
    """模拟页面滚动，更自然的浏览行为"""
    try:
        total_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.body.offsetHeight, "
            "document.documentElement.clientHeight, document.documentElement.scrollHeight, "
            "document.documentElement.offsetHeight);"
        )
        current_position = 0
        
        # 将页面分成多个部分进行滚动
        sections = random.randint(4, 8)  # 随机分成4-8个部分
        scroll_step = total_height // sections
        
        for _ in range(sections):
            if current_position >= total_height:
                break
                
            # 随机滚动步长
            step = random.randint(scroll_step - 100, scroll_step + 100)
            scroll_y = min(step, total_height - current_position)
            
            # 执行滚动
            driver.execute_script(f"window.scrollBy(0, {scroll_y});")
            current_position += scroll_y
            
            # 在每个部分停留随机时间，模拟阅读
            time.sleep(random.uniform(0.5, 1.5))
            
            # 随机小幅上下滚动，模拟阅读行为
            if random.random() < 0.3:  # 30%的概率执行
                small_scroll = random.randint(-100, 100)
                driver.execute_script(f"window.scrollBy(0, {small_scroll});")
                time.sleep(random.uniform(0.3, 0.8))
                
    except Exception as e:
        print(f"滚动过程出错: {str(e)}")

async def simulate_reading(duration):
    """模拟阅读时间"""
    await asyncio.sleep(duration)

def visit_once(url, pbar, ua, counter, max_retries=3):
    """单次访问函数"""
    driver = None
    for retry in range(max_retries):
        try:
            random_ua = ua.random
            driver = create_driver(random_ua)
            
            driver.set_page_load_timeout(20)  # 略微增加超时时间
            driver.set_script_timeout(20)
            
            start_time = time.time()
            driver.get(url)
            
            # 等待页面加载完成
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # 模拟真实阅读行为
            scroll_page(driver)
            
            # 使用异步等待模拟阅读时间
            reading_time = random.uniform(5, 15)  # 5-15秒的阅读时间
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(simulate_reading(reading_time))
            loop.close()
            
            # 记录成功访问
            counter.increment_success()
            pbar.update(1)
            
            # 显示访问统计
            success, fail = counter.get_counts()
            total_time = time.time() - start_time
            pbar.write(f'成功: {success}, 失败: {fail}, 停留: {reading_time:.1f}秒, 总耗时: {total_time:.1f}秒')
            break
            
        except Exception as e:
            if retry == max_retries - 1:
                counter.increment_fail()
                pbar.write(f'访问失败 ({retry + 1}/{max_retries}): {str(e)}')
        finally:
            if driver:
                driver.quit()

def visit_url(url, times, max_workers=5):
    """多线程访问指定URL指定次数"""
    ua = UserAgent()
    counter = VisitCounter()
    
    with tqdm(total=times, desc="访问进度") as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(visit_once, url, pbar, ua, counter)
                for _ in range(times)
            ]
            # 使用as_completed来避免线程阻塞
            for future in futures:
                future.result()
    
    # 显示最终统计
    success, fail = counter.get_counts()
    print(f"\n访问统计:")
    print(f"成功: {success}")
    print(f"失败: {fail}")
    print(f"成功率: {(success/times*100):.1f}%")

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
