import maya.cmds as cmds

def eye_rig():
    outer_crv = "L_outerEyeRef_CRV"
    middle_crv = "L_middleEyeRef_CRV"
    upper_crv = "L_upperEyeRef_CRV"

    outer_curve_points = cmds.ls(f"{outer_crv}.cv[*]", fl=True)
    upper_curve_points = cmds.ls(f"{upper_crv}.cv[*]", fl=True)

    print(len(outer_curve_points))
    print(len(upper_curve_points))


    for i, point in enumerate(outer_curve_points):
        cmds.select(cl=True)
        outer_position = cmds.pointPosition(point)
        upper_position = cmds.pointPosition(upper_curve_points[i])

        lower_position = [upper_position[0], outer_position[1], outer_position[2]]
        upper_position = [upper_position[0], upper_position[1], outer_position[2]]

        lower_joint = cmds.joint(p=lower_position, n=f"L_eyeLower{i}_JNT")
        upper_joint = cmds.joint(p=upper_position, n=f"L_eyeUpper{i}_JNT")


eye_rig()