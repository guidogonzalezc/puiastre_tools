import maya.cmds as cmds
import maya.OpenMayaUI as omui 
import maya.api.OpenMaya as om
from PySide6 import QtWidgets, QtCore, QtGui
from shiboken6 import wrapInstance

try:
    import adn.api.adnx as adnx
except ImportError:
    cmds.warning("Could not import 'adnx'. Please ensure the library is in your scripts path.")

def get_maya_window():
    """
    Get the main Maya window as a QWidget to properly parent the UI.
    """
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)

class AdonisMuscleBuilderUI(QtWidgets.QDialog):
    """
    A Production-ready UI for batch building AdonisFX Muscles.
    """
    
    def __init__(self, parent=None):
        if not parent:
            parent = get_maya_window()
            
        super(AdonisMuscleBuilderUI, self).__init__(parent)
        
        self.setWindowTitle("AdonisFX Muscle Automator :)")
        self.setWindowFlags(QtCore.Qt.Tool) 
        self.resize(400, 500)
        
        self.targets = []
        self.muscles = []
        
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        
    def create_widgets(self):
        # Lists
        self.lw_targets = QtWidgets.QListWidget()
        self.lw_targets.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lw_muscles = QtWidgets.QListWidget()
        self.lw_muscles.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        # Buttons
        self.btn_add_targets = QtWidgets.QPushButton("Add Selected as Targets (Skeleton)")
        self.btn_add_muscles = QtWidgets.QPushButton("Add Selected as Muscles")
        self.btn_clear = QtWidgets.QPushButton("Clear All")
        self.btn_build = QtWidgets.QPushButton("Build Muscles")
        self.btn_build.setStyleSheet("background-color: #5D5; color: black; font-weight: bold;")

        # Labels
        self.lbl_targets = QtWidgets.QLabel("Skeleton / Targets:")
        self.lbl_muscles = QtWidgets.QLabel("Muscles (Solvers):")

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # Target Section
        main_layout.addWidget(self.lbl_targets)
        main_layout.addWidget(self.lw_targets)
        main_layout.addWidget(self.btn_add_targets)
        
        main_layout.addSpacing(10)
        
        # Muscle Section
        main_layout.addWidget(self.lbl_muscles)
        main_layout.addWidget(self.lw_muscles)
        main_layout.addWidget(self.btn_add_muscles)
        
        main_layout.addSpacing(20)
        
        # Footer
        main_layout.addWidget(self.btn_clear)
        main_layout.addWidget(self.btn_build)

    def create_connections(self):
        self.btn_add_targets.clicked.connect(self.add_targets)
        self.btn_add_muscles.clicked.connect(self.add_muscles)
        self.btn_clear.clicked.connect(self.clear_lists)
        self.btn_build.clicked.connect(self.build_setup)

    def add_targets(self):
        sel = cmds.ls(sl=True)
        if not sel:
            return
        self.lw_targets.addItems(sel)
        self.targets.extend(sel)

    def add_muscles(self):
        sel = cmds.ls(sl=True)
        if not sel:
            return
        self.lw_muscles.addItems(sel)
        self.muscles.extend(sel)

    def clear_lists(self):
        self.lw_targets.clear()
        self.lw_muscles.clear()
        self.targets = []
        self.muscles = []

    def build_setup(self):
        """
        Core logic using adnx to build the muscles.
        """
        if not self.muscles:
            cmds.warning("No muscles selected.")
            return

        # Initialize the Rig container
        rig = adnx.AdnRig(host=adnx.AdnHost.kMaya)

        for muscle_geo in self.muscles:
            # Check if geometry exists
            if not cmds.objExists(muscle_geo):
                om.MGlobal.displayWarning(f"Skipping {muscle_geo}, object does not exist.")
                continue

            #  Create the Muscle Object
            muscle = adnx.AdnMuscle(rig)
            
            muscle_name = f"{muscle_geo}_adnMuscle"
            muscle.setName(muscle_name)
            muscle.setParameter("geometry", muscle_geo)
            muscle.setParameter("enable", True)

            # Values to modify with defaults
            muscle.setParameter("iterations", 3)
            muscle.setParameter("spaceScaleMode", 0) 

            muscle.setParameter("gravity", 9.8) 
            muscle.setParameter("pointMassMode", 0) 
            muscle.setParameter("globalMassMultiplier", 0.1)
            muscle.setParameter("triangulateMesh", True)
            muscle.setParameter("hardAttachments", False)
            muscle.setParameter("slidingConstraintsMode", 1) 
            muscle.setParameter("maxSlidingDistance", 1.0)

            # Add Targets (Skeleton)
            if self.targets:
                for target in self.targets:
                    if not cmds.objExists(target):
                        continue
                    
                    if cmds.nodeType(target) == 'transform':
                        shapes = cmds.listRelatives(target, shapes=True)
                        if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                            muscle.addGeometryAttachment(target)
                            om.MGlobal.displayInfo(f"[{muscle_geo}] Added Geometry Attachment: {target}")
                        else:
                            muscle.addTransformAttachment(target)
                            om.MGlobal.displayInfo(f"[{muscle_geo}] Added Transform Attachment: {target}")
                    elif cmds.nodeType(target) == 'joint':
                        muscle.addTransformAttachment(target)
                        om.MGlobal.displayInfo(f"[{muscle_geo}] Added Transform Attachment: {target}")

            try:
                muscle.build()
                om.MGlobal.displayInfo(f"Successfully built muscle: {muscle_name}")
            except Exception as e:
                om.MGlobal.displayError(f"Failed to build muscle {muscle_name}: {e}")

        cmds.select(clear=True)
        om.MGlobal.displayInfo("AdonisFX Muscle Setup Complete.")

# Launch the UI
if __name__ == "__main__":
    try:
        ui.close()
        ui.deleteLater()
    except:
        pass
        
    ui = AdonisMuscleBuilderUI()
    ui.show()