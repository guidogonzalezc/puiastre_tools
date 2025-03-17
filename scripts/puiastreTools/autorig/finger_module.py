import maya.cmds as cmds
import puiastreTools.tools.curve_tool as ctls_cre

class FingerModule(object):
    def __init__(self):
        self.main_finger = cmds.ls(sl=True)[0]
        self.finger_chain = cmds.listRelatives(self.main_finger, ad=True)
        self.finger_chain.append(self.main_finger)
        self.finger_chain.reverse()
        self.side = self.finger_chain[0].split("_")[0]

        self.fk_controllers()
        self.bendy_finger()


    def fk_controllers(self):

        self.ctls = []
        self.blend_joints = []
        for i, jnt in enumerate(self.finger_chain):
            name = jnt.split("_")[1]
            ctl = ctls_cre.controller_creator(name=f"{self.side}_{name}")
            cmds.matchTransform(ctl[1][0], jnt)

            
            cmds.select(clear=True)
            joint = cmds.joint(name = f"{self.side}_{name}Blend_JNT")

            cmds.connectAttr(ctl[0] + ".worldMatrix[0]", joint + ".offsetParentMatrix")

            if self.ctls:
                cmds.parent(ctl[1][0], self.ctls[-1][0])

            self.ctls.append(ctl)
            self.blend_joints.append(joint)
        
    
    def bendy_finger(self):

        self.bendy_joints = []
        for i in range(3):
            name = self.blend_joints[i].split("_")[1]

            cmds.select(clear=True)
            bendy_pos_joint = cmds.joint(name=f"{self.side}_{name}BendyPos_JNT")
            wtAdd = cmds.createNode("wtAddMatrix", name=f"{self.side}_{name}Bendy_WAM", ss=True)
            cmds.connectAttr(f"{self.blend_joints[i]}.worldMatrix[0]", f"{wtAdd}.wtMatrix[0].matrixIn")
            cmds.connectAttr(f"{self.blend_joints[i+1]}.worldMatrix[0]", f"{wtAdd}.wtMatrix[1].matrixIn")
            cmds.setAttr(f"{wtAdd}.wtMatrix[0].weightIn", 0.5)
            cmds.setAttr(f"{wtAdd}.wtMatrix[1].weightIn", 0.5)

            aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{name}Bendy_AIM", ss=True)
            cmds.connectAttr(f"{wtAdd}.matrixSum", aim_matrix + ".inputMatrix")
            cmds.connectAttr(f"{self.blend_joints[i+1]}.worldMatrix[0]", aim_matrix + ".primaryTargetMatrix")
            cmds.setAttr(f"{aim_matrix}.primaryInputAxis", 1, 0, 0)
            

            cmds.connectAttr(aim_matrix + ".outputMatrix", bendy_pos_joint + ".offsetParentMatrix")

            self.bendy_joints.append(bendy_pos_joint)

        bendy_chain = [self.blend_joints[0], self.bendy_joints[0], self.blend_joints[1], self.bendy_joints[1], self.blend_joints[2], self.bendy_joints[2], self.blend_joints[3]]
        positions = [cmds.xform(jnt, q=True, ws=True, t=True) for jnt in bendy_chain]
        bendy_curve = cmds.curve(d=1, p=positions, name=f"{self.side}_Bendy_CRV")

        cmds.select(bendy_curve)
        cmds.nurbsCurveToBezier()

        cmds.select(f"{bendy_curve}.cv[0]",f"{bendy_curve}.cv[1]",f"{bendy_curve}.cv[5]",f"{bendy_curve}.cv[6]",f"{bendy_curve}.cv[7]",f"{bendy_curve}.cv[11]",f"{bendy_curve}.cv[12]",f"{bendy_curve}.cv[13]",f"{bendy_curve}.cv[17]",f"{bendy_curve}.cv[18]", r=True)
        cmds.bezierAnchorPreset(preset=2)
        cmds.select(f"{bendy_curve}.cv[2]",f"{bendy_curve}.cv[3]",f"{bendy_curve}.cv[4]",f"{bendy_curve}.cv[8]",f"{bendy_curve}.cv[9]",f"{bendy_curve}.cv[10]",f"{bendy_curve}.cv[14]",f"{bendy_curve}.cv[15]",f"{bendy_curve}.cv[16]", r=True)
        cmds.bezierAnchorPreset(preset=1)
        cmds.bezierAnchorState(smooth=True, even=True)

        skin_cluster = cmds.skinCluster(bendy_chain, bendy_curve, tsb=True)


        cmds.curve



FingerModule()