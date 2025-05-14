import maya.cmds as cmds
import PyRig.utilites.controller_library as ctls
def stretch_system(main_transforms, rig_transforms, controls_tranforms, spine, ik_curve, spine_module_trn):
        settings_ctl, settings_ctl_grp = ctls.controller_creator(f"C_spineSettings", "Gear") 
        circulo = cmds.circle(name="C_spineSettings01_CTL", degree=3, normal=(0,0,1))

        cmds.parent(cmds.listRelatives(circulo), settings_ctl ,r=True, s=True)
        cmds.delete(circulo)
        cmds.matchTransform(settings_ctl_grp[0], f"C_{spine[0]}_JNT")
        cmds.move(0, 35, -20, settings_ctl_grp[0], relative=True)
        cmds.setAttr(f"{settings_ctl}.overrideEnabled", 1)
        cmds.setAttr(f"{settings_ctl}.overrideColor", 17) 
        cmds.parent(settings_ctl_grp[0], controls_tranforms[5])
        for attribute in ["translateX","translateY","translateZ","rotateX","rotateY","rotateZ","scaleX","scaleY","scaleZ","visibility"]:
            cmds.setAttr(f"{settings_ctl}.{attribute}", lock=True, keyable=False, channelBox=False)
        
        cmds.addAttr(settings_ctl, shortName="stretch", niceName="Stretch", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(settings_ctl, shortName="stretchMin", niceName="Stretch Min", maxValue=1, minValue=0.001,defaultValue=0.8, keyable=True)
        cmds.addAttr(settings_ctl, shortName="stretchMax", niceName="Stretch Max", minValue=1,defaultValue=1.2, keyable=True)
        cmds.addAttr(settings_ctl, shortName="offset", niceName="Offset", maxValue=1, minValue=0,defaultValue=0, keyable=True)

        cmds.addAttr(settings_ctl, shortName="SQUASH", niceName="SQUASH_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(settings_ctl+".SQUASH", channelBox=True, lock=True)
        cmds.addAttr(settings_ctl, shortName="volumePreservation", niceName="Volume Preservation", maxValue=1, minValue=0,defaultValue=1, keyable=True)
        cmds.addAttr(settings_ctl, shortName="falloff", niceName="Falloff", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(settings_ctl, shortName="maxPos", niceName="Max Pos", maxValue=1, minValue=0,defaultValue=0.5, keyable=True)

        cmds.addAttr(settings_ctl, shortName="attachedFk", niceName="FK_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(settings_ctl+".attachedFk", channelBox=True, lock=True)
        cmds.addAttr(settings_ctl, shortName="attachedFKVis", niceName="Attached FK Visibility", attributeType="bool", keyable=True)


        nodes_to_create = {
            "C_spine_CIN": ("curveInfo", None), #0
            "C_spineStretchFactor_FLM": ("floatMath", 3), #1
            "C_spineStretchFactor_CLM": ("clamp", None), #2
            "C_spineInitialArcLegth_FLM": ("floatMath", 2), #3
            "C_spineBaseStretch_FLC": ("floatConstant", None), #4
            "C_spineStretch_BTA": ("blendTwoAttr", None), # 5
            "C_spineStretchValue_FLM": ("floatMath", 2),# 6
        }

        created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        # Connections between selected nodes
        cmds.connectAttr(created_nodes[0] + ".arcLength", created_nodes[1]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[2]+".inputR")
        cmds.connectAttr(created_nodes[3] + ".outFloat", created_nodes[1]+".floatB")
        cmds.connectAttr(created_nodes[2] + ".outputR", created_nodes[5]+".input[1]")
        cmds.connectAttr(created_nodes[4] + ".outFloat", created_nodes[5]+".input[0]")
        cmds.connectAttr(created_nodes[5] + ".output", created_nodes[6]+".floatA")
        cmds.setAttr(created_nodes[4]+".inFloat", 1)
        cmds.connectAttr(f"{settings_ctl}.stretch", created_nodes[5]+".attributesBlender")
        cmds.connectAttr(f"{settings_ctl}.stretchMax", created_nodes[2]+".maxR")
        cmds.connectAttr(f"{settings_ctl}.stretchMin", created_nodes[2]+".minR")
        cmds.connectAttr(f"{ik_curve}.worldSpace[0]", created_nodes[0]+".inputCurve")
        cmds.setAttr(created_nodes[3]+".floatB", cmds.getAttr(created_nodes[0]+".arcLength"))
        cmds.connectAttr(f"{controls_tranforms[5]}.globalScale", created_nodes[3]+".floatA")
        cmds.setAttr(created_nodes[6]+".floatB", cmds.getAttr(f"C_{spine[2]}_JNT.translateY"))
        for joint in spine[1:]:
             cmds.connectAttr(created_nodes[6]+".outFloat", f"C_{joint}_JNT.translateY")
        return settings_ctl, settings_ctl_grp, created_nodes[6]

def reverse_system(stretch_float_math, settings_ctl, main_transforms, rig_transforms, controls_tranforms, spine, ik_curve, spine_module_trn):
    reversed_curve = cmds.reverseCurve(ik_curve,name="C_spineReversed_CRV",  ch=True, rpo=False)
    cmds.parent(reversed_curve[0], spine_module_trn) 
    reversed_joints = cmds.duplicate(f"C_{spine[0]}_JNT", renameChildren=True)

    reverse_chain = []
    for i, joint in enumerate(reversed(reversed_joints)):
        if "effector" in joint:
            reversed_joints.remove(joint)
            cmds.delete(joint)
            
        else:
            renamed_joint = cmds.rename(joint, f"C_spineReversed0{i}_JNT")
            if i != 5:
                cmds.parent(renamed_joint, world=True)
            reverse_chain.append(renamed_joint) 
    for i, joint in enumerate(reverse_chain):
        if i != 0:
            cmds.parent(joint, reverse_chain[i-1])


    cmds.parent(reverse_chain[0], spine_module_trn)
    hdl = cmds.ikHandle(sj=reverse_chain[0], ee=reverse_chain[-1], sol="ikSplineSolver", n="C_spineReversed_HDL", parentCurve=False, curve=reversed_curve[0], createCurve=False) # Create an IK spline handle
    cmds.parent(hdl[0], spine_module_trn) 


    negate_flm = cmds.createNode("floatMath", n="C_spineNegateStretchValue_FLM")
    cmds.setAttr("C_spineNegateStretchValue_FLM.operation", 2)
    cmds.setAttr("C_spineNegateStretchValue_FLM.floatB", -1)
    cmds.connectAttr(stretch_float_math+".outFloat", f"{negate_flm}.floatA")

    for joint in reverse_chain[1:]:
        cmds.connectAttr(negate_flm+".outFloat", f"{joint}.translateY")

    return reversed_curve, reverse_chain

def offset_system(settings_ctl, ik_handle, reverse_chain, curve, spine_module_trn):
    nodes_to_create = {
        "C_spineReversed05_DCM": ("decomposeMatrix", None),
        "C_spineOffset_NPC": ("nearestPointOnCurve", None),
        "C_spineOffsetInitialValue_FLC": ("floatConstant", None),
        "C_spineOffset_BTA": ("blendTwoAttr", None),
    }

    created_nodes = []
    for node_name, (node_type, operation) in nodes_to_create.items():
        node = cmds.createNode(node_type, name=node_name)
        created_nodes.append(node)
        if operation is not None:
            cmds.setAttr(f'{node}.operation', operation)

    cmds.connectAttr(created_nodes[0] + ".outputTranslate", created_nodes[1]+".inPosition")
    cmds.connectAttr(created_nodes[1] + ".parameter", created_nodes[3]+".input[1]")
    cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[3]+".input[0]")
    cmds.connectAttr(f"{settings_ctl}.offset", created_nodes[3]+".attributesBlender")
    cmds.connectAttr(f"{reverse_chain[-1]}.worldMatrix[0]", created_nodes[0]+".inputMatrix")
    cmds.connectAttr(f"{curve}.worldSpace[0]", created_nodes[1]+".inputCurve")
    cmds.connectAttr(f"{created_nodes[3]}.output", ik_handle+".offset")
    cmds.setAttr(created_nodes[2]+".inFloat", 0)




def squash_system(spine_chain, controls_tranforms, spine_module_trn, rig_transforms):
    translations = []

    spine_settings_trn = cmds.createNode("transform", n="C_spineSettings_TRN", parent=spine_module_trn)
    for attribute in ["translateX","translateY","translateZ","rotateX","rotateY","rotateZ","scaleX","scaleY","scaleZ","visibility"]:
        cmds.setAttr(f"{spine_settings_trn}.{attribute}", lock=True, keyable=False, channelBox=False)

    cmds.addAttr(spine_settings_trn, shortName="maxStretchLength", niceName="Max Stretch Length", minValue=1,defaultValue=2, keyable=True)
    cmds.addAttr(spine_settings_trn, shortName="minStretchLength", niceName="Min Stretch Length", maxValue=1, minValue=0.001,defaultValue=0.5, keyable=True)
    cmds.addAttr(spine_settings_trn, shortName="maxStretchEffect", niceName="Max Stretch Effect", minValue=1,defaultValue=2, keyable=True)
    cmds.addAttr(spine_settings_trn, shortName="minStretchEffect", niceName="Min Stretch Effect", maxValue=1, minValue=0.001,defaultValue=0.5, keyable=True)
    
    cmds.addAttr(spine_settings_trn, shortName="VolumeSep", niceName="Volume_____", enumName="_____",attributeType="enum", keyable=True)
    cmds.setAttr(spine_settings_trn+".VolumeSep", channelBox=True, lock=True)
    
    for i in range(len(spine_chain)):
        if i == 0:
            default_value = 0.05
        if i == len(spine_chain)-1:
            default_value = 0.95
        else:
            default_value = (1/(len(spine_chain)-1))*i
        cmds.addAttr(spine_settings_trn, shortName=f"spine0{i+1}SquashPercentage", niceName="Spine01 Squash Percentage", maxValue=1, minValue=0,defaultValue=default_value, keyable=True)
    
    for joint in spine_chain:
        translation = cmds.xform(f"C_{joint}_JNT", query=True, worldSpace=True, translation=True)
        translations.append(translation)
    squash_curve = cmds.curve(p=translations, d=1, n="C_spineSquash_CRV")
    cmds.parent(squash_curve, spine_module_trn)
    

    for i, joint in enumerate(spine_chain):
        dcm = cmds.createNode("decomposeMatrix", n=f"C_{joint}Squash_DCM")
        cmds.connectAttr(f"C_{joint}_JNT.worldMatrix[0]", f"{dcm}.inputMatrix")
        cmds.connectAttr(f"{dcm}.outputTranslate", f"{squash_curve}.controlPoints[{i}]")

    nodes_to_create = {
        "C_spineSquash_CIN": ("curveInfo", None),
        "C_spineSquashBaseLength_FLM": ("floatMath", 2),
        "C_spineSquashFactor_FLM": ("floatMath", 3),
    }

    created_nodes = []
    for node_name, (node_type, operation) in nodes_to_create.items():
        node = cmds.createNode(node_type, name=node_name)
        created_nodes.append(node)
        if operation is not None:   
            cmds.setAttr(f'{node}.operation', operation)

    cmds.connectAttr(f"{squash_curve}.worldSpace[0]", created_nodes[0]+".inputCurve")
    cmds.connectAttr(created_nodes[0] + ".arcLength", created_nodes[2]+".floatA")
    cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[2]+".floatB") 
    cmds.connectAttr(f"{controls_tranforms[5]}.globalScale", created_nodes[1]+".floatA") 
    cmds.setAttr(created_nodes[1]+".floatB", cmds.getAttr(created_nodes[0]+".arcLength"))

    return created_nodes[2], spine_settings_trn


def attached_fk(spine_chain, spine_module_trn, controls_tranforms, settings_ctl, rig_transforms, chest_fix):
    main_spine_joint = []
    for joint in spine_chain:
        if "effector" in joint:
                spine_chain.remove(joint)
        else:
            main_spine_joint.append(f"C_{joint}_JNT")

    ctls_sub_spine = []
    sub_spine_ctl_trn = cmds.createNode("transform", n="C_subSpineControllers_GRP", parent=controls_tranforms[0])
    cmds.connectAttr(f"{settings_ctl}.attachedFKVis", f"{sub_spine_ctl_trn}.visibility")
    for i, joint in enumerate(main_spine_joint):
        
        ctl, controller_grp = ctls.controller_creator(f"C_subSpineFk0{i+1}", "Square")
        for attr in ["scaleX","scaleY","scaleZ","visibility"]:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)
            
        cmds.setAttr(f"{ctl}.overrideEnabled", 1)
        cmds.setAttr(f"{ctl}.overrideColor", 24)
        cmds.scale(5, 5, 5, f"{ctl}.cv[0:36]")
        cmds.parent(controller_grp[0], sub_spine_ctl_trn)
        if i == 0:
            cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{controller_grp[0]}.offsetParentMatrix")
        else:
            mmt = cmds.createNode("multMatrix", n=f"C_spineSubAttachedFk0{i+1}_MMT")
            if i == len(spine_chain)-1:
                cmds.connectAttr(f"{chest_fix}.worldMatrix[0]", f"{mmt}.matrixIn[0]")
            else:
                cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{mmt}.matrixIn[0]")
            cmds.connectAttr(f"{main_spine_joint[i-1]}.worldInverseMatrix[0]", f"{mmt}.matrixIn[1]")
            cmds.connectAttr(f"{ctls_sub_spine[i-1]}.worldMatrix[0]", f"{mmt}.matrixIn[2]")
            cmds.connectAttr(f"{mmt}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix")
        ctls_sub_spine.append(ctl)

    spine_skinning_joints_trn = cmds.createNode("transform", n="C_spineSkinningJoints_TRN", parent=rig_transforms[1])
    sub_spine_joints = []
    for i, joint in enumerate(main_spine_joint):
        cmds.select(clear=True)
        new_joint = cmds.joint(joint, name=f"C_subSpineFk0{i+1}_JNT")
        cmds.setAttr(f"{new_joint}.inheritsTransform", 0)

        cmds.parent(new_joint, spine_skinning_joints_trn)

        cmds.connectAttr(f"{ctls_sub_spine[i]}.worldMatrix[0]", f"{new_joint}.offsetParentMatrix")
        for attr in ["translateX","translateY","translateZ"]:
            cmds.setAttr(f"{new_joint}.{attr}", 0)
        sub_spine_joints.append(new_joint)

    return sub_spine_joints, spine_skinning_joints_trn
    



def volume_preservation_system(settings_ctl, squash_factor_fml, spine_settings_trn, spine_chain, spine_module_trn, controls_tranforms, rig_transforms, chest_fix):
            
    squash_joints, spine_skinning_joints_trn = attached_fk(spine_chain, spine_module_trn, controls_tranforms, settings_ctl, rig_transforms, chest_fix)
    

    nodes_to_create = {
        "C_spineVolumeLowBound_RMV": ("remapValue", None),# 0
        "C_spineVolumeHighBound_RMV": ("remapValue", None),# 1
        "C_spineVolumeLowBoundNegative_FLM": ("floatMath", 1),# 2
        "C_spineVolumeHighBoundNegative_FLM": ("floatMath", 1),# 3
        "C_spineVolumeSquashDelta_FLM": ("floatMath", 1), # 4
        "C_spineVolumeStretchDelta_FLM": ("floatMath", 1), # 5
    } 

    main_created_nodes = []
    for node_name, (node_type, operation) in nodes_to_create.items():
        node = cmds.createNode(node_type, name=node_name)
        main_created_nodes.append(node)
        if operation is not None:
            cmds.setAttr(f'{node}.operation', operation)
    values = [0.001, 0.999]
    for i in range(0,2):
        cmds.connectAttr(f"{settings_ctl}.falloff", f"{main_created_nodes[i]}.inputValue")
        cmds.connectAttr(f"{settings_ctl}.maxPos", f"{main_created_nodes[i]}.outputMin")
        cmds.setAttr(f"{main_created_nodes[i]}.outputMax", values[i])
        cmds.connectAttr(f"{main_created_nodes[i]}.outValue", f"{main_created_nodes[i+2]}.floatB")

    cmds.setAttr(f"{main_created_nodes[2]}.floatA", 0)
    cmds.setAttr(f"{main_created_nodes[3]}.floatA", 2)
    cmds.setAttr(f"{main_created_nodes[4]}.floatB", 1)
    cmds.setAttr(f"{main_created_nodes[5]}.floatA", 1)
    cmds.connectAttr(f"{spine_settings_trn}.maxStretchEffect", f"{main_created_nodes[4]}.floatA")
    cmds.connectAttr(f"{spine_settings_trn}.minStretchEffect", f"{main_created_nodes[5]}.floatB")

    for i, joint in enumerate(squash_joints):
        nodes_to_create = {
            f"C_spineVolumeSquashFactor0{i+1}_FLM": ("floatMath", 2), # 0
            f"C_spineVolumeStretchFactor0{i+1}_FLM": ("floatMath", 2), # 1
            f"C_spineVolumeStretchFullValue0{i+1}_FLM": ("floatMath", 1), # 2
            f"C_spineVolumeSquashFullValue0{i+1}_FLM": ("floatMath", 0), # 3
            f"C_spineVolume0{i+1}_RMV": ("remapValue", None), # 4
            f"C_spineVolumeFactor0{i+1}_RMV": ("remapValue", None), # 5
        }

        created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        cmds.connectAttr(f"{spine_settings_trn}.spine0{i+1}SquashPercentage", f"{created_nodes[5]}.inputValue")
        cmds.connectAttr(f"{main_created_nodes[2]}.outFloat", f"{created_nodes[5]}.value[0].value_Position")
        cmds.connectAttr(f"{main_created_nodes[0]}.outValue", f"{created_nodes[5]}.value[1].value_Position")
        cmds.connectAttr(f"{main_created_nodes[1]}.outValue", f"{created_nodes[5]}.value[2].value_Position")
        cmds.connectAttr(f"{main_created_nodes[3]}.outFloat", f"{created_nodes[5]}.value[3].value_Position")


        cmds.connectAttr(created_nodes[0] + ".outFloat", created_nodes[3]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[2]+".floatB")
        cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[4]+".value[2].value_FloatValue")
        cmds.connectAttr(created_nodes[3] + ".outFloat", created_nodes[4]+".value[0].value_FloatValue")
        cmds.connectAttr(squash_factor_fml + ".outFloat", created_nodes[4]+".inputValue")
        cmds.setAttr(f"{created_nodes[3]}.floatB", 1)
        cmds.setAttr(f"{created_nodes[2]}.floatA", 1)

        cmds.connectAttr(f"{main_created_nodes[4]}.outFloat", created_nodes[0]+".floatA")
        cmds.connectAttr(f"{main_created_nodes[5]}.outFloat", created_nodes[1]+".floatA")
        cmds.connectAttr(f"{created_nodes[5]}.outValue", created_nodes[0]+".floatB")
        cmds.connectAttr(f"{created_nodes[5]}.outValue", created_nodes[1]+".floatB")

        cmds.connectAttr(f"{spine_settings_trn}.maxStretchLength", f"{created_nodes[4]}.value[2].value_Position")
        cmds.connectAttr(f"{spine_settings_trn}.minStretchLength", f"{created_nodes[4]}.value[0].value_Position")   
        cmds.connectAttr(f"{created_nodes[4]}.outValue",f"{joint}.scaleX")   
        cmds.connectAttr(f"{created_nodes[4]}.outValue",f"{joint}.scaleZ")   


        values = [-1, 1, 1, -1]
        for i in range(0,4):
            cmds.setAttr(f"{created_nodes[5]}.value[{i}].value_Interp", 2)
            cmds.setAttr(f"{created_nodes[5]}.value[{i}].value_FloatValue", values[i])

    return squash_joints, spine_skinning_joints_trn




