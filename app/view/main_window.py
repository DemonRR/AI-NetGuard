# coding: utf-8
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import QApplication

from qfluentwidgets import NavigationItemPosition, FluentWindow, SplashScreen, InfoBadge, InfoBadgePosition
from qfluentwidgets import FluentIcon as FIF

from .setting_interface import SettingInterface
from .codeAudit_interface import CodeAuditInterface
from .trafficAnalysis_interface import TrafficAnalysisInterface
from .config_interface import ConfigInterface
from ..common.ShowInfoBar import ShowInfoBar
from ..common.config import cfg
from ..common.icon import Icon
from ..common.signal_bus import signalBus
from ..common import resource


class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()
        self.initWindow()

        # TODO: create sub interface
        self.settingInterface = SettingInterface(self)
        self.configInterface = ConfigInterface()
        self.codeAuditInterface = CodeAuditInterface(self)
        self.trafficAnalysisInterface = TrafficAnalysisInterface()



        self.connectSignalToSlot()

        # add items to navigation interface
        self.initNavigation()

    def connectSignalToSlot(self):
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)

    def initNavigation(self):

        # add custom widget to bottom
        self.addSubInterface(
            self.configInterface, FIF.HOME, '基础配置', NavigationItemPosition.TOP
        )

        self.addSubInterface(
            self.codeAuditInterface, Icon.CODE, '代码分析', NavigationItemPosition.TOP
        )

        self.addSubInterface(
            self.trafficAnalysisInterface, Icon.ANALYZE, '流量分析', NavigationItemPosition.TOP
        )

        setting_button = self.addSubInterface(
            self.settingInterface, FIF.SETTING, self.tr('Settings'), NavigationItemPosition.BOTTOM)

        # 给设置按钮添加徽章
        if self.settingInterface.check_update():
            InfoBadge.attension(
                text=1,
                parent=setting_button.parent(),
                target=setting_button,
                position=InfoBadgePosition.NAVIGATION_ITEM
            )
            ShowInfoBar.createWarningInfoBar(self, '有新版本可以升级！')

        # self.navigationInterface.setCurrentItem(self.searchInterface)

        self.splashScreen.finish()

    def initWindow(self):
        self.resize(960, 680)
        self.setMinimumWidth(760)
        self.setWindowIcon(QIcon(':/app/images/logo.png'))
        self.setWindowTitle('AI-NetGuard')

        self.setCustomBackgroundColor(QColor(240, 244, 249), QColor(32, 32, 32))
        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # create splash screen
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()
        QApplication.processEvents()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'splashScreen'):
            self.splashScreen.resize(self.size())