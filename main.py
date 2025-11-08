import os
import time
import uuid
import random
import asyncio
import tempfile
import threading
from typing import Optional

import requests
from tqdm import tqdm
from fake_useragent import UserAgent

# HTTP 异步请求引擎
import aiohttp
from aiohttp import ClientSession, TCPConnector, ClientTimeout, CookieJar

# Selenium 备用（仅在选择浏览器模式时使用）
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

# 尝试启用 undetected-chromedriver（若已安装）
try:
    import undetected_chromedriver as uc
except Exception:
    uc = None

# 仅用于URL处理
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# Playwright 异步（无需 Chromedriver），保证 JS 执行
try:
    from playwright.async_api import async_playwright
except Exception:
    async_playwright = None


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


# UA 回退列表，fake_useragent不可用时使用
FALLBACK_UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
]


def get_random_ua(ua_provider: Optional[UserAgent]) -> str:
    try:
        if ua_provider:
            return ua_provider.random
        return UserAgent().random
    except Exception:
        return random.choice(FALLBACK_UA)


def random_referer(url: str) -> str:
    domain = urlparse(url).netloc
    candidates = [
        f"https://www.google.com/search?q={domain}",
        f"https://www.bing.com/search?q={domain}",
        f"https://duckduckgo.com/?q={domain}",
        f"https://{domain}/",
    ]
    return random.choice(candidates)


def build_headers(ua_string: str, url: str) -> dict:
    # 浏览器更拟真：增加 sec-ch-ua / sec-fetch / accept-encoding / keep-alive 等
    platform = random.choice(["Windows", "macOS", "Linux", "Android", "iOS"])
    sec_ch_ua_platform = {
        "Windows": "\"Windows\"",
        "macOS": "\"macOS\"",
        "Linux": "\"Linux\"",
        "Android": "\"Android\"",
        "iOS": "\"iOS\"",
    }[platform]
    return {
        "User-Agent": ua_string,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice([
            "zh-CN,zh;q=0.9",
            "en-US,en;q=0.9",
            "zh-TW,zh;q=0.9",
        ]),
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
        "Referer": random_referer(url),
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
        # Client Hints & Fetch metadata
        "sec-ch-ua": "\"Chromium\";v=\"120\", \"Not.A/Brand\";v=\"24\", \"Google Chrome\";v=\"120\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": sec_ch_ua_platform,
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        # 可选伪造IP（部分站点忽略）
        "X-Forwarded-For": f"{random.randint(1, 250)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
    }


def add_cache_bust(url: str) -> str:
    parsed = urlparse(url)
    q = dict(parse_qsl(parsed.query))
    q["_"] = uuid.uuid4().hex
    new_query = urlencode(q)
    return urlunparse(parsed._replace(query=new_query))


def parse_proxy_for_playwright(p: str):
    try:
        u = urlparse(p)
        server = f"{u.scheme}://{u.hostname}:{u.port}"
        if u.username:
            return {"server": server, "username": u.username, "password": u.password}
        return {"server": server}
    except Exception:
        return None


def maybe_load_proxies() -> list:
    path = os.path.join(os.getcwd(), "proxies.txt")
    proxies = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                proxies.append(line)
    return proxies


async def single_visit_http(
    url: str,
    session: ClientSession,
    refresh_once: bool,
    cookie_mode: str,
    ua_provider: Optional[UserAgent],
    proxy: Optional[str] = None,
) -> bool:
    # 清理cookie以确保每次唯一（同一会话，但每次访问前清空）
    session.cookie_jar.clear()

    ua_str = get_random_ua(ua_provider)
    headers = build_headers(ua_str, url)

    # 自定义cookie（若选择），否则让服务器分配新的cookie
    cookies = None
    if cookie_mode == "custom":
        cookies = {"cid": uuid.uuid4().hex}

    try:
        target_url = add_cache_bust(url)
        async with session.get(
            target_url,
            headers=headers,
            allow_redirects=True,
            cookies=cookies,
            proxy=proxy,
        ) as resp:
            await resp.read()
            ok1 = 200 <= resp.status < 400

        ok2 = True
        if refresh_once:
            refreshed_url = add_cache_bust(url)
            async with session.get(
                refreshed_url,
                headers=headers,
                allow_redirects=True,
                cookies=cookies,
                proxy=proxy,
            ) as resp2:
                await resp2.read()
                ok2 = 200 <= resp2.status < 400

        return bool(ok1 and ok2)
    except Exception:
        return False


