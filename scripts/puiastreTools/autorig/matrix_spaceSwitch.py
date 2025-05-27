import maya.cmds as cmds
import maya.api.OpenMaya as om

def switch_matrix_space(target, sources = [None]):

    target_grp = target.replace("CTL", "GRP")
    if not cmds.objExists(target_grp):
        om.MGlobal.displayError(f"Target group '{target_grp}' does not exist.")
        return
    
    
    parent_matrix = cmds.createNode("parentMatrix", name=target.replace("CTL", "PM"))
    mult_matrix = cmds.createNode("multMatrix", name=target.replace("CTL", "MMX"))   
    cmds.connectAttr(f"{target_grp}.worldMatrix[0]", f"{parent_matrix}.inMatrix")
    cmds.connectAttr(f"{parent_matrix}.outMatrix", f"{mult_matrix}.matrixIn[0]")
    cmds.connectAttr(f"{parent_matrix}.worldInverseMatrix", f"{mult_matrix}.matrixIn[1]")

    spaces = []
    condition_nodes = []
    
    for i, matrix in enumerate(sources):
        cmds.connectAttr(f"{matrix}.worldMatrix[0]", f"{parent_matrix}.target[{i}].targetMatrix")

        condition = cmds.createNode("condition", name=f"{target.replace('CTL', 'COND')}")
        cmds.setAttr(f"{condition}.operation", i)
        cmds.setAttr(f"{condition}.colorIfFalseR", 0)

        name = matrix.split("_")[1]
        spaces.append(name)
        condition_nodes.append(condition)


    cmds.addAttr(target, longName="SPACE_SWITCHES", attributeType="enum", enumName="____")
    cmds.setAttr(f"{target}.SPACE_SWITCHES", lock=True, keyable=False)        
    cmds.addAttr(target, longName="Space_Switch", attributeType="enum", enumName=",".join(spaces))
    cmds.addAttr(target, longName="Space_Switch_Value", attributeType="float", min=0, max=1, defaultValue=1, keyable=True)

    for i, condition in enumerate(condition_nodes):
        cmds.connectAttr(f"{target}.Space_Switch", f"{condition}.firstTerm")
        cmds.connectAttr(f"{target}.Space_Switch_Value", f"{condition}.colorIfTrueR")
        cmds.connectAttr(f"{condition}.outColorR", f"{parent_matrix}.weight[{i}]")

    
    cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{target}.offsetParentMatrix")


switch_matrix_space("myControl", ["source1_CTL", "source2_CTL", "source3_CTL"])


