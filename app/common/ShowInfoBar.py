from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from qfluentwidgets import InfoBarPosition, InfoBar


class ShowInfoBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createErrorInfoBar(father, text):
        InfoBar.error(
            title='Error',
            content=text,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=5000,
            parent=father
        )

    def createSuccessInfoBar(father, text):
        # convenient class mothod
        InfoBar.success(
            title='Success',
            content=text,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000,
            parent=father
        )


    def createWarningInfoBar(father, text):
        InfoBar.warning(
            title='Warning',
            content=text,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=5000,
            parent=father
        )


