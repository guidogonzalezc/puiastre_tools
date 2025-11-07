import os
import maya.cmds as cmds
from maya.api import OpenMaya as om
import json

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)).split("\scripts")[0]

class DataManager:
    """
    A class to manage and store data related to controls, guides, meshes, and asset names
    across different modules in the rigging system.
    """
    # initialize class-level storage attributes to avoid AttributeError when getters are called
    _project_path = None
    _ctls_data = None
    _guide_data = None
    _mesh_data = None
    _asset_name = None
    _skinning_data = None

    @classmethod
    def set_project_path(cls, path):
        cls._project_path = path
        store_data()
    
    @classmethod
    def get_project_path(cls):
        return cls._project_path

    @classmethod
    def set_ctls_data(cls, data):
        cls._ctls_data = data
        store_data()

    @classmethod
    def get_ctls_data(cls):
        return cls._ctls_data

    @classmethod
    def set_guide_data(cls, data):
        cls._guide_data = data
        store_data()

    @classmethod
    def get_guide_data(cls):
        return cls._guide_data
    
    @classmethod
    def set_mesh_data(cls, data):
        cls._mesh_data = data
        store_data()

    @classmethod
    def get_mesh_data(cls):
        return cls._mesh_data
    
    @classmethod
    def set_asset_name(cls, data):
        cls._asset_name = data
        store_data()

    @classmethod
    def get_asset_name(cls):
        return cls._asset_name
    
    @classmethod
    def set_skinning_data(cls, data):
        cls._skinning_data = data
        store_data()
    
    @classmethod
    def get_skinning_data(cls):
        return cls._skinning_data
    
    @classmethod
    def clear_data(cls):
        cls._ctls_data = None
        cls._guide_data = None
        cls._mesh_data = None
        cls._asset_name = None

def store_data():
    """
    Store the current data from the DataManager into a JSON file.
    """
    data = {
        "project_path": DataManager.get_project_path(),
        "ctls_data": DataManager.get_ctls_data(),
        "guide_data": DataManager.get_guide_data(),
        "mesh_data": DataManager.get_mesh_data(),
        "asset_name": DataManager.get_asset_name(),
        "skinning_data": DataManager.get_skinning_data()
    }
    file_path = os.path.join(SCRIPT_PATH, "build", "old_data.json")
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)
    om.MGlobal.displayInfo(f"Data stored at: {file_path}")

