import ijson.backends.yajl2_c as ijson
import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg
from PyQt5 import QtCore as qtc
import itertools
import simplejson as json
import qtmodern.styles
import qtmodern.windows
from win10toast import ToastNotifier


def wrapper_search(idList, scope, filename):
    idList = listify(idList)
    if scope == 'Technical id':
        scopetec = 'item.id'
    else:
        scopetec = 'item.functionalId'
    Contracts = []
    idDict = parse_json(filename, scopetec, idList)
    if len(idDict) == 0:
        return('No contract found')
    else:
        for key in idDict:
            Contracts = Contracts + search_contract(filename, idDict[key])
        Contracts = json.dumps(Contracts, sort_keys=True, indent=4)
        return (Contracts)


def listify(term):
    spliting = term.split(';')
    return(spliting)


def parse_json(filename, fieldpath, fieldvalue):
    print(fieldvalue)
    Position_dict = {}
    with open(filename, 'rb') as input_file:
        parser = ijson.parse(input_file)
        count = 0
        try:
            while len(Position_dict) < len(fieldvalue):
                prefix, event, value = next(parser)
                print('prefix={}, event={}, value={}'.format(prefix, event, value))
                if prefix == 'item.id':
                    count = count+1
                    if type(value) is str:
                        cid = int(value)
                    else:
                        cid = value
                if prefix == fieldpath and value in fieldvalue:
                    Position_dict[cid] = count
        except StopIteration:
            pass
        return(Position_dict)


def search_contract(filename, count):
    with open(filename, 'rb') as input_file:
        Contracts = ijson.items(input_file, 'item')
        if count != -1:
            Contracts = itertools.islice(Contracts, count -1, count)
            Contracts = list(Contracts)
            return(Contracts)
        else:
            pass


class SearchWidget(qtw.QWidget):
    submitted = qtc.pyqtSignal(str, str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLayout(qtw.QFormLayout())
        self.term_input = qtw.QLineEdit()
        self.submit_button = qtw.QPushButton(
            'Submit',
            clicked=self.on_submit
        )
        self.cb = qtw.QComboBox()
        self.cb.addItem("Technical id")
        self.cb.addItem("Functional id")

        self.layout().addRow("Scope", self.cb)
        self.layout().addRow('Search', self.term_input)
        self.layout().addRow('', self.submit_button)

    def on_submit(self):
        term = self.term_input.text()
        scope = self.cb.currentText()
        if term != '':
            self.submitted.emit(term, scope)
        else:
            self.submitted.emit('error', scope)



class Worker(qtc.QObject):
    searchedContracts = qtc.pyqtSignal(str)

    @qtc.pyqtSlot(str, str, str)
    def worker_search(self, idList, scope, filename):
        returnedSearch = wrapper_search(idList, scope, filename)
        self.searchedContracts.emit(returnedSearch)

class MainWindow(qtw.QMainWindow):

    search_requested = qtc.pyqtSignal(str, str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Json Search')

        self.main_widget = qtw.QWidget(self)
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        l = qtw.QVBoxLayout(self.main_widget)
        x = qtw.QHBoxLayout()
        self.textedit = qtw.QTextEdit()
        self.file_name = qtw.QLabel('file Selected: ')
        self.file_name_display = qtw.QLabel()
        x.setAlignment(qtc.Qt.AlignLeft)
        x.addWidget(self.file_name)
        x.addWidget(self.file_name_display)
        l.addLayout(x)
        l.addWidget(self.textedit)


        menu = self.menuBar()
        file_menu = menu.addMenu('File')
        save_act = file_menu.addAction(
            'Save',
            self.save
        )
        save_act.setShortcut(qtg.QKeySequence.Save)
        open_act = file_menu.addAction(
            'Open',
            self.open
        )
        open_act.setShortcut(qtg.QKeySequence.Open)
        file_menu.addSeparator()
        file_menu.addAction(
            'Quit', 
            self.close, 
            qtg.QKeySequence.Quit
        )



        self.statusBar().showMessage('Welcome', 5000)

        search_dock = qtw.QDockWidget('Search')
        self.addDockWidget(
            qtc.Qt.LeftDockWidgetArea,
            search_dock
        )
        search_dock.setFeatures(
            qtw.QDockWidget.DockWidgetMovable |
            qtw.QDockWidget.DockWidgetFloatable
        )
        search_widget = SearchWidget()
        search_dock.setWidget(search_widget)
        search_widget.submitted.connect(self.checkSearch)
        
        self.toaster = ToastNotifier()
        self.worker = Worker()
        self.worker_thread = qtc.QThread()
        self.worker.searchedContracts.connect(self.display_search)
        self.search_requested.connect(self.worker.worker_search)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()


    def save(self):
        text = self.textedit.toPlainText()
        filename, _ = qtw.QFileDialog.getSaveFileName()
        if filename:
            with open(filename, 'w') as handle:
                handle.write(text)
                self.statusBar().showMessage(f'Saved to {filename}')


    def open(self):
        myfile, _ = qtw.QFileDialog.getOpenFileName(None, 'Window Name', '', 'JSON files (*.json)')
        self.file_name_display.setText(myfile)


    def checkSearch(self, term, scope):
        filename = self.file_name_display.text()
        if term == 'error' and filename == '':
            self.toaster.show_toast("No Search nor File", "You must define a list of contract to search and a source file (file/open)", threaded=True,
                   icon_path='SINEWAVE.ICO', duration=0)
        elif term == 'error':
            self.toaster.show_toast("No Search", "You must define a list of contract to search", threaded=True,
                   icon_path='SINEWAVE.ICO', duration=0)
        elif filename == '':
            self.toaster.show_toast("No File", "You must define a JSON source file (file/open)", threaded=True,
                   icon_path='SINEWAVE.ICO', duration=0)
        else:
            self.search(term, scope, filename)


    def search(self, term, scope, filename):
        self.statusBar().showMessage(f'Searching in {filename}')
        self.search_requested.emit(term, scope, filename)


    def display_search(self, text):
        self.textedit.clear()
        self.textedit.insertPlainText(text)
        self.textedit.moveCursor(qtg.QTextCursor.Start)
        self.toaster.show_toast("Finished", "Your search has completed", threaded=True,
                   icon_path='SINEWAVE.ICO', duration=0)
        self.statusBar().showMessage('Search completed')


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    window = MainWindow()
    qtmodern.styles.light(app)
    mw = qtmodern.windows.ModernWindow(window)
    mw.show()
    sys.exit(app.exec())