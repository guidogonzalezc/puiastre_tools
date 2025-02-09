try:
    # Qt5
    from PySide2 import QtCore, QtWidgets, QtGui
    from shiboken2 import wrapInstance
except:
    # Qt6
    from PySide6 import QtCore, QtWidgets, QtGui
    from shiboken6 import wrapInstance

import sys
import maya.OpenMayaUI as omui
import maya.cmds as cmds
import maya.api.OpenMaya as om

def maya_main_window():
    """Returns Maya's main window as a QWidget."""
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


class CorrectiveSetup(QtWidgets.QDialog):
    def __init__(self, parent=maya_main_window()):
        super().__init__(parent)

        self.setWindowTitle("Corrective Joint Tool - 0.1")
        self.setMinimumSize(400, 200)

        # Styling
        self.setStyleSheet("background-color: #564b42;")  # Main background

        # Create UI Elements
        self.create_widgets() 
        self.create_layout()
        self.create_connections()

    def add_selected_mesh(self):
        """Add the selected mesh to the mesh field."""
        selection = cmds.ls(selection=True)
        if not selection:
            om.MGlobal.displayWarning("No mesh selected, please select a mesh.")
            return
        
        self.mesh_field_text.setText(selection[0])

    def add_controller(self):
        """Add the selected controller to the output tree."""
        selection = cmds.ls(selection=True)

        if not selection:
            om.MGlobal.displayWarning("No controller selected, please select a controller.")
            return

        if not any(cmds.nodeType(sel) == "nurbsCurve" or cmds.nodeType(cmds.listRelatives(sel, shapes=True)[0]) == "nurbsCurve" for sel in selection) or not any("_CTL" in sel for sel in selection):
            om.MGlobal.displayWarning("Selected object must be a nurbsCurve or its transform and contain '_CTL' in the name.")
            return
        
        self.outputs_tree.clear()
        self.outputs_tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(selection))

    def get_selected_joint(self):
        """Get the selected joint."""
        selection = cmds.ls(selection=True, type="joint")
        if not selection:
            return
        return selection[0]

    def check_pairblend_node(self, joint):
        """Check if a pairBlend node exists on the joint."""
        pairblend = cmds.listConnections(f"{joint}.rotateX", type="pairBlend")
        if pairblend:
            return pairblend[0]
        
    def create_push_joint(self, joint):
        """Create a push joint."""
        sel_joint = self.get_selected_joint()
        check_pairblend = self.check_pairblend_node(sel_joint)
        print(check_pairblend)
    

    def create_widgets(self):
        """Create all UI elements."""
        
        # Transfer Buttons
        self.selecetd_mesh = QtWidgets.QPushButton("Selected Mesh ->")
        self.mesh_field_text = QtWidgets.QLineEdit()
        self.control = QtWidgets.QPushButton("Select Controller")
        self.push_joint_btn= QtWidgets.QPushButton("Create Push Joint")
        self.mesh_field_text.setStyleSheet("background-color: #a68e74; color: white; border-radius: 5px; padding: 5px;")
        self.mesh_field_text.setPlaceholderText("Enter mesh name...")

        # Outputs (Left Side)
        self.outputs_tree = QtWidgets.QTreeWidget()
        self.outputs_tree.setHeaderLabel("Selected controller")
        self.outputs_tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)


        # Inputs (Right Side)
        self.inputs_tree = QtWidgets.QTreeWidget()
        self.inputs_tree.setHeaderLabel("Constraint joints")
        self.inputs_tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        tree_style = """
            QTreeWidget {
            background-color: #a68e74;
            color: white;
            border-radius: 5px;
            padding: 0px;
            }
            QTreeWidget::item {
            text-align: center;
            }
            QTreeWidget::item:selected {
            background-color: #8e7761;
            }
            QTreeWidget::item:!selected {
            color: #d3d3d3;
            }
            QHeaderView::section {
            background-color: #a68e74;
            color: white;
            text-align: center;
            }
        """
        for tree in [self.outputs_tree, self.inputs_tree]:
            tree.setStyleSheet(tree_style)

        # Apply Styles
        button_style = """
            QPushButton {
            background-color: #a68e74;
            color: white;
            border-radius: 5px;
            padding: 5px;
            }
            QPushButton:hover {
            background-color: #8e7761;
            }
            QPushButton:pressed {
            background-color: #755e4a;
            }
        """

        for btn in [self.selecetd_mesh, self.control, self.push_joint_btn]:
            btn.setStyleSheet(button_style)

    def create_layout(self):
        """Set up layouts for widgets."""
        
        # Transfer Buttons Container
        self.transfer_container = QtWidgets.QWidget()
        self.transfer_container.setStyleSheet("background-color: #725e50; border-radius: 5px;")

        transfer_layout = QtWidgets.QVBoxLayout(self.transfer_container)
        horizontal_layout = QtWidgets.QHBoxLayout()
        temp_vertical_layout = QtWidgets.QHBoxLayout()
        transfer_layout.setSpacing(5)
        transfer_layout.setContentsMargins(10, 10, 10, 10)
        horizontal_layout.addWidget(self.selecetd_mesh)
        horizontal_layout.addWidget(self.mesh_field_text)
        transfer_layout.addLayout(horizontal_layout)
        temp_vertical_layout.addWidget(self.outputs_tree)
        temp_vertical_layout.addWidget(self.inputs_tree)
        transfer_layout.addLayout(temp_vertical_layout)
        transfer_layout.addWidget(self.control)
        transfer_layout.addWidget(self.push_joint_btn)


        # OK/Cancel Button Layout
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()


        # Main Layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.transfer_container)
        main_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def create_connections(self):
        """Connect buttons to their functions (currently empty)."""
        self.selecetd_mesh.clicked.connect(self.add_selected_mesh)
        self.control.clicked.connect(self.add_controller)

    def keyPressEvent(self, event):
        """Capture any unhandled key presses so they do not pass to Maya."""
        pass

if __name__ == "__main__":
    try:
        win.close()
        win.deleteLater()
    except:
        pass

    win = CorrectiveSetup()
    win.show()
