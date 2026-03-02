"""
Playwright 配置 - 使用本地 Chrome 浏览器
"""

from playwright.sync_api import sync_playwright

# Chrome 可执行文件路径
CHROME_EXECUTABLE_PATH = r"C:\Users\11497\Downloads\chrome-win64\chrome-win64\chrome.exe"


def create_browser(headless: bool = False):
    """
    创建 Playwright 浏览器实例（使用本地 Chrome）
    
    Args:
        headless: 是否无头模式运行
        
    Returns:
        browser 实例
    """
    playwright = sync_playwright().start()
    
    # 使用本地 Chrome 启动浏览器
    browser = playwright.chromium.launch(
        executable_path=CHROME_EXECUTABLE_PATH,
        headless=headless,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    
    return playwright, browser


def create_page(browser, viewport: dict = None):
    """
    创建新页面
    
    Args:
        browser: 浏览器实例
        viewport: 视口大小，默认 1920x1080
        
    Returns:
        page 实例
    """
    if viewport is None:
        viewport = {"width": 1920, "height": 1080}
    
    context = browser.new_context(
        viewport=viewport,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    page = context.new_page()
    return context, page


# 使用示例
if __name__ == "__main__":
    # 默认使用 headless=True 后台静默运行
    playwright, browser = create_browser(headless=True)
    
    try:
        context, page = create_page(browser)
        
        # 访问示例网站
        page.goto("https://www.baidu.com")
        
        # 截图（headless模式下截图功能正常工作）
        page.screenshot(path="screenshot.png")
        
        context.close()
    finally:
        browser.close()
        playwright.stop()
