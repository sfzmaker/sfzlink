from PySide6.QtCore             import QSettings, Qt, QEvent, QDir, QModelIndex
from PySide6.QtGui              import QIcon, QCursor, QAction, QHoverEvent, QKeySequence, QBrush, QColor
from PySide6.QtWidgets          import QMainWindow, QFileDialog, QMessageBox, QApplication, QButtonGroup, QMenu, QDialog, QFileSystemModel, QTreeView, QTableWidgetItem
from .ui_mainwindow             import Ui_MainWindow
from pathlib                    import Path

import os

def get_relative_path(file_path, _preset_path):
  # calculate the dots for relative path
  preset_path = os.path.join(*os.path.dirname(_preset_path).split(os.sep))
  if os.sep == "/":
    preset_path = f"/{preset_path}"
  #print(file_path)
  #print(preset_path)
  common_path = os.path.commonprefix([file_path, preset_path])
  #print(common_path)
  if preset_path.split(os.sep) == file_path.split(os.sep)[:len(preset_path.split(os.sep))]: # if the preset can go straight to the sample without ../
    return os.path.join(*file_path.split(os.sep)[len(preset_path.split(os.sep)):])
  else:
    dots = (len(os.path.normpath(preset_path).split(os.sep)) - (len(os.path.normpath(common_path).split(os.sep)) - 1))
    r = ""
    for i in range(dots):
        r += f"../"
    define_userpath = r[:-1]
    file_path_ls = os.path.normpath(file_path).split(os.sep)
    common_path_ls = os.path.normpath(common_path).split(os.sep)

    #print(file_path_ls)
    #print(os.path.normpath(preset_path).split(os.sep))
    #print(common_path_ls)

    #if common_path_ls[-1] == "":
    rest_path = os.path.join(*file_path_ls[len(common_path_ls)-1:])
    #else:
    #  rest_path = os.path.join(*file_path_ls[len(common_path_ls):])
    #print(rest_path)
    return f"{define_userpath}/{rest_path}"

