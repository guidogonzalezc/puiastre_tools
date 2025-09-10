#Python libraries import
from maya import cmds
from importlib import reload
import maya.api.OpenMaya as om
import math

# Local imports
from puiastreTools.utils.curve_tool import controller_creator
from puiastreTools.utils.guide_creation import guide_import
from puiastreTools.utils import data_export
from puiastreTools.utils import core
from puiastreTools.utils import basic_structure
from puiastreTools.utils import de_boor_core_002
from puiastreTools.utils.space_switch import fk_switch

reload(data_export)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}


class TailModule():
    """
    Class to create a spine module in a Maya rigging setup.
    This module handles the creation of spine joints, controllers, and various systems such as stretch, reverse, offset, squash, and volume preservation.
    """
    def __init__(self):
        """
        Initializes the SpineModule class, setting up paths and data exporters.
        
        Args:
            self: Instance of the SpineModule class.
        """
        
        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")


    def make(self, guide_name):
        """
        Creates the spine module, including the spine chain, controllers, and various systems.

        Args:
            self: Instance of the SpineModule class.
        """

        self.guide_name = guide_name

        self.primary_aim = "-z"
        self.primary_aim_vector = AXIS_VECTOR[self.primary_aim]
        self.secondary_aim = "y"
        self.secondary_aim_vector = AXIS_VECTOR[self.secondary_aim]

        self.side = self.guide_name.split("_")[0]

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_tailModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_tailControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_tailSkinning_GRP", ss=True, p=self.skel_grp)

        self.create_chain()
        self.create_controllers()

        self.data_exporter.append_data(f"{self.side}_tailModule", 
                            {"skinning_transform": self.skinning_trn,
                            # "body_ctl": self.body_ctl,
                            # "localHip": self.localHip_ctl,
                            # "localChest": self.localChest_ctl,
                            # "main_ctl" : self.localHip,
                            # "end_main_ctl" : self.localChest_ctl
                            }
                            )
    
    def create_chain(self):

        """
        pass
        """

        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)

        

    
    def create_controllers(self):

        """
        Create the controllers setup FK for the ribbon. Must create 7 controllers
        """

        aim_matrix = cmds.createNode("aimMatrix", name=self.guides[0].replace("_GUIDE", "_AMX"), ss=True)
        cmds.setAttr(f"{aim_matrix}.primaryInputAxis", *self.primary_aim_vector)
        cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", *self.secondary_aim_vector)
        cmds.connectAttr(f"{self.guides[0]}.worldMatrix[0]", f"{aim_matrix}.inputMatrix")
        cmds.connectAttr(f"{self.guides[-1]}.worldMatrix[0]", f"{aim_matrix}.primaryTargetMatrix")
        

        self.ctls = []
        self.nodes = []
        self.bendy_ctls = []
        self.bendy_nodes = []
        
        for i in range(7):

            ctl, ctl_grp = controller_creator(name=f"{self.side}_tail0{i}",suffixes=["GRP", "ANM"],lock=["scaleX", "scaleY", "scaleZ", "visibility"], ro=True) # Create controller
            # bendy_ctl, bendy_grp = controller_creator(name=f"{self.side}_tail0{i}Bendy",suffixes=["GRP", "ANM"],lock=["scaleX", "scaleY", "scaleZ", "visibility"], ro=True) # Create controller

            if self.ctls:
                cmds.parent(ctl_grp[0], self.ctls[-1]) # Parent the group to the last controller for FK behavior
                blend_matrix = cmds.createNode("blendMatrix", name=self.guides[0].replace("_GUIDE", "_BMX"), ss=True)
                cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
                cmds.setAttr(f"{blend_matrix}.target[0].rotateWeight", 0)
                cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{blend_matrix}.inputMatrix")
                cmds.connectAttr(f"{self.guides[-1]}.worldMatrix[0]", f"{blend_matrix}.target[0].targetMatrix")
                translate_weight = i / (7 - 1)
                cmds.setAttr(f"{blend_matrix}.target[0].translateWeight", translate_weight) # Set weight based on controller index to place it along the guides
                cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix") # Connect the controller to the blended matrix

            else:
                cmds.parent(ctl_grp[0], self.controllers_trn)
                cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix") # Connect the first controller to the guide

            # blend_matrix_bendy = cmds.createNode("blendMatrix", name=self.guides[0].replace("_GUIDE", "_BMX_Bendy"), ss=True)
            # cmds.setAttr(f"{blend_matrix_bendy}.target[0].scaleWeight", 0)
            # cmds.setAttr(f"{blend_matrix_bendy}.target[0].rotateWeight", 0)
            # cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{blend_matrix_bendy}.inputMatrix")
            # cmds.connectAttr(f"{self.guides[-1]}.worldMatrix[0]", f"{blend_matrix_bendy}.target[0].targetMatrix")
            # translate_weight_bendy = (i + 0.5) / (7 - 1)  # Bendy controllers are placed halfway between the main controllers
            # cmds.setAttr(f"{blend_matrix_bendy}.target[0].translateWeight", translate_weight_bendy) # Set weight based on controller index to place it along the guides
            # cmds.connectAttr(f"{blend_matrix_bendy}.outputMatrix", f"{bendy_grp[0]}.offsetParentMatrix") # Connect the bendy controller to the blended matrix
            # cmds.parent(bendy_grp[0], self.controllers_trn)

            self.ctls.append(ctl)
            self.nodes.append(ctl_grp)
            # self.bendy_ctls.append(bendy_ctl)
            # self.bendy_nodes.append(bendy_grp)

        self.num_joints = len(self.ctls) * 3
        self.old_joints = de_boor_core_002.de_boor_ribbon(aim_axis=self.primary_aim, up_axis=self.secondary_aim, cvs=self.ctls, num_joints=self.num_joints, name=f"{self.side}_tail", parent=self.skinning_trn)


# cmds.file(new=True, force=True)

# core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/test_03.guides")
# core.DataManager.set_ctls_data("H:/ggMayaAutorig/curves/body_template_01.ctls")

# basic_structure.create_basic_structure(asset_name="dragon")
# a = TailModule().make("C_tail01_GUIDE")

