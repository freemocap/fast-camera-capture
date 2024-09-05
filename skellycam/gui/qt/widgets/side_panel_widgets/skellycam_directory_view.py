import logging
import os
from copy import copy
from pathlib import Path
from typing import Union

import PySide6
from PySide6 import QtGui
from PySide6.QtWidgets import QLabel, QMenu, QTreeView, QVBoxLayout, QWidget, QFileSystemModel

from skellycam.gui.gui_state import GUIState, get_gui_state

logger = logging.getLogger(__name__)


class SkellyCamDirectoryViewWidget(QWidget):
    def __init__(self, folder_path: str):
        super().__init__()
        self._minimum_width = 300
        self.setMinimumWidth(self._minimum_width)
        self._folder_path = folder_path

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._path_label = QLabel(str(self._folder_path))
        self._layout.addWidget(self._path_label)
        self._file_system_model = QFileSystemModel()
        self._tree_view_widget = QTreeView()

        self._layout.addWidget(self._tree_view_widget)

        # self._tree_view_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree_view_widget.customContextMenuRequested.connect(self._context_menu)
        self._tree_view_widget.doubleClicked.connect(self.open_file)

        self._tree_view_widget.setModel(self._file_system_model)
        self._file_system_model.sort(3,
                                     PySide6.QtCore.Qt.SortOrder.DescendingOrder)  # 3 is the column index for "Last Modified"

        self._tree_view_widget.setAlternatingRowColors(True)
        self._tree_view_widget.resizeColumnToContents(1)

        if self._folder_path is not None:
            self.set_folder_as_root(self._folder_path)

        self._gui_state: GUIState = get_gui_state()

    def update(self):
        super().update()
        if self._gui_state.recording_info:
            logger.loop(f"Updating: {self}")
            rec_path = Path(self._gui_state.recording_info.recording_folder)
            if self._folder_path != str(rec_path):
                self._folder_path = str(rec_path)
                videos_path = rec_path / "synchronized_videos"
                self.expand_directory_to_path(str(videos_path))

    def expand_directory_to_path(self, directory_path: Union[str, Path], collapse_other_directories: bool = True):
        if collapse_other_directories:
            logger.info("Collapsing other directories")
            self._tree_view_widget.collapseAll()
        og_index = self._file_system_model.index(str(directory_path))
        self._tree_view_widget.expand(og_index)

        parent_path = copy(directory_path)
        while Path(self._file_system_model.rootPath()) in Path(parent_path).parents:
            parent_path = Path(parent_path).parent
            index = self._file_system_model.index(str(parent_path))
            self._tree_view_widget.expand(index)

        self._tree_view_widget.scrollTo(og_index)

    def set_folder_as_root(self, folder_path: Union[str, Path]):
        self._tree_view_widget.setWindowTitle(str(folder_path))
        self._file_system_model.setRootPath(str(folder_path))
        self._tree_view_widget.setRootIndex(
            self._file_system_model.index(str(folder_path))
        )
        self._tree_view_widget.setColumnWidth(0, int(self._minimum_width * 0.9))

    def _context_menu(self):
        menu = QMenu()
        open = menu.addAction("Open file")
        open.triggered.connect(self.open_file)
        load_session = menu.addAction("Load session folder")
        load_session.triggered.connect(self.load_session_folder)

        cursor = QtGui.QCursor()
        menu.exec_(cursor.pos())

    def open_file(self):
        index = self._tree_view_widget.currentIndex()
        file_path = self._file_system_model.filePath(index)
        os.startfile(file_path)


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    skellycam_directory_view_widget = SkellyCamDirectoryViewWidget(folder_path=Path.home())
    skellycam_directory_view_widget.expand_directory_to_path(Path.home() / "Downloads")
    skellycam_directory_view_widget.show()
    sys.exit(app.exec())
