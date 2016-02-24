from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
import pyqtgraph as pg
from serial import Serial, SerialException

class SerialWorker(QtCore.QObject):
    """
        Serial Worker that reads lines from the serial port
    """
    readline = QtCore.pyqtSignal(str)

    def __init__(self):
        super(SerialWorker, self).__init__()
        self.active = True
        self.serial = None
        self.sendNewLine = True

    def openSerial(self, port, baudRate, timeout, sendNewLine=True):
        """ Opens the serial port """
        if self.serial is not None:
            raise Exception("Cannot read multiple serial")
        self.serial = Serial(port = port, baudrate = baudRate, timeout = timeout)
        self.sendNewLine = sendNewLine

    def closeSerial(self):
        """ Closes the serial port """
        if self.serial is not None:
            self.serial.close()
        self.serial = None

    def workerStart(self):
        """ Runs in a loop reading from the serial port """
        while(self.active):
            if self.serial is not None:
                try:
                    if self.sendNewLine:
                        self.serial.write(b"\n")
                        self.serial.flush()
                    line = self.serial.readline()
                except Exception as e:
                    print("Error Reading Serial Port")
                self.readline[str].emit(line)
            else:
                QtCore.QThread.msleep(500)

    def workerStop(self):
        self.closeSerial()

class SerialPlot(QtGui.QWidget):
    """ Serial Plot Window """
    def __init__(self):
        super(SerialPlot, self).__init__()
        self.isRecording = False
        self.data = dict()
        self.plots = dict()
        self.makeGui()
        self.loadConfig("defaultconfig.py")
        self.runConfig()
        self.makeThreads()

    def closeEvent(self, event):
        """ Overridden from QWidget to handle thread cleanups """
        self.serialWorker.active = False
        self.serialWorker.closeSerial()
        self.serialThread.quit()
        self.serialThread.wait()

    def makeThreads(self):
        """ Setup the serial reader thread and worker """
        thread = QtCore.QThread()
        worker = SerialWorker()
        worker.moveToThread(thread)
        thread.started.connect(worker.workerStart)
        thread.finished.connect(worker.workerStop)
        worker.readline.connect(self.addDataLine)
        self.serialThread = thread
        self.serialWorker = worker
        thread.start()

    def makeConfigEditor(self):
        """ Build the config editor pane """
        frame = QtGui.QFrame()
        frame.setFrameShape(QtGui.QFrame.NoFrame)
        layout = QtGui.QGridLayout()
        frame.setContentsMargins(0,0,0,0)
        layout.setContentsMargins(0,0,0,0)

        label = QtGui.QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setText("Config")
        layout.addWidget(label, 0, 0, 1, 2)

        loadButton = QtGui.QPushButton("Load")
        loadButton.clicked.connect(self.handleConfigLoadClick)
        layout.addWidget(loadButton, 1, 0)
        saveButton = QtGui.QPushButton("Save")
        saveButton.clicked.connect(self.handleConfigSaveClick)
        layout.addWidget(saveButton, 1, 1)

        editorTimer = QtCore.QTimer()
        editorTimer.setInterval(1000)
        editorTimer.setSingleShot(True)
        def editorThrottle():
            if editorTimer.isActive():
                editorTimer.stop()
            editorTimer.start()
        editorTimer.timeout.connect(self.handleConfigEditorChange)

        configEditor = QtGui.QTextEdit()
        configEditor.textChanged.connect(editorThrottle)
        layout.addWidget(configEditor, 2, 0, 1, 2)
        self.configEditorWidget = configEditor

        statusLabel = QtGui.QLabel()
        statusLabel.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Preferred))
        layout.addWidget(statusLabel, 3, 0, 1, 2)
        self.configStatusLabelWidget = statusLabel

        frame.setLayout(layout)
        return frame

    def makeDataEditor(self):
        """ Builds the Data editor pane """
        frame = QtGui.QFrame()
        frame.setFrameShape(QtGui.QFrame.NoFrame)
        layout = QtGui.QGridLayout()
        frame.setContentsMargins(0,0,0,0)
        layout.setContentsMargins(0,0,0,0)

        label = QtGui.QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setText("Data")
        layout.addWidget(label, 0, 0, 1, 4)

        clearButton = QtGui.QPushButton("Clear")
        clearButton.clicked.connect(self.handleDataClearClick)
        layout.addWidget(clearButton, 1, 0)
        loadButton = QtGui.QPushButton("Load")
        loadButton.clicked.connect(self.handleDataLoadClick)
        layout.addWidget(loadButton, 1, 1)
        saveButton = QtGui.QPushButton("Save")
        saveButton.clicked.connect(self.handleDataSaveClick)
        layout.addWidget(saveButton, 1, 2)
        recordButton = QtGui.QPushButton("Record")
        recordButton.clicked.connect(self.handleDataRecordClick)
        layout.addWidget(recordButton, 1, 3)
        self.dataRecordButtonWidget = recordButton

        dataEditor = QtGui.QTextEdit()
        dataEditor.setReadOnly(True)
        layout.addWidget(dataEditor, 2, 0, 1, 4)
        self.dataEditorWidget = dataEditor

        statusLabel = QtGui.QLabel()
        statusLabel.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Preferred))
        layout.addWidget(statusLabel, 3, 0, 1, 4)
        self.dataStatusLabelWidget = statusLabel

        frame.setLayout(layout)
        return frame

    def makeLowerPane(self):
        """ Builds the lower Pane """
        hSplitter = QtGui.QSplitter(Qt.Horizontal)
        hSplitter.addWidget(self.makeConfigEditor())
        hSplitter.addWidget(self.makeDataEditor())
        return hSplitter

    def makeGui(self):
        """ Builds the User Interface """
        layout = QtGui.QHBoxLayout()
        vSplitter = QtGui.QSplitter(Qt.Vertical)
        plot = pg.PlotWidget()
        self.plotWidget = plot
        vSplitter.addWidget(plot)
        vSplitter.addWidget(self.makeLowerPane())
        layout.addWidget(vSplitter)
        self.setLayout(layout)

    def defParseLine(self, line):
        """ Default line parsing implementation """
        line = line.strip()
        if (not (line.startswith("###") and line.endswith("###"))):
            return None
        try:
            line = line[3:-3]
            checkSum, line = [item for item in line.split("#")]
            checkSum = int(checkSum)
            for char in line:
                checkSum = checkSum ^ ord(char)
            if checkSum != 0:
                return
            timestamp, label, value = [item.strip() for item in line.split(",")]
            timestamp = float(timestamp)
            value = float(value)
            return (timestamp, label, value)
        except ValueError:
            return None

    def clearData(self):
        """ Clears the plot and the data """
        self.data.clear()
        self.dataEditorWidget.clear()

    def addDataLine(self, line):
        """ Adds a line of data and updates the plot """
        self.dataEditorWidget.insertPlainText(line)
        self.dataEditorWidget.moveCursor(QtGui.QTextCursor.End)
        try:
            item = self.parseLine(str(line))
        except UnicodeEncodeError as e:
            return
        if item is None:
            return
        if self.processLine:
            item = self.processLine(item[0], item[1], item[2])
        timestamp, label, value = item
        if label not in self.data:
            self.data[label] = ([],[])
        self.data[label][0].append(timestamp)
        self.data[label][1].append(value)
        self.updatePlot()

    def loadData(self, filename):
        """ Loads data from a file and updates the plot """
        self.clearData()
        file = open(filename)
        for line in file:
            self.addDataLine(line)
        file.close()
        self.updatePlot()

    def clearPlots(self):
        """ Clears the plots """
        for label, plot in self.plots.iteritems():
            self.plotWidget.removeItem(plot)
        self.plots.clear()

    def updatePlot(self):
        """ Updates the plots. Called when the data has changed. """
        if len(self.plots) == 0:
            for label in self.plotLabels:
                if isinstance(label, tuple):
                    label, color = label
                    color = QtGui.QColor(color)
                    color = (color.red(), color.green(), color.blue())
                else:
                    color = (255,255,255)
                self.plots[label] = self.plotWidget.plot()
                self.plots[label].setClipToView(False)
                self.plots[label].setPen(color)

        for label, plot in self.plots.iteritems():
            if label in self.data:
                plot.setData(x = self.data[label][0], y = self.data[label][1])
            else:
                plot.setData(x = [], y = [])

    def saveData(self, fname):
        """ Save the data to a file """
        with open(fname, "w") as outFile:
            outFile.write(str(self.dataEditorWidget.toPlainText()))

    def saveConfig(self, fname):
        """ Save the config to a file """
        with open(fname, "w") as outFile:
            outFile.write(str(self.configEditorWidget.toPlainText()))

    def loadConfig(self, fname):
        """ Loads a config file. This does not run it immediately. """
        text = open(fname).read()
        self.configEditorWidget.setPlainText(text)

    def config(self, plotLabels = [], parseLine=None, processLine=None, serialPort = "COM3", serialBaudRate=115200, serialTimeout=5, sendNewLine=True):
        """ Configures the app. Called from config scripts. """
        if not isinstance(plotLabels, list):
            raise Exception("plotLabels should be a list")
        self.parseLine = self.defParseLine if parseLine is None else parseLine
        self.plotLabels = plotLabels
        self.serialPort = serialPort
        self.serialBaudRate = serialBaudRate
        self.serialTimeout = serialTimeout
        self.processLine = processLine
        self.sendNewLine = sendNewLine

    def runConfig(self):
        """ Runs the config script currently in the editor """
        code = str(self.configEditorWidget.toPlainText())
        configGlobals = {}
        configLocals = {"config": self.config}
        try:
            exec(code, configGlobals, configLocals)
            self.configStatusLabelWidget.setText("Config OK!")
            self.configStatusLabelWidget.setStyleSheet("QLabel {color: green}")
        except Exception as e:
            self.configStatusLabelWidget.setText(str(e))
            self.configStatusLabelWidget.setStyleSheet("QLabel {color: red}")

    # event handlers

    def handleDataLoadClick(self):
        fname = QtGui.QFileDialog.getOpenFileName(caption="Load Data")
        if len(fname) == 0:
            return
        self.loadData(fname)

    def handleDataClearClick(self):
        self.clearData()
        self.updatePlot()

    def handleDataSaveClick(self):
        fname = QtGui.QFileDialog.getSaveFileName(caption="Save Data")
        if len(fname) == 0:
            return
        self.saveData(fname)

    def handleConfigLoadClick(self):
        fname = QtGui.QFileDialog.getOpenFileName(caption="Load Config")
        if len(fname) == 0:
            return
        self.loadConfig(fname)

    def handleConfigSaveClick(self):
        fname = QtGui.QFileDialog.getSaveFileName(caption="Save Data")
        if len(fname) == 0:
            return
        self.saveConfig(fname)

    def handleConfigEditorChange(self):
        self.runConfig()
        self.clearPlots()
        self.updatePlot()

    def handleDataRecordClick(self):
        self.isRecording = not self.isRecording
        if self.isRecording:
            try:
                self.serialWorker.openSerial(
                    port=self.serialPort,
                    baudRate=self.serialBaudRate,
                    timeout=self.serialTimeout,
                    sendNewLine=self.sendNewLine
                )
                self.dataRecordButtonWidget.setText("Stop")
                self.dataStatusLabelWidget.setStyleSheet("QLabel {color: green}")
                self.dataStatusLabelWidget.setText("Serial Connected!")
            except SerialException as e:
                self.dataStatusLabelWidget.setStyleSheet("QLabel {color: red}")
                self.dataStatusLabelWidget.setText(str(e))
        else:
            self.serialWorker.closeSerial()
            self.dataRecordButtonWidget.setText("Record")

if __name__ == "__main__":
    app = QtGui.QApplication([])
    serialPlot = SerialPlot()
    serialPlot.show()
    app.exec_()
