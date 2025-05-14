"""
Finger module for dragon rigging system
"""
import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import data_export
import os
from importlib import reload
reload(guides_manager)
reload(curve_tool)    
reload(data_export)    

class SpineModule():
    def __init__(self):
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "dragon_guides_template_01.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "template_curves_001.json") 

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")


    def make(self):

        self.module_trn = cmds.createNode("transform", name=f"C_spineModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"C_spineControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"C_spineSkinning_GRP", ss=True, p=self.skel_grp)

        self.create_chain()
        self.spine_module()

    def lock_attr(self, ctl, attrs = ["scaleX", "scaleY", "scaleZ", "visibility"]):
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", keyable=False, channelBox=False, lock=True)

    def create_chain(self):
        
        self.blend_chain = guides_manager.guide_import(
            joint_name=f"C_spine01_JNT",
            all_descendents=True,
            filePath=self.guides_path
        )
        cmds.parent(self.blend_chain[0], self.module_trn)

    def spine_module(self):
        positions = [cmds.xform(joint, query=True, worldSpace=True, translation=True) for joint in (self.blend_chain[0], self.blend_chain[-1])]
        ik_curve = cmds.curve(degree=1, point=positions, name="C_spine_CRV")
        cmds.rebuildCurve(ik_curve, rpo=True, rt=0, end=True, kr=False, kcp=False, kep=True, kt=True, fr=False, s=1, d=2, tol=0.01)
        cmds.delete(ik_curve, ch=True)
        ik_sc = cmds.ikHandle(sj=self.blend_chain[0], ee=self.blend_chain[-1], sol="ikSplineSolver", n="C_spine_HDL", curve=ik_curve, createCurve=False, parentCurve=False) [0]# Create an IK spline handle using the existing ik_curve
        curve_shape = cmds.listRelatives(ik_curve, shapes=True)[0]

        cmds.parent(ik_curve, ik_sc, self.module_trn) 

        self.spine_ctl = []
        self.spine_grp = []

        for i in range(1, 4):
            if i == 1 or i == 3:
                ctl, ctl_grp = curve_tool.controller_creator(f"C_spine0{i}", suffixes = ["GRP"])
            else:
                ctl, ctl_grp = curve_tool.controller_creator(f"C_spineTan", suffixes = ["GRP", "SPC"])
                cmds.addAttr(ctl, shortName="spaceSwitchSep", niceName="spaceSwitch_____", enumName="_____",attributeType="enum", keyable=True)
                cmds.setAttr(ctl+".spaceSwitchSep", channelBox=True, lock=True)
                cmds.addAttr(ctl, shortName="spineFollow", niceName="Spine Follow", maxValue=1, minValue=0, defaultValue=0, keyable=True)

            cmds.parent(ctl_grp[0], self.controllers_trn)

            self.lock_attr(ctl)

            cv_point = cmds.pointPosition(f"{curve_shape}.cv[{i-1}]", w=True)
            cmds.xform(ctl_grp, ws=True, translation=cv_point)

            self.spine_ctl.append(ctl) 
            self.spine_grp.append(ctl_grp) 

            dcm = cmds.createNode("decomposeMatrix", n=f"C_spine0{i}_DCM") 
            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{dcm}.inputMatrix")
            cmds.connectAttr(f"{dcm}.outputTranslate", f"{curve_shape}.controlPoints[{i-1}]")

        parent = cmds.parentConstraint(self.spine_ctl[0], self.spine_ctl[2], self.spine_grp[1][1], mo=True)[0]

        cmds.connectAttr(f"{self.spine_ctl[1]}.spineFollow", f"{parent}.{self.spine_ctl[0]}W0")
        rev = cmds.createNode("reverse", n="C_spineRev")
        cmds.connectAttr(f"{self.spine_ctl[1]}.spineFollow", f"{rev}.inputX")
        cmds.connectAttr(f"{rev}.outputX", f"{parent}.{self.spine_ctl[2]}W1")

        chest_fix = cmds.joint(name = "C_localChest_JNT")
        cmds.delete(cmds.parentConstraint(self.spine_ctl[-1], chest_fix, mo=False))
        cmds.parent(chest_fix, self.spine_module)
        localChest_ctl, localChest_grp = curve_tool.controller_creator(f"C_localChest", suffixes = ["GRP", "SPC"])
        cmds.pointConstraint(self.blend_chain[-1], localChest_grp[0], mo=False)
        cmds.orientConstraint(spine_ctl[2], localChest_grp[0], mo=False)
        cmds.parentConstraint(localChest_ctl, chest_fix, mo=True)
        cmds.parent(localChest_grp[0], controls_tranforms[5])