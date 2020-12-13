import pandas as pd

from PySide6.QtCore import (QObject, QThread, Signal, Qt, Slot,
                            QAbstractTableModel)


class SignalManager(QObject):
    editSignal = Signal(str, int, object)


class BGThread(QThread):
    """
    Thread for running the download in background
    so that the GUI doesn't freeze.
    """

    def __init__(self, ydl, url, parent=None):
        super().__init__(parent=parent)
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
                                                'ETA']),
                                       ignore_index=True)
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
