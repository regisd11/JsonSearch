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
import re
from pyqtspinner.spinner import WaitingSpinner



class SearchWidget(qtw.QWidget):
    submitted = qtc.pyqtSignal(str, str)
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLayout(qtw.QFormLayout())
        self.term_input = qtw.QLineEdit()
        self.term_input.setToolTip('ids are without quote does not end with a space and are separated by semi-column')
        self.submit_button = qtw.QPushButton(
            'Submit',
            clicked=self.on_submit
        )
        self.cb = qtw.QComboBox()
        self.cb.addItem("Technical id")
        self.cb.addItem("Functional id")
        self.message = qtw.QLabel()
        self.extractMessage = qtw.QLabel()
        self.Spinner = WaitingSpinner(self.submit_button,True,True,qtc.Qt.ApplicationModal,
                roundness=70.0, opacity=15.0,
                fade=70.0, radius=3.0, lines=25,
                line_length=10.0, line_width=5.0,
                speed=1.0, color=(0, 0, 0))


        self.layout().addRow("Scope", self.cb)
        self.layout().addRow('Search', self.term_input)
        self.layout().addRow('', self.submit_button)
        self.layout().addRow('', self.message)
        self.layout().addRow('', self.extractMessage)



    def on_submit(self):
        term = self.term_input.text()
        scope = self.cb.currentText()
        if term != '':
            self.submitted.emit(term, scope)
        else:
            self.submitted.emit('error', scope)


    @qtc.pyqtSlot(int, int)
    def update_message(self, foundNb, totNb):
        self.message.setText(f'Contracts found : {foundNb}/{totNb}')

    @qtc.pyqtSlot(int, int)
    def update_extract(self, foundNb, totNb):
        self.extractMessage.setText(f'Contracts extracted : {foundNb}/{totNb}')

    @qtc.pyqtSlot(bool)
    def Toggle_spinner(self, toggle):
        if toggle is True:
            self.Spinner.start()
        else:
            self.Spinner.stop()


class Worker(qtc.QObject):
    searchedContracts = qtc.pyqtSignal(str)
    logMessage = qtc.pyqtSignal(int, int)
    logExtract = qtc.pyqtSignal(int, int)


    def wrapper_search(self, idList, scope, filename):
        idList = self.listify(idList)
        idList = list(set(idList))
        nbTot = len(idList)
        extractedNb = 0
        self.logExtract.emit(extractedNb, nbTot)
        if scope == 'Technical id':
            scopetec = 'id'
        else:
            scopetec = 'functionalId'
        idDict, extractDict = self.parse_json(filename, scopetec, idList)
        for key in idDict:
            if idDict[key] == -1:
                Contract = '{} not found'.format(key)
            else :
                Contract = extractDict[key]
                extractedNb = extractedNb + 1
                self.logExtract.emit(extractedNb, nbTot)
            Contract = json.dumps(Contract, sort_keys=True, indent=4)
            Contract = Contract + '\n' 
            yield (Contract)


    def listify(self, term):
        if term.find(';') != -1:
            spliting = term.split(';')
        else:
            spliting = [str(term)]
        return(spliting)


    def parse_json(self, filename, field, fieldvalue):
        not_exist_flag = -1
        Position_dict = dict.fromkeys(fieldvalue,not_exist_flag)
        Contract_dict = dict.fromkeys(fieldvalue,not_exist_flag)
        totNb = len(fieldvalue)
        foundNb = 0
        self.logMessage.emit(foundNb, totNb)
        with open(filename, 'rb') as input_file:
            parser = ijson.kvitems(input_file, 'item')
            count = 0
            contratids = (v for k, v in parser if k == field)
            count=0
            for contractid in contratids:
                count = count + 1
                if contractid in Position_dict:
                    Position_dict[contractid] = count
                    contractextract = self.search_contract(filename,Position_dict[contractid])
                    Contract_dict[contractid] = contractextract
                    foundNb = foundNb + 1
                    self.logMessage.emit(foundNb, totNb)
                if -1 not in Position_dict.values():
                    break
            return(Position_dict, Contract_dict)


    def search_contract(self, filename, count):
        with open(filename, 'rb') as input_file:
            Contracts = ijson.items(input_file, 'item')
            if count != -1:
                Contracts = itertools.islice(Contracts, count -1, count)
                Contracts = list(Contracts)
                extract = Contracts[0]
                return(extract)
            else:
                pass


    @qtc.pyqtSlot(str, str, str)
    def worker_search(self, idList, scope, filename):
        returnedSearch = self.wrapper_search(idList, scope, filename)
        for c in returnedSearch: 
            self.searchedContracts.emit(c)

class MainWindow(qtw.QMainWindow):

    search_requested = qtc.pyqtSignal(str, str, str)
    toggle_spinner = qtc.pyqtSignal(bool)

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
        self.worker.logMessage.connect(search_widget.update_message)
        self.worker.logExtract.connect(search_widget.update_extract)
        self.toggle_spinner.connect(search_widget.Toggle_spinner)


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
        elif re.match('^((.*)([^ ];))+((.[^ ]*)([^ ;]))$|((.[^ ]*)([^ ;]))$', term):
            self.search(term, scope, filename)
            self.textedit.clear()
            self.toggle_spinner.emit(True)
        else:
            self.toaster.show_toast("invalid search", "the search entered does not match pattern", threaded=True, 
                    icon_path='SINEWAVE.ICO', duration=0)


    def search(self, term, scope, filename):
        self.statusBar().showMessage(f'Searching in {filename}')
        self.search_requested.emit(term, scope, filename)


    def display_search(self, text):
        self.textedit.append(text)
        self.toaster.show_toast("Updated", "Your search has been updated with a contract", threaded=True,
                   icon_path='resources/atom.jpg', duration=0)
        self.statusBar().showMessage('updated')
        self.toggle_spinner.emit(False)



if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    window = MainWindow()
    qtmodern.styles.light(app)
    mw = qtmodern.windows.ModernWindow(window)
    mw.show()
    sys.exit(app.exec())