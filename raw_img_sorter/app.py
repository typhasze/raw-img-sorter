import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from .window import MainWindow


def main() -> int:
    QCoreApplication.setOrganizationName("RAW IMG Sorter")
    QCoreApplication.setApplicationName("RAW IMG Sorter")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#eeeeee"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#151515"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#eeeeee"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#303134"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#eeeeee"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3f6ad8"))
    app.setPalette(palette)
    window = MainWindow()
    window.show()
    return app.exec()
