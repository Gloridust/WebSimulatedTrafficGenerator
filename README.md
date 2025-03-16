# 🌐 网页访问量刷新工具 (Web Traffic Generator)

这是一个使用Selenium和多线程技术实现的网页访问量生成工具，可以模拟真实用户访问网站的行为。

## ✨ 特点

- 🚀 多线程并行访问，提高效率
- 🔄 自动重试机制，处理网络错误
- 👤 随机User-Agent，模拟不同浏览器
- 📱 模拟真实用户行为（滚动、停留等）
- 📊 实时显示访问统计信息

## 🛠️ 安装要求

### 必要软件

- ✅ Python 3.6+
- ✅ Google Chrome浏览器 (最新版)
- ✅ ChromeDriver (与Chrome版本匹配)

### 快速安装 (推荐)

我们提供了一个自动安装脚本，可以帮助您快速设置环境：

```bash
# 克隆仓库
git clone https://github.com/yourusername/WebSimulatedTrafficGenerator.git
cd WebSimulatedTrafficGenerator

# 运行安装脚本
python setup.py
```

安装脚本会自动：
- ✅ 检查Python版本
- ✅ 安装所有Python依赖
- ✅ 检查Chrome浏览器是否已安装
- ✅ 下载并安装匹配的ChromeDriver
- ✅ 测试环境是否正常

### 手动安装

如果自动安装失败，您也可以手动安装：

1. **安装Python依赖**：
```bash
pip install -r requirements.txt
```

2. **安装Chrome浏览器**：
   - 访问 https://www.google.com/chrome/ 下载并安装

3. **安装ChromeDriver**：
   - 确认Chrome版本：打开Chrome，点击右上角三点菜单，选择"帮助" > "关于Google Chrome"
   - 访问 https://chromedriver.chromium.org/downloads 下载对应版本
   - 将ChromeDriver添加到系统PATH

## 🚀 使用方法

1. 运行程序：
```bash
python mian.py
```

2. 按照提示输入：
   - 要访问的网址
   - 访问次数
   - 并行线程数（建议1-10）

3. 程序会自动：
   - ✅ 检测Chrome浏览器是否可用
   - ✅ 验证URL格式和可访问性
   - ✅ 开始多线程访问
   - ✅ 显示实时进度和统计信息

## 📊 性能优化

- 🔧 **调整线程数**：根据您的计算机性能和网络状况调整并行线程数
- 🔒 **减少SSL错误**：程序已内置自动重试机制处理SSL错误
- 💾 **缓存管理**：程序会自动管理浏览器缓存，减少内存占用
- 🖼️ **禁用图片**：默认已禁用图片加载，提高访问速度

## ⚠️ 注意事项

- 🔒 请勿用于非法用途或违反网站服务条款的活动
- 🔋 高并发访问会消耗较多系统资源
- 🌐 部分网站可能有反爬虫机制，可能导致IP被临时封禁
- 💻 长时间运行可能导致内存占用增加

## 🐛 常见问题

1. **Chrome浏览器检测失败**
   - 确保已安装最新版Chrome
   - 确保ChromeDriver版本与Chrome版本匹配
   - 尝试运行 `python setup.py` 自动安装

2. **SSL错误**
   - 程序会自动重试，无需担心
   - 如果持续失败，可能是目标网站SSL配置问题
   - 尝试访问其他网站测试

3. **内存占用过高**
   - 减少并行线程数
   - 定期重启程序
   - 确保系统有足够的可用内存

## 📝 许可证

本项目仅供学习和研究使用，请遵守相关法律法规。 