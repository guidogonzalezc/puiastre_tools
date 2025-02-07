try:
    # Qt5
    from PySide2 import QtCore
    from PySide2 import QtWidgets
    from shiboken2 import wrapInstance
except:
    # Qt6
    from PySide6 import QtCore
    from PySide6 import QtWidgets
    from shiboken6 import wrapInstance
    
import sys
import maya.OpenMayaUI as omui
    
    
def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
             
class ToolDialog(QtWidgets.QDialog):
    
    def __init__(self, parent=maya_main_window()):
        super().__init__(parent)
        
        self.setWindowTitle("Common Widgets")
        self.setMinimumSize(400, 200)
                    
        self.create_widgets()
        self.create_layout()
        self.create_connections()
            
    def create_widgets(self):
        
        self.ok_btn = QtWidgets.QPushButton("OK")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        
    def create_layout(self):
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(btn_layout)
        
    def create_connections(self):
        pass
        
    def keyPressEvent(self, event):
        # Capture any unhandled key presses so they
        # are not passed to Maya's main window
        pass
        
        
if __name__ == "__main__":
    try:
        win.close()        # pylint: disable=E0601
        win.deleteLater()
    except:
        pass
        
    win = ToolDialog()
    win.show()
    
    
    
    
    
    
    
    