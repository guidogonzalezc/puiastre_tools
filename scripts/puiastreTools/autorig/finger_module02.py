import maya.cmds as cmds
import puiastreTools.tools.curve_tool as ctls_cre

class FingerModule(object):

    def __init__(self, main_finger):
        self.main_finger = main_finger
        self.finger_chain = cmds.listRelatives(self.main_finger, ad=True)
        self.finger_chain.append(self.main_finger)
        self.finger_chain.reverse()
        self.side = self.finger_chain[0].split("_")[0]

        name = self.finger_chain[0].split("_")[1]
        self.controllers_grp = cmds.createNode("transform", n=f"{self.side}_{name}Controllers_GRP")
        self.module_grp = cmds.createNode("transform", n=f"{self.side}_{name}Module_GRP")
        self.skinning_joints_grp = cmds.createNode("transform", n=f"{self.side}_{name}SkinningJoints_GRP")


    def original_controllers(self):

        self.ctls_originals = []
        self.end = []
        for i, jnt in enumerate(self.finger_chain):
            name = jnt.split("_")[1]
            ctl = ctls_cre.controller_creator(name=f"{self.side}_{name}Main")
            
            cmds.parent(ctl[1][0], self.controllers_grp)
            cmds.matchTransform(ctl[1][0], jnt)

            
            cmds.select(clear=True)
            joint = cmds.joint(name = f"{self.side}_{name}BlendMain_JNT")
            cmds.parent(joint, self.module_grp)

            cmds.connectAttr(ctl[0] + ".worldMatrix[0]", joint + ".offsetParentMatrix")

            if self.ctls_originals:
                cmds.parent(ctl[1][0], self.ctls_originals[-1][0])

            self.ctls_originals.append(ctl)
            self.end.append(joint)

        self.fk_controllers()
        skinning_joints = self.controllers_move()
        return  skinning_joints


    def fk_controllers(self):

        self.ctls_grp = [] 
        self.ctls = []
        self.blend_joints = []
        for i, jnt in enumerate(self.finger_chain):
            name = jnt.split("_")[1]
            ctl = ctls_cre.controller_creator(name=f"{self.side}_{name}")
            self.ctls_grp.append(ctl[1][0])
            cmds.parent(ctl[1][0], self.controllers_grp)
            cmds.matchTransform(ctl[1][0], jnt)

            
            cmds.select(clear=True)
            joint = cmds.joint(name = f"{self.side}_{name}Blend_JNT")
            cmds.parent(joint, self.skinning_joints_grp)

            cmds.connectAttr(ctl[0] + ".worldMatrix[0]", joint + ".offsetParentMatrix")

            self.ctls.append(ctl)
            self.blend_joints.append(joint)
        
    
    def controllers_move(self):
        name = self.blend_joints[0].split("_")[1]
        points = [cmds.xform(jnt, q=True, ws=True, t=True) for jnt in self.finger_chain]
        curve = cmds.curve(d=1, p=points, name=f"{self.side}_{name}Main_CRV")
        cmds.rebuildCurve(curve, ch=True, rpo=True, rt=0, end=True, kr=False, kcp=False, kep=True, kt=False, s=11, d=3, tol=0.01)
        offset_crv = cmds.offsetCurve(curve, d=100, nr=[1, 0, 0], useGivenNormal=True , n=f"{self.side}_{name}Offset_CRV")[0]
        
        aim_trn_main = cmds.createNode("transform", n=f"{self.side}_{name}Aim_GRP")

        cmds.parent(curve, offset_crv, aim_trn_main, self.module_grp)


        mpas = []
        for i, ctl in enumerate(self.ctls):
            name = ctl[1][0].split("_")[1]
            decompose = cmds.createNode("decomposeMatrix", name=f"{self.side}_{name}_DCM")
            cmds.connectAttr(f"{ctl[1][0]}.worldMatrix[0]", f"{decompose}.inputMatrix")
            nearest_point = cmds.createNode("nearestPointOnCurve", name=f"{self.side}_{name}_NPC")
            cmds.connectAttr(f"{curve}.worldSpace[0]", f"{nearest_point}.inputCurve")
            cmds.connectAttr(f"{decompose}.outputTranslate", f"{nearest_point}.inPosition")
            parameter = cmds.getAttr(f"{nearest_point}.parameter")

            cmds.delete(nearest_point, decompose)

            mpas.append(cmds.createNode("motionPath", name=f"{self.side}_{name}_MPA"))
            cmds.setAttr(f"{mpas[i]}.uValue", parameter)
            cmds.connectAttr(f"{curve}.worldSpace[0]", f"{mpas[i]}.geometryPath")
            cmds.connectAttr(f"{mpas[i]}.allCoordinates", f"{ctl[1][0]}.translate")


        parameters = [cmds.getAttr(f"{mpa}.uValue") for mpa in mpas]

        bendy_joints = []
        ctls_bendy_grp =[]
        mpas_bendys = []
        for i in range(0, len(parameters)-1):
            distance_value = parameters[i+1] - parameters[i]
            distance_value = distance_value / 4
            
            for j in range(1, 4):
                name = self.blend_joints[i].split("_")[1]
                mpa = cmds.createNode("motionPath", name=f"{self.side}_{name}0{j}_MPA")
                mpas_bendys.append(mpa)
                cmds.setAttr(f"{mpa}.uValue", parameters[i] + (distance_value * j))
                cmds.connectAttr(f"{curve}.worldSpace[0]", f"{mpa}.geometryPath")
                
                
                ctl, ctl_grp = ctls_cre.controller_creator(name=f"{self.side}_{name}Bendy0{j}")
                ctls_bendy_grp.append(ctl_grp[0])
                cmds.parent(ctl_grp[0], self.controllers_grp)

                cmds.connectAttr(f"{mpa}.allCoordinates", f"{ctl_grp[0]}.translate")

                cmds.select(clear=True)
                joint = cmds.joint(name = f"{self.side}_{name}Bendy0{j}_JNT")
                cmds.parent(joint, self.skinning_joints_grp)
                cmds.connectAttr(ctl + ".worldMatrix[0]", joint + ".offsetParentMatrix")

                bendy_joints.append(joint)



        cmds.skinCluster(self.end, curve, tsb=True)

        
        
        skinning_joints = []
        end_mpas = []
        grps = []
        for i in range(0, len(self.blend_joints)-1):
            skinning_joints.append(self.blend_joints[i])
            skinning_joints.append(bendy_joints[i*3])
            skinning_joints.append(bendy_joints[(i*3)+1])
            skinning_joints.append(bendy_joints[(i*3)+2])

            end_mpas.append(mpas[i])
            end_mpas.append(mpas_bendys[i*3])
            end_mpas.append(mpas_bendys[(i*3)+1])
            end_mpas.append(mpas_bendys[(i*3)+2])

            grps.append(self.ctls_grp[i])
            grps.append(ctls_bendy_grp[i*3])
            grps.append(ctls_bendy_grp[(i*3)+1])
            grps.append(ctls_bendy_grp[(i*3)+2])
            
        skinning_joints.append(self.blend_joints[-1])
        end_mpas.append(mpas[-1])
        grps.append(self.ctls_grp[-1])

        aimer_trn = []
        for i, joint in enumerate(skinning_joints):
            parameter = cmds.getAttr(end_mpas[i] + ".uValue")
            name = joint.split("_")[1]
            aim_trn = cmds.createNode("transform", n=f"{self.side}_{name}Aim_TRN", parent=aim_trn_main)
            
            mpa_offset = cmds.createNode("motionPath", n=f"{self.side}_{name}0{j}Offset_MPA")
            cmds.setAttr(mpa_offset + ".uValue", parameter)
            cmds.connectAttr(offset_crv + ".worldSpace", mpa_offset + ".geometryPath")
            cmds.connectAttr(mpa_offset + ".allCoordinates", aim_trn + ".translate")        

            if i == len(parameters)-2:
                aim_helper = cmds.createNode("transform", n=f"{self.side}_{name}AimHelper_TRN", p=aim_trn_main)
                cmds.connectAttr(mpa + ".allCoordinates", aim_helper + ".translate") 

            aimer_trn.append(aim_trn)
        for i, joint in enumerate(skinning_joints):  # Iterate through all skinning joints
            name = joint.split("_")[1]
            if i < len(skinning_joints) - 1:  # If not the last joint
                aim_constraint = cmds.aimConstraint(
                    skinning_joints[i + 1],  # Parent: the next skinning joint
                    grps[i],  # Child: the _grp of the controller
                    aimVector=[1, 0, 0],
                    upVector=[0, 1, 0],
                    worldUpType="objectrotation",
                    worldUpVector=[0, 1, 0],
                    worldUpObject=aimer_trn[i]  # World up object: the aim_trn
                )
            else:  # If it's the last joint
                aim_constraint = cmds.aimConstraint(
                    aim_helper,  # Parent: the aim_helper_trn
                    grps[i],  # Child: the _grp of the controller
                    aimVector=[-1, 0, 0],  # Reverse aim vector
                    upVector=[0, 1, 0],
                    worldUpType="objectrotation",
                    worldUpVector=[0, 1, 0],
                    worldUpObject=aimer_trn[i]  # World up object: the aim_trn
                )
                



        return skinning_joints

