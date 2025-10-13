import os
import re
import json
from pathlib import Path
import time
import chardet
import requests
from PySide6.QtCore import QTimer, QThread, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFileSystemModel
from PySide6.QtWidgets import QWidget, QFileDialog, QApplication
from openai import OpenAI
from qfluentwidgets import FluentIcon

from ..common.config import cfg
from ..common.ShowInfoBar import ShowInfoBar
from ..view.AiTools_ui import Ui_Form

VULN_PATTERN = re.compile(
    r"^\[(高危|中危)\] (.+?) - (.+?):(\d+) - (.+?)(\s*\[POC\](.+))?$",
    re.MULTILINE
)


class AnalyzeThread(QThread):
    fileAnalyzed = Signal(str, list)
    analysisFinished = Signal()

    def __init__(self, files, analyze_func):
        super().__init__()
        self.files = files
        self.analyze_func = analyze_func
        self._is_running = True

    def run(self):
        for file in self.files:
            if not self._is_running:
                break
            try:
                result = self.analyze_func(file)
                self.fileAnalyzed.emit(file, result)
            except Exception as e:
                self.fileAnalyzed.emit(file, [("错误", f"分析失败: {str(e)}", "")])

        self.analysisFinished.emit()

    def stop(self):
        self._is_running = False


