from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent
from tqdm import tqdm
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

class VisitCounter:
    def __init__(self):
        self.count = 0
        self.lock = threading.Lock()
    
    def increment(self):
        with self.lock:
            self.count += 1
            return self.count

def create_driver(user_agent):
    """创建一个配置好的 Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    return webdriver.Chrome(options=chrome_options)

def visit_once(url, pbar, ua):
    """单次访问函数"""
    try:
        random_ua = ua.random
        driver = create_driver(random_ua)
        
        pbar.write(f'正在使用用户代理: {random_ua}')
        driver.get(url)
        
        wait_time = random.uniform(1, 3)
        time.sleep(wait_time)
        
        driver.quit()
        pbar.update(1)
        
    except Exception as e:
        pbar.write(f'访问出错: {str(e)}')

def visit_url(url, times, max_workers=5):
    """多线程访问指定URL指定次数"""
    ua = UserAgent()
    
    with tqdm(total=times, desc="访问进度") as pbar:
        # 使用线程池
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            futures = [
                executor.submit(visit_once, url, pbar, ua)
                for _ in range(times)
            ]
            # 等待所有任务完成
            for future in futures:
                future.result()

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
