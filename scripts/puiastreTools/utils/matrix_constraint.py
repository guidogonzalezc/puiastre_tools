import maya.cmds as cmds

def create_matrix_parent_constraint(driver, driven):


    # Get matrices
    driver_world_matrix = cmds.getAttr(f"{driven}.worldMatrix[0]")  # Driver's world matrix
    driven_world_inv_matrix = cmds.getAttr(f"{driver}.worldMatrix[0]")  # Driver's world matrix
    driver_inv_matrix = cmds.getAttr(f"{driver}.worldInverseMatrix[0]")  # Driver's inverse world matrix
    driven_world_matrix = cmds.getAttr(f"{driven}.worldMatrix[0]")  # Driven's world matrix

    # Multiply child world matrix by parent inverse world matrix
    mult_matrix = cmds.createNode('multMatrix', name=f"{driven}_multMatrix")
    cmds.connectAttr(f"{driven}.worldMatrix[0]", f"{mult_matrix}.matrixIn[0]")
    cmds.connectAttr(f"{driver}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]")

    # Connect the output to the driven object's offset parent matrix
    cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{driven}.offsetParentMatrix")

    mult_matrix2 = cmds.createNode('multMatrix', name=f"{driven}_multMatrix")
    matrix_sum = cmds.getAttr(f"{mult_matrix}.matrixSum")

    cmds.setAttr(f"{mult_matrix2}.matrixIn[0]", matrix_sum, type="matrix")
    cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{mult_matrix2}.matrixIn[1]")
    cmds.connectAttr(f"{driven}.worldInverseMatrix[0]", f"{mult_matrix2}.matrixIn[2]")


# Example Usage
create_matrix_parent_constraint("pCube1", "pCube2")