def load_data():
    """
    Load data from the JSON file into the DataManager.
    """
    file_path = os.path.join(SCRIPT_PATH, "build", "old_data.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            DataManager.set_project_path(data.get("project_path"))
            DataManager.set_ctls_data(data.get("ctls_data"))
            DataManager.set_guide_data(data.get("guide_data"))
            DataManager.set_mesh_data(data.get("mesh_data"))
            DataManager.set_asset_name(data.get("asset_name"))
            DataManager.set_skinning_data(data.get("skinning_data"))
        om.MGlobal.displayInfo(f"Data loaded from: {file_path}")
    else:
        om.MGlobal.displayWarning(f"No data file found at: {file_path}")

def pv_locator(name, parents =[], parent_append = None):
    curve = cmds.curve(d=1, p=[(0, 0, 0), (0, 1, 0)], k=[0, 1], name=name+"_CTL")
    cmds.delete(curve, ch=True)
    for i, p in enumerate(parents):
        decompose = cmds.createNode("decomposeMatrix", name=f"{name}0{i}_DCP", ss=True)
        cmds.connectAttr(f"{p}.worldMatrix[0]", f"{decompose}.inputMatrix")
        cmds.connectAttr(f"{decompose}.outputTranslate", f"{curve}.controlPoints[{i}]")
    if parent_append:
        cmds.parent(curve, parent_append)

    cmds.setAttr(f"{curve}.overrideEnabled", 1)
    cmds.setAttr(f"{curve}.overrideDisplayType", 1)
    cmds.setAttr(f"{curve}.hiddenInOutliner ", 1)
    cmds.setAttr(f"{curve}.inheritsTransform ", 0)

    cmds.setAttr(f"{curve}.translate", 0, 0, 0, type="double3")
    cmds.setAttr(f"{curve}.rotate", 0, 0, 0, type="double3")

    return curve

def init_template_file(ext=".guides", export=True):
    """
    Initializes the TEMPLATE_FILE variable.
    If a path is provided, it sets TEMPLATE_FILE to that path.
    Otherwise, it uses the default template file path.
    """

    if ext == ".guides":
        file_name = DataManager.get_guide_data()
    elif ext == ".ctls":
        file_name = DataManager.get_ctls_data()

    end_file_path = None


    if not os.path.isabs(file_name):
        folder= {".guides": "guides", ".ctls": "curves"}
        complete_path = os.path.realpath(__file__)
        relative_path = complete_path.split("\scripts")[0]
        guides_dir = os.path.join(relative_path, folder[ext])
        base_name = file_name
        # Find all files matching the pattern
        existing = [
            f for f in os.listdir(guides_dir)
            if f.startswith(base_name) and f.endswith(ext)
        ]
        max_num = 1
        for f in existing:
            try:
                num = int(f[len(base_name):len(base_name)+2])
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
        default_template = os.path.join(guides_dir, f"{base_name}{max_num:02d}{ext}")
    else:
        default_template = file_name
        base_name = os.path.splitext(file_name)[0]

    if export:
        if os.path.exists(default_template):
            result = cmds.confirmDialog(
                title='Template Exists',
                message=f'{default_template} already exists. Replace it?',
                button=['Replace', 'Add +1', 'Cancel'],
                defaultButton='Replace',
                cancelButton='Cancel',
                dismissString='Cancel'
            )
            if result == 'Replace':
                end_file_path = default_template
            elif result == 'Add +1':
                base, ext = os.path.splitext(default_template)
                i = 2
                while True:
                        new_template = f"{base[:-2]}{i:02d}{ext}"
                        if not os.path.exists(new_template):
                                end_file_path = new_template
                                break
                        i += 1
            elif result == 'Cancel':
                om.MGlobal.displayWarning("Template creation cancelled.")
                return None
            else:
                end_file_path = None
    else:
        end_file_path = default_template

    return end_file_path

def square_multiyply(distance, side):
    name = distance.split(".")[0]
    name = "_".join(name.split("_")[:2])
    multiply = cmds.createNode("multiply", name=f"{name}Squared{side}_MULT")
    cmds.connectAttr(f"{distance}", f"{multiply}.input[0]")
    cmds.connectAttr(f"{distance}", f"{multiply}.input[1]")
    return f"{multiply}.output"

def law_of_cosine(sides = [], power=[], name = "L_armModule", negate=False, acos=False):
    """`
    Calculate the angle opposite side c using the law of cosines.
    """
    

    if len(sides) != 3:
        raise ValueError("Three sides are required.")
    else:
        a, b, c = sides

    if len(power) == 3:
        a_square, b_square, c_square = power
    else:
        a_square = None
        b_square = None
        c_square = None

    if a_square is None:
        a_square = square_multiyply(a, "A")
    if b_square is None:
        b_square = square_multiyply(b, "B")
    if c_square is None:
        c_square = square_multiyply(c, "C")

    power_mults = [a_square, b_square, c_square]

    # a2 + c2 -b2
    sum = cmds.createNode("sum", name=f"{name}CustomSolver_SUM")
    cmds.connectAttr(f"{a_square}", f"{sum}.input[0]")
    cmds.connectAttr(f"{c_square}", f"{sum}.input[1]")

    subtract = cmds.createNode("subtract", name=f"{name}CosNumerator_SUB")
    cmds.connectAttr(f"{sum}.output", f"{subtract}.input1")
    cmds.connectAttr(f"{b_square}", f"{subtract}.input2")

    # 2ac
    multiply = cmds.createNode("multiply", name=f"{name}CosDenominator_MULT")
    cmds.setAttr(f"{multiply}.input[0]", 2)
    cmds.connectAttr(f"{a}", f"{multiply}.input[1]")
    cmds.connectAttr(f"{c}", f"{multiply}.input[2]")

    #complete formula
    divide = cmds.createNode("divide", name=f"{name}CosValue_DIV", ss=True)
    cmds.connectAttr(f"{subtract}.output", f"{divide}.input1")
    cmds.connectAttr(f"{multiply}.output", f"{divide}.input2")

    if acos and negate:
        acos = cmds.createNode("acos", name=f"{name}CustomSolver_ACOS")
        cmds.connectAttr(f"{divide}.output", f"{acos}.input")
        negate_cos_value = cmds.createNode("negate", name=f"{name}CosineValue_NEGATE")
        cmds.connectAttr(f"{divide}.output", f"{negate_cos_value}.input")
    
        return divide, acos, power_mults, negate_cos_value

    if acos:
        acos = cmds.createNode("acos", name=f"{name}CustomSolver_ACOS")
        cmds.connectAttr(f"{divide}.output", f"{acos}.input")

        return divide, acos, power_mults

    if negate:
        negate_cos_value = cmds.createNode("negate", name=f"{name}CosineValue_NEGATE")
        cmds.connectAttr(f"{divide}.output", f"{negate_cos_value}.input")

        return divide, power_mults, negate_cos_value

    return divide, power_mults