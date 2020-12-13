def showProgress(download, row, signal):
    """
    Show the progress of the download to the user
    """
    if download['status'] == 'finished':
        print("Finished")
    elif download['status'] != "error":
        if not download['total_bytes'] is None:
            percent = int(
                (download['downloaded_bytes'] / download['total_bytes']) * 100)
            signal.editSignal.emit("Percent", int(row), str(percent)+"%")
        if not download['eta'] is None:
            signal.editSignal.emit("ETA", int(row), download['eta'])
