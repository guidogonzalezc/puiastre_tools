"""
FK module for dragon rigging system
"""
import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import data_export
from importlib import reload
reload(data_export)  

class FKModule():
    def __init__(self):
        """
        Initialize the leg module, setting up paths and basic structure.
        
        Args:
            self: The instance of the LegModule class.
        """
        data_exporter = data_export.DataExport()

        self.modules_grp = data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = data_exporter.get_data("basic_structure", "masterWalk_CTL")

    def make(self, chain):

        name = chain.replace("_JNT", "")
        self.chain = chain

        self.controllers_trn = cmds.createNode("transform", name=f"{name}Controllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{name}Skinning_GRP", ss=True, parent=self.skel_grp)

        ctl = self.duplicate_leg()
        return ctl

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


    def duplicate_leg(self):
        """
        Duplicate the leg guides and create the necessary joint chains for IK, FK, and blending.
        
        Args:
            self: The instance of the LegModule class.
        """

        self.fk_chain = []


        guides = guides_manager.guide_import(
            joint_name=self.chain,
            all_descendents=True)

        grps = []
        ctls = []
        for guide in guides:    
            cmds.parent(guide, self.skinning_trn)
        for guide in guides:
            guide_name = guide.replace("_JNT", "")
            ctl, grp = curve_tool.controller_creator(guide_name, suffixes = ["GRP"])
            self.lock_attr(ctl)

            if ctls:
                cmds.parent(grp[0], ctls[-1])
            
            else:
                cmds.parent(grp[0], self.controllers_trn)

            cmds.matchTransform(grp[0], guide)

            for attr in ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ", "jointOrientX", "jointOrientY", "jointOrientZ"]:
                cmds.setAttr(f"{guide}.{attr}", 0)

            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{guide}.offsetParentMatrix", force=True)

            grps.append(grp)
            ctls.append(ctl)

        return ctls[0]
            

