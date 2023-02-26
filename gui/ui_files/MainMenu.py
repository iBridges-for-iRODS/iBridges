"""Created by: PyQt6 UI code generator from the corresponding UI file

WARNING: Any manual changes made to this file will be lost when pyuic6 is
run again.  Do not edit this file unless you know what you are doing.
"""


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1300, 850)
        MainWindow.setMinimumSize(QtCore.QSize(1300, 850))
        MainWindow.setStyleSheet("QWidget\n"
"{\n"
"    color: rgb(86, 184, 139);\n"
"    background-color: rgb(54, 54, 54);\n"
"    selection-background-color: rgb(58, 152, 112);\n"
"}\n"
"\n"
"QLabel#globalErrorLabel\n"
"{\n"
"    color: rgb(217, 174, 23);\n"
"}\n"
"\n"
"QTabBar::tab:top:selected {\n"
"    background-color: rgb(58, 152, 112);\n"
"    color: rgb(54, 54, 54);\n"
"}\n"
"")
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setStyleSheet("")
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setMinimumSize(QtCore.QSize(600, 300))
        self.tabWidget.setObjectName("tabWidget")
        self.verticalLayout.addWidget(self.tabWidget)
        self.globalErrorLabel = QtWidgets.QLabel(self.centralwidget)
        self.globalErrorLabel.setStyleSheet("")
        self.globalErrorLabel.setText("")
        self.globalErrorLabel.setObjectName("globalErrorLabel")
        self.verticalLayout.addWidget(self.globalErrorLabel)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1300, 26))
        self.menubar.setObjectName("menubar")
        self.menuMenu = QtWidgets.QMenu(self.menubar)
        font = QtGui.QFont()
        font.setPointSize(13)
        font.setBold(False)
        font.setWeight(50)
        self.menuMenu.setFont(font)
        self.menuMenu.setObjectName("menuMenu")
        self.menuOptions = QtWidgets.QMenu(self.menubar)
        font = QtGui.QFont()
        font.setPointSize(13)
        self.menuOptions.setFont(font)
        self.menuOptions.setObjectName("menuOptions")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionCloseSession = QtGui.QAction(MainWindow)
        font = QtGui.QFont()
        self.actionCloseSession.setFont(font)
        self.actionCloseSession.setObjectName("actionCloseSession")
        self.actionExit = QtGui.QAction(MainWindow)
        font = QtGui.QFont()
        self.actionExit.setFont(font)
        self.actionExit.setObjectName("actionExit")
        self.actionSearch = QtGui.QAction(MainWindow)
        font = QtGui.QFont()
        self.actionSearch.setFont(font)
        self.actionSearch.setObjectName("actionSearch")
        self.actionSaveConfig = QtGui.QAction(MainWindow)
        font = QtGui.QFont()
        self.actionSaveConfig.setFont(font)
        self.actionSaveConfig.setObjectName("actionSaveConfig")
        self.menuMenu.addAction(self.actionCloseSession)
        self.menuMenu.addAction(self.actionExit)
        self.menuOptions.addAction(self.actionSearch)
        self.menuOptions.addAction(self.actionSaveConfig)
        self.menubar.addAction(self.menuMenu.menuAction())
        self.menubar.addAction(self.menuOptions.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(-1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.menuMenu.setTitle(_translate("MainWindow", "Menu"))
        self.menuOptions.setTitle(_translate("MainWindow", "Options"))
        self.actionCloseSession.setText(_translate("MainWindow", "Close Session"))
        self.actionExit.setText(_translate("MainWindow", "Exit"))
        self.actionSearch.setText(_translate("MainWindow", "Search"))
        self.actionSaveConfig.setText(_translate("MainWindow", "Save configuration"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
