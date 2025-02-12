import maya.cmds as cmds
import maya.OpenMaya as om
import json
import os

def create_curve_from_data(degree, form, knots, cvs, lineWidth, colourShape, colourTransform, shape_name):
    """
    Creates a NURBS curve in Maya.

    Args:
        degree (int): Degree of the curve.
        form (int): Form of the curve (open, closed, periodic).
        knots (list): Knot values.
        cvs (list): CV positions.
        name (str): Name of the new curve.
        lineWidth (int): Width of the curve.
        colour (int): Colour of the curve.
    """
    # Create curve
    curve = cmds.curve(d=degree, p=cvs, k=knots)
    shape = cmds.listRelatives(curve, shapes=True)[0]

    # Close curve if necessary
    if form == 2 or form == 3:
        cmds.closeCurve(curve, preserveShape=False, replaceOriginal=True)
    # Add the thickness and colour
    cmds.setAttr(f"{curve}.lineWidth", lineWidth)
    cmds.setAttr(f"{shape}.overrideEnabled", 1)
    cmds.setAttr(f"{shape}.overrideColor", colourShape)
    cmds.setAttr(f"{curve}.overrideEnabled", 1)
    cmds.setAttr(f"{curve}.overrideColor", colourTransform)

    # Rename curve
    renamed_curve = cmds.rename(curve, shape_name)  

    # Delete construction history
    cmds.delete(renamed_curve, constructionHistory=True)

    return renamed_curve

def controller_creator(name):
    """
    Creates a controller with a specific name and offset transformsand returns the controller and the groups.

    Args:
        name (str): Name of the controller.
    """
    created_grps = []
    for suffix in ["GRP", "SPC", "OFF", "SDK", "ANM"]:
        if cmds.ls(f"{name}_{suffix}"):
            om.MGlobal.displayWarning(f"{name}_{suffix} already exists.")
            if created_grps:
                cmds.delete(created_grps[0])
            return
        tra = cmds.createNode("transform", name=f"{name}_{suffix}")
        if created_grps:
            cmds.parent(tra, created_grps[-1])
        created_grps.append(tra)

    if cmds.ls(f"{name}_CTL"):
        om.MGlobal.displayWarning(f"{name}_CTL already exists.")
        if created_grps:
            cmds.delete(created_grps[0])
        return
    else:
        ctl = import_nurbs_curves_from_json(f"{name}_CTL")
        cmds.parent(ctl, created_grps[-1])

        return ctl, created_grps # Return the controller and the groups

def export_nurbs_curve():
    """
    Exports selected NURBS curves in Maya to a JSON file.
    """
    selection = cmds.ls(selection=True)
    
    # Check if a NURBS curve is selected
    if not selection:
        om.MGlobal.displayError("Please select a NURBS curve to export.")
        return
    
    curve_dict = {}

    # Iterate through selected NURBS curves
    for transforms in selection:
        relatives = cmds.listRelatives(transforms, fullPath=True, shapes=True)

        # Check if the selected object is a NURBS curve
        if not relatives:
            om.MGlobal.displayError(f"{transforms} is not a NURBS curve.")
            continue

        shapes_dict = {}
        for i, shape in enumerate(relatives):
            dag_path = om.MDagPath()
            selection_list = om.MSelectionList()
            selection_list.add(shape)
            selection_list.getDagPath(0, dag_path)
            shape_fn = om.MFnNurbsCurve(dag_path)

            # Get curve data
            degree = shape_fn.degree()
            form = shape_fn.form()
            cvs = cmds.ls(f'{shape}.cv[*]', fl=1)
            points = []
            for cv in cvs:
                loc = cmds.xform(cv, q=1, t=1, ws=True)
                rounded_loc = tuple(round(coord, 2) for coord in loc)
                points.append(rounded_loc)


            num_points = len(points)
            num_knots = num_points + degree - 1
            knots = [i for i in range(-degree + 1, num_knots - degree + 1)]

            # Populate shape dictionary
            shapes_dict[f"{transforms}_shape{i+1}"] = {
                "knots": knots,
                "degree": degree,
                "form": form,
                "points": points,
                "lineWidth": cmds.getAttr(f"{shape}.lineWidth"),
                "colourShape": cmds.getAttr(f"{shape}.overrideColor"),
                "colourTransform": cmds.getAttr(f"{transforms}.overrideColor"),
            }

            curve_dict[transforms] = shapes_dict

    # Specify JSON file path
    file_path = cmds.fileDialog2(dialogStyle=2, fileMode=0, fileFilter="JSON Files (*.json)")
    if file_path:
        file_path = file_path[0]

        # Write to JSON file
        with open(file_path, 'w') as json_file:
            json.dump(curve_dict, json_file, indent=4)

        om.MGlobal.displayInfo(f"NURBS curve data exported to {file_path}.")
    else:
        om.MGlobal.displayError("Export cancelled.")

def import_nurbs_curves_from_json(shape_name):
    """
    Imports NURBS curves from a JSON file and creates them in Maya.

    Args:
        json_path (str): Path to the JSON file.
    """
    json_path = get_script_file_path()
    with open(json_path, 'r') as file:
        curve_data = json.load(file)
    # Extract the data for the specific group

    data = curve_data.get(shape_name)

    if data:
        main_curve = None
        for curve_name, shapes in data.items():
            # Create curve from JSON data
            degree = shapes['degree']
            form = shapes['form']
            knots = shapes['knots']
            cvs = shapes['points']
            lineWidth = shapes['lineWidth']
            colourShape = shapes['colourShape']
            colourTransform = shapes['colourTransform']

            # Create curve in Maya
            curve = create_curve_from_data(degree, form, knots, cvs, lineWidth, colourShape, colourTransform, shape_name)

            # Parent shapes to main curve
            if main_curve:
                shape = cmds.listRelatives(curve, shapes=True)[0]
                cmds.parent(shape, main_curve, relative=True, shape=True)
                cmds.delete(curve)
            else:
                main_curve = curve
    else:
        main_curve = cmds.circle(name=shape_name, normal=(0, 1, 0), constructionHistory=False)[0]
    
    return main_curve

def get_script_file_path():
    """
    Returns the file path of the currently executed script.
    """
    complete_path = os.path.realpath(__file__)
    script_path = complete_path.replace("\\", "/")
    relative_path = script_path.split("/scripts/puiastreTools/tools/curve_tool.py")[0]
    relative_path = relative_path.replace("/", "\\")
    final_path = os.path.join(relative_path, "curves", "curve_test.json")
    return final_path

