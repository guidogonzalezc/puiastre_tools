import maya.api.OpenMaya as om
import maya.cmds as cmds
import json
import os


complete_path = os.path.realpath(__file__)
relative_path = complete_path.split("\scripts")[0]
TEMPLATE_FILE = os.path.join(relative_path, "curves", "template_curves_001.json") 


def get_all_ctl_curves_data():
    """
    Collects data from all controller curves in the scene and saves it to a JSON file.
    This function retrieves information about each controller's transform and its associated nurbsCurve shapes,
    including their CV positions, form, knots, degree, and override attributes.
    """

    ctl_data = {}

    transforms = cmds.ls("*_CTL*", type="transform", long=True)

    for transform_name in transforms:
        shapes = cmds.listRelatives(transform_name, shapes=True, fullPath=True) or []
        nurbs_shapes = []

        for shape in shapes:
            if cmds.nodeType(shape) == "nurbsCurve":
                nurbs_shapes.append(shape)

        if not nurbs_shapes:
            continue  

        sel_list = om.MSelectionList()
        sel_list.add(transform_name)
        transform_obj = sel_list.getDependNode(0)

        def get_override_info(node_obj):
            fn_dep = om.MFnDependencyNode(node_obj)
            try:
                override_enabled = fn_dep.findPlug('overrideEnabled', False).asBool()
                override_color = fn_dep.findPlug('overrideColor', False) if override_enabled else None
                override_color_value = override_color.asInt() if override_color else None
            except:
                override_enabled = False
                override_color_value = None
            return override_enabled, override_color_value

        transform_override_enabled, transform_override_color = get_override_info(transform_obj)

        shape_data_list = []

        for shape in nurbs_shapes:
            sel_list.clear()
            sel_list.add(shape)
            shape_obj = sel_list.getDependNode(0)

            shape_override_enabled, shape_override_color = get_override_info(shape_obj)

            fn_shape_dep = om.MFnDependencyNode(shape_obj)
            try:
                always_on_top = fn_shape_dep.findPlug('alwaysDrawOnTop', False).asBool()
            except:
                always_on_top = False

            curve_fn = om.MFnNurbsCurve(shape_obj)

            cvs = []
            for i in range(curve_fn.numCVs):
                pt = curve_fn.cvPosition(i)
                cvs.append((pt.x, pt.y, pt.z))

            form_types = {
                om.MFnNurbsCurve.kOpen: "open",
                om.MFnNurbsCurve.kClosed: "closed",
                om.MFnNurbsCurve.kPeriodic: "periodic"
            }

            form = form_types.get(curve_fn.form, "unknown")
            if form == "unknown":
                om.MGlobal.displayWarning(f"Curve form unknown for {shape}")

            knots = curve_fn.knots()
            degree = curve_fn.degree

            shape_data_list.append({
                "name": shape.split("|")[-1],
                "overrideEnabled": shape_override_enabled,
                "overrideColor": shape_override_color,
                "alwaysDrawOnTop": always_on_top,
                "curve": {
                    "cvs": cvs,
                    "form": form,
                    "knots": list(knots),
                    "degree": degree
                }
            })

        ctl_data[transform_name] = {
            "transform": {
                "name": transform_name.split("|")[-1],
                "overrideEnabled": transform_override_enabled,
                "overrideColor": transform_override_color
            },
            "shapes": shape_data_list
        }

    with open(TEMPLATE_FILE, "w") as f:
        json.dump(ctl_data, f, indent=4)

    print(f"Controllers template saved to: {TEMPLATE_FILE}")

