"""
Arm system for the dragon wing.

"""

import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
import maya.mel as mel
import math
import os
from importlib import reload
reload(guides_manager)
reload(curve_tool)    

class WingArmModule(object):
    def __init__(self):
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "arm_guides_template_01.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "arm_ctl.json")
    
    def make(self, side):
        
        self.side = side

        self.module_trn = cmds.createNode("transform", n=f"{self.side}_wingArmModule_GRP")
        self.controllers_trn = cmds.createNode("transform", n=f"{self.side}_wingArmControllers_GRP")
        self.skinning_trn = cmds.createNode("transform", n=f"{self.side}_wingArmSkinningJoints_GRP", p=self.module_trn)

    def lock_attrs(self, ctl, attrs):
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def duplicate_guides(self):
        
        self.fk_chain = []
        self.ik_chain = []
        self.blend_chain = []

        chains = {
            "Fk": self.fk_chain,
            "Ik": self.ik_chain,
            "Blend": self.blend_chain
        }

        for name, chain in chains.items():
            guides = guides_manager.guide_import(
                joint_name=f"{self.side}_shoulder_JNT",
                all_descendents=True,
                filePath=self.guides_path
            )
            cmds.parent(guides[0], self.module_trn)

            for joint in guides:
                chain.append(cmds.rename(joint, joint.replace("_JNT", f"{name}_JNT")))

    def pair_blends(self):

        for i, joint in enumerate(self.blend_chain):
            
            self.pair_blend_node = cmds.createNode("pairBlend", n=f"{joint.replace("_JNT"), ("_PBL")}")
            cmds.connectAttr(f"{self.ik_chain[i]}.translate", f"{self.pair_blend_node}.inTranslate1")
            cmds.connectAttr(f"{self.fk_chain[i]}.translate", f"{self.pair_blend_node}.inTranslate2")
            cmds.connectAttr(f"{self.ik_chain[i]}.rotate", f"{self.pair_blend_node}.inRotate1")
            cmds.connectAttr(f"{self.fk_chain[i]}.rotate", f"{self.pair_blend_node}.inRotate2")
            cmds.connectAttr(f"{self.pair_blend_node}.outTranslate", f"{joint}.translate")
            cmds.connectAttr(f"{self.pair_blend_node}.outRotate", f"{joint}.rotate")



    def set_controllers(self):
        
        # --- FK/IK Switch Controller ---
        self.settings_curve_ctl, self.settings_curve_grp = curve_tool.controller_creator(f"{self.side}_ArmSettings", suffixes = ["GRP"])
        cmds.addAttr(self.settings_curve_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.matchTransform(self.settings_curve_grp[0], self.fk_chain[0], pos=True, rot=True)
        cmds.move(100, 0, 0, self.settings_curve_grp[0], r=True, os=True)
        
        self.arm_fk_controllers_trn = cmds.createNode("transform", n=f"{self.side}_wingArmFKControllers_GRP")
        self.arm_ik_controllers_trn = cmds.createNode("transform", n=f"{self.side}_wingArmIKControllers_GRP")

        reverse_vis = cmds.createNode("reverse", n=f"{self.side}_wingArmReverseVis_REV")
        cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{reverse_vis}.inputX")
        cmds.connectAttr(f"{reverse_vis}.outputX", f"{self.arm_ik_controllers_trn}.visibility")
        cmds.connectAttr(f"{self.settings_curve_ctl}.Switch IK --> FK", f"{self.arm_fk_controllers_trn}.visibility")
        cmds.parent(self.arm_fk_controllers_trn, self.arm_ik_controllers_trn, self.controllers_trn)


        # --- FK/IK Controllers ---
        self.arm_fk_controllers = []

        for i, joint in enumerate(self.fk_chain):
            ctl, grp = curve_tool.controller_creator(f"{self.side}_wingArm{i+1}Fk_CTL", suffixes=["GRP", "OFF"])
            cmds.parent(grp, self.arm_fk_controllers_trn)
            cmds.matchTransform(ctl, joint, pos=True, rot=True, scl=False)
            cmds.parentConstraint(ctl, joint, mo=False)
            self.lock_attrs(ctl, ["sx", "sy", "sz", "v"])
            if self.arm_fk_controllers:
                cmds.parent(grp, self.arm_fk_controllers[-1])
            self.arm_fk_controllers.append(grp)


        self.arm_ik_controllers = []

        self.root_ctl, self.root_grp = curve_tool.controller_creator(f"{self.side}_wingArmRoot", suffixes=["GRP", "OFF"])
        self.lock_attrs(self.root_ctl, ["sx", "sy", "sz", "v"])
        self.wrist_ik_ctl, self.wrist_ik_grp = curve_tool.controller_creator(f"{self.side}_wingArmWrist", suffixes=["GRP", "OFF"])
        self.lock_attrs(self.wrist_ik_ctl, ["sx", "sy", "sz", "v"])
        cmds.matchTransform(self.root_grp[0], self.ik_chain[0], pos=True, rot=True) 
        cmds.matchTransform(self.wrist_ik_grp[0], self.ik_chain[-1], pos=True, rot=True)
        cmds.parent(self.root_grp, self.wrist_ik_grp, self.arm_ik_controllers_trn)

            