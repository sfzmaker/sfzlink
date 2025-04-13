from PySide6.QtCore             import QSettings, Qt, QEvent, QDir, QModelIndex
from PySide6.QtGui              import QIcon, QCursor, QAction, QHoverEvent, QKeySequence, QBrush, QColor
from PySide6.QtWidgets          import QMainWindow, QFileDialog, QMessageBox, QApplication, QButtonGroup, QMenu, QDialog, QFileSystemModel, QTreeView, QTableWidgetItem
from .ui_mainwindow             import Ui_MainWindow
from pathlib                    import Path

from subprocess import Popen, PIPE, call, run
from subprocess import check_output
from platform import system

#from .utils.multiplatform_opener import subprocess_opener
import os
import re

OSNAME = system().lower()

formats = (".wav", ".aif", ".aiff", ".flac", ".ogg")
patterns = (r"sample=(.*?\.wav)", r"sample=(.*?\.aif)", r"sample=(.*?\.aiff)", r"sample=(.*?\.flac)", r"sample=(.*?\.ogg)")

def replace_substrings_safe(text, replacements):
    """
    Yeah this thing is by chatGPT because this kind of feature is AWFUL to write, it saved my day
    Replaces substrings in a string without interfering with previous replacements.
    
    :param text: Original string.
    :param replacements: List of tuples (search, replace).
    :return: Modified string.
    """
    placeholder = "{{}}"  # Placeholder to avoid recursive replacements
    temp_text = text
    changes = {}
    
    # First pass: Mark positions without modifying original words
    for search, replace in replacements:
        pos = temp_text.find(search)
        if pos != -1:
            #print(f"Substring '{search}' found at position {pos}")
            changes[pos] = (search, replace)
    
    # Sort positions to replace from left to right
    sorted_changes = sorted(changes.items())
    offset = 0
    
    for pos, (search, replace) in sorted_changes:
        real_pos = pos + offset  # Adjust for previous insertions
        temp_text = temp_text[:real_pos] + replace + temp_text[real_pos+len(search):]
        offset += len(replace) - len(search)
    
    return temp_text

def insert_path(default_path, _sfz):
    
    sfz = _sfz.replace(chr(92), "/") # stupid backslashes!!!

    for p in patterns:
        samples = re.findall(p, sfz)
        if len(samples) != 0:
            break

    #default_paths = re.findall(r"default_path=([^\n]*)", sfz, flags=re.MULTILINE)
      
    #includes = re.findall(r'#include\s+"([^"]+)"', sfz)

    #inls = []
    #dels = []
    smls = []
    #for i in includes:
    #    inls.append((i, f"{default_path}{i}"))
    #for i in default_paths:
    #    dels.append((i, f"{default_path}{i}"))
    
    for i in samples:
        smls.append((i, f"{default_path}{i}"))
    
    r1 = replace_substrings_safe(sfz, smls)
    #r2 = replace_substrings_safe(r1, dels)

    #print(r2)
    return r1

def get_open_command(filepath):
  if 'windows' in OSNAME:
      opener = 'start'
  elif 'osx' in OSNAME or 'darwin' in OSNAME:
      opener = 'open'
  else:
      opener = 'xdg-open'
  return [opener, filepath]

