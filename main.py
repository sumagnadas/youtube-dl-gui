#!/mnt/sda2/python/virtualenvs/youtube-dl-gui/bin/python
import youtube_dl
import sys
import pandas as pd

from youtube_search import YoutubeSearch
from urllib import request
from os.path import abspath, exists
from os import system
from PySide2.QtWidgets import (QApplication, QWidget, QLabel, QPushButton,
                               QVBoxLayout, QHBoxLayout, QLineEdit,
                               QSizePolicy, QMenu, QFrame, QFileDialog,
                               QTabWidget, QTableView, QMainWindow)
from PySide2.QtGui import QImage, QPixmap
from PySide2.QtCore import (Qt, QThread, QAbstractTableModel,
                            QObject, Signal, Slot)


class SignalManager(QObject):
    editSignal = Signal(str, int, object)


class TableModel(QAbstractTableModel):
    """
    Table Model for the table on the Downloads tab
    """

    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data

    def data(self, index, role):
        """
        Return the data in the cell pointed to by its index in "index" variable
        This function helps display the data on the table
        """
        if role == Qt.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)

    def rowCount(self, index):
        """
        Return the number of rows
        """
        return self._data.shape[0]

    def setData(self, column, row, value):
        """
        Change the value of the individual cell pointed to
        by the "column" and "row"
        """
        self.layoutAboutToBeChanged.emit()
        self._data.at[row, str(column)] = value
        self.layoutChanged.emit()

    def addRow(self):
        """
        Add an empty row to the table
        """
        self.layoutAboutToBeChanged.emit()
        self._data = self._data.append(pd.DataFrame([["", "", "", ""]],
                                       columns=['Video Name',
                                                'File Name',
                                                'Percent',
                                                'ETA']), ignore_index=True)
        self.layoutChanged.emit()

    def columnCount(self, index):
        """
        Return the number of columns
        """
        return self._data.shape[1]

    def headerData(self, section, orientation, role):
        """
        Show the name of the column
        """
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])

            if orientation == Qt.Vertical:
                return str(self._data.index[section])

    @Slot(str, int, object)
    def update_item(self, col, row, value):
        self.setData(col, row, value)


class BGThread(QThread):
    """
    Thread for running the download in background
    so that the GUI doesn't freeze.
    """

    def __init__(self, ydl, url):
        QThread.__init__(self)
        self.ydl, self.url = ydl, url
        self.started = False

    def run(self):
        if not self.started:
            # if the download hasn't started yet, then start it
            self.ydl.download([self.url])
            self.started = True


class Extractor(object):
    """
    Extract the data of the resolutions in which the video
    is available from the the YoutubeDL module
    """

    def debug(self, msg):
        with open("output.txt", "w") as f:
            self.qualityList = list()
            for line in msg.splitlines():
                quality = line.split()[3]
                if quality.isalnum() and (not quality.isalpha()) and \
                                         (not quality.isnumeric()):
                    self.qualityList.append(quality)
            self.qualityList = set(self.qualityList)
            f.write("\n".join(self.qualityList))

    def error(self, msg):
        print(msg)


class Results(QWidget):
    """
    Show the results in a list form on the window
    """

    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)


class Specs(QMenu):
    """
    Menu for
    1) selecting the resolution of the video
    2) the option for downloading only the audio
    """

    def __init__(self):
        super().__init__()
        self.qualMenu = self.addMenu("Quality")
        self.addAction("Audio only").setCheckable(True)


class Video(QFrame):
    """
    Each Item in the Results tab is built using this class
    """

    def __init__(self, widget):
        super().__init__()

        self.layout = QHBoxLayout()
        self.fileName = str()
        self.downloadButton = QPushButton(
            "Download", clicked=lambda: download(self, None))
        self.downloadButton.setContextMenuPolicy(Qt.CustomContextMenu)
        self.downloadButton.customContextMenuRequested.connect(self.rightClick)
        self.specs = Specs()
        self.extractor = Extractor()
        self.title = QLabel()
        self.image = QImage()
        self.thumbUrl = ""
        self.image_cont = QLabel()
        self.rightClicked = 0
        self.w = (30/100) * self.image_cont.width()
        self.h = (18/100) * self.image_cont.height()

        self.layout.addWidget(self.image_cont)
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.downloadButton)
        self.downloadButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setLayout(self.layout)
        self.PWidget = widget
        self.model = self.PWidget.model

    def set(self, title, image_url, id, c):
        """
        Set the title and thumbnail for the frame
        """
        if not exists(f"/tmp/.video{c}.jpg") or image_url != self.thumbUrl:
            # save the thumbnail if it doesn't exist
            request.urlretrieve(image_url, f"/tmp/.video{c}.jpg")
        self.image.load(f"/tmp/.video{c}.jpg")  # load the thumbnail
        self.thumbUrl = image_url
        self.image_cont.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.image_cont.setPixmap(QPixmap().fromImage(
            self.image).scaled(self.w, self.h, Qt.KeepAspectRatio))
        self.title.setText(title)  # Change the title of the box

        self.setFrameShape(QFrame.Box)
        self.setLineWidth(1)

        self.videoId = id

    def rightClick(self, point):
        # get the resolutions
        if not hasattr(self.extractor, 'qualityList'):
            ydl_opts = {
                'listformats': True,
                'logger': self.extractor
            }
            # download the info
            youtube_dl.YoutubeDL(ydl_opts).download(
                [f'https://www.youtube.com/watch?v={self.videoId}'])

        # dont add any more resolution options
        if self.rightClicked != 1:
            for quality in self.extractor.qualityList:
                self.specs.qualMenu.addAction(quality)
                self.specs.qualMenu.actions()[-1].setCheckable(True)
            self.rightClicked += 1

        # show context menu
        self.specs.exec_(self.downloadButton.mapToGlobal(point))


