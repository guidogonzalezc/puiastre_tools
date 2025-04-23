import maya.api.OpenMaya as om2


def get_data_from_curve(curve_name):
    """
    Retrieves the degree, form, knots, and CVs of a NURBS curve in Maya.

    Args:
        curve_name (str): Name of the curve.

    Returns:
        tuple: A tuple containing the degree, form, knots, and CVs of the curve.
    """
    # Get the MObject for the curve
    selection_list = om2.MSelectionList()
    selection_list.add(curve_name)
    curve_dag_path = selection_list.getDagPath(0)
    print(curve_dag_path)
    curve_mobject = curve_dag_path.node()
    print(curve_mobject)

    # Get the MFnNurbsCurve function set
    nurbs_curve_fn = om2.MFnNurbsCurve(curve_mobject)

    # Retrieve the degree, form, knots, and CVs
    degree = nurbs_curve_fn.degree()
    print(degree)
    form = nurbs_curve_fn.form()
    knots = nurbs_curve_fn.knots()
    cvs = nurbs_curve_fn.cvPositions()

    return degree, form, knots, cvs

print(get_data_from_curve("nurbsCircleShape1"))  # Replace "curve1" with the name of your curve in Maya