async def run_http(
    url: str,
    times: int,
    concurrency: int,
    refresh_once: bool,
    cookie_mode: str,
    timeout_sec: int = 12,
) -> tuple:
    ua_provider = None
    try:
        ua_provider = UserAgent()
    except Exception:
        ua_provider = None

    proxies = maybe_load_proxies()
    connector = TCPConnector(limit=concurrency * 8, limit_per_host=concurrency * 4)

    # 为每个并发工作者创建一个独立的会话（各自的cookie jar），并复用连接
    sessions = [
        ClientSession(
            connector=connector,
            cookie_jar=CookieJar(unsafe=True),
            timeout=ClientTimeout(total=timeout_sec),
            trust_env=False,
        )
        for _ in range(concurrency)
    ]

    counter = VisitCounter()
    with tqdm(total=times, desc="访问进度") as pbar:
        # 将任务平均分配到各个会话上，确保每个会话内部串行执行，避免cookie清理冲突
        base = times // concurrency
        rem = times % concurrency
        per_worker_counts = [base + (1 if i < rem else 0) for i in range(concurrency)]

        async def worker(i: int, count: int):
            session = sessions[i]
            proxy = random.choice(proxies) if proxies else None
            for _ in range(count):
                ok = await single_visit_http(
                    url,
                    session,
                    refresh_once,
                    cookie_mode,
                    ua_provider,
                    proxy,
                )
                if ok:
                    counter.increment_success()
                else:
                    counter.increment_fail()
                pbar.update(1)

        tasks = [asyncio.create_task(worker(i, c)) for i, c in enumerate(per_worker_counts) if c > 0]
        await asyncio.gather(*tasks)

    # 关闭所有会话和连接器
    for s in sessions:
        await s.close()
    connector.close()
    return counter.get_counts()


# ---------------- Playwright JS 模式（无需 Chromedriver） -----------------
async def single_visit_playwright_js(browser, url: str, refresh_once: bool, cookie_mode: str, dwell_ms: int, ua_provider: Optional[UserAgent]) -> bool:
    try:
        ua_str = get_random_ua(ua_provider)
        locale = random.choice(["zh-CN", "en-US", "zh-TW"])
        # 每次新建独立上下文，隔离cookie/localStorage
        context = await browser.new_context(user_agent=ua_str, locale=locale, ignore_https_errors=True)

        # 自定义cookie（若选择）
        if cookie_mode == "custom":
            domain = urlparse(url).hostname or ""
            await context.add_cookies([
                {"name": "cid", "value": uuid.uuid4().hex, "domain": domain, "path": "/"}
            ])

        page = await context.new_page()
        # 预先清空存储，避免复用本地标识
        await page.add_init_script("try{localStorage.clear();sessionStorage.clear();}catch(e){}")

        target = add_cache_bust(url)
        await page.goto(target, wait_until="load", timeout=20000)
        if refresh_once:
            await page.reload(wait_until="load")

        # 等待JS逻辑执行
        await asyncio.sleep(max(0, dwell_ms) / 1000.0)

        await context.close()
        return True
    except Exception:
        return False


async def run_playwright_js(url: str, times: int, concurrency: int, refresh_once: bool, cookie_mode: str, dwell_ms: int) -> tuple:
    ua_provider = None
    try:
        ua_provider = UserAgent()
    except Exception:
        ua_provider = None

    proxies = maybe_load_proxies()
    counter = VisitCounter()

    async with async_playwright() as p:
        # 构建浏览器池（每个并发一个浏览器，可绑定不同代理）
        browsers = []
        for i in range(concurrency):
            proxy_cfg = None
            if proxies:
                pr = parse_proxy_for_playwright(random.choice(proxies))
                proxy_cfg = pr if pr else None
            b = await p.chromium.launch(headless=True, proxy=proxy_cfg, args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-extensions",
                "--disable-dev-shm-usage",
            ])
            browsers.append(b)

        with tqdm(total=times, desc="访问进度") as pbar:
            base = times // concurrency
            rem = times % concurrency
            per_counts = [base + (1 if i < rem else 0) for i in range(concurrency)]

            async def worker(idx: int, count: int):
                b = browsers[idx]
                for _ in range(count):
                    ok = await single_visit_playwright_js(b, url, refresh_once, cookie_mode, dwell_ms, ua_provider)
                    if ok:
                        counter.increment_success()
                    else:
                        counter.increment_fail()
                    pbar.update(1)

            tasks = [asyncio.create_task(worker(i, c)) for i, c in enumerate(per_counts) if c > 0]
            await asyncio.gather(*tasks)

        for b in browsers:
            try:
                await b.close()
            except Exception:
                pass

    return counter.get_counts()


