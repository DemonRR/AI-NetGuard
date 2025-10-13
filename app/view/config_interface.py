# coding:utf-8
import os
import sys

import requests
from PySide6.QtCore import Qt, QPoint, QSize, QUrl, QRect, QPropertyAnimation, Signal, QTimer
from PySide6.QtGui import QIcon, QFont, QColor, QPainter, QDesktopServices
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect, QLabel, QPushButton

from qfluentwidgets import (
    IconWidget, BodyLabel, CaptionLabel,
    TransparentToolButton, FluentIcon,
    ImageLabel, SimpleCardWidget,
    HeaderCardWidget, InfoBarIcon,
    PrimaryPushButton, TitleLabel, PillPushButton, setFont, ScrollArea,
    VerticalSeparator, GroupHeaderCardWidget,
    ComboBox, LineEdit, PasswordLineEdit, HorizontalSeparator, HyperlinkLabel, HyperlinkButton
)
from requests.exceptions import RequestException, Timeout

from ..common.ShowInfoBar import ShowInfoBar
from ..common.icon import Icon
from ..common.config import cfg
from ..common.setting import VERSION, owner, STAR_URL, date


class StatisticsWidget(QWidget):
    """ Statistics widget """

    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent=parent)
        self.titleLabel = CaptionLabel(title, self)
        self.valueLabel = BodyLabel(value, self)
        self.vBoxLayout = QVBoxLayout(self)

        self.vBoxLayout.setContentsMargins(16, 0, 16, 0)
        self.vBoxLayout.addWidget(self.valueLabel, 0, Qt.AlignmentFlag.AlignTop)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignBottom)

        setFont(self.valueLabel, 18, QFont.Weight.DemiBold)
        self.titleLabel.setTextColor(QColor(96, 96, 96), QColor(206, 206, 206))


class AppInfoCard(SimpleCardWidget):
    """ App information card """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.iconLabel = ImageLabel(":/app/images/logo.png", self)
        self.iconLabel.setBorderRadius(8, 8, 8, 8)
        self.iconLabel.scaledToWidth(120)

        self.nameLabel = TitleLabel('AI-NetGuard', self)

        self.versionWidget = StatisticsWidget('当前版本', VERSION, self)
        self.separator1 = VerticalSeparator(self)
        self.authorWidget = StatisticsWidget('作者', owner, self)
        self.separator2 = VerticalSeparator(self)
        self.dateWidget = StatisticsWidget('更新日期', date, self)

        self.descriptionLabel = BodyLabel(
            '基于Python和PySide6框架开发，集成DeepSeek等先进AI模型，提供智能代码审计、Webshell检测及流量分析研判功能，助力网络安全团队高效识别与处置威胁，提升整体防御能力。', self)
        self.descriptionLabel.setWordWrap(True)

        self.tagButton = PillPushButton('Github', self)
        self.tagButton.setCheckable(False)
        setFont(self.tagButton, 12)
        self.tagButton.setFixedSize(80, 32)

        self.shareButton = TransparentToolButton(FluentIcon.SHARE, self)
        self.shareButton.setFixedSize(32, 32)
        self.shareButton.setIconSize(QSize(14, 14))
        self.shareButton.clicked.connect(self.onShareButtonClicked)

        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()
        self.topLayout = QHBoxLayout()
        self.statisticsLayout = QHBoxLayout()
        self.buttonLayout = QHBoxLayout()

        self.initLayout()
        self.setBorderRadius(8)

    def initLayout(self):
        self.hBoxLayout.setSpacing(30)
        self.hBoxLayout.setContentsMargins(34, 24, 24, 24)
        self.hBoxLayout.addWidget(self.iconLabel)
        self.hBoxLayout.addLayout(self.vBoxLayout)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        # name label and install button
        self.vBoxLayout.addLayout(self.topLayout)
        self.topLayout.setContentsMargins(0, 0, 0, 0)
        self.topLayout.addWidget(self.nameLabel)

        # statistics widgets
        self.vBoxLayout.addSpacing(20)
        self.vBoxLayout.addLayout(self.statisticsLayout)
        self.statisticsLayout.setContentsMargins(0, 0, 0, 0)
        self.statisticsLayout.setSpacing(10)
        self.statisticsLayout.addWidget(self.versionWidget)
        self.statisticsLayout.addWidget(self.separator1)
        self.statisticsLayout.addWidget(self.authorWidget)
        self.statisticsLayout.addWidget(self.separator2)
        self.statisticsLayout.addWidget(self.dateWidget)
        self.statisticsLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # description label
        self.vBoxLayout.addSpacing(20)
        self.vBoxLayout.addWidget(self.descriptionLabel)

        # button
        self.vBoxLayout.addSpacing(12)
        self.buttonLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.addLayout(self.buttonLayout)
        self.buttonLayout.addWidget(self.tagButton, 0, Qt.AlignmentFlag.AlignLeft)
        self.buttonLayout.addWidget(self.shareButton, 0, Qt.AlignmentFlag.AlignRight)

    def onShareButtonClicked(self):
        # 打开指定的 URL
        url = QUrl(STAR_URL)  # 替换为你想要打开的 URL
        QDesktopServices.openUrl(url)


