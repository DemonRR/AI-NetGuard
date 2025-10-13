import requests
from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication
from openai import OpenAI

from qfluentwidgets import (
    TextEdit, BodyLabel, HeaderCardWidget, PrimaryPushButton, FluentIcon
)

from ..common.config import cfg
from ..common.ShowInfoBar import ShowInfoBar


class DescriptionCard(HeaderCardWidget):
    """描述卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("描述")
        self.descriptionLabel = BodyLabel(
            "轻量级 HTTP 流量分析小工具，用户输入数据包，AI 模型快速检测异常特征，输出分析结果，一键识别潜在网络攻击。",
            self
        )
        self.descriptionLabel.setWordWrap(True)
        self.viewLayout.addWidget(self.descriptionLabel)
        self.setBorderRadius(8)


class HttpHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.rules = []

        method_format = QTextCharFormat()
        method_format.setForeground(QColor("#6f42c1"))
        method_format.setFontWeight(QFont.Weight.Bold)
        for method in ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"]:
            self.rules.append((QRegularExpression(rf"\b{method}\b"), method_format))

        protocol_format = QTextCharFormat()
        protocol_format.setForeground(QColor("#6f42c1"))
        self.rules.append((QRegularExpression(r"HTTP/\d\.\d"), protocol_format))

        url_param_format = QTextCharFormat()
        url_param_format.setForeground(QColor("#d73a49"))
        self.rules.append((QRegularExpression(r"(/\S+)"), url_param_format))

        self.header_line_pattern = QRegularExpression(r"^([\w-]+)\s*:\s*(.+)$")
        self.header_key_format = QTextCharFormat()
        self.header_key_format.setForeground(QColor("#6f42c1"))
        self.header_key_format.setFontWeight(QFont.Weight.Bold)

        self.header_value_format = QTextCharFormat()
        self.header_value_format.setForeground(QColor("#b31d28"))

    def highlightBlock(self, text: str):
        try:
            for pattern, fmt in self.rules:
                it = pattern.globalMatch(text)
                while it.hasNext():
                    match = it.next()
                    self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

            header_match = self.header_line_pattern.match(text)
            if header_match.hasMatch():
                self.setFormat(header_match.capturedStart(1), header_match.capturedLength(1), self.header_key_format)
                self.setFormat(header_match.capturedStart(2), header_match.capturedLength(2), self.header_value_format)
        except Exception as e:
            print("高亮异常：", e)


class TrafficAnalysisInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("trafficAnalysisInterface")
        self.descriptionCard = DescriptionCard(self)
        self._init_ui()
        self._init_layout()
        self.httpHighlighter = HttpHighlighter(self.inputEdit.document())

    def _init_ui(self):
        self.inputLabel = BodyLabel("📝 请输入 HTTP 请求数据包：")
        self.outputLabel = BodyLabel("📜 分析结果：")
        self.inputEdit = TextEdit()
        self.clearButton = PrimaryPushButton(FluentIcon.DELETE, '清空')
        self.startButton = PrimaryPushButton(FluentIcon.SEND, "开始分析")
        self.outputEdit = TextEdit()
        self.outputEdit.setReadOnly(True)

        self.clearButton.clicked.connect(self.inputEdit.clear)
        self.clearButton.clicked.connect(self.outputEdit.clear)
        self.startButton.clicked.connect(self._start_analysis)

    def _init_layout(self):
        self.mainLayout = QVBoxLayout()
        self.layout = QHBoxLayout()
        self.leftLayout = QVBoxLayout()
        self.rightLayout = QVBoxLayout()
        self.buttonLayout = QHBoxLayout()

        self.mainLayout.addWidget(self.descriptionCard)
        self.leftLayout.addWidget(self.inputLabel)
        self.leftLayout.addWidget(self.inputEdit)
        self.buttonLayout.addWidget(self.clearButton)
        self.buttonLayout.addWidget(self.startButton)
        self.leftLayout.addLayout(self.buttonLayout)
        self.rightLayout.addWidget(self.outputLabel)
        self.rightLayout.addWidget(self.outputEdit)

        self.layout.addLayout(self.leftLayout)
        self.layout.addLayout(self.rightLayout)
        self.layout.setStretch(0, 1)
        self.layout.setStretch(1, 1)

        self.mainLayout.addLayout(self.layout)
        self.setLayout(self.mainLayout)

    def _start_analysis(self):
        try:
            self.outputEdit.clear()
            QApplication.processEvents()  # 强制刷新清空状态

            raw_text = self.inputEdit.toPlainText().strip()
            if not raw_text:
                ShowInfoBar.createWarningInfoBar(self, "请输入 HTTP 请求内容")
                return

            # 显示初始分析状态
            self.outputEdit.append("📝 分析报告 (结果的准确度取决于使用的模型)")
            self.outputEdit.append("=" * 40)
            self.outputEdit.append("⚠️ 是存在风险数据包: 正在分析中...")
            self.outputEdit.append("=" * 40 + "\n")
            QApplication.processEvents()

            prompt = self._build_prompt(raw_text)

            if cfg.API_TYPE.value == "Ollama":
                response = self._analyze_with_ollama(prompt)
            elif cfg.API_TYPE.value == "SiliconFlow":
                response = self._analyze_with_siliconcloud(prompt)
            elif cfg.API_TYPE.value == "Deepseek":
                response = self._analyze_with_deepseek(prompt)
            else:
                response = "❌ 未配置模型类型"

            self._append_analysis_result(response)

        except Exception as e:
            ShowInfoBar.createErrorInfoBar(self, f"分析异常: {str(e)}")

    def _build_prompt(self, content: str) -> str:
        return f"""【强制指令】你是网络安全威胁鉴定专家，请严格按照以下格式进行分析：

            【分析结果】是/否
            【依据】
            - [攻击类型] 简要说明
            - [协议异常] 描述（如存在）
            
            【分析对象】
            {content}
            """

    def _analyze_with_ollama(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{cfg.OLLAMA_API_URL.value}/api/generate",
                json={
                    "model": cfg.OLLAMA_MODEL.value,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            result = response.json()
            raw_text = result.get("response", "")
            if "</think>" in raw_text:
                raw_text = raw_text.split("</think>", 1)[-1].strip()
            return raw_text
        except Exception as e:
            return f"❌ API 请求失败：{e}"

    def _analyze_with_siliconcloud(self, prompt: str) -> str:
        try:
            headers = {
                "Authorization": f"Bearer {cfg.SILICONCLOUD_API_KEY.value}",
                "Content-Type": "application/json"
            }
            data = {
                "model": cfg.SILICONCLOUD_MODEL.value,
                "messages": [
                    {"role": "system", "content": "你是网络安全威胁鉴定专家"},
                    {"role": "user", "content": prompt}
                ]
            }
            response = requests.post(cfg.SILICONCLOUD_API_URL.value, headers=headers, json=data)
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            return f"❌ API 请求失败：{e}"

    def _analyze_with_deepseek(self, prompt: str) -> str:
        try:
            data = {
                "messages": [
                    {"role": "system", "content": "你是网络安全威胁鉴定专家"},
                    {"role": "user", "content": prompt}
                ]
            }

            client = OpenAI(api_key=cfg.DEEPSEEK_API_KEY.value, base_url=cfg.DEEPSEEK_API_URL.value)
            response = client.chat.completions.create(
                model=cfg.DEEPSEEK_MODEL.value,
                messages=data["messages"],
                stream=False
            )
            result = response.choices[0].message.content
            return result
        except Exception as e:
            return f"❌ API 请求失败：{e}"

    def _append_analysis_result(self, response: str):
        """美化格式并更新风险状态提示"""
        formatted = self._format_response(response)
        self.outputEdit.append(formatted)

        # ✅ 更新“正在分析中...”行内容
        cursor = self.outputEdit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(QTextCursor.MoveOperation.Down)  # 到 ======
        cursor.movePosition(QTextCursor.MoveOperation.Down)  # 到 ⚠️ 正在分析中...

        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()

        if "【分析结果】是" in response or "【分析结果】: 是" in response:
            cursor.insertText("⚠️ 是存在风险数据包: 是")
        elif "【分析结果】否" in response or "【分析结果】: 否" in response:
            cursor.insertText("⚠️ 是存在风险数据包: 否")
        else:
            cursor.insertText("⚠️ 是存在风险数据包: 无法识别")

        self.outputEdit.setTextCursor(cursor)

    def _format_response(self, response: str) -> str:
        """优化显示格式"""
        if "【分析对象】" in response:
            response = response.split("【分析对象】")[0].strip()

        lines = response.strip().splitlines()
        formatted = []
        for line in lines:
            line = line.strip()
            if line.startswith("【分析结果】"):
                formatted.append(f"🔍 {line}")
            elif line.startswith("【依据】"):
                formatted.append(f"\n📌 {line}")
            elif line.startswith("-"):
                formatted.append(f"   {line}")
            else:
                formatted.append(line)

        return "\n".join(formatted)