# ---------------- Selenium 备用模式（需要本地Chrome/Chromedriver） -----------------
def get_cache_dir() -> str:
    cache_dir = os.path.join(tempfile.gettempdir(), "chrome_cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return cache_dir


def create_driver(user_agent: str):
    chrome_options = Options()
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-background-networking")

    # 禁用图片加载
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "disk-cache-size": 104857600,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # 优先使用 undetected-chromedriver，绕过常见反爬检测
    if uc is not None:
        try:
            driver = uc.Chrome(options=chrome_options, headless=True, use_subprocess=True)
            return driver
        except Exception:
            pass

    # 退回到常规 chromedriver
    return webdriver.Chrome(options=chrome_options)


def selenium_visit_once(driver, url: str, pbar, counter: VisitCounter, refresh_once: bool):
    try:
        start = time.time()
        target = add_cache_bust(url)
        driver.get(target)

        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        if refresh_once:
            driver.refresh()
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        # 清理可能的本地存储，确保不复用站点本地标识
        try:
            driver.execute_script("try{localStorage.clear();sessionStorage.clear();}catch(e){}");
        except Exception:
            pass
        # JS停留以保证前端计数逻辑执行
        time.sleep(random.uniform(0.8, 1.6))

        counter.increment_success()
        pbar.update(1)
        success, fail = counter.get_counts()
        pbar.write(f"成功: {success}, 失败: {fail}, 总耗时: {time.time() - start:.1f}秒")
    except Exception as e:
        counter.increment_fail()
        pbar.update(1)
        pbar.write(f"浏览器访问失败: {e}")


def selenium_visit_url(url: str, times: int, max_workers: int = 4, refresh_once: bool = True):
    # 预创建浏览器池并复用，避免反复启动浏览器的巨大开销
    drivers = []
    try:
        for _ in range(max_workers):
            ua_str = get_random_ua(None)
            d = create_driver(ua_str)
            d.set_page_load_timeout(25)
            d.set_script_timeout(25)
            drivers.append(d)

        counter = VisitCounter()
        from concurrent.futures import ThreadPoolExecutor
        with tqdm(total=times, desc="访问进度") as pbar:
            def worker(idx: int, count: int):
                driver = drivers[idx]
                for _ in range(count):
                    # 清理cookie以确保每次独立
                    try:
                        driver.delete_all_cookies()
                    except Exception:
                        pass
                    selenium_visit_once(driver, url, pbar, counter, refresh_once)

            base = times // max_workers
            rem = times % max_workers
            per_counts = [base + (1 if i < rem else 0) for i in range(max_workers)]

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(worker, i, c) for i, c in enumerate(per_counts) if c > 0]
                for f in futures:
                    f.result()

        success, fail = counter.get_counts()
        print("\n访问统计:")
        print(f"成功: {success}")
        print(f"失败: {fail}")
        print(f"成功率: {(success / times * 100):.1f}%")
    finally:
        for d in drivers:
            try:
                d.quit()
            except Exception:
                pass


