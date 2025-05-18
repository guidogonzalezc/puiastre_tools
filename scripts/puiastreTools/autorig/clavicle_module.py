import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool 
import os
from importlib import reload
from puiastreTools.utils import data_export
from puiastreTools.utils import guides_manager
reload(guides_manager)
reload(curve_tool)    
reload(data_export)    

# FK CHAIN

class ClavicleModule():
    def __init__(self):
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "dragon_guides_template_01.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "template_curves_001.json") 

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")


    def make(self, side):

        self.side = side   

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_clavicleModule_GRP", ss=True, parent=self.modules_grp)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_clavicleSkinning_GRP", ss=True, p=self.skel_grp)

        self.clavicle_module()

    def clavicle_module(self):
        self.clavicle_joint = guides_manager.guide_import(
            joint_name=f"{self.side}_clavicle_JNT",
            all_descendents=False,
            filePath=self.guides_path
        )

        shoulder = guides_manager.guide_import(
            joint_name=f"{self.side}_shoulder_JNT",
            all_descendents=False,
            filePath=self.guides_path
        )


        armIk = self.data_exporter.get_data(f"{self.side}_armModule", "armIk") 
        ctl_switch = self.data_exporter.get_data(f"{self.side}_armModule", "armSettings") 
        spine_joints = self.data_exporter.get_data(f"spine", "lastSpineJnt") 

        cmds.parentConstraint(spine_joints, self.module_trn, mo=True)
        cmds.scaleConstraint(self.masterWalk_ctl, self.module_trn, mo=True)
        
        ctl_ik, created_grps = curve_tool.controller_creator(name=f"{self.side}_clavicleIk",  suffixes = ["GRP", "OFF"])
        cmds.parent(created_grps[0], self.masterWalk_ctl)
        cmds.matchTransform(created_grps[0], self.clavicle_joint)
        cmds.parentConstraint(ctl_ik, self.clavicle_joint, mo=False)
        cmds.parentConstraint(spine_joints, created_grps[0], mo=True)
        for attribute in ["scaleX","scaleY","scaleZ","visibility"]:
            cmds.setAttr(f"{ctl_ik}.{attribute}", lock=True, keyable=False, channelBox=False)




        ik_pos = cmds.xform(self.clavicle_joint, q=True, ws=True, t=True)
        armIk_pos = cmds.xform(shoulder, q=True, ws=True, t=True)
        distance = ((ik_pos[0] - armIk_pos[0]) ** 2 + (ik_pos[1] - armIk_pos[1]) ** 2 + (ik_pos[2] - armIk_pos[2]) ** 2) ** 0.5

        sphere = cmds.sphere(name=f'{self.side}_armAutoClavicleSlide_NRB', radius=distance, sections=4, startSweep=160)[0]
        cmds.delete(sphere, ch=True)
        cmds.parent(sphere, self.module_trn)
        cmds.matchTransform(sphere, self.clavicle_joint, rotation=False)
        if self.side == "L":
            cmds.rotate(-90,-90,0, sphere)
        elif self.side == "R":
            cmds.rotate(-90,90,0, sphere)
        
        locator = cmds.spaceLocator(name=f'{self.side}_armAutoClavicleSlide_LOC')
        cmds.parent(locator, self.module_trn)
        cmds.matchTransform(locator, shoulder, rotation=False)
        
        dupe = cmds.duplicate(locator, name=f'{self.side}_armAutoClavicleSlideReduced_LOC')
        cmds.pointConstraint(armIk, locator)
        cmds.geometryConstraint(sphere, locator)
        offset=cmds.createNode("transform", name=f"{self.side}_armAutoClavicleSlide_OFF")
        cmds.parent(offset, self.module_trn)
        cmds.matchTransform(offset, shoulder, rotation=False)
        cmds.parent(dupe, offset)
        constraint = cmds.parentConstraint(locator, offset, dupe, mo=True)
        cmds.setAttr(f"{constraint[0]}.{locator[0]}W0", 0.8)
        cmds.setAttr(f"{constraint[0]}.{offset}W1", 0.2)
        aim = cmds.aimConstraint(dupe, created_grps[1], aimVector=(1,0,0), upVector=(0,0,1), maintainOffset=True, worldUpType="objectrotation", worldUpVector=(0,0,1), wuo=spine_joints)

        cmds.addAttr(ctl_switch, shortName="autoClavicleIk", niceName="Auto Clavicle Ik", maxValue=1, minValue=0,defaultValue=0, keyable=True)

        cmds.connectAttr(f"{ctl_switch}.autoClavicleIk", f"{aim[0]}.{dupe[0]}W0")

        cmds.parent(self.clavicle_joint, self.skinning_trn)
        cmds.delete(shoulder)

        return ctl_ik