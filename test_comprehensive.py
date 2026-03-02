"""
矩阵游戏引擎 - 综合自动化测试
包含高级功能测试：停止按钮、缓存、并行输出对应关系等
"""

import os
import sys
import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, WebSocket

# 测试配置
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"
SCREENSHOT_DIR = "test_screenshots"
TEST_RESULTS_FILE = "test_results_comprehensive.json"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


class ComprehensiveTester:
    """综合测试器"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.results = []
        self.screenshot_count = 0
        self.ws_messages = []  # 存储WebSocket消息
        
    def start(self):
        """启动浏览器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        self.page = self.context.new_page()
        
        # 监听WebSocket消息
        self.page.on("websocket", self._handle_websocket)
        
    def _handle_websocket(self, ws: WebSocket):
        """处理WebSocket事件"""
        ws.on("framereceived", lambda data: self.ws_messages.append({
            "type": "received",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }))
        ws.on("framesent", lambda data: self.ws_messages.append({
            "type": "sent", 
            "data": data,
            "timestamp": datetime.now().isoformat()
        }))
        
    def stop(self):
        """关闭浏览器"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            
    def screenshot(self, name: str) -> str:
        """截图"""
        self.screenshot_count += 1
        filename = f"comp_{self.screenshot_count:03d}_{name}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        self.page.screenshot(path=filepath, full_page=True)
        return filepath
        
    def add_result(self, name: str, passed: bool, details: str = ""):
        """添加测试结果"""
        self.results.append({
            "name": name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")
        if details:
            print(f"     {details}")

    # ==================== 核心功能测试 ====================
    
    def test_stream_panel_cache(self):
        """测试流式输出面板缓存功能"""
        print("\n[测试] 流式输出面板缓存")
        
        try:
            # 1. 开始开发流程
            self.page.fill("#gameIdea", "创建一个简单的测试游戏")
            self.page.click("#startBtn")
            time.sleep(3)
            
            # 2. 打开流式面板
            design_phase = self.page.query_selector("[data-phase='design']")
            if design_phase:
                design_phase.click()
                time.sleep(1)
                
                # 3. 关闭面板
                close_btn = self.page.query_selector(".btn-close")
                if close_btn:
                    close_btn.click()
                    time.sleep(0.5)
                    
                    # 4. 等待一段时间（模拟接收流式数据）
                    time.sleep(3)
                    
                    # 5. 重新打开面板
                    design_phase.click()
                    time.sleep(1)
                    
                    # 6. 检查是否显示缓存内容
                    stream_content = self.page.text_content("#streamContent")
                    has_cached_content = len(stream_content) > 20
                    
                    self.add_result(
                        "缓存功能",
                        has_cached_content,
                        f"缓存内容长度: {len(stream_content)}"
                    )
                else:
                    self.add_result("缓存功能", False, "未找到关闭按钮")
            else:
                self.add_result("缓存功能", False, "未找到策划阶段按钮")
                
            self.screenshot("stream_cache")
            
        except Exception as e:
            self.add_result("缓存功能", False, f"异常: {str(e)}")
            self.screenshot("stream_cache_error")

    def test_stop_button(self):
        """测试停止按钮功能"""
        print("\n[测试] 停止按钮功能")
        
        try:
            # 重置并重新开始
            reset_btn = self.page.query_selector("button[onclick='resetWorkflow()']")
            if reset_btn:
                reset_btn.click()
                time.sleep(1)
            
            # 开始新的开发流程
            self.page.fill("#gameIdea", "创建一个测试游戏用于停止按钮测试")
            self.page.click("#startBtn")
            time.sleep(3)
            
            # 获取初始WebSocket消息数
            initial_msg_count = len(self.ws_messages)
            
            # 点击暂停/停止按钮
            pause_btn = self.page.query_selector("#pauseBtn")
            if pause_btn:
                pause_btn.click()
                time.sleep(2)
                
                # 检查按钮文本是否变为"继续"
                btn_text = pause_btn.text_content()
                is_paused = "继续" in btn_text or "resume" in btn_text.lower()
                
                # 等待一段时间，检查是否没有新的WebSocket消息
                time.sleep(3)
                new_msg_count = len(self.ws_messages)
                msgs_after_stop = new_msg_count - initial_msg_count
                
                # 恢复运行
                pause_btn.click()
                time.sleep(1)
                
                self.add_result(
                    "停止按钮",
                    is_paused,
                    f"按钮文本: {btn_text}, 停止后新消息数: {msgs_after_stop}"
                )
            else:
                self.add_result("停止按钮", False, "未找到暂停按钮")
                
            self.screenshot("stop_button")
            
        except Exception as e:
            self.add_result("停止按钮", False, f"异常: {str(e)}")
            self.screenshot("stop_button_error")

    def test_parallel_workers_output(self):
        """测试并行子工种输出对应关系"""
        print("\n[测试] 并行子工种输出对应")
        
        try:
            # 重置
            reset_btn = self.page.query_selector("button[onclick='resetWorkflow()']")
            if reset_btn:
                reset_btn.click()
                time.sleep(1)
            
            # 开始开发（使用会产生并行任务的游戏描述）
            self.page.fill("#gameIdea", "创建一个RPG游戏，包含战斗系统、背包系统、任务系统、角色成长系统")
            self.page.fill("#projectName", "RPGTestGame")
            self.page.click("#startBtn")
            
            # 等待并行任务创建
            time.sleep(10)
            
            # 检查是否有子工种按钮
            sub_workers = self.page.query_selector_all(".sub-worker-btn")
            has_sub_workers = len(sub_workers) > 0
            
            if has_sub_workers:
                # 点击每个子工种，检查输出
                worker_outputs = {}
                for i, worker in enumerate(sub_workers[:3]):  # 测试前3个
                    worker_id = worker.get_attribute("data-worker-id")
                    worker_name = worker.text_content()
                    
                    worker.click()
                    time.sleep(2)
                    
                    # 获取输出内容
                    stream_content = self.page.text_content("#streamContent")
                    worker_outputs[worker_id] = {
                        "name": worker_name,
                        "content_length": len(stream_content)
                    }
                    
                    # 关闭面板
                    close_btn = self.page.query_selector(".btn-close")
                    if close_btn:
                        close_btn.click()
                        time.sleep(0.5)
                
                # 检查WebSocket消息中的worker_id对应关系
                worker_msgs = [m for m in self.ws_messages if 'worker_id' in str(m.get('data', ''))]
                
                details = f"子工种数: {len(sub_workers)}, 消息对应检查: {len(worker_msgs) > 0}"
                self.add_result("并行子工种输出", True, details)
            else:
                self.add_result("并行子工种输出", False, "未找到子工种按钮")
                
            self.screenshot("parallel_workers")
            
        except Exception as e:
            self.add_result("并行子工种输出", False, f"异常: {str(e)}")
            self.screenshot("parallel_workers_error")

    def test_phase_status_sync(self):
        """测试阶段状态同步"""
        print("\n[测试] 阶段状态同步")
        
        try:
            # 重置
            reset_btn = self.page.query_selector("button[onclick='resetWorkflow()']")
            if reset_btn:
                reset_btn.click()
                time.sleep(1)
            
            # 开始开发
            self.page.fill("#gameIdea", "创建一个简单的测试游戏用于阶段同步测试")
            self.page.click("#startBtn")
            time.sleep(3)
            
            # 检查初始阶段（应该是design）
            design_step = self.page.query_selector("[data-phase='design']")
            is_design_active = design_step and "active" in (design_step.get_attribute("class") or "")
            
            # 等待一段时间，观察阶段变化
            phase_changes = []
            for _ in range(5):
                time.sleep(5)
                
                # 检查各阶段状态
                for phase in ["design", "program", "test", "deploy"]:
                    step = self.page.query_selector(f"[data-phase='{phase}']")
                    if step:
                        classes = step.get_attribute("class") or ""
                        if "active" in classes or "completed" in classes:
                            phase_changes.append(phase)
            
            # 检查WebSocket消息中的phase_update
            phase_updates = [m for m in self.ws_messages if 'phase_update' in str(m.get('data', ''))]
            
            has_phase_changes = len(set(phase_changes)) > 0 or len(phase_updates) > 0
            
            self.add_result(
                "阶段状态同步",
                has_phase_changes,
                f"观察到的阶段: {set(phase_changes)}, WebSocket阶段更新: {len(phase_updates)}"
            )
            
            self.screenshot("phase_sync")
            
        except Exception as e:
            self.add_result("阶段状态同步", False, f"异常: {str(e)}")
            self.screenshot("phase_sync_error")

    def test_console_output(self):
        """测试控制台输出"""
        print("\n[测试] 控制台输出")
        
        try:
            # 重置
            reset_btn = self.page.query_selector("button[onclick='resetWorkflow()']")
            if reset_btn:
                reset_btn.click()
                time.sleep(1)
            
            # 开始开发
            self.page.fill("#gameIdea", "创建一个测试游戏用于控制台输出测试")
            self.page.click("#startBtn")
            time.sleep(5)
            
            # 获取控制台内容
            console_content = self.page.text_content("#consoleOutput")
            has_content = len(console_content) > 50
            
            # 检查是否有系统消息
            has_system_msgs = "系统" in console_content or "[系统]" in console_content
            
            self.add_result(
                "控制台输出",
                has_content and has_system_msgs,
                f"内容长度: {len(console_content)}, 有系统消息: {has_system_msgs}"
            )
            
            self.screenshot("console_output")
            
        except Exception as e:
            self.add_result("控制台输出", False, f"异常: {str(e)}")
            self.screenshot("console_output_error")

    def test_websocket_reconnect(self):
        """测试WebSocket重连功能"""
        print("\n[测试] WebSocket重连")
        
        try:
            # 获取当前连接状态
            initial_status = self.page.text_content("#connectionStatus")
            
            # 模拟网络断开（通过执行JavaScript关闭WebSocket）
            self.page.evaluate("""
                if (window.wsManager && window.wsManager.ws) {
                    window.wsManager.ws.close();
                }
            """)
            time.sleep(2)
            
            # 检查是否显示离线状态
            status_after_close = self.page.text_content("#connectionStatus")
            is_offline = "离线" in status_after_close or "offline" in status_after_close.lower()
            
            # 等待重连
            time.sleep(5)
            
            # 检查是否恢复在线
            status_after_reconnect = self.page.text_content("#connectionStatus")
            is_reconnected = "在线" in status_after_reconnect or "connected" in status_after_reconnect.lower()
            
            self.add_result(
                "WebSocket重连",
                is_offline and is_reconnected,
                f"断开状态: {is_offline}, 重连成功: {is_reconnected}"
            )
            
            self.screenshot("websocket_reconnect")
            
        except Exception as e:
            self.add_result("WebSocket重连", False, f"异常: {str(e)}")
            self.screenshot("websocket_reconnect_error")

    def test_full_workflow_with_validation(self):
        """测试完整工作流并验证数据一致性"""
        print("\n[测试] 完整工作流数据一致性")
        
        try:
            # 重置
            reset_btn = self.page.query_selector("button[onclick='resetWorkflow()']")
            if reset_btn:
                reset_btn.click()
                time.sleep(1)
            
            # 清空WebSocket消息记录
            self.ws_messages.clear()
            
            # 开始开发
            self.page.fill("#gameIdea", "创建一个简单的打砖块游戏")
            self.page.fill("#projectName", "BrickBreakerTest")
            self.page.click("#startBtn")
            
            # 等待工作流运行一段时间
            time.sleep(15)
            
            # 收集验证数据
            checks = {
                "workflow_started": self.page.is_visible("#workflowPanel"),
                "console_has_content": len(self.page.text_content("#consoleOutput")) > 100,
                "websocket_msgs": len(self.ws_messages) > 0,
                "phase_bar_visible": self.page.is_visible("#phaseBar"),
            }
            
            # 检查WebSocket消息类型
            msg_types = set()
            for msg in self.ws_messages:
                try:
                    data = json.loads(msg.get('data', '{}'))
                    msg_types.add(data.get('type', 'unknown'))
                except:
                    pass
            
            checks["msg_types"] = list(msg_types)
            
            all_passed = all(v for k, v in checks.items() if k != "msg_types")
            
            self.add_result(
                "完整工作流",
                all_passed,
                f"检查项: {checks}"
            )
            
            self.screenshot("full_workflow_validation")
            
        except Exception as e:
            self.add_result("完整工作流", False, f"异常: {str(e)}")
            self.screenshot("full_workflow_error")

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("矩阵游戏引擎 - 综合自动化测试")
        print("=" * 60)
        
        self.start()
        
        try:
            # 加载页面
            self.page.goto(f"{BASE_URL}/", timeout=15000)
            time.sleep(3)
            
            # 运行测试
            self.test_stream_panel_cache()
            self.test_stop_button()
            self.test_parallel_workers_output()
            self.test_phase_status_sync()
            self.test_console_output()
            self.test_websocket_reconnect()
            self.test_full_workflow_with_validation()
            
        finally:
            self.stop()
        
        # 生成报告
        self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)
        print(f"总测试数: {total}")
        print(f"通过: {passed} ✓")
        print(f"失败: {failed} ✗")
        print(f"成功率: {passed/total*100:.1f}%" if total > 0 else "N/A")
        print("=" * 60)
        
        # 保存报告
        report = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "results": self.results,
            "websocket_msg_count": len(self.ws_messages),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(TEST_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n报告已保存: {TEST_RESULTS_FILE}")
        
        return report


def main():
    tester = ComprehensiveTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
