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
       
        positions = [cmds.xform(jnt, q=True, ws=True, t=True) for jnt in self.blend_joints]
        linear_curve = cmds.curve(name=f"{self.side}_linear_CRV", d=1, p=positions)

        detached01 = cmds.detachCurve( f'{linear_curve}.u[{1}]', ch=True, replaceOriginal=False)
        detached02 = cmds.detachCurve( f'{detached01[1]}.u[{2}]', ch=True, replaceOriginal=True)

        for cv in range(len(positions)):
            name = self.blend_joints[cv].split("_")[1]
            dcpm = cmds.createNode("decomposeMatrix", name=f"{self.side}_{name}0{cv+1}_DCM")
            cmds.connectAttr(f"{self.blend_joints[cv]}.worldMatrix[0]", f"{dcpm}.inputMatrix")
            cmds.connectAttr(f"{dcpm}.outputTranslate", f"{linear_curve}.controlPoints[{cv}]")

        self.bendy_curves = []
        for i, curve in enumerate([detached01[0], detached01[1], detached02[0]]):
            name = self.blend_joints[i].split("_")[1]
            renamed = cmds.rename(curve, f"{self.side}_{self.blend_joints[i].split('_')[1]}0_CRV")

            cmds.select(clear=True)
            bendy_pos_joint = cmds.joint(name=f"{self.side}_{name}BendyPos_JNT")
            wtAdd = cmds.createNode("wtAddMatrix", name=f"{self.side}_{name}Bendy_WAM", ss=True)
            cmds.connectAttr(f"{self.blend_joints[i]}.worldMatrix[0]", f"{wtAdd}.wtMatrix[0].matrixIn")
            cmds.connectAttr(f"{self.blend_joints[i+1]}.worldMatrix[0]", f"{wtAdd}.wtMatrix[1].matrixIn")

            pickMatrix = cmds.createNode("pickMatrix", name=f"{self.side}_{name}Bendy_PM", ss=True)
            cmds.connectAttr(f"{wtAdd}.matrixSum", f"{pickMatrix}.inputMatrix")
            cmds.setAttr(f"{wtAdd}.wtMatrix[0].weightIn", 0.5)
            cmds.setAttr(f"{wtAdd}.wtMatrix[1].weightIn", 0.5)
            for attr in ["useRotate", "useScale", "useShear"]:
                cmds.setAttr(f"{pickMatrix}.{attr}", 0)

            aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{name}Bendy_AIM", ss=True)
            cmds.connectAttr(f"{pickMatrix}.outputMatrix", aim_matrix + ".inputMatrix")
            cmds.connectAttr(f"{self.blend_joints[i+1]}.worldMatrix[0]", aim_matrix + ".primaryTargetMatrix")
            cmds.setAttr(f"{aim_matrix}.primaryInputAxis", 1, 0, 0)

            cmds.connectAttr(aim_matrix + ".outputMatrix", bendy_pos_joint + ".offsetParentMatrix")
        
            cmds.rebuildCurve(renamed, ch=True, rpo=True, rt=0, end=True, kr=False, kcp=False, kep=True, kt=True, fr=False, s=2, d=1, tol=0.01)
            cmds.delete(renamed, ch=True)

            cmds.select(renamed, r=True)
            cmds.nurbsCurveToBezier()
            cmds.select(renamed + ".cv[0]", renamed + ".cv[1]", renamed + ".cv[5]", renamed + ".cv[6]", r=True)
            cmds.bezierAnchorPreset(preset=2)
            cmds.select(renamed + ".cv[2]", renamed + ".cv[3]", renamed + ".cv[4]", r=True)
            cmds.bezierAnchorPreset(preset=1)
            cmds.bezierAnchorState(smooth=True, even=True)

            self.bendy_curves.append(renamed)

            bendy_joints = []
            for names in ["Root", "Mid", "Hook"]:
                cmds.select(clear=True)
                bendy_joints.append(cmds.joint(name=f"{self.side}_{name}{names}_JNT"))


            bendy_ctl = ctls_cre.controller_creator(name=f"{self.side}_{name}Bendy")
            cmds.connectAttr(bendy_pos_joint + ".worldMatrix[0]", bendy_ctl[1][0] + ".offsetParentMatrix")

            cmds.connectAttr(f"{self.blend_joints[i]}.worldMatrix[0]", bendy_joints[0] + ".offsetParentMatrix")
            cmds.connectAttr(f"{self.blend_joints[i+1]}.worldMatrix[0]", bendy_joints[2] + ".offsetParentMatrix")
            cmds.connectAttr(bendy_ctl[0] + ".worldMatrix[0]", bendy_joints[1] + ".offsetParentMatrix")

            skin = cmds.skinCluster(bendy_joints, renamed, n=f"{self.side}_{name}_SKN")[0]    

            cmds.skinPercent(skin, renamed + ".cv[2]", tv=(bendy_joints[1], 1))
            cmds.skinPercent(skin, renamed + ".cv[4]", tv=(bendy_joints[1], 1))

            off_curve = cmds.offsetCurve(renamed, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=50, tol=0.01, sd=0, ugn=False, name=f"{self.side}_{name}Offset_CRV")

            cmds.setAttr(f"{off_curve[1]}.useGivenNormal", 1)
            cmds.setAttr(f"{off_curve[1]}.normal", 0,0,1)

            cmds.setAttr(off_curve[1] + ".normal", 1, 0 , 0)

            # for i in range(5):





FingerModule()