joints = ["L_ring01_JNT", "L_pinky01_JNT", "L_middle01_JNT", "L_index01_JNT", "L_thumb01_JNT"]

fingers_skinning_joints = []
for joint in joints:
    fingers = FingerModule(joint)
    skinning = fingers.original_controllers()
    fingers_skinning_joints.append(skinning)

#add wing curvature


for i in range(0, len(fingers_skinning_joints)-1):
    name = fingers_skinning_joints[i][0].split("_")[1]
    side = fingers_skinning_joints[i][0].split("_")[0]  
    skinning_joints_trn = cmds.createNode("transform", n=f"{side}_{name}PushSkinningJoints_GRP")
    push_joints_module = cmds.createNode("transform", n=f"{side}_{name}PushModule_GRP")
    trn_settings = cmds.createNode("transform", n=f"{side}_{name}Settings_TRN", p=push_joints_module)

    for j, joint in enumerate(fingers_skinning_joints[i][1:]):  # Skip the first joint
        name = joint.split("_")[1]
        
        cmds.addAttr(trn_settings, longName=f"WingSpacing{j+2}", attributeType="float", min=0, max=0.3 + (j * 0.1), defaultValue=0.3 + (j * 0.1), keyable=True) 

        cmds.select(clear=True)
        joint_parent = cmds.joint(name = f"{side}_{name}PushPoint_JNT")
        joint_child = cmds.joint(name = f"{side}_{name}Push_JNT")   
        cmds.parent(joint_parent, push_joints_module)

        cmds.select(clear=True)
        skin_joint = cmds.joint(name = f"{side}_{name}PushSkin_JNT")
        cmds.parent(skin_joint, skinning_joints_trn)
        cmds.connectAttr(joint_child + ".worldMatrix[0]", skin_joint + ".offsetParentMatrix")

        wtadd = cmds.createNode("wtAddMatrix", n=f"{side}_{name}Push_WTAM")

        cmds.connectAttr(fingers_skinning_joints[i][j+1] + ".worldMatrix[0]", wtadd + ".wtMatrix[0].matrixIn")
        cmds.connectAttr(fingers_skinning_joints[i+1][j+1] + ".worldMatrix[0]", wtadd + ".wtMatrix[1].matrixIn")
        cmds.setAttr(wtadd + ".wtMatrix[0].weightIn", 0.5)
        cmds.setAttr(wtadd + ".wtMatrix[1].weightIn", 0.5)

        cmds.connectAttr(wtadd + ".matrixSum", joint_parent + ".offsetParentMatrix")

        distance = cmds.createNode("distanceBetween", n=f"{side}_{name}_DBT")
        distance_factor = cmds.createNode("floatMath", n=f"{side}_{name}DistanceFactor_FLM")
        distanceMultiplied = cmds.createNode("floatMath", n=f"{side}_{name}DistanceMultiplied_FLM")
        distanceMultipliedNegate = cmds.createNode("floatMath", n=f"{side}_{name}DistanceMultipliedNegate_FLM")
        condition = cmds.createNode("condition", n=f"{side}_{name}Condition_CON")


        operation_values = [1, 2, 2, 5]
        for k, value in enumerate([distance_factor, distanceMultiplied, distanceMultipliedNegate, condition]):
            cmds.setAttr(value + f".operation", operation_values[k])

        cmds.connectAttr(fingers_skinning_joints[i][j+1] + ".worldMatrix[0]", distance + ".inMatrix1")
        cmds.connectAttr(fingers_skinning_joints[i+1][j+1] + ".worldMatrix[0]", distance + ".inMatrix2")

        distance_value = cmds.getAttr(distance + ".distance")

        cmds.setAttr(distance_factor + ".floatA", distance_value)
        cmds.connectAttr(distance + ".distance", distance_factor + ".floatB")

        cmds.connectAttr(trn_settings + f".WingSpacing{j+2}", distanceMultiplied + ".floatB")
        cmds.connectAttr(distance_factor + ".outFloat", distanceMultiplied + ".floatA")
        cmds.connectAttr(distanceMultiplied + ".outFloat", distanceMultipliedNegate + ".floatA")
        cmds.setAttr(distanceMultipliedNegate + ".floatB", -1)

        cmds.setAttr(condition + ".secondTerm", distance_value)
        cmds.connectAttr(distance + ".distance", condition + ".firstTerm")
        cmds.connectAttr(distanceMultipliedNegate + ".outFloat", condition + ".colorIfTrueR")
        cmds.setAttr(condition + ".colorIfFalseR", 0)

        cmds.connectAttr(condition + ".outColorR", joint_child + ".translateY")

        

        