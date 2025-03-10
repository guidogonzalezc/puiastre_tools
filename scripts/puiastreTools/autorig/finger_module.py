import maya.cmds as cmds
import puiastreTools.tools.curve_tool as ctls_cre

class FingerModule(object):
    def __init__(self):
        self.main_finger = cmds.ls(sl=True)[0]
        self.finger_chain = cmds.listRelatives(self.main_finger, ad=True)
        self.finger_chain.append(self.main_finger)
        self.finger_chain.reverse()

        self.pairblends()

    def pairblends(self):
        
        ik_chain = []
        fk_chain = []
        for i, name in enumerate(["Fk", "Ik"]):
            dupe = cmds.duplicate(self.finger_chain, n=name)

            for j, joint in enumerate(dupe):
                self.side = self.finger_chain[j].split("_")[0]
                self.name = self.finger_chain[j].split("_")[1]
                end_joint = cmds.rename(joint, self.side + "_" + self.name + name + "_JNT")

                if name == "Ik":
                    ik_chain.append(end_joint)
                elif name == "Fk":
                    fk_chain.append(end_joint)

        for i, joint in enumerate(ik_chain):
            pairblend = cmds.createNode("pairBlend", n=joint.replace("Ik_JNT", "_PBL"))
            cmds.connectAttr(joint + ".translate", pairblend + ".inTranslate1")
            cmds.connectAttr(joint + ".rotate", pairblend + ".inRotate1")
            cmds.connectAttr(fk_chain[i] + ".translate", pairblend + ".inTranslate2")
            cmds.connectAttr(fk_chain[i] + ".rotate", pairblend + ".inRotate2")
            cmds.connectAttr(pairblend + ".outTranslate", self.finger_chain[i] + ".translate")
            cmds.connectAttr(pairblend + ".outRotate", self.finger_chain[i] + ".rotate")
FingerModule()