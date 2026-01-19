import maya.cmds as cmds
import maya.OpenMayaUI as omui
import maya.api.OpenMaya as om
from PySide6 import QtWidgets, QtCore, QtGui
from shiboken6 import wrapInstance

try:
    import adn.api.adnx as adnx
except ImportError:
    om.MGlobal.displayWarning("Could not import 'adnx'. Please ensure the library is in your scripts path.")


DEFAULT_LOCATORS = [
    {
        "name": "L_LegUpper_adnLocatorRotation_Thigh",
        "inputs": ["L_clavicle_ENV", "L_backLegUpperBendy00_ENV", "L_backLegMiddleBendy00_ENV"]
    },
    {
        "name": "L_LegMiddle_adnLocatorRotation_Knee",
        "inputs": ["L_backLegUpperBendy00_ENV", "L_backLegMiddleBendy00_ENV", "L_backLegLowerBendy00_ENV"]
    },
    {
        "name": "L_LegLower_adnLocatorRotation_Ankle",
        "inputs": ["L_backLegMiddleBendy00_ENV", "L_backLegLowerBendy00_ENV", "L_backLegLowerBendy05_ENV"]
    },
    {
        "name": "L_armUpper_adnLocatorRotation_Shoulder",
        "inputs": ["L_clavicle_ENV", "L_armUpperBendy00_ENV", "L_armUpperBendy04_ENV"]
    },
    {
        "name": "L_armMiddle_adnLocatorRotation_Elbow",
        "inputs": ["L_armUpperBendy00_ENV", "L_armLowerBendy00_ENV", "L_armLowerBendy05_ENV"]
    },
    {
        "name": "L_clavicle_frontDistance_adnLocatorDistance",
        "inputs": ["C_leftHeadDistance_JNT", "L_clavicle_ENV"]
    },
    {
        "name": "L_clavicle_backDistance_adnLocatorDistance",
        "inputs": ["L_clavicle_ENV", "C_spine00_ENV"]
    },
    {
        "name": "C_neck_backDistance_adnLocatorDistance",
        "inputs": ["C_neck00_ENV", "C_localChest_ENV"]
    },
    {
        "name": "C_neck_upperDistance_adnLocatorDistance",
        "inputs": ["C_centerUpHeadDistance_JNT", "C_neck00_ENV"]
    },
    {
        "name": "C_neck_frontDistance_adnLocatorDistance",
        "inputs": ["C_neck00_ENV", "C_leftHeadDistance_JNT"]
    }
]

def get_maya_window():
    """
    Get the main Maya window as a QWidget to properly parent the UI.
    """
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)

class LocatorsTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LocatorsTab, self).__init__(parent)
        self.create_widgets()
        self.create_layout()
        self.populate_table()
        self.create_connections()

    def create_widgets(self):
        self.lbl_info = QtWidgets.QLabel("Modify joint mappings below. Separate joints with commas.")
        self.lbl_info.setWordWrap(True)
        
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Locator Name", "Joint Inputs (Start, [Mid], End)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)

        self.btn_create = QtWidgets.QPushButton("Create All Locators")
        self.btn_create.setStyleSheet("background-color: #5D5; color: black; font-weight: bold; padding: 10px;")

    def create_layout(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.lbl_info)
        layout.addWidget(self.table)
        layout.addWidget(self.btn_create)

    def create_connections(self):
        self.btn_create.clicked.connect(self.build_locators)

    def populate_table(self):
        self.table.setRowCount(len(DEFAULT_LOCATORS))
        
        for i, item in enumerate(DEFAULT_LOCATORS):
            name_item = QtWidgets.QTableWidgetItem(item["name"])
            name_item.setFlags(name_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 0, name_item)
            
            inputs_str = ", ".join(item["inputs"])
            input_item = QtWidgets.QTableWidgetItem(inputs_str)
            self.table.setItem(i, 1, input_item)

    def build_locators(self):
        rig = adnx.AdnRig(host=adnx.AdnHost.kMaya)
        
        row_count = self.table.rowCount()
        built_count = 0

        for i in range(row_count):
            name = self.table.item(i, 0).text()
            inputs_text = self.table.item(i, 1).text()
            
            inputs = [x.strip() for x in inputs_text.split(",") if x.strip()]
            
            if "adnLocatorRotation" in name:
                self.build_rotation_locator(rig, name, inputs)
                built_count += 1
            elif "adnLocatorDistance" in name:
                self.build_distance_locator(rig, name, inputs)
                built_count += 1
            else:
                om.MGlobal.displayWarning(f"Unknown locator type for '{name}'. Must contain 'adnLocatorRotation' or 'adnLocatorDistance'.")

        om.MGlobal.displayInfo(f"--- AdonisFX: Built {built_count} Locators ---")

    def build_rotation_locator(self, rig, name, inputs):
        if len(inputs) != 3:
            om.MGlobal.displayWarning(f"Skipping {name}: Rotation locators require exactly 3 inputs (Start, Mid, End). Found {len(inputs)}.")
            return

        start, mid, end = inputs
        
        for jnt in inputs:
            if not cmds.objExists(jnt):
                om.MGlobal.displayWarning(f"Skipping {name}: Joint '{jnt}' does not exist in scene.")
                return

        sensor = adnx.AdnSensorRotation(rig)
        
        shape_name = name + "Shape"
        sensor.setName(shape_name)

        sensor_name = name.replace("adnLocatorRotation", "adnSensorRotation")
        sensor.setParameter("sensorName", sensor_name)

        sensor._data["node"] = shape_name 

        sensor.setParameter("sensorStart", start)
        sensor.setParameter("sensorMid", mid)
        sensor.setParameter("sensorEnd", end)
        
        try:
            sensor.build()
            om.MGlobal.displayInfo(f"Built Rotation Locator: {name} | Sensor: {sensor_name}")
        except Exception as e:
            om.MGlobal.displayError(f"Failed to build {name}: {e}")

    def build_distance_locator(self, rig, name, inputs):
        if len(inputs) != 2:
            om.MGlobal.displayWarning(f"Skipping {name}: Distance locators require exactly 2 inputs (Start, End). Found {len(inputs)}.")
            return

        start, end = inputs

        for jnt in inputs:
            if not cmds.objExists(jnt):
                om.MGlobal.displayWarning(f"Skipping {name}: Joint '{jnt}' does not exist in scene.")
                return

        sensor = adnx.AdnSensorDistance(rig)
        
        shape_name = name + "Shape"
        sensor.setName(shape_name)

        sensor_name = name.replace("adnLocatorDistance", "adnSensorDistance")
        sensor.setParameter("sensorName", sensor_name)

        sensor._data["node"] = shape_name 
        
        sensor.setParameter("sensorStart", start)
        sensor.setParameter("sensorEnd", end)
        
        try:
            sensor.build()
            om.MGlobal.displayInfo(f"Built Distance Locator: {name} | Sensor: {sensor_name}")
        except Exception as e:
            om.MGlobal.displayError(f"Failed to build {name}: {e}")


class MusclesTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(MusclesTab, self).__init__(parent)
        self.targets = []
        self.muscles = []
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.lw_targets = QtWidgets.QListWidget()
        self.lw_targets.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lw_muscles = QtWidgets.QListWidget()
        self.lw_muscles.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        self.btn_add_targets = QtWidgets.QPushButton("Add Selected as Targets (Skeleton)")
        self.btn_add_muscles = QtWidgets.QPushButton("Add Selected as Muscles")
        self.btn_clear = QtWidgets.QPushButton("Clear Lists")
        self.btn_build = QtWidgets.QPushButton("Configure Muscles")
        self.btn_build.setStyleSheet("background-color: #5D5; color: black; font-weight: bold; padding: 10px;")

        self.lbl_targets = QtWidgets.QLabel("Skeleton / Targets:")
        self.lbl_muscles = QtWidgets.QLabel("Muscles (Solvers):")

    def create_layout(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.lbl_targets)
        layout.addWidget(self.lw_targets)
        layout.addWidget(self.btn_add_targets)
        layout.addSpacing(10)
        layout.addWidget(self.lbl_muscles)
        layout.addWidget(self.lw_muscles)
        layout.addWidget(self.btn_add_muscles)
        layout.addSpacing(20)
        layout.addWidget(self.btn_clear)
        layout.addWidget(self.btn_build)

    def create_connections(self):
        self.btn_add_targets.clicked.connect(self.add_targets)
        self.btn_add_muscles.clicked.connect(self.add_muscles)
        self.btn_clear.clicked.connect(self.clear_lists)
        self.btn_build.clicked.connect(self.build_setup)

    def add_targets(self):
        sel = cmds.ls(sl=True)
        if sel:
            self.lw_targets.addItems(sel)
            self.targets.extend(sel)

    def add_muscles(self):
        sel = cmds.ls(sl=True)
        if sel:
            self.lw_muscles.addItems(sel)
            self.muscles.extend(sel)

    def clear_lists(self):
        self.lw_targets.clear()
        self.lw_muscles.clear()
        self.targets = []
        self.muscles = []

    def build_setup(self):
        if not self.muscles:
            om.MGlobal.displayWarning("No muscles selected.")
            return

        rig = adnx.AdnRig(host=adnx.AdnHost.kMaya)

        for muscle_geo in self.muscles:
            if not cmds.objExists(muscle_geo):
                continue

            muscle = adnx.AdnMuscle(rig)
            muscle_name = f"{muscle_geo}_adnMuscle"
            muscle.setName(muscle_name)
            muscle.setParameter("geometry", muscle_geo)
            muscle.setParameter("enable", True)

            muscle.setParameter("iterations", 3)
            muscle.setParameter("spaceScaleMode", 0) 
            
            muscle.setParameter("gravity", 9.8) 
            muscle.setParameter("pointMassMode", 0) 
            muscle.setParameter("globalMassMultiplier", 0.1)
            muscle.setParameter("triangulateMesh", True)
            muscle.setParameter("hardAttachments", False)
            muscle.setParameter("slidingConstraintsMode", 1) 
            muscle.setParameter("maxSlidingDistance", 1.0)

            if self.targets:
                for target in self.targets:
                    if not cmds.objExists(target):
                        continue
                    
                    if cmds.nodeType(target) == 'transform':
                        shapes = cmds.listRelatives(target, shapes=True)
                        if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                            muscle.addGeometryAttachment(target)
                        else:
                            muscle.addTransformAttachment(target)
                    elif cmds.nodeType(target) == 'joint':
                        muscle.addTransformAttachment(target)

            try:
                muscle.build()
                om.MGlobal.displayInfo(f"Built muscle: {muscle_name}")
            except Exception as e:
                om.MGlobal.displayError(f"Failed to build muscle {muscle_name}: {e}")
        
        cmds.select(clear=True)
        om.MGlobal.displayInfo("AdonisFX Muscle Setup Complete.")


class AdonisBuilderUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        if not parent:
            parent = get_maya_window()
        super(AdonisBuilderUI, self).__init__(parent)
        
        self.setWindowTitle("AdonisFX Automator")
        self.setWindowFlags(QtCore.Qt.Tool)
        self.resize(500, 600)
        
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        
        self.tab_locators = LocatorsTab()
        self.tab_muscles = MusclesTab()
        
        self.tabs.addTab(self.tab_locators, "Locators Creation")
        self.tabs.addTab(self.tab_muscles, "Muscle Configuration")
        
        self.main_layout.addWidget(self.tabs)

if __name__ == "__main__":
    try:
        ui.close()
        ui.deleteLater()
    except:
        pass
        
    ui = AdonisBuilderUI()
    ui.show()