def build_curves_from_template(target_transform_name=None):
    """
    Builds controller curves from a predefined template JSON file.
    If a specific target transform name is provided, it filters the curves to only create those associated with that transform.
    If no target transform name is provided, it creates all curves defined in the template.
    Args:
        target_transform_name (str, optional): The name of the target transform to filter curves by. Defaults to None.
    Returns:
        list: A list of created transform names.
    """

    if not os.path.exists(TEMPLATE_FILE):
        om.MGlobal.displayError("Template file does not exist.")
        return

    with open(TEMPLATE_FILE, "r") as f:
        ctl_data = json.load(f)

    if target_transform_name:
        ctl_data = {k: v for k, v in ctl_data.items() if v["transform"]["name"] == target_transform_name}
        if not ctl_data:
            return

    created_transforms = []

    for transform_path, data in ctl_data.items():
        transform_info = data["transform"]
        shape_data_list = data["shapes"]

        dag_modifier = om.MDagModifier()
        transform_obj = dag_modifier.createNode("transform")
        dag_modifier.doIt()

        transform_fn = om.MFnDagNode(transform_obj)
        final_name = transform_fn.setName(transform_info["name"])
        created_transforms.append(final_name)

        if transform_info["overrideEnabled"]:
            fn_dep = om.MFnDependencyNode(transform_obj)
            fn_dep.findPlug('overrideEnabled', False).setBool(True)
            fn_dep.findPlug('overrideColor', False).setInt(transform_info["overrideColor"])

        created_shapes = []

        for shape_data in shape_data_list:
            curve_info = shape_data["curve"]
            cvs = curve_info["cvs"]
            degree = curve_info["degree"]
            knots = curve_info["knots"]
            form = curve_info["form"]

            form_flags = {
                "open": om.MFnNurbsCurve.kOpen,
                "closed": om.MFnNurbsCurve.kClosed,
                "periodic": om.MFnNurbsCurve.kPeriodic
            }
            form_flag = form_flags.get(form, om.MFnNurbsCurve.kOpen)

            points = om.MPointArray()
            for pt in cvs:
                points.append(om.MPoint(pt[0], pt[1], pt[2]))

            curve_fn = om.MFnNurbsCurve()
            shape_obj = curve_fn.create(
                points,
                knots,
                degree,
                form_flag,
                False,    
                True,     
                transform_obj
            )

            shape_fn = om.MFnDagNode(shape_obj)
            shape_fn.setName(shape_data["name"])

            if shape_data["overrideEnabled"]:
                fn_dep = om.MFnDependencyNode(shape_obj)
                fn_dep.findPlug('overrideEnabled', False).setBool(True)
                fn_dep.findPlug('overrideColor', False).setInt(shape_data["overrideColor"])

            if shape_data.get("alwaysDrawOnTop", False):
                fn_dep = om.MFnDependencyNode(shape_obj)
                fn_dep.findPlug('alwaysDrawOnTop', False).setBool(True)

            created_shapes.append(shape_obj)


    return created_transforms


def controller_creator(name, suffixes=["GRP"]):
    """
    Creates a controller with a specific name and offset transforms and returns the controller and the groups.

    Args:
        name (str): Name of the controller.
        suffixes (list): List of suffixes for the groups to be created. Default is ["GRP"].
    """
    created_grps = []
    for suffix in suffixes:
        if cmds.ls(f"{name}_{suffix}"):
            om.MGlobal.displayWarning(f"{name}_{suffix} already exists.")
            if created_grps:
                cmds.delete(created_grps[0])
            return
        tra = cmds.createNode("transform", name=f"{name}_{suffix}", ss=True)
        if created_grps:
            cmds.parent(tra, created_grps[-1])
        created_grps.append(tra)

    if cmds.ls(f"{name}_CTL"):
        om.MGlobal.displayWarning(f"{name}_CTL already exists.")
        if created_grps:
            cmds.delete(created_grps[0])
        return
    else:
        ctl = build_curves_from_template(f"{name}_CTL")

        if not ctl:
            ctl = cmds.circle(name=f"{name}_CTL", ch=False)
        else:
            ctl = [ctl[0]]  # make sure ctl is a list with one element for consistency

        cmds.parent(ctl[0], created_grps[-1])
        return ctl[0], created_grps

def get_dag_path(node_name):
    """
    Returns the MObject dag path for a given node name.
    Args:
        node_name (str): The name of the node to get the dag path for.
    Returns:
        om.MDagPath: The dag path of the node.
    """
    sel = om.MSelectionList()
    sel.add(node_name)
    return sel.getDagPath(0)

def curves_match(curveA, curveB):
    """
    Compares two MFnNurbsCurve objects to check if they have the same structure.
    Args:
        curveA (om.MFnNurbsCurve): The first curve to compare.
        curveB (om.MFnNurbsCurve): The second curve to compare.
    Returns:
        bool: True if the curves match in structure, False otherwise.
    """
    return (
        curveA.degree == curveB.degree and
        curveA.numCVs == curveB.numCVs and
        curveA.form == curveB.form and
        curveA.numSpans == curveB.numSpans and
        curveA.knots() == curveB.knots()
    )