class DescriptionCard(HeaderCardWidget):
    """ Description card """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('描述')

        self.infoLabel = BodyLabel('请填写对应平台的API接口、模型和秘钥，秘钥非必填项；点击下方按钮可查看对应平台支持的模型', self)
        self.successIcon = IconWidget(InfoBarIcon.SUCCESS, self)
        self.DeepSeekLinkButton = HyperlinkButton(QIcon(':/app/images/icons/deepseek.svg'), "https://api-docs.deepseek.com/zh-cn/quick_start/pricing", 'Deepseek')
        self.SiliconFlowLinkButton = HyperlinkButton(QIcon(":/app/images/icons/SiliconCloud.svg"), "https://cloud.siliconflow.cn/i/248qVb73", 'SiliconFlow')
        self.OllamaLinkButton = HyperlinkButton(Icon.OLLAMA, "https://ollama.com/search", 'Ollama')

        self.vBoxLayout = QVBoxLayout()
        self.hBoxLayout = QHBoxLayout()
        self.buttonLayout = QHBoxLayout()

        self.successIcon.setFixedSize(16, 16)
        self.hBoxLayout.setSpacing(10)
        self.vBoxLayout.setSpacing(16)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)

        self.hBoxLayout.addWidget(self.successIcon)
        self.hBoxLayout.addWidget(self.infoLabel)
        self.vBoxLayout.addLayout(self.hBoxLayout)
        self.buttonLayout.addWidget(self.SiliconFlowLinkButton, 0, Qt.AlignmentFlag.AlignLeft)
        self.buttonLayout.addWidget(self.OllamaLinkButton, 0, Qt.AlignmentFlag.AlignLeft)
        self.buttonLayout.addWidget(self.DeepSeekLinkButton, 0, Qt.AlignmentFlag.AlignLeft)
        self.vBoxLayout.addLayout(self.buttonLayout)

        self.viewLayout.addLayout(self.vBoxLayout)


class ModelTypeCard(GroupHeaderCardWidget):
    modelTypeChanged = Signal(str)  # 定义一个信号，用于传递当前选择的模型类型

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("平台选择")
        self.setBorderRadius(8)

        self.model_type_comboBox = ComboBox()
        items = ['Ollama', 'SiliconFlow', 'Deepseek']
        self.model_type_comboBox.addItems(items)
        self.model_type_comboBox.setCurrentText(cfg.API_TYPE.value)
        self.model_type_comboBox.setFixedWidth(120)
        self.model_type_comboBox.currentIndexChanged.connect(self.onModelTypeChanged)

        self.addGroup(Icon.MODEL_TYPE, "Service Platforms", "请选择你需要使用的模型服务平台", self.model_type_comboBox)

    def onModelTypeChanged(self, index):
        """当模型类型发生变化时，发射信号"""
        model_type = self.model_type_comboBox.currentText()
        self.modelTypeChanged.emit(model_type)
        cfg.set(cfg.API_TYPE, self.model_type_comboBox.currentText().strip())