def spine_module(spine, side, type, main_transforms, rig_transforms, controls_tranforms): 
    spine.reverse() 
    side.reverse()
    type.reverse()

    spine_module_trn = cmds.createNode("transform", n="C_spineModule_GRP", p=rig_transforms[0]) 

    cmds.parent(f"{side[0]}_{spine[0]}_{type[0]}", spine_module_trn) 

    start_joint_pos = cmds.xform(f"{side[0]}_{spine[0]}_{type[0]}", query=True, worldSpace=True, translation=True)
    end_joint_pos = cmds.xform(f"{side[-1]}_{spine[-1]}_{type[-1]}", query=True, worldSpace=True, translation=True)
    ik_curve = cmds.curve(degree=1, point=[start_joint_pos, end_joint_pos], name="C_spine_CRV")
    cmds.rebuildCurve(ik_curve, rpo=True, rt=0, end=True, kr=False, kcp=False, kep=True, kt=True, fr=False, s=1, d=2, tol=0.01)
    cmds.delete(ik_curve, ch=True)

    ik_sc = cmds.ikHandle(sj=f"{side[0]}_{spine[0]}_{type[0]}", ee=f"{side[-1]}_{spine[-1]}_{type[-1]}", sol="ikSplineSolver", n="C_spine_HDL", curve=ik_curve, createCurve=False, parentCurve=False) [0]# Create an IK spline handle using the existing ik_curve
    curve_shape = cmds.listRelatives(ik_curve, shapes=True)[0]
    spine_ctl = []
    spine_grp = []

    cmds.parent(ik_curve, spine_module_trn) 
    cmds.parent(ik_sc, spine_module_trn)

    values = [0,1 , 2]

    for i in range(3):
        if i == 1 or i == 3:
            ctl, ctl_grp = ctls.controller_creator(f"{side[i]}_spine0{values[i]}Tan", "circle")

            cmds.setAttr(f"{ctl}.overrideEnabled", 1) 
            cmds.setAttr(f"{ctl}.overrideColor", 21)

            
        else:
            ctl, ctl_grp = ctls.controller_creator(f"{side[i]}_spine0{values[i]}", "circle") 
            if ctl == "C_spine02_CTL":
                chest = ctl
            
            cmds.setAttr(f"{ctl}.overrideEnabled", 1)
            cmds.setAttr(f"{ctl}.overrideColor", 17)

        for attr in ["scaleX","scaleY","scaleZ","visibility"]:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

        cmds.scale(12, 12, 12, f"{ctl}.cv[*]", r=True, ocp=True)
        cluster = cmds.cluster(f"{ik_curve}.cv[{i}]", n=f"{side[i]}_{spine[i]}_CLS") 

        spine_ctl.append(ctl) 
        spine_grp.append(ctl_grp) 

        cmds.matchTransform(ctl_grp[0], cluster) 
        cmds.delete(cluster) 

        dcm = cmds.createNode("decomposeMatrix", n=f"{side[i]}_{spine[i]}_DCM") 
        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{dcm}.inputMatrix")
        cmds.connectAttr(f"{dcm}.outputTranslate", f"{curve_shape}Orig.controlPoints[{i}]")

    cmds.parent(spine_grp[2][0], spine_ctl[0])
    cmds.parent(spine_grp[1][0], spine_ctl[2])


    chest_fix = cmds.joint(name = "C_localChest_JNT")
    cmds.delete(cmds.parentConstraint(spine_ctl[-1], chest_fix, mo=False))
    cmds.parent(chest_fix, spine_module_trn)
    localChest_ctl, localChest_grp = ctls.controller_creator(f"C_chest", "LocalChest")
    cmds.setAttr(f"{localChest_ctl}.overrideEnabled", 1) 
    cmds.setAttr(f"{localChest_ctl}.overrideColor", 17)
    cmds.pointConstraint(f"{side[-1]}_{spine[-1]}_{type[-1]}", localChest_grp[0], mo=False)
    cmds.orientConstraint(spine_ctl[2], localChest_grp[0], mo=False)
    cmds.parentConstraint(localChest_ctl, chest_fix, mo=True)
    cmds.parent(localChest_grp[0], controls_tranforms[5])


    spine_hip_ctl, spine_hip_ctl_grp = ctls.controller_creator(f"{side[i]}_localHip", "LocalHip")
    cmds.matchTransform(spine_hip_ctl_grp[0], spine_grp[0][0])
    cmds.setAttr(f"{spine_hip_ctl}.overrideEnabled", 1)
    cmds.setAttr(f"{spine_hip_ctl}.overrideColor", 17)

    for attr in ["scaleX","scaleY","scaleZ","visibility"]:
        cmds.setAttr(f"{spine_hip_ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    cmds.parent(spine_hip_ctl_grp[0], controls_tranforms[5]) 

    body_ctl, body_ctl_grp = ctls.controller_creator(f"{side[i]}_body", "Body") 
    cmds.matchTransform(body_ctl_grp[0], spine_grp[0][0])
    cmds.setAttr(f"{body_ctl}.overrideEnabled", 1)
    cmds.setAttr(f"{body_ctl}.overrideColor", 13)

    for controllers in [spine_hip_ctl, body_ctl]:
        for attr in ["scaleX","scaleY","scaleZ","visibility"]:
            cmds.setAttr(f"{controllers}.{attr}", lock=True, keyable=False, channelBox=False)
    
    cmds.parent(spine_grp[0][0], body_ctl) 
    cmds.parent(body_ctl_grp[0], controls_tranforms[5]) 

    movable_ctl = cmds.circle(n="C_movablePivot_CTL", ch=False, normal=(0,1,0))[0] 
    cmds.matchTransform(movable_ctl, spine_grp[0][0]) 
    cmds.parent(movable_ctl, body_ctl)
    

    cmds.connectAttr(f"{movable_ctl}.translate", f"{body_ctl}.rotatePivot")
    cmds.connectAttr(f"{movable_ctl}.translate", f"{body_ctl}.scalePivot") 

    for attr in ["rotateX","rotateY","rotateZ","scaleX","scaleY","scaleZ","visibility"]:
        cmds.setAttr(f"{movable_ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    cmds.setAttr(f"{movable_ctl}.alwaysDrawOnTop", 1) 

    dummy_body = cmds.createNode("transform", n="C_dummyBody_TRN", p=body_ctl) 
    cmds.parentConstraint(dummy_body, spine_hip_ctl_grp[0], mo=True) 

    localHip = cmds.duplicate(f"{side[0]}_{spine[0]}_{type[0]}", n=f"{side[0]}_localHip_{type[0]}", parentOnly=True)
    cmds.scaleConstraint(controls_tranforms[5], localHip) 
    localHip_end = cmds.duplicate(localHip, n=f"{side[0]}_localHipEnd_{type[0]}", parentOnly=True)
    cmds.parent(localHip_end, localHip) 
    cmds.move(0, 6, 0, localHip_end, relative=True)



    cmds.parentConstraint(spine_hip_ctl, localHip)

    cmds.setAttr(f"{ik_sc}.dTwistControlEnable", 1) 
    cmds.setAttr(f"{ik_sc}.dWorldUpType", 4)
    cmds.setAttr(f"{ik_sc}.dForwardAxis", 2)
    cmds.setAttr(f"{ik_sc}.dWorldUpAxis", 6)
    cmds.setAttr(f"{ik_sc}.dWorldUpVectorX", 1)
    cmds.setAttr(f"{ik_sc}.dWorldUpVectorY", 0)
    cmds.setAttr(f"{ik_sc}.dWorldUpVectorZ", 0)
    cmds.setAttr(f"{ik_sc}.dWorldUpVectorEndX", 1)
    cmds.setAttr(f"{ik_sc}.dWorldUpVectorEndY", 0)
    cmds.setAttr(f"{ik_sc}.dWorldUpVectorEndZ", 0)
    cmds.connectAttr(f"{spine_ctl[0]}.worldMatrix[0]", f"{ik_sc}.dWorldUpMatrix")
    cmds.connectAttr(f"{spine_ctl[2]}.worldMatrix[0]", f"{ik_sc}.dWorldUpMatrixEnd")

    settings_ctl, settings_ctl_grp, stretch_float_math =stretch_system(main_transforms, rig_transforms, controls_tranforms, spine, ik_curve, spine_module_trn)

    cmds.parentConstraint(spine_ctl[0], settings_ctl_grp[0], mo=True)    

    reversed_curve, reverse_chain = reverse_system(stretch_float_math, settings_ctl, main_transforms, rig_transforms, controls_tranforms, spine, ik_curve, spine_module_trn)
    offset_system(settings_ctl, ik_sc, reverse_chain, curve_shape, spine_module_trn)
    squash_factor_fml, spine_settings_trn = squash_system(spine, controls_tranforms,spine_module_trn, rig_transforms)
    squash_joints, spine_skinning_joints_trn = volume_preservation_system(settings_ctl, squash_factor_fml, spine_settings_trn, spine, spine_module_trn, controls_tranforms, rig_transforms, chest_fix)
    
    cmds.parent(localHip, spine_skinning_joints_trn) 

    return spine_hip_ctl, body_ctl, chest, squash_joints