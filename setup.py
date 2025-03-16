#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import platform

def check_python_version():
    """检查Python版本是否满足要求"""
    print("🔍 检查Python版本...")
    if sys.version_info < (3, 6):
        print("❌ 错误: 需要Python 3.6或更高版本")
        sys.exit(1)
    print(f"✅ Python版本: {sys.version.split()[0]}")

def install_dependencies():
    """安装所有依赖包"""
    print("\n📦 安装Python依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖安装成功")
    except subprocess.CalledProcessError:
        print("❌ 依赖安装失败，请手动运行: pip install -r requirements.txt")
        sys.exit(1)

def check_chrome():
    """检查Chrome浏览器是否已安装"""
    print("\n🔍 检查Chrome浏览器...")
    
    system = platform.system()
    chrome_paths = {
        "Windows": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "Darwin": [  # macOS
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ],
        "Linux": [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
        ]
    }
    
    if system in chrome_paths:
        for path in chrome_paths[system]:
            if os.path.exists(path):
                print(f"✅ 找到Chrome浏览器: {path}")
                return True
    
    print("❓ 未找到Chrome浏览器，请确保已安装")
    print("📝 下载链接: https://www.google.com/chrome/")
    return False

def install_chromedriver():
    """尝试安装ChromeDriver"""
    print("\n🔧 尝试安装ChromeDriver...")
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium import webdriver
        
        print("📥 正在下载匹配的ChromeDriver...")
        driver_path = ChromeDriverManager().install()
        print(f"✅ ChromeDriver安装成功: {driver_path}")
        
        # 测试ChromeDriver
        print("🧪 测试ChromeDriver...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        driver.quit()
        print("✅ ChromeDriver测试成功")
        
    except Exception as e:
        print(f"❌ ChromeDriver安装或测试失败: {str(e)}")
        print("📝 请手动下载ChromeDriver: https://chromedriver.chromium.org/downloads")
        return False
    
    return True

def main():
    """主函数"""
    print("🚀 开始设置网页访问量刷新工具...")
    
    check_python_version()
    install_dependencies()
    chrome_installed = check_chrome()
    
    if chrome_installed:
        chromedriver_installed = install_chromedriver()
    else:
        print("\n⚠️ 请先安装Chrome浏览器，然后再运行此脚本")
        chromedriver_installed = False
    
    print("\n📋 设置结果:")
    print(f"✅ Python依赖: 已安装")
    print(f"{'✅' if chrome_installed else '❌'} Chrome浏览器: {'已安装' if chrome_installed else '未找到'}")
    print(f"{'✅' if chromedriver_installed else '❌'} ChromeDriver: {'已安装' if chromedriver_installed else '未安装'}")
    
    if chrome_installed and chromedriver_installed:
        print("\n🎉 恭喜！所有依赖已成功安装。")
        print("🚀 现在可以运行程序: python mian.py")
    else:
        print("\n⚠️ 部分依赖未安装，请按照上述提示手动安装后再运行程序。")

if __name__ == "__main__":
    main() 