import maya.cmds as cmds
import puiastreTools.tools.curve_tool as ctls_cre

class FingerModule(object):
    def __init__(self):
        self.main_finger = cmds.ls(sl=True)[0]
        self.finger_chain = cmds.listRelatives(self.main_finger, ad=True)
        self.finger_chain.append(self.main_finger)
        self.finger_chain.reverse()
        self.side = self.finger_chain[0].split("_")[0]
        self.name = self.finger_chain[0].split("_")[1]

        self.pairblends()
        self.add_controllers()

    def pairblends(self):

        
        count = 0
        for name in ["GRP", "SPC", "OFF", "SDK", "ANM", "CTL"]:
            if cmds.ls(f"{self.side}_settings{self.name}_{name}"):
                count += 1

        if count == 0:
            self.settings_ctl, self.settings_grp = ctls_cre.controller_creator(f"{self.side}_settings{self.name}")
            cmds.matchTransform(self.settings_grp[0], self.finger_chain[0])
            cmds.move(0, 100, 0, self.settings_grp[0], r=True, worldSpace=True)
            for attr in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "visibility"]:
                cmds.setAttr(f"{self.settings_ctl}.{attr}", lock=True, keyable=False, channelBox=False)

            cmds.addAttr(self.settings_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=1, keyable=True)
            cmds.addAttr(self.settings_ctl, shortName="curvatureSep", niceName="CURVATURE_____", enumName="_____",attributeType="enum", keyable=True)
            cmds.addAttr(self.settings_ctl, shortName="curvature", niceName="Curvature", maxValue=1, minValue=0,defaultValue=0, keyable=True)
            cmds.setAttr(self.settings_ctl+".curvatureSep", channelBox=True, lock=True)              

        else:
            self.settings_ctl = f"{self.side}settings_ctl"
            self.settings_grp = [f"{self.side}_settings_{name}" for name in ["GRP", "SPC", "OFF", "SDK", "ANM"]]

        

        self.ik_chain = []
        self.fk_chain = []
        for i, name in enumerate(["Fk", "Ik"]):
            dupe = cmds.duplicate(self.finger_chain, n=name)

            for j, joint in enumerate(dupe):
                self.name = self.finger_chain[j].split("_")[1]
                end_joint = cmds.rename(joint, self.side + "_" + self.name + name + "_JNT")

                if name == "Ik":
                    self.ik_chain.append(end_joint)
                elif name == "Fk":
                    self.fk_chain.append(end_joint)

        for i, joint in enumerate(self.ik_chain):
            pairblend = cmds.createNode("pairBlend", n=joint.replace("Ik_JNT", "_PBL"))
            cmds.connectAttr(joint + ".translate", pairblend + ".inTranslate1")
            cmds.connectAttr(joint + ".rotate", pairblend + ".inRotate1")
            cmds.connectAttr(self.fk_chain[i] + ".translate", pairblend + ".inTranslate2")
            cmds.connectAttr(self.fk_chain[i] + ".rotate", pairblend + ".inRotate2")
            cmds.connectAttr(pairblend + ".outTranslate", self.finger_chain[i] + ".translate")
            cmds.connectAttr(pairblend + ".outRotate", self.finger_chain[i] + ".rotate")
            cmds.connectAttr(self.settings_ctl + ".switchIkFk", pairblend + ".weight")

        self.ik_handle = cmds.ikHandle(sj=self.ik_chain[0], ee=self.ik_chain[-1], n=f"{self.side}_{self.name}_HDL", solver="ikRPsolver")
        


    def add_controllers(self):
        self.fk_ctls = []
        self.fk_ctls_grp = []

        for fk_joint in self.fk_chain:
            ctl, grp = ctls_cre.controller_creator(fk_joint.replace("_JNT", ""))
            cmds.matchTransform(grp[0], fk_joint)

            if self.fk_ctls:
                cmds.parent(grp[0], self.fk_ctls[-1])
            self.fk_ctls.append(ctl)
            self.fk_ctls_grp.append(grp)

            cmds.parentConstraint(ctl, fk_joint) ##### CANVIAR QUAN LA LAIA ACABI MATRIUS


        self.ik_ctls = []
        self.ik_ctls_grp = []

        for i, names in enumerate([self.name, f"{self.name}Pv", f"{self.name}Ik"]):
            ctl, grp = ctls_cre.controller_creator(f"{self.side}_{names}")
            cmds.matchTransform(grp[0], self.ik_chain[])

            



FingerModule()