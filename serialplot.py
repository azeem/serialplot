from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
import pyqtgraph as pg

class SerialPlot(QtGui.QWidget):
    def __init__(self):
        super(SerialPlot, self).__init__()
        self.data = dict()
        self.plots = dict()
        self.makeGui()
        self.loadConfig("defaultconfig.py")
        self.runConfig()

    def makeConfigEditor(self):
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
        layout.addWidget(statusLabel, 3, 0, 1, 2)
        self.configStatusLabelWidget = statusLabel

        frame.setLayout(layout)
        return frame

    def makeDataEditor(self):
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
        layout.addWidget(recordButton, 1, 3)

        dataEditor = QtGui.QTextEdit()
        dataEditor.setReadOnly(True)
        layout.addWidget(dataEditor, 2, 0, 1, 4)
        self.dataEditorWidget = dataEditor

        frame.setLayout(layout)
        return frame

    def makeLowerPane(self):
        hSplitter = QtGui.QSplitter(Qt.Horizontal)
        hSplitter.addWidget(self.makeConfigEditor())
        hSplitter.addWidget(self.makeDataEditor())
        return hSplitter

    def makeGui(self):
        layout = QtGui.QHBoxLayout()
        vSplitter = QtGui.QSplitter(Qt.Vertical)
        plot = pg.PlotWidget()
        self.plotWidget = plot
        vSplitter.addWidget(plot)
        vSplitter.addWidget(self.makeLowerPane())
        layout.addWidget(vSplitter)
        self.setLayout(layout)

    def parseLine(self, line):
        line = line.strip()
        if (not (line.startswith("###") and line.endswith("###"))):
            return None
        line = line[3:-3]
        try:
            timestamp, label, value = [item.strip() for item in line.split(",")]
            timestamp = float(timestamp)
            value = float(value)
            return (timestamp, label, value)
        except ValueError:
            return None

    def clearData(self):
        self.data.clear()
        self.dataEditorWidget.clear()

    def loadData(self, filename):
        self.clearData()
        file = open(filename)
        for line in file:
            self.dataEditorWidget.insertPlainText(line)
            item = self.parseLine(line)
            if item is None:
                continue
            timestamp, label, value = item
            if label not in self.data:
                self.data[label] = ([],[])
            self.data[label][0].append(timestamp)
            self.data[label][1].append(value)
        file.close()
        self.dataEditorWidget.moveCursor(QtGui.QTextCursor.End)
        self.updatePlot()

    def clearPlots(self):
        for label, plot in self.plots.iteritems():
            self.plotWidget.removeItem(plot)
        self.plots.clear()

    def updatePlot(self):
        if len(self.plots) == 0:
            for label in self.plotLabels:
                if isinstance(label, tuple):
                    label, color = label
                    color = QtGui.QColor(color)
                    color = (color.red(), color.green(), color.blue())
                else:
                    color = (255,255,255)
                self.plots[label] = self.plotWidget.plot()
                self.plots[label].setPen(color)

        for label, plot in self.plots.iteritems():
            if label in self.data:
                plot.setData(x = self.data[label][0], y = self.data[label][1])
            else:
                plot.setData(x = [], y = [])

    def saveData(self, fname):
        with open(fname, "w") as outFile:
            outFile.write(str(self.dataEditorWidget.toPlainText()))

    def saveConfig(self, fname):
        with open(fname, "w") as outFile:
            outFile.write(str(self.configEditorWidget.toPlainText()))

    def loadConfig(self, fname):
        text = open(fname).read()
        self.configEditorWidget.setPlainText(text)

    def config(self, plotLabels = [], serialPort = "COM3", serialBaud=192500):
        if not isinstance(plotLabels, list):
            raise Exception("plotLabels should be a list")
        self.plotLabels = plotLabels
        self.serialPort = serialPort
        self.serialBaud = serialBaud

    def runConfig(self):
        code = str(self.configEditorWidget.toPlainText())
        print(repr(code))
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


if __name__ == "__main__":
    app = QtGui.QApplication([])
    serialPlot = SerialPlot()
    serialPlot.show()
    app.exec_()