def get_relative_path(file_path, _preset_path):
  # calculate the dots for relative path
  preset_path = os.path.join(*os.path.dirname(_preset_path).split(os.sep))
  if os.sep == "/":
    preset_path = f"/{preset_path}"
  common_path = os.path.commonprefix([file_path, preset_path])
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

    rest_path = os.path.join(*file_path_ls[len(common_path_ls)-1:])
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
    self.lastsfz = None
    self.sfz_ls = []

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
    self.save_current_sfz = self.save_menu.addAction("Save SFZ In New Location"); self.save_current_sfz.setEnabled(False)
    self.add_sfz_item = self.save_menu.addAction("Add SFZ item"); self.add_sfz_item.setEnabled(False)
    self.delete_sfz_item = self.save_menu.addAction("Remove SFZ item"); self.delete_sfz_item.setEnabled(False)
    self.save_sfz_result = self.save_menu.addAction("Save SFZ Result"); self.delete_sfz_item.setEnabled(False)

    # SIGNALS
    self.ui.treeSfz.selectionModel().selectionChanged.connect(self.onSelectedFile)
    self.ui.treeSfz.doubleClicked.connect(self.onAddSfz)
    self.ui.pbnOpen.clicked.connect(self.onOpen)
    self.save_current_sfz.triggered.connect(self.onSaveSfz)
    self.ui.cbxTemplate.currentIndexChanged.connect(self.onAddSfz)
    self.delete_sfz_item.triggered.connect(self.onDeleteItem)
    self.add_sfz_item.triggered.connect(self.onAddItem)
    self.save_sfz_result.triggered.connect(self.onSaveSfzResult)
    #self.ui.chkInclude.stateChanged.connect(self.onInclude)
  
  def onInclude(self):
    if self.ui.chkInclude.isChecked():
      self.ui.chkInsert.setDisabled(False)
    else:
      self.ui.chkInsert.setDisabled(True)

  def mousePressEvent(self, QMouseEvent):
    if QMouseEvent.button() == Qt.RightButton:
      self.save_menu.exec(QCursor.pos())
  
  def onSelectedFile(self):
    if self.model.isDir(self.ui.treeSfz.currentIndex()):
      self.settings.setValue("root_folder", self.model.filePath(self.ui.treeSfz.currentIndex()))
  
  def onDeleteItem(self):
    if self.ui.listSfz.count() != 1:
      item_idx = self.ui.listSfz.currentRow()
      del self.sfz_ls[item_idx]; self.ui.listSfz.clear(); self.ui.listSfz.addItems(self.sfz_ls); self.ui.listSfz.setCurrentRow(item_idx-1) # update
      sfzpath = self.settings.value("last_file_path")
      sfzname = self.settings.value("last_filename")
      with open(f"{os.path.dirname(__file__)}/templates/{self.ui.cbxTemplate.currentText()}", 'r') as file:
        self.template = file.read()
      self.save_sfz(self.sfz_ls, sfzpath, sfzname, self.template, False)
  
  def onAddItem(self):
    if not self.model.isDir(self.ui.treeSfz.currentIndex()):
      self.lastsfz = self.model.filePath(self.ui.treeSfz.currentIndex())
      item_idx = self.ui.listSfz.currentRow()
      self.sfz_ls.append(self.lastsfz); self.ui.listSfz.clear(); self.ui.listSfz.addItems(self.sfz_ls); self.ui.listSfz.setCurrentRow(item_idx+1)# update
      sfzpath = self.settings.value("last_file_path")
      sfzname = self.settings.value("last_filename")
      with open(f"{os.path.dirname(__file__)}/templates/{self.ui.cbxTemplate.currentText()}", 'r') as file:
        self.template = file.read()
      self.save_sfz(self.sfz_ls, sfzpath, sfzname, self.template, False)

  def onAddSfz(self):
    if not self.model.isDir(self.ui.treeSfz.currentIndex()):
      if self.settings.value("last_file_path") is None:
        self.lastsfz = self.model.filePath(self.ui.treeSfz.currentIndex())
        sfzpath = QFileDialog.getSaveFileName(parent=self, caption="Save SFZ Link", dir=self.settings.value("root_folder"), filter="SFZ(*.sfz)")
        if sfzpath[0] != "":
          with open(f"{os.path.dirname(__file__)}/templates/{self.ui.cbxTemplate.currentText()}", 'r') as file:
            self.template = file.read()
          self.sfz_ls.append(self.lastsfz)
          self.save_sfz(self.sfz_ls, os.path.dirname(sfzpath[0]), sfzpath[0].split(os.sep)[-1], self.template, False)
          self.settings.setValue('last_file_path', f"{os.path.dirname(sfzpath[0])}"); #print(f"{os.path.dirname(sfzpath[0])}")
          self.settings.setValue("last_filename", sfzpath[0].split(os.sep)[-1]); #print(sfzpath[0].split(os.sep)[-1])
          self.ui.lblSfz.setText(f"{self.settings.value("last_file_path")}/{self.settings.value("last_filename")}")
          self.save_current_sfz.setEnabled(True)
          self.add_sfz_item.setEnabled(True)
          self.delete_sfz_item.setEnabled(True)
          self.save_sfz_result.setEnabled(True)
          self.ui.listSfz.addItems(self.sfz_ls); self.ui.listSfz.setCurrentRow(0)
      else:
        item_idx = self.ui.listSfz.currentRow()
        self.lastsfz = self.model.filePath(self.ui.treeSfz.currentIndex())
        self.sfz_ls[self.ui.listSfz.currentRow()] = self.lastsfz; self.ui.listSfz.clear(); self.ui.listSfz.addItems(self.sfz_ls); self.ui.listSfz.setCurrentRow(item_idx) # update
        sfzpath = self.settings.value("last_file_path")
        sfzname = self.settings.value("last_filename")
        with open(f"{os.path.dirname(__file__)}/templates/{self.ui.cbxTemplate.currentText()}", 'r') as file:
          self.template = file.read()
        self.save_sfz(self.sfz_ls, sfzpath, sfzname, self.template, False)

  def onOpen(self):
    if not self.model.isDir(self.ui.treeSfz.currentIndex()):
      print(get_open_command(self.model.filePath(self.ui.treeSfz.currentIndex())))
      subproc = run(
          get_open_command(self.model.filePath(self.ui.treeSfz.currentIndex()))
      )

  def onSaveSfz(self):
    if not self.model.isDir(self.ui.treeSfz.currentIndex()):
      self.lastsfz = self.model.filePath(self.ui.treeSfz.currentIndex())
      item_idx = self.ui.listSfz.currentIndex()
      self.sfz_ls[self.ui.listSfz.currentRow()] = self.lastsfz; self.ui.listSfz.clear(); self.ui.listSfz.addItems(self.sfz_ls); self.ui.listSfz.setCurrentIndex(item_idx) # update
      sfzpath = QFileDialog.getSaveFileName(parent=self, caption="Save SFZ Link", dir=self.settings.value("last_file_path"), filter="SFZ(*.sfz)")
      if sfzpath[0] != "":
        self.save_sfz(self.sfz_ls, os.path.dirname(sfzpath[0]), sfzpath[0].split(os.sep)[-1], self.template, False)
        self.settings.setValue('last_file_path', f"{os.path.dirname(sfzpath[0])}"); #print(f"{os.path.dirname(sfzpath[0])}")
        self.settings.setValue("last_filename", sfzpath[0].split(os.sep)[-1]); #print(sfzpath[0].split(os.sep)[-1])
  
  def onSaveSfzResult(self):
    if self.model.isDir(self.ui.treeSfz.currentIndex()):
      sfzpath = self.model.filePath(self.ui.treeSfz.currentIndex())
      self.save_sfz(self.sfz_ls, sfzpath, f"{self.sfz_ls[0].split(os.sep)[-1].split(".")[0]} M0D.sfz", "", True)

  def save_sfz(self, sources, path, name, template, add_path):
    sfz_content = f"{template}\n"
    sfz_content += f"{self.ui.txtOpcodes.toPlainText()}\n"
    for source in sources:
      if add_path is False:
        # copy/paste instead of #include
        if self.ui.chkInclude.isChecked():
          with open(source, 'r') as file:
            content = file.read()
        #  print((self.ui.chkInsert.isEnabled(), self.ui.chkInsert.isChecked()))
        #  if all((self.ui.chkInsert.isEnabled(), self.ui.chkInsert.isChecked())):
        #    print(os.path.dirname(get_relative_path(source, f"{path}/{name}")))
        #    content = insert_path(f"{os.path.dirname(get_relative_path(source, f"{path}/{name}"))}/", content)
        else:
          content = None
        
        sfz_content += f"<control>\n"
        sfz_content += f"default_path={os.path.dirname(get_relative_path(source, f"{path}/{name}"))}/\n"
        if content is not None:
          sfz_content += content
        else:
          sfz_content += f"#include \"{get_relative_path(source, f"{path}/{name}")}\"\n"
      else:
        with open(source, 'r') as file:
          content = file.read()
        
        sfz_content += insert_path(f"{os.path.dirname(get_relative_path(source, f"{path}/{name}"))}/", content)

    filename = name.split(".")[0]
    # write sfz
    #print(path, filename)
    f_sfz = open(os.path.normpath(f"{path}/{filename}.sfz"), "w", encoding="utf8")
    f_sfz.write(sfz_content)
    f_sfz.close()

    
    #self.ui.lblLog.setText(f"""WRITTEN: {os.path.normpath(str(path) + ".sfz")}""")

