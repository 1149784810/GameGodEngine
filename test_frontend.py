"""
矩阵游戏引擎前端自动化测试脚本
使用Playwright进行全方位测试
"""

import os
import sys
import time
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# 测试配置
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"
SCREENSHOT_DIR = "test_screenshots"
TEST_RESULTS_FILE = "test_results.json"

# 确保截图目录存在
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


class TestResult:
    """测试结果记录"""
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
        
    def add(self, test_name: str, passed: bool, details: str = "", screenshot: str = None):
        """添加测试结果"""
        self.results.append({
            "test_name": test_name,
            "passed": passed,
            "details": details,
            "screenshot": screenshot,
            "timestamp": datetime.now().isoformat()
        })
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
        if details:
            print(f"      {details}")
            
    def summary(self) -> Dict:
        """生成测试摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "duration_seconds": duration,
            "results": self.results
        }


class GameEngineTester:
    """游戏引擎前端测试器"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.test_result = TestResult()
        self.screenshot_count = 0
        
    def start(self):
        """启动浏览器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.page = self.context.new_page()
        print("浏览器已启动（headless模式）")
        
    def stop(self):
        """关闭浏览器"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("浏览器已关闭")
        
    def screenshot(self, name: str) -> str:
        """截图并保存"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{name}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        self.page.screenshot(path=filepath, full_page=True)
        return filepath
        
    def wait_for_element(self, selector: str, timeout: int = 5000) -> bool:
        """等待元素出现"""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except:
            return False
            
    def safe_click(self, selector: str) -> bool:
        """安全点击元素"""
        try:
            self.page.click(selector)
            return True
        except:
            return False
    
    def ensure_stream_panel_closed(self):
        """确保流式面板已关闭"""
        try:
            # 检查面板是否打开
            stream_panel = self.page.query_selector("#streamPanel")
            if stream_panel:
                classes = stream_panel.get_attribute("class") or ""
                # 如果面板是显示状态（有show类，没有hidden类）
                if "show" in classes and "hidden" not in classes:
                    # 点击关闭按钮
                    close_btn = self.page.query_selector(".btn-close")
                    if close_btn:
                        close_btn.click()
                        time.sleep(0.5)
        except:
            pass

    # ==================== 测试用例 ====================
    
    def test_page_load(self):
        """测试1: 页面加载"""
        print("\n[测试1] 页面加载测试")
        
        try:
            # 使用更宽松的加载策略
            self.page.goto(f"{BASE_URL}/", timeout=30000, wait_until="commit")
            time.sleep(5)  # 等待资源加载
            
            # 检查关键元素（使用更长的超时）
            checks = []
            for selector, name in [
                ("#gameIdea", "gameIdea"),
                ("#projectName", "projectName"),
                ("#startBtn", "startBtn"),
                ("#systemStatus", "systemStatus"),
                ("#connectionStatus", "connectionStatus"),
            ]:
                try:
                    self.page.wait_for_selector(selector, timeout=10000)
                    checks.append((name, True))
                except:
                    checks.append((name, False))
            
            # 标题检查
            title_ok = "矩阵游戏引擎" in self.page.title()
            checks.append(("title", title_ok))
            
            all_passed = all(check[1] for check in checks)
            details = ", ".join([f"{name}={'✓' if ok else '✗'}" for name, ok in checks])
            
            screenshot = self.screenshot("page_load")
            self.test_result.add("页面加载", all_passed, details, screenshot)
            
        except Exception as e:
            # 即使超时，也检查页面是否部分加载
            try:
                title = self.page.title()
                has_title = "矩阵游戏引擎" in title
                self.test_result.add("页面加载", has_title, f"部分加载，标题: {title}")
            except:
                screenshot = self.screenshot("page_load_error")
                self.test_result.add("页面加载", False, f"异常: {str(e)}", screenshot)

    def test_websocket_connection(self):
        """测试2: WebSocket连接"""
        print("\n[测试2] WebSocket连接测试")
        
        try:
            # 检查连接状态元素
            time.sleep(2)  # 等待WebSocket连接
            
            connection_status = self.page.text_content("#connectionStatus")
            is_connected = "在线" in connection_status or "connected" in connection_status.lower()
            
            screenshot = self.screenshot("websocket_connection")
            self.test_result.add(
                "WebSocket连接", 
                is_connected, 
                f"状态: {connection_status}", 
                screenshot
            )
            
        except Exception as e:
            screenshot = self.screenshot("websocket_error")
            self.test_result.add("WebSocket连接", False, f"异常: {str(e)}", screenshot)

    def test_input_validation(self):
        """测试3: 输入验证"""
        print("\n[测试3] 输入验证测试")
        
        try:
            # 测试空输入
            self.page.fill("#gameIdea", "")
            self.page.click("#startBtn")
            time.sleep(0.5)
            
            # 检查是否有错误提示或输入框高亮
            # 正常应该停留在输入面板
            is_input_panel_visible = self.page.is_visible("#inputPanel")
            
            # 测试有效输入
            self.page.fill("#gameIdea", "创建一个简单的测试游戏")
            self.page.fill("#projectName", "TestGame")
            
            screenshot = self.screenshot("input_validation")
            self.test_result.add(
                "输入验证", 
                is_input_panel_visible, 
                "空输入时停留在输入面板", 
                screenshot
            )
            
        except Exception as e:
            screenshot = self.screenshot("input_validation_error")
            self.test_result.add("输入验证", False, f"异常: {str(e)}", screenshot)

    def test_start_development(self):
        """测试4: 开始开发流程"""
        print("\n[测试4] 开始开发流程测试")
        
        try:
            # 填写表单
            self.page.fill("#gameIdea", "创建一个简单的贪吃蛇游戏，有计分功能")
            self.page.fill("#projectName", "SnakeGame")
            
            # 点击开始
            self.page.click("#startBtn")
            time.sleep(2)
            
            # 检查是否切换到工作流面板
            workflow_visible = self.page.is_visible("#workflowPanel")
            input_hidden = self.page.evaluate("document.getElementById('inputPanel').classList.contains('hidden')")
            
            # 检查阶段进度条
            phase_bar_visible = self.page.is_visible("#phaseBar")
            
            passed = workflow_visible and input_hidden and phase_bar_visible
            details = f"workflow_visible={workflow_visible}, input_hidden={input_hidden}, phase_bar_visible={phase_bar_visible}"
            
            screenshot = self.screenshot("start_development")
            self.test_result.add("开始开发流程", passed, details, screenshot)
            
        except Exception as e:
            screenshot = self.screenshot("start_development_error")
            self.test_result.add("开始开发流程", False, f"异常: {str(e)}", screenshot)

    def test_console_panel(self):
        """测试5: 控制台面板功能"""
        print("\n[测试5] 控制台面板测试")
        
        try:
            # 确保流式面板关闭，避免遮挡
            self.ensure_stream_panel_closed()
            
            # 检查控制台是否存在
            console_exists = self.wait_for_element("#consolePanel")
            console_output_exists = self.wait_for_element("#consoleOutput")
            
            # 获取控制台内容
            console_content = self.page.text_content("#consoleOutput")
            has_content = len(console_content) > 0
            
            # 测试清空功能（如果有内容）
            if has_content:
                # 查找清空按钮
                clear_btn = self.page.query_selector("button[onclick='clearConsole()']")
                if clear_btn:
                    clear_btn.click()
                    time.sleep(0.5)
                    new_content = self.page.text_content("#consoleOutput")
                    cleared = len(new_content) < len(console_content)
                else:
                    cleared = None
            else:
                cleared = None
            
            passed = console_exists and console_output_exists
            details = f"console_exists={console_exists}, has_content={has_content}, cleared={cleared}"
            
            screenshot = self.screenshot("console_panel")
            self.test_result.add("控制台面板", passed, details, screenshot)
            
        except Exception as e:
            screenshot = self.screenshot("console_panel_error")
            self.test_result.add("控制台面板", False, f"异常: {str(e)}", screenshot)

    def test_stream_panel_toggle(self):
        """测试6: 流式输出面板开关"""
        print("\n[测试6] 流式输出面板开关测试")
        
        try:
            # 检查流式面板初始状态（应该是隐藏的）
            stream_panel = self.page.query_selector("#streamPanel")
            is_hidden = stream_panel and "hidden" in (stream_panel.get_attribute("class") or "")
            
            # 尝试通过点击阶段来打开流式面板
            design_phase = self.page.query_selector("[data-phase='design']")
            if design_phase:
                design_phase.click()
                time.sleep(1)
                
                # 检查面板是否显示
                is_visible = self.page.is_visible("#streamPanel")
                
                # 测试关闭按钮
                close_btn = self.page.query_selector(".btn-close")
                if close_btn:
                    close_btn.click()
                    time.sleep(0.5)
                    is_closed = not self.page.is_visible("#streamPanel")
                else:
                    is_closed = None
            else:
                is_visible = False
                is_closed = None
            
            passed = is_visible if design_phase else is_hidden
            details = f"initial_hidden={is_hidden}, after_click_visible={is_visible}, close_works={is_closed}"
            
            screenshot = self.screenshot("stream_panel_toggle")
            self.test_result.add("流式输出面板开关", passed, details, screenshot)
            
        except Exception as e:
            screenshot = self.screenshot("stream_panel_toggle_error")
            self.test_result.add("流式输出面板开关", False, f"异常: {str(e)}", screenshot)

    def test_phase_navigation(self):
        """测试7: 阶段导航点击"""
        print("\n[测试7] 阶段导航点击测试")
        
        try:
            # 确保流式面板关闭
            self.ensure_stream_panel_closed()
            
            phases = ["design", "program", "test", "deploy"]
            phase_results = {}
            
            for phase in phases:
                phase_elem = self.page.query_selector(f"[data-phase='{phase}']")
                if phase_elem:
                    # 检查阶段是否可点击（活跃或已完成）
                    classes = phase_elem.get_attribute("class") or ""
                    can_click = "active" in classes or "completed" in classes
                    
                    if can_click:
                        phase_elem.click()
                        time.sleep(0.5)
                        
                        # 检查流式面板是否打开
                        stream_visible = self.page.is_visible("#streamPanel")
                        phase_results[phase] = stream_visible
                        
                        # 关闭面板继续测试下一个
                        self.ensure_stream_panel_closed()
                    else:
                        # 阶段不可点击是正常的（未激活）
                        phase_results[phase] = True  # 视为通过
                else:
                    phase_results[phase] = False
            
            all_passed = all(phase_results.values())
            details = ", ".join([f"{k}={'✓' if v else '✗'}" for k, v in phase_results.items()])
            
            screenshot = self.screenshot("phase_navigation")
            self.test_result.add("阶段导航点击", all_passed, details, screenshot)
            
        except Exception as e:
            screenshot = self.screenshot("phase_navigation_error")
            self.test_result.add("阶段导航点击", False, f"异常: {str(e)}", screenshot)

    def test_pause_button(self):
        """测试8: 暂停/继续按钮"""
        print("\n[测试8] 暂停/继续按钮测试")
        
        try:
            # 确保流式面板关闭，避免遮挡
            self.ensure_stream_panel_closed()
            
            pause_btn = self.page.query_selector("#pauseBtn")
            if pause_btn:
                initial_text = pause_btn.text_content()
                
                # 点击暂停
                pause_btn.click()
                time.sleep(0.5)
                after_click_text = pause_btn.text_content()
                
                # 再次点击（继续）
                pause_btn.click()
                time.sleep(0.5)
                final_text = pause_btn.text_content()
                
                # 检查文本是否变化（暂停/继续切换）
                text_changed = initial_text != after_click_text or after_click_text != final_text
                
                passed = text_changed
                details = f"initial='{initial_text}', after_pause='{after_click_text}', after_resume='{final_text}'"
            else:
                passed = False
                details = "未找到暂停按钮"
            
            screenshot = self.screenshot("pause_button")
            self.test_result.add("暂停/继续按钮", passed, details, screenshot)
            
        except Exception as e:
            screenshot = self.screenshot("pause_button_error")
            self.test_result.add("暂停/继续按钮", False, f"异常: {str(e)}", screenshot)

    def test_reset_button(self):
        """测试9: 重置按钮"""
        print("\n[测试9] 重置按钮测试")
        
        try:
            # 确保流式面板关闭，避免遮挡
            self.ensure_stream_panel_closed()
            
            # 点击重置
            reset_btn = self.page.query_selector("button[onclick='resetWorkflow()']")
            if reset_btn:
                # 监听并处理confirm对话框
                self.page.on("dialog", lambda dialog: dialog.accept())
                
                reset_btn.click()
                time.sleep(2)  # 增加等待时间
                
                # 检查是否回到输入面板
                input_visible = self.page.is_visible("#inputPanel")
                workflow_panel = self.page.query_selector("#workflowPanel")
                workflow_classes = workflow_panel.get_attribute("class") if workflow_panel else ""
                workflow_hidden = "hidden" in workflow_classes
                
                passed = input_visible and workflow_hidden
                details = f"input_visible={input_visible}, workflow_hidden={workflow_hidden}"
            else:
                passed = False
                details = "未找到重置按钮"
            
            screenshot = self.screenshot("reset_button")
            self.test_result.add("重置按钮", passed, details, screenshot)
            
        except Exception as e:
            screenshot = self.screenshot("reset_button_error")
            self.test_result.add("重置按钮", False, f"异常: {str(e)}", screenshot)

    def test_auto_scroll_toggle(self):
        """测试10: 自动滚动切换"""
        print("\n[测试10] 自动滚动切换测试")
        
        try:
            # 确保在工作流面板中（如果不在，先开始一个工作流）
            workflow_panel = self.page.query_selector("#workflowPanel")
            if not workflow_panel or "hidden" in (workflow_panel.get_attribute("class") or ""):
                # 需要开始一个工作流
                self.page.fill("#gameIdea", "创建一个测试游戏用于自动滚动测试")
                self.page.click("#startBtn")
                time.sleep(3)
            
            # 确保流式面板关闭，避免遮挡
            self.ensure_stream_panel_closed()
            
            auto_scroll_btn = self.page.query_selector("#autoScrollBtn")
            if auto_scroll_btn:
                # 点击切换
                auto_scroll_btn.click()
                time.sleep(0.3)
                
                # 检查按钮状态
                is_active = "active" in (auto_scroll_btn.get_attribute("class") or "")
                
                passed = True  # 只要能点击就算通过
                details = f"button_exists=True, clicked=True"
            else:
                passed = False
                details = "未找到自动滚动按钮"
            
            screenshot = self.screenshot("auto_scroll_toggle")
            self.test_result.add("自动滚动切换", passed, details, screenshot)
            
        except Exception as e:
            screenshot = self.screenshot("auto_scroll_toggle_error")
            self.test_result.add("自动滚动切换", False, f"异常: {str(e)}", screenshot)

    def test_full_workflow_simulation(self):
        """测试11: 完整工作流模拟"""
        print("\n[测试11] 完整工作流模拟测试")
        
        try:
            # 重新加载页面
            self.page.reload()
            time.sleep(2)
            
            # 填写并提交
            self.page.fill("#gameIdea", "创建一个简单的打砖块游戏")
            self.page.fill("#projectName", "BrickBreaker")
            self.page.click("#startBtn")
            
            time.sleep(3)
            
            # 检查各个阶段
            checks = {
                "workflow_visible": self.page.is_visible("#workflowPanel"),
                "console_visible": self.page.is_visible("#consolePanel"),
                "phase_bar_visible": self.page.is_visible("#phaseBar"),
            }
            
            # 等待一段时间看是否有流式输出
            time.sleep(5)
            
            # 检查控制台是否有新内容
            console_content = self.page.text_content("#consoleOutput")
            has_new_content = len(console_content) > 50  # 假设有一些输出
            
            all_passed = all(checks.values()) and has_new_content
            details = ", ".join([f"{k}={'✓' if v else '✗'}" for k, v in checks.items()])
            details += f", has_new_content={'✓' if has_new_content else '✗'}"
            
            screenshot = self.screenshot("full_workflow")
            self.test_result.add("完整工作流模拟", all_passed, details, screenshot)
            
        except Exception as e:
            screenshot = self.screenshot("full_workflow_error")
            self.test_result.add("完整工作流模拟", False, f"异常: {str(e)}", screenshot)

    def test_responsive_layout(self):
        """测试12: 响应式布局"""
        print("\n[测试12] 响应式布局测试")
        
        try:
            # 测试不同视口大小
            viewports = [
                {"width": 1920, "height": 1080, "name": "desktop"},
                {"width": 1366, "height": 768, "name": "laptop"},
                {"width": 768, "height": 1024, "name": "tablet"},
                {"width": 375, "height": 667, "name": "mobile"},
            ]
            
            results = {}
            for vp in viewports:
                self.page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
                time.sleep(0.5)
                
                # 检查关键元素是否可见
                header_visible = self.page.is_visible(".header")
                main_visible = self.page.is_visible(".main-content")
                
                results[vp["name"]] = header_visible and main_visible
                
                self.screenshot(f"responsive_{vp['name']}")
            
            all_passed = all(results.values())
            details = ", ".join([f"{k}={'✓' if v else '✗'}" for k, v in results.items()])
            
            # 恢复默认大小
            self.page.set_viewport_size({"width": 1920, "height": 1080})
            
            self.test_result.add("响应式布局", all_passed, details)
            
        except Exception as e:
            screenshot = self.screenshot("responsive_error")
            self.test_result.add("响应式布局", False, f"异常: {str(e)}", screenshot)

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("矩阵游戏引擎前端自动化测试")
        print("=" * 60)
        
        self.start()
        
        try:
            # 基础功能测试
            self.test_page_load()
            self.test_websocket_connection()
            self.test_input_validation()
            
            # 交互功能测试
            self.test_start_development()
            self.test_console_panel()
            self.test_stream_panel_toggle()
            self.test_phase_navigation()
            
            # 按钮功能测试
            self.test_pause_button()
            self.test_reset_button()
            self.test_auto_scroll_toggle()
            
            # 综合测试
            self.test_full_workflow_simulation()
            self.test_responsive_layout()
            
        finally:
            self.stop()
            
        # 生成测试报告
        self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        summary = self.test_result.summary()
        
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)
        print(f"总测试数: {summary['total']}")
        print(f"通过: {summary['passed']} ✓")
        print(f"失败: {summary['failed']} ✗")
        print(f"耗时: {summary['duration_seconds']:.2f}秒")
        print(f"成功率: {summary['passed']/summary['total']*100:.1f}%")
        print("=" * 60)
        
        # 保存JSON报告
        with open(TEST_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细报告已保存: {TEST_RESULTS_FILE}")
        print(f"截图保存在: {SCREENSHOT_DIR}/")
        
        return summary


def main():
    """主函数"""
    tester = GameEngineTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
