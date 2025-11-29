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
    _finger_data = None

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
    
    def set_finger_data(cls, side, data):
        # ensure dict storage per side
        if cls._finger_data is None:
            cls._finger_data = {}
        cls._finger_data[side] = data
        store_data()

    @classmethod
    def get_finger_data(cls, side=None):
        if cls._finger_data is None:    
            return None if side is not None else {}
        if side is None:
            return cls._finger_data
        return cls._finger_data.get(side)
    
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

def square_multiyply(distance, side):
    name = distance.split(".")[0]
    name = "_".join(name.split("_")[:2])
    multiply = cmds.createNode("multiply", name=f"{name}Squared{side}_MULT")
    cmds.connectAttr(f"{distance}", f"{multiply}.input[0]")
    cmds.connectAttr(f"{distance}", f"{multiply}.input[1]")
    return f"{multiply}.output"

def law_of_cosine(sides = [], power=[], name = "L_armModule", negate=False, acos=False):
    """
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

def get_offset_matrix(child, parent):
    """
    Calculate the offset matrix between a child and parent transform in Maya.
    Args:
        child (str): The name of the child transform or matrix attribute.
        parent (str): The name of the parent transform or matrix attribute. 
    Returns:
        list: The offset matrix as a flat list of 16 floats in row-major order that transforms the child into the parent's space.
    """
    def get_world_matrix(node):
        try:
            dag = om.MSelectionList().add(node).getDagPath(0)
            return dag.inclusiveMatrix()
        except:
            matrix = cmds.getAttr(node)
            return om.MMatrix(matrix)

    child_world_matrix = get_world_matrix(child)
    parent_world_matrix = get_world_matrix(parent)

    offset_matrix = child_world_matrix * parent_world_matrix.inverse()

    # Convert to Python list (row-major order)
    offset_matrix_list = list(offset_matrix)

    return offset_matrix_list

def get_closest_transform(main_transform, transform_list):
    """
    Returns the transform from transform_list that is closest to main_transform.
    
    Args:
        main_transform (str): Name of the main transform.
        transform_list (list): List of transform names to compare.

    Returns:
        str: Name of the closest transform.
    """
    main_pos = om.MVector(main_transform)
    
    closest_obj = None
    closest_dist = float('inf')
    
    for t in transform_list:
        if not cmds.objExists(t):
            continue
        
        pos = om.MVector(cmds.xform(t, q=True, ws=True, t=True))
        dist = (pos - main_pos).length()
        
        if dist < closest_dist:
            closest_dist = dist
            closest_obj = t

    return closest_obj

def getClosestParamsToPositionSurface(surface, position):
    """
    Returns the closest parameters (u, v) on the given NURBS surface 
    to a world-space position.

    Args:
        surface (str or MObject or MDagPath): The surface to evaluate.
        position (list or tuple): A 3D world-space position [x, y, z].

    Returns:
        tuple: (u, v) parameters on the surface closest to the given position.
    """
    # Get MDagPath for surface
    if isinstance(surface, str):
        sel = om.MSelectionList()
        sel.add(surface)
        surface_dag_path = sel.getDagPath(0)
    elif isinstance(surface, om.MObject):
        surface_dag_path = om.MDagPath.getAPathTo(surface)
    elif isinstance(surface, om.MDagPath):
        surface_dag_path = surface
    else:
        raise TypeError("Surface must be a string name, MObject, or MDagPath.")

    # Create function set for NURBS surface
    surface_fn = om.MFnNurbsSurface(surface_dag_path)

    # Convert position to MPoint
    point = om.MPoint(*position)

    # Get closest point and parameters
    closest_point, u, v = surface_fn.closestPoint(point, space=om.MSpace.kWorld)

    return u, v

def number_to_ordinal_word(n):
    base_ordinal = {
        1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth',
        6: 'sixth', 7: 'seventh', 8: 'eighth', 9: 'ninth', 10: 'tenth',
        11: 'eleventh', 12: 'twelfth', 13: 'thirteenth', 14: 'fourteenth',
        15: 'fifteenth', 16: 'sixteenth', 17: 'seventeenth', 18: 'eighteenth',
        19: 'nineteenth'
    }
    tens = {
        20: 'twentieth', 30: 'thirtieth', 40: 'fortieth',
        50: 'fiftieth', 60: 'sixtieth', 70: 'seventieth',
        80: 'eightieth', 90: 'ninetieth'
    }
    tens_prefix = {
        20: 'twenty', 30: 'thirty', 40: 'forty', 50: 'fifty',
        60: 'sixty', 70: 'seventy', 80: 'eighty', 90: 'ninety'
    }
    if n <= 19:
        return base_ordinal[n]
    elif n in tens:
        return tens[n]
    elif n < 100:
        ten = (n // 10) * 10
        unit = n % 10
        return tens_prefix[ten] + "-" + base_ordinal[unit]
    else:
        return str(n)
    
def local_space_parent(ctl, parents=[], default_weights=0.5):

    name = ctl.replace("_CTL", "")

    parentMatrix = cmds.createNode("parentMatrix", name=f"{name}LocalSpaceParent_PMX", ss=True)

    grp = ctl.replace("_CTL", "_GRP")
    off = ctl.replace("_CTL", "_OFF")

    cmds.connectAttr(f"{grp}.worldMatrix[0]", f"{parentMatrix}.inputMatrix", force=True)

    for i, parent in enumerate(parents):
        cmds.connectAttr(f"{parent}.worldMatrix[0]", f"{parentMatrix}.target[{i}].targetMatrix", force=True)
        cmds.setAttr(f"{parentMatrix}.target[{i}].offsetMatrix", get_offset_matrix(grp, parent), type="matrix")

    # cmds.connectAttr(f"{parents[0]}.worldMatrix[0]", f"{parentMatrix}.target[1].targetMatrix", force=True)
    # cmds.connectAttr(f"{parents[1]}.worldMatrix[0]", f"{parentMatrix}.target[0].targetMatrix", force=True)
    # cmds.setAttr(f"{parentMatrix}.target[1].offsetMatrix", get_offset_matrix(grp, parents[0]), type="matrix")
    # cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", get_offset_matrix(grp, parents[1]), type="matrix")

    multmatrix = cmds.createNode("multMatrix", name=f"{name}LocalSpaceParent_MMX", ss=True)
    cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{multmatrix}.matrixIn[0]", force=True)
    cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
    cmds.connectAttr(f"{multmatrix}.matrixSum", f"{off}.offsetParentMatrix", force=True)

    if len(parents) == 2:
        try:
            cmds.addAttr(ctl, longName="SpaceSwitchSep", niceName = "Space Switches  ———", attributeType="enum", enumName="———", keyable=True)
            cmds.setAttr(f"{ctl}.SpaceSwitchSep", channelBox=True, lock=True)   

            cmds.addAttr(ctl, longName="SpaceFollow", attributeType="float", min=0, max=1, defaultValue=default_weights, keyable=True)
        except:
            pass
        cmds.connectAttr(f"{ctl}.SpaceFollow", f"{parentMatrix}.target[0].weight", force=True)
        rev = cmds.createNode("reverse", name=f"{name}LocalSpaceParent_REV", ss=True)
        cmds.connectAttr(f"{ctl}.SpaceFollow", f"{rev}.inputX", force=True)
        cmds.connectAttr(f"{rev}.outputX", f"{parentMatrix}.target[1].weight", force=True)

    return multmatrix

def local_mmx(ctl, grp):
    name = ctl.replace("_CTL", "")

    multmatrix = cmds.createNode("multMatrix", name=f"{name}local_MMX", ss=True)
    cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{multmatrix}.matrixIn[0]", force=True)
    cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
    cmds.setAttr(f"{multmatrix}.matrixIn[2]", cmds.getAttr(f"{ctl}.worldMatrix[0]"), type="matrix")

    return f"{multmatrix}.matrixSum"

def getClosestParamToWorldMatrixCurve(curve, pos, point=False, both=False):
    """
    Returns the closest parameter (u) on the curve to the given worldMatrix.
    """
    selection_list = om.MSelectionList()
    selection_list.add(curve)
    curve_dag_path = selection_list.getDagPath(0)

    curveFn = om.MFnNurbsCurve(curve_dag_path)

    point_pos = om.MPoint(*pos)
    closestPoint, paramU = curveFn.closestPoint(point_pos, space=om.MSpace.kWorld)

    if point:
        return closestPoint
    
    elif both:
        return closestPoint, paramU

    return paramU

def getPositionFromParmCurve(curve, u_value):
    """
    Returns the world position on the curve at the given parameter (u).
    """
    selection_list = om.MSelectionList()
    selection_list.add(curve)
    curve_dag_path = selection_list.getDagPath(0)

    curveFn = om.MFnNurbsCurve(curve_dag_path)

    point_pos = curveFn.getPointAtParam(u_value, space=om.MSpace.kWorld)

    return [point_pos.x, point_pos.y, point_pos.z]