class BaseModelCard(GroupHeaderCardWidget):
    """Base class for model cards"""

    def __init__(self, title, icon, items, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setBorderRadius(8)
        self.model_lineEdit = LineEdit()
        self.Url_lineEdit = LineEdit()
        self.Key_lineEdit = PasswordLineEdit()
        self.balanceLabel = QLabel()
        self.balanceButton = PrimaryPushButton("刷新余额")
        self.timeout_comboBox = ComboBox()
        items = ["30", "60", "90", "120"]
        self.timeout_comboBox.addItems(items)
        self.timeout_comboBox.setCurrentText(cfg.TIME_OUT.value)
        self.timeout_comboBox.currentIndexChanged.connect(self.onTimeoutChanged)

        self.model_lineEdit.setFixedWidth(320)
        self.Url_lineEdit.setFixedWidth(320)
        self.Key_lineEdit.setFixedWidth(400)

        self.addGroup(icon, 'Models', "输入或选择一个大模型", self.model_lineEdit)
        self.addGroup(icon, "API URL", "输入API地址", self.Url_lineEdit)
        self.addGroup(icon, "API KEY", "输入你的API秘钥", self.Key_lineEdit)
        self.addGroup(icon, "Timeout", '自定义api响应超时时间', self.timeout_comboBox)


        self.saveIcon = IconWidget(InfoBarIcon.INFORMATION)
        self.saveLabel = BodyLabel("点击按钮进行保存 👉")
        self.saveButton = PrimaryPushButton(FluentIcon.SEND, "保存")
        self.bottomLayout = QHBoxLayout()
        self.saveIcon.setFixedSize(16, 16)
        self.bottomLayout.setSpacing(10)
        self.bottomLayout.setContentsMargins(24, 15, 24, 20)
        self.bottomLayout.addWidget(self.saveIcon, 0, Qt.AlignmentFlag.AlignLeft)
        self.bottomLayout.addWidget(self.saveLabel, 0, Qt.AlignmentFlag.AlignLeft)
        self.bottomLayout.addStretch(1)
        self.bottomLayout.addWidget(self.saveButton, 0, Qt.AlignmentFlag.AlignRight)
        self.bottomLayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.line = HorizontalSeparator()
        self.vBoxLayout.addWidget(self.line)
        self.vBoxLayout.addLayout(self.bottomLayout)

        # 绑定保存按钮的点击事件
        self.saveButton.clicked.connect(lambda: self.save_settings(title))


    def _get_balance(self):
        aa = ConfigInterface(self)
        self.saveButton.clicked.connect(aa.get_balance())

    def save_settings(self, types):
        """保存配置项"""
        try:
            # 获取输入框内容
            api_url = self.Url_lineEdit.text().strip()
            model = self.model_lineEdit.text().strip()
            api_key = self.Key_lineEdit.text().strip()

            # 验证必填项
            if not api_url or not model:
                ShowInfoBar.createErrorInfoBar(self.parent().parent(), "API接口和模型为必填项")
                return

            # 根据类型保存配置
            if types == "Ollama":
                cfg.set(cfg.OLLAMA_API_URL, api_url)
                cfg.set(cfg.OLLAMA_MODEL, model)
                cfg.set(cfg.OLLAMA_API_KEY, api_key)
            elif types == "Deepseek":
                if not api_key:
                    ShowInfoBar.createWarningInfoBar(self.parent().parent(), "API密钥为必填项")
                    return
                cfg.set(cfg.DEEPSEEK_API_URL, api_url)
                cfg.set(cfg.DEEPSEEK_MODEL, model)
                cfg.set(cfg.DEEPSEEK_API_KEY, api_key)
            elif types == "SiliconFlow":
                if not api_key:
                    ShowInfoBar.createWarningInfoBar(self.parent().parent(), "API密钥为必填项")
                    return
                cfg.set(cfg.SILICONCLOUD_API_URL, api_url)
                cfg.set(cfg.SILICONCLOUD_MODEL, model)
                cfg.set(cfg.SILICONCLOUD_API_KEY, api_key)
            else:
                ShowInfoBar.createWarningInfoBar(self.parent().parent(), "未知的配置类型")
                return

            # 保存成功提示
            ShowInfoBar.createSuccessInfoBar(self.parent().parent(), "保存成功！")

        except Exception as e:
            # 捕获并处理异常
            ShowInfoBar.createWarningInfoBar(self.parent().parent(), f"保存失败：{str(e)}")

    def onTimeoutChanged(self):
        cfg.set(cfg.TIME_OUT, self.timeout_comboBox.currentText())

class OllamaCard(BaseModelCard):
    def __init__(self, parent=None):
        super().__init__("Ollama", Icon.OLLAMA, "OLLAMA_MODELS", parent)
        self.Url_lineEdit.setText(cfg.OLLAMA_API_URL.value)
        self.model_lineEdit.setText(cfg.OLLAMA_MODEL.value)



class DeepseekCard(BaseModelCard):
    def __init__(self, parent=None):
        super().__init__("Deepseek", ":/app/images/icons/Deepseek.svg", parent)
        self.Url_lineEdit.setText(cfg.DEEPSEEK_API_URL.value)
        self.model_lineEdit.setText(cfg.DEEPSEEK_MODEL.value)
        self.Key_lineEdit.setText(cfg.DEEPSEEK_API_KEY.value)
        self.DeepseekBalance = self.addGroup(":/app/images/icons/balance.svg", '￥', '当前API余额', self.balanceButton)

class SiliconCloudCard(BaseModelCard):
    def __init__(self, parent=None):
        super().__init__("SiliconFlow", ":/app/images/icons/SiliconCloud.svg", parent)
        self.Url_lineEdit.setText(cfg.SILICONCLOUD_API_URL.value)
        self.model_lineEdit.setText(cfg.SILICONCLOUD_MODEL.value)
        self.Key_lineEdit.setText(cfg.SILICONCLOUD_API_KEY.value)
        self.SiliconFlowBalance = self.addGroup(":/app/images/icons/balance.svg", '￥', '当前API余额', self.balanceButton)


class ConfigInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWidget(self)

        # 初始化界面组件（注意：卡片不要提前创建）
        self.appCard = AppInfoCard(self)
        self.descriptionCard = DescriptionCard(self)
        self.modelTypeCard = ModelTypeCard(self)

        # 初始化 card 占位（延迟创建）
        self.ollamaCard = None
        self.deepseekCard = None
        self.siliconCloud = None
        self.currentCard = None  # ✅ 当前显示的卡片

        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("appInterface")

        # 设置布局
        self.vBoxLayout = QVBoxLayout(self.view)
        self.vBoxLayout.setSpacing(10)
        self.vBoxLayout.setContentsMargins(0, 0, 10, 30)
        self.vBoxLayout.addWidget(self.appCard, 0, Qt.AlignmentFlag.AlignTop)
        self.vBoxLayout.addWidget(self.descriptionCard, 0, Qt.AlignmentFlag.AlignTop)
        self.vBoxLayout.addWidget(self.modelTypeCard, 0, Qt.AlignmentFlag.AlignTop)

        # 启用透明背景
        self.enableTransparentBackground()

        # 连接信号槽，当模型类型发生变化时，动态更新布局
        self.modelTypeCard.modelTypeChanged.connect(self.updateModelCards)

        # ✅ 启动后延迟执行：先更新卡片，再刷新余额
        QTimer.singleShot(0, self._init_after_show)

        # 初始化时，根据当前选择的平台加载卡片并设置 currentCard
        QTimer.singleShot(0, lambda: self.updateModelCards(self.modelTypeCard.model_type_comboBox.currentText()))

    def updateModelCards(self, model_type):
        """根据模型类型动态更新布局"""
        # 移除并隐藏所有旧卡片（但不销毁）
        for widget in [self.ollamaCard, self.deepseekCard, self.siliconCloud]:
            if widget is not None:
                widget.hide()
                self.vBoxLayout.removeWidget(widget)

        # 清理 layout 中所有 BaseModelCard 子类（防止 macOS 堆叠）
        for i in reversed(range(self.vBoxLayout.count())):
            item = self.vBoxLayout.itemAt(i).widget()
            if isinstance(item, BaseModelCard):
                self.vBoxLayout.removeWidget(item)
                item.setParent(None)
                item.deleteLater()

        # 根据选择重新创建卡片并设为 currentCard
        if model_type == 'Ollama':
            self.ollamaCard = OllamaCard(self)
            self.currentCard = self.ollamaCard
            self.vBoxLayout.addWidget(self.ollamaCard, 0, Qt.AlignmentFlag.AlignTop)

        elif model_type == 'Deepseek':
            self.deepseekCard = DeepseekCard(self)
            self.currentCard = self.deepseekCard
            self.deepseekCard.DeepseekBalance.setTitle(f'￥{cfg.DEEPSEEK_BALANCE.value}')
            self.deepseekCard.balanceButton.clicked.connect(self.refresh_balance)
            self.vBoxLayout.addWidget(self.deepseekCard, 0, Qt.AlignmentFlag.AlignTop)

        elif model_type == 'SiliconFlow':
            self.siliconCloud = SiliconCloudCard(self)
            self.currentCard = self.siliconCloud
            self.siliconCloud.SiliconFlowBalance.setTitle(f'￥{cfg.SILICONCLOUD_BALANCE.value}')
            self.siliconCloud.balanceButton.clicked.connect(self.refresh_balance)
            self.vBoxLayout.addWidget(self.siliconCloud, 0, Qt.AlignmentFlag.AlignTop)

        self.view.adjustSize()
        self.view.update()
        self.view.repaint()
        self.update()
        self.repaint()

    def get_balance(self):
        """通用方法：查询模型余额，并更新当前显示的卡片余额信息"""
        model_type = cfg.API_TYPE.value
        url = None
        api_key = None

        try:
            if model_type == 'Deepseek':
                url = "https://api.deepseek.com/user/balance"
                api_key = cfg.DEEPSEEK_API_KEY.value
            elif model_type == 'SiliconFlow':
                url = "https://api.siliconflow.cn/v1/user/info"
                api_key = cfg.SILICONCLOUD_API_KEY.value
            else:
                return  # Ollama 不支持余额查询

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Accept': 'application/json'
            }

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            result = response.json()

            # ⚠️ 获取当前显示的卡片
            card = getattr(self, 'currentCard', None)
            if not card:
                ShowInfoBar.createWarningInfoBar(self, "未找到当前卡片")
                return

            # 更新余额信息到 currentCard
            if model_type == 'Deepseek' and 'balance_infos' in result and result['balance_infos']:
                balance = result["balance_infos"][0].get("total_balance", "未知余额")
                cfg.set(cfg.DEEPSEEK_BALANCE, str(balance))
                if hasattr(card, "DeepseekBalance"):
                    card.DeepseekBalance.setTitle(f'￥{str(balance)}')

            elif model_type == 'SiliconFlow' and 'data' in result and 'balance' in result['data']:
                balance = result['data']['balance']
                cfg.set(cfg.SILICONCLOUD_BALANCE, str(balance))
                if hasattr(card, "SiliconFlowBalance"):
                    card.SiliconFlowBalance.setTitle(f'￥{str(balance)}')

            else:
                ShowInfoBar.createWarningInfoBar(self, "未能获取到余额信息")
                return

            ShowInfoBar.createSuccessInfoBar(self, "余额刷新成功！")

        except (Timeout, RequestException) as e:
            ShowInfoBar.createWarningInfoBar(self, f"余额查询失败: {str(e)}")
        except Exception as e:
            ShowInfoBar.createWarningInfoBar(self, f"未知错误: {str(e)}")

        self.refreshLayout()

    def refresh_balance(self):
        """刷新余额，刷新前强制重新渲染当前卡片，避免堆叠"""
        # ⚠️ 移除旧卡片（彻底重新触发布局）
        self.updateModelCards(cfg.API_TYPE.value)

        # ✅ 更新余额（更新的是刚刚新建的 currentCard）
        self.get_balance()

        # ✅ 展示成功信息
        ShowInfoBar.createSuccessInfoBar(self, "余额刷新成功！")

    def refreshLayout(self):
        # 停止所有动画
        for child in self.findChildren(QPropertyAnimation):
            child.stop()

        # 更新布局
        layout = self.layout()
        if layout:
            layout.update()
            layout.activate()

        # 重绘组件
        self.update()
        self.repaint()

    def _init_after_show(self):
        self.updateModelCards(self.modelTypeCard.model_type_comboBox.currentText())
        self.get_balance()

