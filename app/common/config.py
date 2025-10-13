# coding:utf-8
import sys
from enum import Enum

from PySide6.QtCore import QLocale
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator, Theme, FolderValidator, ConfigSerializer)

from .setting import CONFIG_FILE

class Language(Enum):
    """ Language enumeration """

    CHINESE_SIMPLIFIED = QLocale(QLocale.Language.Chinese, QLocale.Country.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Language.Chinese, QLocale.Country.HongKong)
    ENGLISH = QLocale(QLocale.Language.English)
    AUTO = QLocale()


class LanguageSerializer(ConfigSerializer):
    """ Language serializer """

    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO


def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000


class Config(QConfig):
    """ Config of application """

    # TODO: ADD YOUR CONFIG GROUP HERE


    # main window
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", isWin11(), BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    language = OptionsConfigItem(
        "MainWindow", "Language", Language.AUTO, OptionsValidator(Language), LanguageSerializer(), restart=True)

    # software update
    checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", True, BoolValidator())

    API_TYPE = ConfigItem(
        "API_TYPE", "API_TYPE", "SiliconFlow"
    )

    # DeepSeek API配置
    DEEPSEEK_API_URL = ConfigItem(
        "DEEPSEEK", "DEEPSEEK_API_URL", "https://api.deepseek.com"
    )

    DEEPSEEK_API_KEY = ConfigItem(
        "DEEPSEEK", "DEEPSEEK_API_KEY", ""
    )

    # DeepSeek模型名称，官方默认模型: "deepseek-chat"
    DEEPSEEK_MODEL = ConfigItem(
        "DEEPSEEK", "DEEPSEEK_MODEL", "deepseek-chat"
    )

    DEEPSEEK_BALANCE = ConfigItem(
        "DEEPSEEK", "DEEPSEEK_BALANCE", "0"
    )



    # Ollama API配置
    OLLAMA_API_URL = ConfigItem(
        "OLLAMA", "OLLAMA_API_URL", "http://localhost:11434"
    )

    OLLAMA_API_KEY = ConfigItem(
        "OLLAMA", "OLLAMA_API_KEY", ""
    )

    OLLAMA_MODEL = ConfigItem(
        "OLLAMA", "OLLAMA_MODEL", "qwen2.5-coder:14b"
    )


    # SiliconCloud API配置
    SILICONCLOUD_API_URL = ConfigItem(
        "SILICONCLOUD", "SILICONCLOUD_API_URL", "https://api.siliconflow.cn/v1/chat/completions"
    )

    SILICONCLOUD_API_KEY = ConfigItem(
        "SILICONCLOUD", "SILICONCLOUD_API_KEY", ""
    )

    SILICONCLOUD_MODEL = ConfigItem(
        "SILICONCLOUD", "SILICONCLOUD_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
    )

    SILICONCLOUD_BALANCE = ConfigItem(
        "SILICONCLOUD", "SILICONCLOUD_BALANCE", "0"
    )

    TIME_OUT = ConfigItem(
        "TIME_OUT","TIME_OUT", 30
    )



cfg = Config()
cfg.themeMode.value = Theme.AUTO
qconfig.load(str(CONFIG_FILE.absolute()), cfg)