class MainWindow(QMainWindow):
  def __init__(self, app, parent=None):
    super().__init__(parent)
    self._window = parent

    self.ui = Ui_MainWindow()
    self.ui.setupUi(self)
    self.setAcceptDrops(True)

    self.settings = QSettings(self, QSettings.IniFormat, QSettings.UserScope, QApplication.organizationName, QApplication.applicationDisplayName)
    self.settings.setValue("last_file_path", None)
    self.settings.setValue("last_filename", None)

    self.template = ""

    self.model = QFileSystemModel()
    if self.settings.value("root_folder") is None:
      self.model.setRootPath(__file__)
    self.model.setNameFilters(("*.sfz", "*.SFZ"))
    self.model.setNameFilterDisables(False)

    self.ui.treeSfz.setModel(self.model)
    if self.settings.value("root_folder") is not None:
      self.model.setRootPath(__file__)
      self.model.setNameFilters(("*.sfz", "*.SFZ"))
      self.ui.treeSfz.setCurrentIndex(self.model.index(self.settings.value("root_folder")))
    
    self.templates_ls = os.listdir(f"{os.path.dirname(__file__)}/templates")
    self.ui.cbxTemplate.addItems(self.templates_ls)
    self.ui.cbxTemplate.setCurrentIndex(self.templates_ls.index("SFZ.template"))

    # MENUS
    self.save_menu = QMenu(self)
    self.save_current_sfz = self.save_menu.addAction("Save SFZ In New Location")

    # SIGNALS
    self.ui.treeSfz.selectionModel().selectionChanged.connect(self.onSelectedFile)
    self.ui.treeSfz.doubleClicked.connect(self.onAddSfz)
    self.ui.pbnSave.clicked.connect(self.onAddSfz)
    self.save_current_sfz.triggered.connect(self.onSaveSfz)

  def mousePressEvent(self, QMouseEvent):
    if QMouseEvent.button() == Qt.RightButton:
      self.save_menu.exec(QCursor.pos())
  
  def onSelectedFile(self):
    if self.model.isDir(self.ui.treeSfz.currentIndex()):
      self.settings.setValue("root_folder", self.model.filePath(self.ui.treeSfz.currentIndex()))
  
  def onAddSfz(self):
    if not self.model.isDir(self.ui.treeSfz.currentIndex()):
      if self.settings.value("last_file_path") is None:
        sfzsource = self.model.filePath(self.ui.treeSfz.currentIndex())
        sfzpath = QFileDialog.getSaveFileName(parent=self, caption="Save SFZ Link", dir=self.settings.value("root_folder"), filter="SFZ(*.sfz)")
        if sfzpath[0] != "":
          with open(f"{os.path.dirname(__file__)}/templates/{self.ui.cbxTemplate.currentText()}", 'r') as file:
            self.template = file.read()
          if self.ui.chkInclude.isChecked():
            with open(sfzsource, 'r') as file:
              content = file.read()
          else:
            content = None
          self.save_sfz(sfzsource, os.path.dirname(sfzpath[0]), sfzpath[0].split(os.sep)[-1], self.template, content)
          self.settings.setValue('last_file_path', f"{os.path.dirname(sfzpath[0])}"); #print(f"{os.path.dirname(sfzpath[0])}")
          self.settings.setValue("last_filename", sfzpath[0].split(os.sep)[-1]); #print(sfzpath[0].split(os.sep)[-1])
          self.ui.lblSfz.setText(f"{self.settings.value("last_file_path")}/{self.settings.value("last_filename")}")
      else:
        sfzsource = self.model.filePath(self.ui.treeSfz.currentIndex())
        sfzpath = self.settings.value("last_file_path")
        sfzname = self.settings.value("last_filename")
        with open(f"{os.path.dirname(__file__)}/templates/{self.ui.cbxTemplate.currentText()}", 'r') as file:
          self.template = file.read()
        if self.ui.chkInclude.isChecked():
          with open(sfzsource, 'r') as file:
            content = file.read()
        else:
          content = None
        self.save_sfz(sfzsource, sfzpath, sfzname, self.template, content)

  def onSaveSfz(self):
    if not self.model.isDir(self.ui.treeSfz.currentIndex()):
      sfzsource = self.model.filePath(self.ui.treeSfz.currentIndex())
      sfzpath = QFileDialog.getSaveFileName(parent=self, caption="Save SFZ Link", dir=self.settings.value("last_file_path"), filter="SFZ(*.sfz)")
      if sfzpath[0] != "":
        if self.ui.chkInclude.isChecked():
          with open(sfzsource, 'r') as file:
            content = file.read()
        else:
          content = None
        self.save_sfz(sfzsource, os.path.dirname(sfzpath[0]), sfzpath[0].split(os.sep)[-1], self.template, content)
        self.settings.setValue('last_file_path', f"{os.path.dirname(sfzpath[0])}"); #print(f"{os.path.dirname(sfzpath[0])}")
        self.settings.setValue("last_filename", sfzpath[0].split(os.sep)[-1]); #print(sfzpath[0].split(os.sep)[-1])

  def save_sfz(self, source, path, name, template, content):
    sfz_content = f"{template}\n"
    sfz_content += f"{self.ui.txtOpcodes.toPlainText()}\n"
    sfz_content += f"<control>\n"
    sfz_content += f"default_path={os.path.dirname(get_relative_path(source, f"{path}/{name}"))}/\n"
    if content is not None:
      sfz_content += content
    else:
      sfz_content += f"#include \"{get_relative_path(source, f"{path}/{name}")}\"\n"
    filename = name.split(".")[0]
    # write sfz
    #print(path, filename)
    f_sfz = open(os.path.normpath(f"{path}/{filename}.sfz"), "w", encoding="utf8")
    f_sfz.write(sfz_content)
    f_sfz.close()

    
    #self.ui.lblLog.setText(f"""WRITTEN: {os.path.normpath(str(path) + ".sfz")}""")

