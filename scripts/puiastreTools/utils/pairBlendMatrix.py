import maya.cmds as cmds

def duplicate_chain(joint):

    chain = cmds.listRelatives(joint, allDescendents=True)
    ik_chain = []
    fk_chain = []
    for i, jnt in range(len(chain)*2):
        cmds.select(clear=True)
        if i < len(chain):
            jnt_ik = cmds.joint(n=jnt.replace("_JNT", "Ik_JNT"))
            cmds.matchTransform(jnt_ik, jnt)
            ik_chain.append(jnt_ik)
        else:
            jnt_fk = cmds.joint(n=jnt.replace("_JNT", "Fk_JNT"))
            cmds.matchTransform(jnt_fk, jnt)
            fk_chain.append(jnt_fk)


    return ik_chain, fk_chain, chain

def blend_matrix(joint, blender):
    
    ik_chain, fk_chain, chain = duplicate_chain()

    blender_shape = cmds.listRelatives(blender, shapes=True)
    
    if not blender_shape:
        cmds.error("Blender object has no shape node")
        return

    for i, jnt_ik, jnt_fk in enumerate(zip(ik_chain, fk_chain)):

        blend_node = cmds.createNode("wtAddMatrix", n=chain[i].replace("_JNT", "ADM"))
        reverse_node = cmds.createNode("reverse", n=chain[i].replace("_JNT", "REV"))

        cmds.connectAttr(f"{jnt_ik}.worldMatrix", f"{blend_node}.wtMatrix[0].matrixIn")
        cmds.connectAttr(f"{jnt_fk}.worldMatrix", f"{blend_node}.wtMatrix[1].matrixIn")
        cmds.connectAttr(f"{blender}.Ik_Fk", f"{reverse_node}.inputX")
        cmds.connectAttr(f"{reverse_node}.outputX", f"{blend_node}.wtMatrix[0].weightIn")
        cmds.connectAttr(f"{blender}.Ik_Fk", f"{blend_node}.wtMatrix[1].weightIn")
        
        
        