class CodeAuditInterface(Ui_Form, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.session = requests.Session()
        self.setupUi(self)
        self.setObjectName("aitoolsInterface")
        self._init_ui()
        self._init_state()

    def _init_ui(self):
        self.outputEdit.setReadOnly(True)
        self.MultifileButton.setChecked(True)
        self.CodeRadioButton.setChecked(True)
        self.fileButton.setText('选择数据源')
        self.model = QFileSystemModel()
        self.filetree.setModel(self.model)
        self.fileButton.clicked.connect(self._select_source)
        self.StartButton.clicked.connect(self._toggle_analysis)
        self.buffer = ""
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_output)
        self.PHP_CheckBox.setChecked(True)
        self.ASP_CheckBox.setChecked(True)
        self.ASPX_CheckBox.setChecked(True)
        self.JSP_CheckBox.setChecked(True)
        self.CodeRadioButton.clicked.connect(self.radio_type)
        self.ShellRadioButton.clicked.connect(self.radio_type)

    def _init_state(self):
        self.current_files = []
        self.results = {}
        self.is_analysing = False

        # 定义提示词模板
        self.ollama_prompt = """【强制指令】你是一个专业的安全审计AI，请按以下要求分析代码：

                    1. 漏洞分析流程：
                       1.1 识别潜在风险点（SQL操作、文件操作、用户输入点、文件上传漏洞、CSRF、SSRF、XSS、RCE、OWASP top10等漏洞）
                       1.2 验证漏洞可利用性
                       1.3 按CVSS评分标准评估风险等级

                    2. 输出规则：
                       - 仅输出确认存在的高危/中危漏洞
                       - 使用严格格式：[风险等级] 类型 - 位置:行号 - 50字内描述
                       - 禁止解释漏洞原理
                       - 禁止给出修复建议
                       - 如果有可能，给出POC（HTTP请求数据包）

                    3. 输出示例（除此外不要有任何输出）：
                       [高危] SQL注入 - user_login.php:32 - 未过滤的$_GET参数直接拼接SQL查询
                       [POC]POST /login.php HTTP/1.1
                       Host: example.com
                       Content-Type: application/x-www-form-urlencoded
                       [中危] XSS - comment.jsp:15 - 未转义的userInput输出到HTML
                       [POC]POST /login.php HTTP/1.1
                       Host: example.com
                       Content-Type: application/x-www-form-urlencoded

                    4. 当前代码（仅限分析）：
                    {content}"""

        self.siliconflow_prompt = {
            "messages": [
                {
                    "content": """【强制指令】你是一个专业的安全审计AI，请按以下要求分析代码：

                            1. 漏洞分析流程：
                               1.1 识别潜在风险点（SQL操作、文件操作、用户输入点、文件上传漏洞、CSRF、SSRF、XSS、RCE、OWASP top10等漏洞）
                               1.2 验证漏洞可利用性
                               1.3 按CVSS评分标准评估风险等级

                            2. 输出规则：
                               - 仅输出确认存在的高危/中危漏洞
                               - 使用严格格式：[风险等级] 类型 - 位置:行号 - 50字内描述
                               - 禁止解释漏洞原理
                               - 禁止给出修复建议
                               - 如果有可能，给出POC（HTTP请求数据包）

                            3. 输出示例（除此外不要有任何输出）：
                               [高危] SQL注入 - user_login.php:32 - 未过滤的$_GET参数直接拼接SQL查询
                               [POC]POST /login.php HTTP/1.1
                               Host: example.com
                               Content-Type: application/x-www-form-urlencoded
                               [中危] XSS - comment.jsp:15 - 未转义的userInput输出到HTML
                               [POC]POST /login.php HTTP/1.1
                               Host: example.com
                               Content-Type: application/x-www-form-urlencoded""",
                    "role": "system"
                },
                {
                    "content": "{content}",
                    "role": "user"
                }
            ]
        }

        self.deepseek_prompt = {
            "messages": [
                {
                    "role": "system",
                    "content": """【强制指令】你是一个专业的安全审计AI，请按以下要求分析代码：

                                    1. 漏洞分析流程：
                                       1.1 识别潜在风险点（SQL操作、文件操作、用户输入点、文件上传漏洞、CSRF、SSRF、XSS、RCE、OWASP top10等漏洞）
                                       1.2 验证漏洞可利用性
                                       1.3 按CVSS评分标准评估风险等级

                                    2. 输出规则：
                                       - 仅输出确认存在的高危/中危漏洞
                                       - 使用严格格式：[风险等级] 类型 - 位置:行号 - 50字内描述
                                       - 禁止解释漏洞原理
                                       - 禁止给出修复建议
                                       - 如果有可能，给出POC（HTTP请求数据包）

                                    3. 输出示例（除此外不要有任何输出）：
                                       [高危] SQL注入 - user_login.php:32 - 未过滤的$_GET参数直接拼接SQL查询
                                       [POC]POST /login.php HTTP/1.1
                                       Host: example.com
                                       Content-Type: application/x-www-form-urlencoded
                                       [中危] XSS - comment.jsp:15 - 未转义的userInput输出到HTML
                                       [POC]POST /login.php HTTP/1.1
                                       Host: example.com
                                       Content-Type: application/x-www-form-urlencoded"""
                },
                {
                    "role": "user",
                    "content": "{content}"
                }
            ]
        }

    def _select_source(self):
        try:
            if self.MultifileButton.isChecked():
                directory = QFileDialog.getExistingDirectory(self, "选择文件夹", str(Path.home()))
                if directory:
                    self._set_source(directory, is_dir=True)
            else:
                file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", str(Path.home()))
                if file_path:
                    self._set_source(file_path, is_dir=False)
        except Exception as e:
            ShowInfoBar.createErrorInfoBar(self, f"文件选择失败: {str(e)}")

    def _set_source(self, path: str, is_dir: bool):
        if not Path(path).exists():
            ShowInfoBar.createErrorInfoBar(self, "指定路径不存在！")
            return

        self.current_source = path
        if is_dir:
            self.QLabel.setText(f"📂 数据源：{path}")
            root_index = self.model.setRootPath(path)
            self.filetree.setRootIndex(root_index)

            selected_exts = set()

            # 判断当前是 WebShell 模式 还是 代码审计模式
            if self.ShellRadioButton.isChecked():
                # WebShell 检测模式下的勾选项
                if self.PHP_CheckBox.isChecked(): selected_exts.add("php")
                if self.JSP_CheckBox.isChecked(): selected_exts.add("jsp")
                if self.ASP_CheckBox.isChecked(): selected_exts.add("asp")
                if self.ASPX_CheckBox.isChecked(): selected_exts.add("aspx")
                if self.JAVA_CheckBox.isChecked(): selected_exts.add("java")
                if self.PY_CheckBox.isChecked(): selected_exts.add("py")
                if self.HTML_CheckBox.isChecked(): selected_exts.add("html")
                if self.JS_CheckBox.isChecked(): selected_exts.add("js")
            else:
                # 代码审计模式下的勾选项（你可以定制不同的范围）
                if self.PHP_CheckBox.isChecked(): selected_exts.add("php")
                if self.JAVA_CheckBox.isChecked(): selected_exts.add("java")
                if self.PY_CheckBox.isChecked(): selected_exts.add("py")
                if self.HTML_CheckBox.isChecked(): selected_exts.add("html")
                if self.JS_CheckBox.isChecked(): selected_exts.add("js")

            self.current_files = [
                str(p) for p in Path(path).rglob("*")
                if p.is_file() and p.suffix.lower().lstrip('.') in selected_exts
            ]
        else:
            self.QLabel.setText(f"📄 数据源：{path}")
            root_index = self.model.setRootPath(str(Path(path).parent))
            self.filetree.setRootIndex(root_index)
            self.current_files = [path]

    def _toggle_analysis(self):
        """开始/暂停分析（多文件逐个显示）"""
        if not self.is_analysing:
            if not hasattr(self, 'current_source'):
                ShowInfoBar.createWarningInfoBar(self, '请先选择数据源！')
                return

            self.fileButton.setEnabled(False)
            self.results = {}
            self.outputEdit.clear()

            self.outputEdit.append("📝 分析报告 (结果的准确度取决于使用的模型)")
            self.outputEdit.append("=" * 40)
            self.outputEdit.append(f"📂 扫描文件总数: 正在统计中...")

            if self.ShellRadioButton.isChecked():
                self.outputEdit.append("⚠️ 检测为恶意文件: 正在统计中...")
                self.outputEdit.append("✅ 安全文件数量: 正在统计中...")
            else:
                self.outputEdit.append("⚠️ 存在风险文件: 正在统计中...")
                self.outputEdit.append("🐞 存在漏洞数量: 正在统计中...")

            self.outputEdit.append("=" * 40 + "\n")
            QApplication.processEvents()

            self.is_analysing = True
            self.StartButton.setText("暂停分析")
            self.StartButton.setIcon(FluentIcon.PAUSE)

            if os.path.isfile(self.current_source):
                result = self._analyze_single_file(self.current_source)
                self.results[self.current_source] = result
                self._append_single_file_report(self.current_source)
                self._update_report_stats()
                ShowInfoBar.createSuccessInfoBar(self, "分析完成")
                self.fileButton.setEnabled(True)
                self.is_analysing = False
                self.StartButton.setText("开始分析")
                self.StartButton.setIcon(FluentIcon.PLAY)
            else:
                self.analysis_thread = AnalyzeThread(self.current_files, self._analyze_single_file)
                self.analysis_thread.fileAnalyzed.connect(self._on_file_analyzed)
                self.analysis_thread.analysisFinished.connect(self._on_analysis_finished)
                self.analysis_thread.start()
        else:
            # 暂停分析时正确停止线程
            if hasattr(self, 'analysis_thread'):
                self.analysis_thread.stop()
                self.analysis_thread.quit()  # 请求退出线程事件循环
                self.analysis_thread.wait()  # 等待线程完全退出
            self.is_analysing = False
            self.StartButton.setText("开始分析")
            self.StartButton.setIcon(FluentIcon.PLAY)
            self.fileButton.setEnabled(True)

    def _on_analysis_finished(self):
        ShowInfoBar.createSuccessInfoBar(self, "分析完成")
        self.fileButton.setEnabled(True)
        self.is_analysing = False
        self.StartButton.setText("开始分析")
        self.StartButton.setIcon(FluentIcon.PLAY)

    def _on_file_analyzed(self, file_path: str, result: list):
        """在主线程中处理分析结果并更新 UI"""
        self.results[file_path] = result
        self._append_single_file_report(file_path)
        self._update_report_stats()

    def _analyze_single_file(self, file_path: str):
        """分析单个文件，并返回分析结果（适用于线程调用）"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(3000)
                encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'

            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read(3000)

            start_time = time.time()  # ✅ 开始计时

            # 判断分析模式
            if self.ShellRadioButton.isChecked():
                prompt = f"""请分析以下文件内容是否为WebShell或内存马。要求：
                    1. 检查PHP/JSP/ASP等WebShell特征（如加密函数、执行系统命令、文件操作）
                    2. 识别内存马特征（如无文件落地、进程注入、异常网络连接）
                    3. 分析代码中的可疑功能（如命令执行、文件上传、信息收集）
                    4. 检查混淆编码、加密手段等规避技术
                    5. 最终结论：是否为恶意软件（是/否）
                    6. 如果否，则输出安全文件，其他不要输出

                    请用中文按以下格式响应：
                    【分析结果】是/否
                    【恶意类型】WebShell/内存马/其他
                    【技术特征】列出检测到的技术指标
                    【风险等级】高/中/低

                    文件内容：
                    {content}"""
                if cfg.API_TYPE.value == "Ollama":
                    result = self._analyze_webshell_with_ollama(file_path, prompt)
                elif cfg.API_TYPE.value == "SiliconFlow":
                    result = self._analyze_webshell_with_siliconcloud(file_path, prompt)
                elif cfg.API_TYPE.value == "Deepseek":
                    result = self._analyze_webshell_with_deepseek(file_path, prompt)
                else:
                    result = [("错误", "未配置有效的模型类型", "")]
            else:
                # 普通代码审计模式
                if cfg.API_TYPE.value == "Ollama":
                    result = self._analyze_with_ollama(file_path, content)
                elif cfg.API_TYPE.value == "SiliconFlow":
                    result = self._analyze_with_siliconcloud(file_path, content)
                elif cfg.API_TYPE.value == "Deepseek":
                    result = self._analyze_with_deepseek(file_path, content)
                else:
                    result = [("错误", "未配置有效的模型类型", "")]

            duration = time.time() - start_time  # ✅ 计算耗时
            result.append(("__duration__", duration))  # ✅ 添加耗时数据
            return result

        except Exception as e:
            return [("错误", f"文件分析失败: {str(e)}", "")]

    def _analyze_directory(self, dir_path: str):
        """分析目录"""
        valid_extensions = {'php', 'java', 'py', 'js', 'jsp', 'html', 'asp', 'aspx'}
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.split('.')[-1].lower() not in valid_extensions:
                    continue

                full_path = os.path.join(root, file)
                self._analyze_single_file(full_path)

    def _analyze_with_ollama(self, file_path: str, content: str) -> list:
        try:
            if self.ShellRadioButton.isChecked():
                prompt = f"""请分析以下文件内容是否为WebShell或内存马。要求：
                    1. 检查PHP/JSP/ASP等WebShell特征（如加密函数、执行系统命令、文件操作）
                    2. 识别内存马特征（如无文件落地、进程注入、异常网络连接）
                    3. 分析代码中的可疑功能（如命令执行、文件上传、信息收集）
                    4. 检查混淆编码、加密手段等规避技术
                    5. 最终结论：是否为恶意软件（是/否）
                    6. 如果否，则输出安全文件，其他不要输出

                    请用中文按以下格式响应：
                    【分析结果】是/否
                    【恶意类型】WebShell/内存马/其他
                    【技术特征】列出检测到的技术指标
                    【风险等级】高/中/低

                    文件内容：
                    {content}
                    """
            else:
                prompt = self.ollama_prompt.format(content=content)

            response = self.session.post(
                f"{cfg.OLLAMA_API_URL.value}/api/generate",
                json={
                    "model": cfg.OLLAMA_MODEL.value,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=int(cfg.TIME_OUT.value)
            )
            response.raise_for_status()
            result = response.json()
            full_response = result.get("response", "")
            if "</think>" in full_response:
                full_response = full_response.split("</think>", 1)[-1].strip()
            return self._parse_result(file_path, full_response)
        except requests.exceptions.RequestException as e:
            return [("错误", f"API连接失败: {str(e)}", "")]
        except Exception as e:
            return [("错误", f"分析异常: {str(e)}", "")]

    def _analyze_with_siliconcloud(self, file_path: str, content: str) -> list:
        try:
            if self.ShellRadioButton.isChecked():
                # WebShell 检测提示词
                messages = [
                    {
                        "role": "system",
                        "content": """请分析以下文件内容是否为WebShell或内存马。要求：
                                    1. 检查PHP/JSP/ASP等WebShell特征（如加密函数、执行系统命令、文件操作）
                                    2. 识别内存马特征（如无文件落地、进程注入、异常网络连接）
                                    3. 分析代码中的可疑功能（如命令执行、文件上传、信息收集）
                                    4. 检查混淆编码、加密手段等规避技术
                                    5. 最终结论：是否为恶意软件（是/否）
                                    6. 如果否，则输出安全文件，其他不要输出

                                    请用中文按以下格式响应：
                                    【分析结果】是/否
                                    【恶意类型】WebShell/内存马/其他
                                    【技术特征】列出检测到的技术指标
                                    【风险等级】高/中/低"""
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            else:
                # 默认代码审计 messages
                messages = [
                    {
                        "role": "system",
                        "content": self.siliconflow_prompt["messages"][0]["content"]
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ]

            headers = {
                "Authorization": f"Bearer {cfg.SILICONCLOUD_API_KEY.value}",
                "Content-Type": "application/json"
            }

            data = {
                "model": cfg.SILICONCLOUD_MODEL.value,
                "messages": messages
            }

            start_time = time.time()
            response = requests.post(cfg.SILICONCLOUD_API_URL.value, headers=headers, json=data)
            print(f"📡 SiliconFlow 响应耗时: {time.time() - start_time:.2f}s")
            response.raise_for_status()
            result = response.json()
            print(result)
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            return self._parse_result(file_path, content)

        except requests.exceptions.RequestException as e:
            return [("错误", f"API连接失败: {str(e)}", "")]
        except Exception as e:
            return [("错误", f"分析异常: {str(e)}", "")]

    def _analyze_with_deepseek(self, file_path: str, content: str) -> list:
        try:
            if self.ShellRadioButton.isChecked():
                # WebShell 检测提示词
                messages = [
                    {
                        "role": "system",
                        "content": """请分析以下文件内容是否为WebShell或内存马。要求：
                                    1. 检查PHP/JSP/ASP等WebShell特征（如加密函数、执行系统命令、文件操作）
                                    2. 识别内存马特征（如无文件落地、进程注入、异常网络连接）
                                    3. 分析代码中的可疑功能（如命令执行、文件上传、信息收集）
                                    4. 检查混淆编码、加密手段等规避技术
                                    5. 最终结论：是否为恶意软件（是/否）
                                    6. 如果否，则输出安全文件，其他不要输出

                                    请用中文按以下格式响应：
                                    【分析结果】是/否
                                    【恶意类型】WebShell/内存马/其他
                                    【技术特征】列出检测到的技术指标
                                    【风险等级】高/中/低"""
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            else:
                # 默认代码审计 messages
                messages = [
                    {
                        "role": "system",
                        "content": self.deepseek_prompt["messages"][0]["content"]
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ]

            start_time = time.time()
            client = OpenAI(api_key=cfg.DEEPSEEK_API_KEY.value, base_url=cfg.DEEPSEEK_API_URL.value)
            response = client.chat.completions.create(
                model=cfg.DEEPSEEK_MODEL.value,
                messages=messages,
                stream=False
            )
            print(f"📡 Deepseek 响应耗时: {time.time() - start_time:.2f}s")
            content = response.choices[0].message.content
            return self._parse_result(file_path, content)

        except requests.exceptions.RequestException as e:
            return [("错误", f"API连接失败: {str(e)}", "")]
        except Exception as e:
            return [("错误", f"分析异常: {str(e)}", "")]

    def _parse_result(self, file_path: str, response: str) -> list:
        if self.ShellRadioButton.isChecked():
            return self._parse_webshell_result(file_path, response)
        else:
            return self._parse_code_audit_result(file_path, response)

    def _parse_webshell_result(self, file_path: str, response: str) -> list:
        """专门解析 WebShell 检测结果"""
        try:
            result = {}

            # 提取每一项
            analysis_match = re.search(r"【分析结果】\s*(是|否)", response)
            type_match = re.search(r"【恶意类型】\s*(.+?)\s*(?:【|$)", response)
            feature_match = re.search(r"【技术特征】([\s\S]*?)【风险等级】", response)
            risk_match = re.search(r"【风险等级】\s*(高|中|低)", response)

            result["分析结果"] = analysis_match.group(1).strip() if analysis_match else ""
            result["恶意类型"] = type_match.group(1).strip() if type_match else ""
            result["技术特征"] = feature_match.group(1).strip() if feature_match else ""
            result["风险等级"] = risk_match.group(1).strip() if risk_match else ""

            # 图标映射
            risk_icon = {
                "高": "🔥",
                "中": "⚠️",
                "低": "🟡"
            }.get(result["风险等级"], "")

            if result["分析结果"] == "是":
                return [(
                    "恶意",
                    result["恶意类型"],
                    result["技术特征"],
                    f"{risk_icon} 风险等级: {result['风险等级']}"
                )]
            else:
                return [("安全", "", "", "")]
        except Exception as e:
            return [("错误", f"WebShell 检测解析失败: {str(e)}", "")]

    def _parse_code_audit_result(self, file_path: str, response: str) -> list:
        findings = []
        current_vul = {}
        current_poc = []

        lines = response.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            vul_match = VULN_PATTERN.match(line)
            if vul_match:
                if current_vul:
                    current_vul['poc'] = '\n'.join(current_poc)
                    findings.append((
                        f"[{current_vul['level']}] {current_vul['type']}",
                        f"{os.path.basename(file_path)}:{current_vul['line']} - {current_vul['desc']}",
                        current_vul['poc']
                    ))
                    current_vul = {}
                    current_poc = []

                level, vul_type, filename, lineno, desc, _, poc_line = vul_match.groups()
                current_vul = {
                    'level': level,
                    'type': vul_type,
                    'file': filename,
                    'line': lineno,
                    'desc': desc
                }
                if poc_line:
                    current_poc.append(poc_line.strip())

                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith('[POC]'):
                        current_poc.append(next_line[5:].strip())
                        i += 1
                        while i < len(lines):
                            block_line = lines[i]
                            if VULN_PATTERN.match(block_line.strip()) or block_line.strip().startswith("[POC]"):
                                break
                            current_poc.append(block_line)
                            i += 1
                        continue
                    elif VULN_PATTERN.match(next_line):
                        # 不再回退索引，直接跳出内层循环，外层循环将处理新漏洞行
                        break
                    else:
                        i += 1
                continue
            i += 1

        if current_vul:
            current_vul['poc'] = '\n'.join(current_poc)
            findings.append((
                f"[{current_vul['level']}] {current_vul['type']}",
                f"{os.path.basename(file_path)}:{current_vul['line']} - {current_vul['desc']}",
                current_vul['poc']
            ))

        return findings if findings else [("信息", "未发现可验证的安全漏洞", "")]

    def _update_output(self):
        """定时批量更新 UI 输出，同时限制文本控件内容量"""
        if self.buffer:
            self.outputEdit.append(self.buffer)
            # 限制文本行数，例如只保留最近1000行
            if self.outputEdit.document().blockCount() > 1000:
                self.outputEdit.clear()
            self.buffer = ""
        else:
            self.timer.stop()

    def _generate_report(self) -> str:
        if self.ShellRadioButton.isChecked():
            return self._generate_webshell_report()
        else:
            return self._generate_code_audit_report()

    def _generate_code_audit_report(self) -> str:
        report = ["📝 分析报告", "=" * 40]
        total_files = len(self.results)
        vuln_files = sum(
            1 for issues in self.results.values()
            if any(issue[0].startswith("[高危") or issue[0].startswith("[中危") for issue in issues)
        )
        vuln_count = sum(
            1 for issues in self.results.values()
            for i in issues if i[0].startswith("[高危") or i[0].startswith("[中危")
        )

        report.append(f"📂 扫描文件总数: {total_files}")
        report.append(f"⚠️ 存在风险文件: {vuln_files}")
        report.append(f"🐞 存在漏洞数量: {vuln_count}")
        report.append("=" * 40 + "\n")

        for idx, (file_path, issues) in enumerate(self.results.items(), 1):
            base_name = os.path.basename(file_path)
            report.append(f"{idx}. 📄 文件: {base_name}")
            vuln_index = 1
            has_vul = False

            for issue in issues:
                if issue[0] == "错误":
                    report.append(f"   ❌ {issue[1]}")
                    continue
                if issue[0].startswith("[高危") or issue[0].startswith("[中危"):
                    has_vul = True
                    vul_type, desc, poc = issue
                    report.append(f"   {vuln_index}. 🔥 {vul_type}")
                    report.append(f"      📍 {desc}")
                    if poc.strip():
                        indented_poc = '\n'.join(f"         {line}" for line in poc.strip().splitlines())
                        report.append("      🔗 POC示例:")
                        report.append(indented_poc)
                    else:
                        report.append("      🚫 暂无可用POC示例")
                    report.append("")
                    vuln_index += 1

            if not has_vul:
                report.append("   ✅ 未发现可验证的安全漏洞")
            report.append("")

        return '\n'.join(report)

    def _generate_webshell_report(self) -> str:
        report = ["📝 分析报告", "=" * 40]
        total = len(self.results)
        malicious = sum(1 for issues in self.results.values() if issues and issues[0][0] == "恶意")
        safe = sum(1 for issues in self.results.values() if issues and issues[0][0] == "安全")

        report.append(f"📂 扫描文件总数: {total}")
        report.append(f"⚠️ 检测为恶意文件: {malicious}")
        report.append(f"✅ 安全文件数量: {safe}")
        report.append("=" * 40 + "\n")

        for idx, (file_path, issues) in enumerate(self.results.items(), 1):
            base_name = os.path.basename(file_path)
            report.append(f"{idx}. 📄 文件: {base_name}")
            issue = issues[0] if issues else None

            if not issue or issue[0] == "错误":
                report.append(f"   ❌ 检测失败: {issue[1] if issue else '未知错误'}")
            elif issue[0] == "恶意":
                _, evil_type, features, risk = issue
                report.append("   🚨 恶意文件: 是")
                report.append(f"   【恶意类型】{evil_type}")
                report.append("   【技术特征】")
                for line in features.strip().splitlines():
                    report.append(f"   {line.strip()}")
                report.append(f"   【风险等级】{risk}")
            elif issue[0] == "安全":
                report.append("   ✅ 未发现可疑WebShell或内存马")
            else:
                report.append("   ⚠️ 无法解析检测结果")

            report.append("")

        return '\n'.join(report)

    def _append_single_file_report(self, file_path: str):
        if self.ShellRadioButton.isChecked():
            self._append_webshell_report(file_path)
        else:
            self._append_code_audit_report(file_path)

        # 将光标移动到文本编辑框的最后一行
        cursor = self.outputEdit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.outputEdit.setTextCursor(cursor)
        self.outputEdit.ensureCursorVisible()

    def _append_code_audit_report(self, file_path: str):
        """代码审计模式下展示报告"""
        report = []
        base_name = os.path.basename(file_path)
        issues = self.results[file_path]
        idx = list(self.results.keys()).index(file_path) + 1
        report.append(f"{idx}. 📄 文件: {base_name}")

        # 提取响应时间
        duration = None
        if issues and isinstance(issues[-1], tuple) and issues[-1][0] in ("__duration__", "duration"):
            duration = issues.pop()[1]

        vuln_index = 1
        has_vul = False

        for issue in issues:
            if issue[0] == "错误":
                report.append(f"   ❌ {issue[1]}")
                continue

            if issue[0].startswith("[高危") or issue[0].startswith("[中危"):
                has_vul = True
                vul_type, desc, poc = issue
                report.append(f"   {vuln_index}. 🔥 {vul_type}")
                report.append(f"      📍 {desc}")
                if poc.strip():
                    indented_poc = '\n'.join(f"         {line}" for line in poc.strip().splitlines())
                    report.append("      🔗 POC示例:")
                    report.append(indented_poc)
                else:
                    report.append("      🚫 暂无可用POC示例")
                report.append("")
                vuln_index += 1

        if not has_vul:
            report.append("   ✅ 未发现可验证的安全漏洞")

        if duration:
            report.append(f"   🕒 响应耗时: {duration:.2f}s")

        report.append("")  # 文件之间空行
        self.outputEdit.append('\n'.join(report))
        QApplication.processEvents()

    def _append_webshell_report(self, file_path: str):
        """WebShell 检测模式下展示报告"""
        report = []
        base_name = os.path.basename(file_path)
        issues = self.results[file_path]
        idx = list(self.results.keys()).index(file_path) + 1
        report.append(f"{idx}. 📄 文件: {base_name}")

        # 提取响应时间
        duration = None
        if issues and isinstance(issues[-1], tuple) and issues[-1][0] in ("__duration__", "duration"):
            duration = issues.pop()[1]

        issue = issues[0] if issues else None
        if not issue or issue[0] == "错误":
            report.append(f"   ❌ 检测失败: {issue[1] if issue else '未知错误'}")
        elif issue[0] == "恶意":
            _, evil_type, features, risk = issue
            report.append("   🚨 恶意文件: 是")
            report.append(f"   【恶意类型】{evil_type}")
            report.append("   【技术特征】")
            for line in features.strip().splitlines():
                report.append(f"   {line.strip()}")
            report.append(f"   【风险等级】{risk}")
        elif issue[0] == "安全":
            report.append("   ✅ 未发现可疑WebShell或内存马")
        else:
            report.append("   ⚠️ 无法解析检测结果")

        if duration:
            report.append(f"   🕒 响应耗时: {duration:.2f}s")

        report.append("")
        self.outputEdit.append('\n'.join(report))
        QApplication.processEvents()

    def _update_report_stats(self):
        """更新报告统计头（支持 WebShell 与代码审计）"""
        total_files = len(self.results)
        malicious_files = 0
        safe_files = 0
        vuln_count = 0  # 仅用于代码审计

        for issues in self.results.values():
            if self.ShellRadioButton.isChecked():
                has_malicious = any(i[0] == "WebShell" for i in issues)
                if has_malicious:
                    malicious_files += 1
                else:
                    safe_files += 1
            else:
                has_vul = False
                for i in issues:
                    if isinstance(i, tuple) and (i[0].startswith("[高危") or i[0].startswith("[中危")):
                        vuln_count += 1
                        has_vul = True
                if has_vul:
                    malicious_files += 1
                else:
                    safe_files += 1

        cursor = self.outputEdit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(QTextCursor.MoveOperation.Down)  # ==== 分隔线
        cursor.movePosition(QTextCursor.MoveOperation.Down)  # 📂 扫描文件总数
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(f"📂 扫描文件总数: {total_files}")

        cursor.movePosition(QTextCursor.MoveOperation.Down)  # ⚠️ or 🔥
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        if self.ShellRadioButton.isChecked():
            cursor.insertText(f"⚠️ 检测为恶意文件: {malicious_files}")
        else:
            cursor.insertText(f"⚠️ 存在风险文件: {malicious_files}")

        cursor.movePosition(QTextCursor.MoveOperation.Down)  # ✅ or 🐞
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        if self.ShellRadioButton.isChecked():
            cursor.insertText(f"✅ 安全文件数量: {safe_files}")
        else:
            cursor.insertText(f"🐞 存在漏洞数量: {vuln_count}")

        self.outputEdit.setTextCursor(cursor)

        # 将光标移动到文本编辑框的最后一行
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.outputEdit.setTextCursor(cursor)
        self.outputEdit.ensureCursorVisible()

    def _analyze_webshell_with_ollama(self, file_path: str, prompt: str) -> list:
        try:
            response = requests.post(
                f"{cfg.OLLAMA_API_URL.value}/api/generate",
                json={"model": cfg.OLLAMA_MODEL.value, "prompt": prompt, "stream": False},
                timeout=int(cfg.TIME_OUT.value)
            )
            result = response.json()
            print(result)
            text = result.get("response", "")
            if "</think>" in text:
                text = text.split("</think>", 1)[-1].strip()
            # ❗返回给 _parse_webshell_result() 解析
            return self._parse_webshell_result(file_path, text)
        except Exception as e:
            return [("错误", f"Ollama API失败: {e}", "")]

    def _analyze_webshell_with_siliconcloud(self, file_path: str, prompt: str) -> list:
        try:
            headers = {
                "Authorization": f"Bearer {cfg.SILICONCLOUD_API_KEY.value}",
                "Content-Type": "application/json"
            }
            data = {
                "model": cfg.SILICONCLOUD_MODEL.value,
                "messages": [
                    {"role": "system", "content": "你是网络安全专家，负责WebShell与内存马检测"},
                    {"role": "user", "content": prompt}
                ]
            }

            start_time = time.time()
            response = requests.post(cfg.SILICONCLOUD_API_URL.value, headers=headers, json=data)
            print(f"📡 SiliconFlow 响应耗时: {time.time() - start_time:.2f}s")
            result = response.json()
            print(result)
            text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            # ❗返回给 _parse_webshell_result() 解析
            return self._parse_webshell_result(file_path, text)
        except Exception as e:
            return [("错误", f"Silicon API失败: {e}", "")]

    def _analyze_webshell_with_deepseek(self, file_path: str, prompt: str) -> list:
        try:
            data = {
                "model": cfg.SILICONCLOUD_MODEL.value,
                "messages": [
                    {"role": "system", "content": "你是网络安全专家，负责WebShell与内存马检测"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }

            start_time = time.time()
            client = OpenAI(api_key=cfg.DEEPSEEK_API_KEY.value, base_url=cfg.DEEPSEEK_API_URL.value)
            response = client.chat.completions.create(
                model=cfg.DEEPSEEK_MODEL.value,
                messages=data["messages"],
                stream=False
            )

            print(f"📡 Deepseek 响应耗时: {time.time() - start_time:.2f}s")
            text = response.choices[0].message.content

            print(text)
            # ❗返回给 _parse_webshell_result() 解析
            return self._parse_webshell_result(file_path, text)
        except Exception as e:
            return [("错误", f"deepseek API失败: {e}", "")]

    def radio_type(self):
        if self.CodeRadioButton.isChecked():
            self.HTML_CheckBox.setEnabled(True)
            self.JS_CheckBox.setEnabled(True)
        else:
            self.HTML_CheckBox.setEnabled(False)
            self.JS_CheckBox.setEnabled(False)