def rebuild_target_curve(src_transform, src_shape, tgt_transform, tgt_shape_name):
    """
    Rebuilds the target curve shape by duplicating the source curve and renaming it.
    Args:
        src_transform (str): The source transform containing the original curve.
        src_shape (str): The name of the source shape to duplicate.
        tgt_transform (str): The target transform where the new shape will be parented.
        tgt_shape_name (str): The name for the new shape in the target transform.
    Returns:
        str: The name of the newly created shape in the target transform.
    """ 
    if cmds.objExists(tgt_shape_name):
        cmds.delete(tgt_shape_name)

    dup = cmds.duplicate(f"{src_transform}|{src_shape}", name="tempCurveDup", returnRootsOnly=True)[0]
    new_shape = cmds.listRelatives(dup, shapes=True, fullPath=False)[0]

    final_shape = cmds.rename(new_shape, tgt_shape_name)
    cmds.parent(final_shape, tgt_transform, shape=True, relative=True)
    cmds.delete(dup)  

    return final_shape

def mirror_all_L_CTL_shapes():
    """
    Mirrors all left controller shapes (L_*_CTL) to their right counterparts (R_*_CTL).
    This function searches for all transform nodes that match the pattern "L_*_CTL", retrieves their shapes,
    and creates or updates the corresponding right-side shapes by mirroring the CV positions.
    """
    all_transforms = cmds.ls(type="transform")
    left_ctl_transforms = [t for t in all_transforms if "L_" in t and t.endswith("_CTL")]

    if not left_ctl_transforms:
        om.MGlobal.displayWarning("No matching 'L_*_CTL' transform nodes found.")
        return

    mirror_matrix = om.MMatrix([
        [-1, 0, 0, 0],
        [ 0, 1, 0, 0],
        [ 0, 0, 1, 0],
        [ 0, 0, 0, 1]
    ])

    for src_transform in left_ctl_transforms:
        shapes = cmds.listRelatives(src_transform, shapes=True, fullPath=False)
        if not shapes:
            om.MGlobal.displayWarning(f"No shape under {src_transform}. Skipping.")
            continue

        for src_shape in shapes:
            if not cmds.objectType(src_shape, isType="nurbsCurve"):
                om.MGlobal.displayWarning(f"{src_shape} is not a nurbsCurve. Skipping.")
                continue

            if "L_" not in src_shape:
                continue

            tgt_shape_name = src_shape.replace("L_", "R_", 1)
            tgt_transform = src_transform.replace("L_", "R_", 1)

            if not cmds.objExists(tgt_transform):
                om.MGlobal.displayWarning(f"Target transform '{tgt_transform}' not found. Skipping.")
                continue

            try:
                src_dag = get_dag_path(f"{src_transform}|{src_shape}")
                src_curve = om.MFnNurbsCurve(src_dag)

                if not cmds.objExists(tgt_shape_name):
                    final_shape = rebuild_target_curve(src_transform, src_shape, tgt_transform, tgt_shape_name)
                    tgt_dag = get_dag_path(f"{tgt_transform}|{final_shape}")
                else:
                    tgt_dag = get_dag_path(f"{tgt_transform}|{tgt_shape_name}")
                    tgt_curve = om.MFnNurbsCurve(tgt_dag)

                    if not curves_match(src_curve, tgt_curve):
                        final_shape = rebuild_target_curve(src_transform, src_shape, tgt_transform, tgt_shape_name)
                        tgt_dag = get_dag_path(f"{tgt_transform}|{final_shape}")

                tgt_curve = om.MFnNurbsCurve(tgt_dag)

                mirrored_points = om.MPointArray()
                for i in range(src_curve.numCVs):
                    pt = src_curve.cvPosition(i)
                    mirrored_points.append(pt * mirror_matrix)

                tgt_curve.setCVPositions(mirrored_points)
                tgt_curve.updateCurve()

                om.MGlobal.displayInfo(f"Mirrored and synced '{src_shape}' → '{tgt_shape_name}'")

            except Exception as e:
                om.MGlobal.displayError(f"Error processing {src_shape}: {e}")


