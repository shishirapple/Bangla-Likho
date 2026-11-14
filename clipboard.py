# -*- coding: utf-8 -*-
"""Thread-safe clipboard access through Qt (owned by this process: no helper processes, no races)."""
import threading

from PySide6 import QtCore, QtGui


class Clip(QtCore.QObject):
    _req_set = QtCore.Signal(str)
    _req_get = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._ev = threading.Event()
        self._val = None
        self._req_set.connect(self._do_set, QtCore.Qt.QueuedConnection)
        self._req_get.connect(self._do_get, QtCore.Qt.QueuedConnection)

    @QtCore.Slot(str)
    def _do_set(self, t):
        QtGui.QGuiApplication.clipboard().setText(t)
        self._ev.set()

    @QtCore.Slot()
    def _do_get(self):
        self._val = QtGui.QGuiApplication.clipboard().text()
        self._ev.set()

    def _in_main(self):
        return QtCore.QThread.currentThread() == self.thread()

    def set_text(self, t, timeout=0.5):
        if self._in_main():
            return self._do_set(t)
        self._ev.clear()
        self._req_set.emit(t)
        self._ev.wait(timeout)

    def get_text(self, timeout=0.5):
        if self._in_main():
            self._do_get()
            return self._val
        self._ev.clear()
        self._val = None
        self._req_get.emit()
        self._ev.wait(timeout)
        return self._val
