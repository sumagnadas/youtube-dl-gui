#!/mnt/sda2/python/virtualenvs/youtube-dl-gui/bin/python
import sys
import tempfile

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt
from modules.views import Window

threads = list()

if __name__ == "__main__":
    app = QApplication(["Youtube Downloader"])
    tempdir = tempfile.TemporaryDirectory()

    # Create the main window
    mainwindow = QMainWindow()
    mainwindow.setCentralWidget(Window())

    # Hide the maximize/minimize button
    mainwindow.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint |
                              Qt.WindowTitleHint | Qt.WindowSystemMenuHint |
                              Qt.WindowMinimizeButtonHint |
                              Qt.WindowCloseButtonHint)

    # Show the GUI application
    mainwindow.show()

    try:
        app.exec_()

        # Stop the threads which are downloading files
        for thread in threads:
            thread.terminate()
            thread.wait()

        # Exit the program
        sys.exit(0)
    except Exception:
        sys.exit(1)
