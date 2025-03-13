import maya.cmds as cmds

disconnect_list = ["useTranslate", "useRotate", "useScale", "useShear"]

def pick_matrix_create(driven):

    node_name = f"{driven.split('_')[0]}_{driven.split('_')[1]}"
    decompose_matrix = cmds.createNode("decomposeMatrix", n=f"{node_name}_DCM")
    driven_parent = cmds.listRelatives(driven, parent=True)[0]

    if cmds.xform(driven, ws=True) == cmds.xform(driven_parent, ws=True):
        mult_matrix = cmds.createNode('multMatrix', n=node_name)
        cmds.connectAttr(f"{driven_parent}.worldInverseMatix", f"{mult_matrix}.matrixIn[1]")

    return decompose_matrix

def offset_constraint(driver, driven):

    node_name = f"{driven.split('_')[0]}_{driven.split('_')[1]}"

    mult_matrix = cmds.createNode("multMatrix", n=f"{node_name}_MMX")
    cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{mult_matrix}.matrixIn[0]")

    inverse_driven = cmds.getAttr(f"{driven}.worldInverseMatrix")
    cmds.setAttr(f"{mult_matrix}.matrixIn[1]", inverse_driven, type="matrix")
    
    return mult_matrix

def parent(driver, driven, offset=True):

    decompose_matrix = pick_matrix_create(driven)

    if offset:
        mult_matrix = offset_constraint(driver, driven)
        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{decompose_matrix}.inputMatrix")
    else:
        cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{decompose_matrix}.inputMatrix")

    cmds.connectAttr(f"{decompose_matrix}.outputTranslate", f"{driven}.translate")
    cmds.connectAttr(f"{decompose_matrix}.outputRotate", f"{driven}.rotate")

def point(driver, driven, offset=True):

    decompose_matrix = pick_matrix_create(driven)

    if offset:
        mult_matrix = offset_constraint(driver, driven)
        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{decompose_matrix}.inputMatrix")
    else:
        cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{decompose_matrix}.inputMatrix")

    cmds.connectAttr(f"{decompose_matrix}.outputTranslate", f"{driven}.translate")

def orient(driver, driven, offset=True):

    decompose_matrix = pick_matrix_create(driven)

    if offset:
        mult_matrix = offset_constraint(driver, driven)
        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{decompose_matrix}.inputMatrix")
    else:
        cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{decompose_matrix}.inputMatrix")

    cmds.connectAttr(f"{decompose_matrix}.outputRotate", f"{driven}.rotate")

def scale(driver, driven, offset=True):

    decompose_matrix = pick_matrix_create(driven)

    if offset:
        mult_matrix = offset_constraint(driver, driven)
        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{decompose_matrix}.inputMatrix")
    else:
        cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{decompose_matrix}.inputMatrix")

    cmds.connectAttr(f"{decompose_matrix}.outputScale", f"{driven}.scale")