class Tabs(QTabWidget):
    def __init__(self, widget):
        super().__init__()

        # The tabs
        self.searchTab = QWidget()
        self.downloadTab = QWidget()

        # Widgets for the tabs in the window
        self.results = Results()
        self.downloadTable = QTableView()
        self.downloadLayout = QVBoxLayout()
        self.searchLayout = QVBoxLayout()
        self.pageCtrlLayout = QHBoxLayout()

        # Buttons which control the page of results
        self.nextButton = QPushButton("Next", clicked=widget.next)
        self.previousButton = QPushButton("Previous", clicked=widget.previous)
        self.pageCount = 0

        # Add the widgets to the different layouts
        self.pageCtrlLayout.addWidget(self.previousButton)
        self.pageCtrlLayout.addWidget(self.nextButton)
        self.downloadLayout.addWidget(self.downloadTable)
        self.searchLayout.addWidget(self.results)
        self.searchLayout.addLayout(self.pageCtrlLayout)
        # Set the model for the table for showing
        self.downloadTable.setModel(widget.model)

        # Set the layouts for the different tabs
        self.searchTab.setLayout(self.searchLayout)
        self.downloadTab.setLayout(self.downloadLayout)

        # Add the tabs to the window
        self.addTab(self.searchTab, "Results")
        self.addTab(self.downloadTab, "Downloads")