def main():
    print("欢迎使用网页访问量刷新工具")

    url = input("请输入要访问的网址: ").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        print(f"已自动添加https前缀: {url}")

    # 快速可访问性测试（HTTP）
    try:
        print("正在测试URL可访问性...")
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            print(f"✓ URL测试成功，状态码: {r.status_code}")
        else:
            print(f"! URL返回非200状态码: {r.status_code}，但仍将继续")
    except Exception as e:
        print(f"! URL测试失败: {e}，但仍将继续")

    # 选择模式
    mode_in = input("选择模式: [1] HTTP极速 [2] 浏览器(Selenium) [3] 浏览器(Playwright 无Chromedriver，默认): ").strip()
    if mode_in == "1":
        mode = "http"
    elif mode_in == "2":
        mode = "selenium"
    else:
        mode = "playwright"  # 默认为 playwright

    # 次数与并发
    while True:
        try:
            times_input = input("请输入要访问的次数 (默认2000): ").strip()
            times = int(times_input) if times_input else 2000
            if times > 0:
                break
            print("请输入大于0的数字")
        except ValueError:
            print("请输入有效的数字")

    if mode == "http":
        while True:
            try:
                concurrency_input = input("请输入并发数 (默认1，建议10-200): ").strip()
                concurrency = int(concurrency_input) if concurrency_input else 1
                if 1 <= concurrency <= 1000:
                    break
                print("请输入1-1000之间的数字")
            except ValueError:
                print("请输入有效的数字")

        refresh_ans = input("是否每次刷新一次页面? [Y/n]: ").strip().lower()
        refresh_once = False if refresh_ans == "n" else True
        cookie_mode_in = input("cookie模式: [1] 服务器分配(默认) [2] 自定义随机cid: ").strip()
        cookie_mode = "custom" if cookie_mode_in == "2" else "server"

        print(f"\n开始HTTP并发访问 {url}...")
        print(f"并发: {concurrency}, 计划访问: {times}, 刷新: {refresh_once}, cookie模式: {cookie_mode}")
        try:
            success, fail = asyncio.run(
                run_http(url, times, concurrency, refresh_once, cookie_mode)
            )
            print("\n✓ 访问完成！")
            print("访问统计:")
            print(f"成功: {success}")
            print(f"失败: {fail}")
            print(f"成功率: {(success / times * 100):.1f}%")
        except KeyboardInterrupt:
            print("\n! 程序被用户中断")
        except Exception as e:
            print(f"\n× 程序执行出错: {e}")
        finally:
            print("程序已退出")
    elif mode == "selenium":
        # 浏览器模式简单检测（不强制）
        try:
            options = Options()
            options.add_argument("--headless=new")
            test_driver = webdriver.Chrome(options=options)
            test_driver.quit()
            print("✓ Chrome浏览器检测正常")
        except Exception as e:
            print("× Chrome浏览器检测失败或Chromedriver不可用，将继续尝试运行")
            print(f"错误信息: {e}")

        while True:
            try:
                threads = int(input("请输入并行线程数(建议1-8): "))
                if 1 <= threads <= 20:
                    break
                print("请输入1-20之间的数字")
            except ValueError:
                print("请输入有效的数字")

        # JS 停留时间设置
        while True:
            try:
                dwell_input = input("JS停留毫秒 (默认800，建议800-3000): ").strip()
                dwell_ms = int(dwell_input) if dwell_input else 800
                if 50 <= dwell_ms <= 10000:
                    break
                print("请输入50-10000之间的数字")
            except ValueError:
                print("请输入有效的数字")

        print(f"\n开始使用浏览器访问 {url}...")
        print(f"使用 {threads} 个并行线程，计划访问 {times} 次，JS停留{dwell_ms}ms")
        try:
            selenium_visit_url(url, times, max_workers=threads, refresh_once=True)
            print("\n✓ 访问完成！")
        except KeyboardInterrupt:
            print("\n! 程序被用户中断")
        except Exception as e:
            print(f"\n× 程序执行出错: {e}")
        finally:
            print("程序已退出")
    else:
        # Playwright 模式（JS保证执行，不依赖 Chromedriver）
        if async_playwright is None:
            print("未检测到playwright库，请先安装: pip install playwright，并执行: python -m playwright install chromium")
            return

        while True:
            try:
                concurrency_input = input("请输入并发数 (默认1，建议1-20): ").strip()
                concurrency = int(concurrency_input) if concurrency_input else 1
                if 1 <= concurrency <= 50:
                    break
                print("请输入1-50之间的数字")
            except ValueError:
                print("请输入有效的数字")

        refresh_ans = input("是否每次刷新一次页面? [Y/n]: ").strip().lower()
        refresh_once = False if refresh_ans == "n" else True
        cookie_mode_in = input("cookie模式: [1] 服务器分配(默认) [2] 自定义随机cid: ").strip()
        cookie_mode = "custom" if cookie_mode_in == "2" else "server"

        while True:
            try:
                dwell_input = input("JS停留毫秒 (默认800，建议800-3000): ").strip()
                dwell_ms = int(dwell_input) if dwell_input else 800
                if 200 <= dwell_ms <= 10000:
                    break
                print("请输入200-10000之间的数字")
            except ValueError:
                print("请输入有效的数字")

        print(f"\n开始Playwright并发访问 {url}...")
        print(f"并发: {concurrency}, 计划访问: {times}, 刷新: {refresh_once}, cookie模式: {cookie_mode}, JS停留: {dwell_ms}ms")
        try:
            success, fail = asyncio.run(
                run_playwright_js(url, times, concurrency, refresh_once, cookie_mode, dwell_ms)
            )
            print("\n✓ 访问完成！")
            print("访问统计:")
            print(f"成功: {success}")
            print(f"失败: {fail}")
            print(f"成功率: {(success / times * 100):.1f}%")
        except KeyboardInterrupt:
            print("\n! 程序被用户中断")
        except Exception as e:
            print(f"\n× 程序执行出错: {e}")
        finally:
            print("程序已退出")



if __name__ == "__main__":
    main()
