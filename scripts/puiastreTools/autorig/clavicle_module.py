import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool 
from importlib import reload
from puiastreTools.utils import data_export
from puiastreTools.utils import guides_manager  
reload(data_export)    


class ClavicleModule():
    """
    Class to create a clavicle module in a Maya rigging setup.
    This module handles the creation of clavicle joints, controllers, and constraints.

    """
    def __init__(self):
        """
        Initializes the ClavicleModule class, setting up paths and data exporters.

        Args:
            self: Instance of the ClavicleModule class.
        """

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")


    def make(self, side):
        """
        Creates the clavicle module for the specified side (left or right).

        Args:
            side (str): The side for which to create the clavicle module. Should be either "L" or "R".
        """

        self.side = side   

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_clavicleModule_GRP", ss=True, parent=self.modules_grp)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_clavicleSkinning_GRP", ss=True, p=self.skel_grp)

        self.clavicle_module()

        data_exporter = data_export.DataExport()
        data_exporter.append_data(
            f"{self.side}_clavicleModule",
            {
                "clavicle_ctl": self.ctl_ik,
            }
        )
    def lock_attr(self, ctl, attrs = ["scaleX", "scaleY", "scaleZ", "visibility"], ro=True):
        """
        Lock specified attributes of a controller, added rotate order attribute if ro is True.
        
        Args:
            ctl (str): The name of the controller to lock attributes on.
            attrs (list): List of attributes to lock. Default is ["scaleX", "scaleY", "scaleZ", "visibility"].
            ro (bool): If True, adds a rotate order attribute. Default is True.
        """

        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", keyable=False, channelBox=False, lock=True)
        
        if ro:
            cmds.addAttr(ctl, longName="rotate_order", nn="Rotate Order", attributeType="enum", enumName="xyz:yzx:zxy:xzy:yxz:zyx", keyable=True)
            cmds.connectAttr(f"{ctl}.rotate_order", f"{ctl}.rotateOrder")

    def clavicle_module(self):
        """
        Creates the clavicle module by importing guides, creating controllers, and setting up constraints.

        Args:
            self: Instance of the ClavicleModule class.
        """
        self.clavicle_joint = guides_manager.guide_import(
            joint_name=f"{self.side}_clavicle_JNT",
            all_descendents=False)

        shoulder = guides_manager.guide_import(
            joint_name=f"{self.side}_shoulder_JNT",
            all_descendents=False)


        armIk = self.data_exporter.get_data(f"{self.side}_armModule", "armIk") 
        ctl_switch = self.data_exporter.get_data(f"{self.side}_armModule", "armSettings") 
        spine_joints = self.data_exporter.get_data(f"C_spineModule", "lastSpineJnt") 

        cmds.parentConstraint(spine_joints, self.module_trn, mo=True)
        cmds.scaleConstraint(self.masterWalk_ctl, self.module_trn, mo=True)
        
        self.ctl_ik, created_grps = curve_tool.controller_creator(name=f"{self.side}_clavicle",  suffixes = ["GRP", "OFF"])
        cmds.parent(created_grps[0], self.masterWalk_ctl)
        cmds.matchTransform(created_grps[0], self.clavicle_joint)
        cmds.parentConstraint(self.ctl_ik, self.clavicle_joint, mo=False)
        self.lock_attr(self.ctl_ik)




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