class Window(QWidget):
    """
    The main widget
    """

    def __init__(self):
        super().__init__()

        # Model (data) for the table to show
        self.data = pd.DataFrame([],
                                 columns=['Video Name',
                                          'File Name',
                                          'Percent',
                                          'ETA'])
        self.model = TableModel(self.data)

        # Widgets and layouts for the window
        self.tabs = Tabs(self)
        self.layout = QVBoxLayout()
        self.search_layout = QHBoxLayout()
        self.urlDownloadLayout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.orLabel = QLabel("OR")
        self.download = QPushButton(
            "Download", clicked=lambda: download(self, self.url_input.text()))
        self.search_term_input = QLineEdit()
        self.button = QPushButton("Search")

        # Make the layout for the "download from URL" area
        self.urlDownloadLayout.addWidget(self.url_input)
        self.urlDownloadLayout.addWidget(self.download)

        # Make the layout for the search area
        self.search_layout.addWidget(self.search_term_input)
        self.search_layout.addWidget(self.button)

        # Add the search area and the tabs
        self.layout.addLayout(self.urlDownloadLayout)
        self.layout.addWidget(self.orLabel)
        self.layout.addLayout(self.search_layout)
        self.layout.addWidget(self.tabs)

        self.setLayout(self.layout)  # set the layout for the window
        self.setProps()  # set the initial properties of a few widgets

    def search(self, i):
        """
        Show the results on the window
        """
        if i == 0:
            self.tabs.pageCount = 0

        terms = self.search_term_input.text()
        # Search with the terms given by the user
        results = YoutubeSearch(terms, max_results=100).to_dict()

        if not hasattr(self, "video_widgets"):
            self.video_widgets = list()
            for j in range(i, i+4):
                video = results[j]
                video_widget = Video(self)
                video_widget.set(video['title'], video['thumbnails'][0],
                                 video['id'], j)
                self.video_widgets.append(video_widget)
                self.tabs.results.layout.addWidget(video_widget)
            self.tabs.results.show()
            self.tabs.previousButton.show()
            self.tabs.nextButton.show()
            self.tabs.show()
        else:
            for j in range(i, i+4):
                video = results[j]
                widget = self.video_widgets[j - self.tabs.pageCount * 5]
                widget.set(video['title'], video['thumbnails'][0],
                           video['id'], j)

    def previous(self):
        if self.tabs.pageCount > 0:
            self.tabs.pageCount -= 1
            self.search(self.tabs.pageCount * 5)

    def next(self):
        if self.tabs.pageCount < 20:
            self.tabs.pageCount += 1
            self.search(self.tabs.pageCount * 5)

    def setProps(self):
        # Set the shortcut for the "Search" button
        self.button.setShortcut("Return")

        # Hide the widgets before the search
        self.tabs.hide()

        # Show a grayed out text when the input areas are empty
        self.url_input.setPlaceholderText("Youtube Video URL")
        self.search_term_input.setPlaceholderText("Search")

        # Stop the page controls from expanding freely
        self.tabs.previousButton.setSizePolicy(
            QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.tabs.nextButton.setSizePolicy(
            QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Make the program call the search function
        # when the "Search" button is clicked
        self.button.clicked.connect(lambda: self.search(0))

        self.setWindowTitle("Youtube Downloader")  # Set the window title

    def closeEvent(self, e):
        # remove the downloaded thumbnails
        system("rm /tmp/.video*.jpg")


def showProgress(download, row, signal):
    """
    Show the progress of the download to the user
    """
    if download['status'] == 'finished':
        print("Finished")
    elif download['status'] != "error":
        if not download['total_bytes'] is None:
            percent = int((download['downloaded_bytes'] / download['total_bytes']) * 100)
            signal.editSignal.emit("Percent", int(row), str(percent)+"%")
        if not download['eta'] is None:
            signal.editSignal.emit("ETA", int(row), download['eta'])


def download(widget, url):
    """
    Download the video with the user-specified options
    to the selected location
    """
    # If the video is being downloaded from an URL, then hide everything
    # in the "Results" tab
    # if it is not already shown
    if isinstance(widget, Window):
        if widget.tabs.isHidden():
            widget.tabs.show()
            widget.tabs.results.hide()
            widget.tabs.previousButton.hide()
            widget.tabs.nextButton.hide()

        # If the video is being downloaded from the search results,
        # then the following things must be done
    if isinstance(widget, Video):
        # Set the URL and the row assigned to the specific download
        url = f"https://www.youtube.com/watch?v={widget.videoId}"
        quality = ''
        widget.row = widget.model.rowCount(0)

        for i in widget.specs.qualMenu.actions():
            # if a specific quality is set, then extract it
            if i.isChecked():
                quality = i.text()

        widget.quality = 1080 if not quality else quality.split("p")[0]

        if widget.specs.actions()[-1].isChecked():
            # download only the audio as per the user
            widget.format = 'bestaudio'
        else:
            # download the video with audio
            widget.format = f'bestvideo[height<={widget.quality}]+bestaudio'

    # Set the variables to the default variables if the video is not being
    # downloaded from the search results
    # else set it to preset variables
    row = widget.model.rowCount(0) if not hasattr(
        widget, "row") else widget.row
    quality = 1080 if not hasattr(widget, "quality") else widget.quality

    # download the video with audio, by defualt
    # else download with the user-provided format
    format = f'bestvideo[height<={quality}]+bestaudio' if not hasattr(
        widget, "format") else widget.format

    # Get the filename for saving
    files = "Videos (*.mp4 *.mkv);;Audio (*.mp3)"
    defFileName = abspath('./output.mp4')
    head = "Set save location for the video/audio file"
    filename, ok = QFileDialog().getSaveFileName(widget,
                                                 head,
                                                 defFileName,
                                                 widget.tr(files))

    widget.signal = SignalManager()

    # set the options for the downloader
    ydl_opts = {
            'outtmpl': filename,
            'format': format,
            'progress_hooks': [lambda d: showProgress(d,
                                                      row,
                                                      widget.signal)],
            'quiet': True,
            'no_warnings': True
    }

    # Set the video title to "N/A" when downloaded straight from URL
    # as it cannot be retrieved,
    # else set it to the video name from the search result
    video_name = "N/A" if not hasattr(widget,
                                      "title") else widget.title.text()

    # download the video
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        if ok:
            # create the thread for the download
            widget.downloader = BGThread(ydl, url)
            widget.model.addRow()  # add a row to the table on "Downloads" tab

            # Set the data in the empty row
            widget.model.setData("Video Name",
                                 row,
                                 video_name)
            widget.model.setData("File Name",
                                 row,
                                 filename)
            widget.model.setData("Percent", row, 0)
            widget.model.setData("ETA", row, "N/A")

            # connect a function for cross-thread GUI changing
            widget.signal.editSignal.connect(widget.model.update_item)
            widget.downloader.start()  # Start the download


if __name__ == "__main__":
    app = QApplication(["Youtube Downloader"])

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
        sys.exit(app.exec_())
    except Exception:
        sys.exit(1)
