import maya.cmds as cmds
import maya.api.OpenMaya as om
from importlib import reload
import os
import math

from puiastreTools.utils import data_export
from puiastreTools.utils import guide_creation
from puiastreTools.utils import curve_tool
from puiastreTools.utils import basic_structure
from puiastreTools.utils import core
from puiastreTools.utils import guide_creation

import puiastreTools.utils.de_boor_core_002 as de_boors_002

reload(data_export)
reload(guide_creation)
reload(curve_tool)

reload(de_boors_002)
reload(basic_structure)
reload(core)
reload(guide_creation)

class EyelidModule(object):

    def __init__(self, guide_name):

        """
        Initialize the eyelidModule class, setting up the necessary groups and controllers.
        """
        self.side = guide_name.split("_")[0]
        self.modules = data_export.DataExport().get_data("basic_structure", "modules_GRP")
        self.skel_grp = data_export.DataExport().get_data("basic_structure", "skel_GRP")
        self.masterwalk_ctl = data_export.DataExport().get_data("basic_structure", "masterwalk_ctl")
        # self.head_ctl = data_export.DataExport().get_data("neck_module", "head_ctl")
        self.guides_grp = data_export.DataExport().get_data("basic_structure", "guides_GRP")
        self.guides = guide_creation.guide_import(guide_name, all_descendents=True, path=None)
        self.upper_guides = [guide for guide in self.guides if "Up" in guide]
        self.lower_guides = [guide for guide in self.guides if "Down" in guide]

    def make(self):

        """ 
        Create the eyelid module structure and controllers. Call this method with the side ('L' or 'R') to create the respective eyelid module.
        Args:
            side (str): The side of the eyelid ('L' or 'R').

        """
        
        self.module_name = f"{self.side}_eyelid"
        self.module_trn = cmds.createNode("transform", name=f"{self.module_name}Module_GRP", ss=True, p=self.modules)
        cmds.setAttr(f"{self.module_trn}.inheritsTransform", 0)
        self.skeleton_grp = cmds.createNode("transform", name=f"{self.module_name}Skinning_GRP", ss=True, p=self.skel_grp)
        self.controllers_grp = cmds.createNode("transform", name=f"{self.module_name}Controllers_GRP", ss=True)

    

        self.create_main_eye_setup()
        self.create_controllers()
        self.attributes()
        # self.create_blink_setup()

    def lock_attributes(self, ctl, attrs):

        """
        Lock and hide attributes on a controller.
        Args:
            ctl (str): The name of the controller.
            attrs (list): A list of attributes to lock and hide.
        """
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def local(self, ctl):

        """
        Create a local transform node for a controller.
        Args:
            ctl (str): The name of the controller.
        Returns:
            str: The name of the local transform node.
        """

        local_grp = cmds.createNode("transform", name=ctl.replace("_CTL", "Local_GRP"), ss=True, p=self.module_trn)
        local_trn = cmds.createNode("transform", name=ctl.replace("_CTL", "Local_TRN"), ss=True, p=local_grp)
        grp = ctl.replace("_CTL", "_GRP")
        mult_matrix = cmds.createNode("multMatrix", name=ctl.replace("_CTL", "Local_MMT"))
        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{mult_matrix}.matrixIn[0]")
        cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]")
        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{local_trn}.offsetParentMatrix")
        cmds.matchTransform(local_grp, ctl)

        return local_grp, local_trn


    def create_main_eye_setup(self):

        """
        Create the main eye setup for the eyelid module.
        """

        sel = cmds.ls(f"{self.side}_eyelid*_GUIDE", type="transform")
        cluster = cmds.cluster(sel, name=f"{self.side}_eyeCluster")
        self.eye_joint = cmds.joint(name=f"{self.side}_eye_JNT")
        cmds.parent(self.eye_joint, self.skeleton_grp)
        cmds.matchTransform(self.eye_joint, cluster[1])
        cmds.delete(cluster)

        if self.side == "L":
            self.main_aim_ctl, self.main_aim_nodes,= curve_tool.controller_creator(name=f"C_eyeMain", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
            # cmds.parent(self.main_aim_nodes, self.head_ctl)
            # self.lock_attributes(self.main_aim_ctl, ["sx", "sy", "sz", "v", "rx", "ry", "rz"])
            before_translate = cmds.xform(self.eye_joint, q=True, t=True, ws=True)
            cmds.setAttr(f"{self.eye_joint}.tx", 0)
            cmds.matchTransform(self.main_aim_nodes[0], self.eye_joint)
            cmds.select(self.main_aim_nodes[0])
            cmds.move(0, 0, 10, relative=True, objectSpace=True, worldSpaceDistance=True)
            cmds.xform(self.eye_joint, t=before_translate, ws=True)

        self.side_aim_ctl, side_aim_nodes = curve_tool.controller_creator(name=f"{self.side}_eye", suffixes=["GRP"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.parent(side_aim_nodes[0], self.controllers_grp)
        cmds.matchTransform(side_aim_nodes[0], self.eye_joint)
        cmds.select(side_aim_nodes[0])
        cmds.move(0, 0, 10, relative=True, objectSpace=True, worldSpaceDistance=True)
        # self.lock_attributes(self.side_aim_ctl, ["sx", "sy", "sz", "v", "rx", "ry", "rz"])
        cmds.parent(side_aim_nodes[0], "C_eyeMain_CTL")

        # Aim setup
        self.eye_jnt_matrix = cmds.xform(self.eye_joint, q=True, m=True, ws=True)
        self.aim = cmds.createNode("aimMatrix", name=f"{self.side}_eye_AIM", ss=True)
        cmds.setAttr(f"{self.aim}.primaryInputAxis", 0, 0, 1)
        cmds.setAttr(f"{self.aim}.secondaryInputAxis", 0, 1, 0)
        cmds.setAttr(f"{self.aim}.secondaryTargetVector", 0, 1, 0)
        cmds.setAttr(f"{self.aim}.secondaryMode", 2) # Align
        cmds.setAttr(f"{self.aim}.inputMatrix", self.eye_jnt_matrix, type="matrix")
        cmds.connectAttr(f"{self.side_aim_ctl}.worldMatrix[0]", f"{self.aim}.primaryTargetMatrix")
        # cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{self.aim}.secondaryTargetMatrix")
        cmds.connectAttr(f"{self.aim}.outputMatrix", f"{self.eye_joint}.offsetParentMatrix")
        cmds.xform(self.eye_joint, m=om.MMatrix.kIdentity)

    def create_controllers(self):

        """
        Create controllers for the eyelid module.
        """

        self.upper_local_trn = []
        self.lower_local_trn = []

        self.controllers = []
        print(self.upper_guides, self.lower_guides)

        up_positions = [self.upper_guides[0], self.upper_guides[len(self.upper_guides)//4], self.upper_guides[len(self.upper_guides)//2], self.upper_guides[(len(self.upper_guides)//4)*3], self.upper_guides[-1]]
        down_positions = [self.lower_guides[0], self.lower_guides[len(self.lower_guides)//4], self.lower_guides[len(self.lower_guides)//2], self.lower_guides[(len(self.lower_guides)//4)*3], self.lower_guides[-1]]
        ctl_names = ["eyelidIn", "eyelidIn", "eyelid", "eyelidOut", "eyelidOut"]
        for i, loc in enumerate(zip(self.upper_guides, self.lower_guides)):
            
            name = "Up" if "Up" in loc else "Down"
            ctl, node  = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}{name}", suffixes=["GRP"])
            local_grp, local_trn = self.local(ctl)
            if "eyelidIn_" in loc or "eyelidOut_" in loc or "eyelidDown_" in loc or "eyelidUp_" in loc:
                ctl_01, node_01 = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}{name}01", suffixes=["GRP"], parent=ctl)
                local_grp_01, local_trn_01 = self.local(ctl_01)
                cmds.parent(local_grp_01, local_trn)
            cmds.parent(node, self.controllers_grp)
            if "Up" in loc:
                self.upper_local_trn.append(local_trn)
            elif "Down" in loc:
                self.lower_local_trn.append(local_trn)
            else:
                self.upper_local_trn.append(local_trn)
                self.lower_local_trn.append(local_trn)
            self.lock_attributes(ctl, ["sx", "sy", "sz", "v"]) 
            
            cmds.matchTransform(node[0], loc)
            cmds.matchTransform(local_grp, loc)
            self.controllers.append(ctl)

        

        sel_upper = [ctl for ctl in self.upper_local_trn]
        self.upper_skinning_jnt_trn, temp = de_boors_002.de_boor_ribbon(cvs=sel_upper, name=f"{self.side}_eyelidUpper", aim_axis='x', up_axis='y', num_joints=18)

        sel_lower = [ctl_low for ctl_low in self.lower_local_trn]
        self.lower_skinning_jnt_trn, temp_down = de_boors_002.de_boor_ribbon(cvs=sel_lower, name=f"{self.side}_eyelidLower", aim_axis="x", up_axis="y", num_joints=18)

        cmds.parent(self.upper_skinning_jnt_trn, self.skeleton_grp)
        cmds.parent(self.lower_skinning_jnt_trn, self.skeleton_grp)
        cmds.delete(temp, temp_down)

    def attributes(self):

        """
        Add custom attributes to the eyelid controllers.
        """

        self.eye_direct_nodes, self.eye_direct_ctl = curve_tool.create_controller(name=f"{self.side}_eyeDirect", offset=["GRP"])
        # cmds.parent(self.eye_direct_nodes[0], self.head_ctl)
        cmds.matchTransform(self.eye_direct_nodes[0], self.eye_joint)
        cmds.select(self.eye_direct_nodes[0])
        cmds.move(0, 0, 3, relative=True, objectSpace=True, worldSpaceDistance=True)
        self.lock_attributes(self.eye_direct_ctl, ["sx", "sy", "sz", "v", "rx", "ry", "rz"])

        cmds.addAttr(self.eye_direct_ctl, ln="EYE_ATTRIBUTES", at="enum", en="____", k=True)
        cmds.setAttr(f"{self.eye_direct_ctl}.EYE_ATTRIBUTES", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.eye_direct_ctl, ln="Upper_Blink", at="float", min=0, max=1, dv=0, k=True)
        cmds.addAttr(self.eye_direct_ctl, ln="Lower_Blink", at="float", min=0, max=1, dv=0, k=True)
        cmds.addAttr(self.eye_direct_ctl, ln="Blink_Height", at="float", min=0, max=1, dv=0.6, k=True)

        # Connect the aim matrix to the eye direct controller and orient constrain the eye joint to it
        eye_direct_matrix = cmds.xform(self.eye_direct_nodes, q=True, m=True, ws=True)
        cmds.setAttr(f"{self.aim}.inputMatrix", eye_direct_matrix, type="matrix")
        cmds.connectAttr(f"{self.aim}.outputMatrix", f"{self.eye_direct_nodes[0]}.offsetParentMatrix", force=True)
        cmds.xform(self.eye_direct_nodes[0], m=om.MMatrix.kIdentity)
        cmds.setAttr(f"{self.eye_direct_nodes[0]}.inheritsTransform", 0)
        pick_matrix_rotation = cmds.createNode("pickMatrix", name=f"{self.side}_eye_PMK", ss=True)
        cmds.connectAttr(f"{self.eye_direct_ctl}.worldMatrix[0]", f"{pick_matrix_rotation}.inputMatrix")
        cmds.setAttr(f"{pick_matrix_rotation}.useTranslate", 0)
        cmds.setAttr(f"{pick_matrix_rotation}.useScale", 0)
        cmds.connectAttr(f"{pick_matrix_rotation}.outputMatrix", f"{self.eye_joint}.offsetParentMatrix", force=True)
        cmds.xform(self.eye_joint, m=self.eye_jnt_matrix)
        

    def create_blink_setup(self):

        """
        Create the blink setup for the eyelid module.
        """
        pass

                


    def get_offset_matrix(self, child, parent):

        """
        Calculate the offset matrix between a child and parent transform in Maya.
        Args:
            child (str): The name of the child transform.
            parent (str): The name of the parent transform. 
        Returns:
            om.MMatrix: The offset matrix that transforms the child into the parent's space.
        """
        child_dag = om.MSelectionList().add(child).getDagPath(0)
        parent_dag = om.MSelectionList().add(parent).getDagPath(0)

        child_world_matrix = child_dag.inclusiveMatrix()
        parent_world_matrix = parent_dag.inclusiveMatrix()
        
        offset_matrix = child_world_matrix * parent_world_matrix.inverse()

        
        return offset_matrix
    


            

# a = EyelidModule("L_eyeDown01_GUIDE").make()
