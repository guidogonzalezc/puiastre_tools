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
        self.guides = guide_creation.guide_import(guide_name, all_descendents=True, path=None) # Get self.side_eye_GUIDE and its children

        self.upper_guides = [guide for guide in self.guides if "Up" in guide and "Blink" not in guide] # Upper guides
        self.lower_guides = [guide for guide in self.guides if "Down" in guide and "Blink" not in guide] # Lower guides
        self.blink_guides = [guide for guide in self.guides if "eyeBlink" in guide] # Blink ref guides
        self.up_blink_guides = [guide for guide in self.guides if "UpBlink" in guide] # Upper blink guides
        self.down_blink_guides = [guide for guide in self.guides if "DownBlink" in guide] # Lower blink guides

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
        self.out_skinning_joints()
        # self.create_blink_setup()


    def create_main_eye_setup(self):

        """
        Create the main eye setup for the eyelid module.
        """
        self.eye_joint = cmds.joint(name=f"{self.side}_eye_JNT")
        cmds.matchTransform(self.eye_joint, self.guides[0])
        cmds.parent(self.eye_joint, self.skeleton_grp)

        self.side_aim_ctl, side_aim_nodes = curve_tool.controller_creator(name=f"{self.side}_eye", suffixes=["GRP"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.parent(side_aim_nodes[0], self.controllers_grp)
        cmds.matchTransform(side_aim_nodes[0], self.eye_joint)
        cmds.select(side_aim_nodes[0])
        cmds.move(50, 0, 0, relative=True, objectSpace=True, worldSpaceDistance=True)


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

        self.upper_controllers = []
        self.upper_nodes = []

        up_positions = [self.upper_guides[1], self.upper_guides[len(self.upper_guides)//4], self.upper_guides[len(self.upper_guides)//2], self.upper_guides[(len(self.upper_guides)//4)*3], self.upper_guides[-1]]
        down_positions = [self.lower_guides[1], self.lower_guides[(len(self.lower_guides)//4)], self.lower_guides[len(self.lower_guides)//2], self.lower_guides[(len(self.lower_guides)//4)*3], self.lower_guides[-1]]
        ctl_names = ["eyelidIn", "eyelidIn", "eyelid", "eyelidOut", "eyelidOut"]

        for i, pos in enumerate(up_positions): # Create upper eyelid controllers
            
            if i == 1 or i == 2 or i == 3:
                ctl, nodes = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Up", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                if i == 2:
                    cmds.connectAttr(f"{pos}.worldMatrix[0]", f"{nodes[0]}.offsetParentMatrix", force=True)
                else:
                    cmds.matchTransform(nodes[0], pos)
                local_grp, local_trn = self.local(ctl)
            else:
                ctl, nodes = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                cmds.connectAttr(f"{pos}.worldMatrix[0]", f"{nodes[0]}.offsetParentMatrix", force=True)
                local_grp, local_trn = self.local(ctl)

            if i == 0 or i == 2 or i == 4:
                if i == 2:
                    ctlSub, nodesSub = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}SubUp", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                    localSub_grp, localSub_trn = self.local(ctlSub)
                    cmds.parent(localSub_grp, local_trn)
                    cmds.matchTransform(localSub_grp, local_trn)
                else:
                    ctlSub, nodesSub = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Sub", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                    localSub_grp, localSub_trn = self.local(ctlSub)
                    cmds.parent(localSub_grp, local_trn)
                    
                cmds.parent(nodesSub[0], ctl)
                cmds.xform(nodesSub[0], m=om.MMatrix.kIdentity)

            cmds.parent(nodes[0], self.controllers_grp)
            
            self.upper_local_trn.append(local_trn)
            self.upper_controllers.append(ctl)
            self.upper_nodes.append(nodes[0])

        
        self.lower_controllers = []
        self.lower_nodes = []
        self.lower_local_trn.append(self.upper_local_trn[0])
        self.lower_nodes.append(self.upper_nodes[0])
        self.lower_controllers.append(self.upper_controllers[0])
        for i, pos in enumerate(down_positions): # Create lower eyelid controllers
            if i != 0 or i != 4:
                if i == 1 or i == 2 or i == 3:
                    ctl, nodes = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Down", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"], parent=self.controllers_grp)
                    if i == 2:
                        cmds.connectAttr(f"{pos}.worldMatrix[0]", f"{nodes[0]}.offsetParentMatrix", force=True)
                    else:
                        cmds.matchTransform(nodes[0], pos)
                    local_grp, local_trn = self.local(ctl)
                    self.lower_local_trn.append(local_trn)
                    self.lower_nodes.append(nodes[0])
                    self.lower_controllers.append(ctl)
                if i == 2:
                    ctlSub, nodesSub = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}SubDown", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                    localSub_grp, localSub_trn = self.local(ctlSub)
                    cmds.parent(localSub_grp, self.lower_local_trn[-1])
                    cmds.parent(nodesSub[0], ctl)
                    cmds.xform(nodesSub[0], m=om.MMatrix.kIdentity)

        self.lower_local_trn.append(self.upper_local_trn[-1])
        self.lower_nodes.append(self.upper_nodes[-1])
        self.lower_controllers.append(self.upper_controllers[-1])

        #Constraints between controllers
        self.constraints_callback(self.upper_nodes[1], [self.upper_controllers[2], self.upper_controllers[0]])
        self.constraints_callback(self.upper_nodes[-2], [self.upper_controllers[2], self.upper_controllers[-1]])
        self.constraints_callback(self.lower_nodes[1], [self.lower_controllers[2], self.lower_controllers[0]])
        self.constraints_callback(self.lower_nodes[-2], [self.lower_controllers[2], self.lower_controllers[-1]])

        #Constraints between local groups
        up_in_pm = self.constraints_callback(self.upper_local_trn[1], [self.upper_local_trn[2], self.upper_local_trn[0]])
        up_out_pm = self.constraints_callback(self.upper_local_trn[-2], [self.upper_local_trn[2], self.upper_local_trn[-1]])
        low_in_pm = self.constraints_callback(self.lower_local_trn[1], [self.lower_local_trn[2], self.lower_local_trn[0]])
        low_out_pm = self.constraints_callback(self.lower_local_trn[-2], [self.lower_local_trn[2], self.lower_local_trn[-1]])

        indices = [1, -2, 1, -2]
        for i, (local_trn, pm) in enumerate(zip([self.upper_local_trn[1], self.upper_local_trn[-2], self.lower_local_trn[1], self.lower_local_trn[-2]], [up_in_pm, up_out_pm, low_in_pm, low_out_pm])): # Connect the rest of the local groups to the respective parentMatrix nodes
            
            mult_matrix = cmds.createNode("multMatrix", name=local_trn.replace("Local_TRN", "Local_MMT"))
            if i < 2:
                cmds.connectAttr(f"{self.upper_controllers[indices[i]]}.worldMatrix[0]", f"{mult_matrix}.matrixIn[0]")
                cmds.connectAttr(f"{self.upper_nodes[indices[i]]}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]")
            else:
                cmds.connectAttr(f"{self.lower_controllers[indices[i]]}.worldMatrix[0]", f"{mult_matrix}.matrixIn[0]")
                cmds.connectAttr(f"{self.lower_nodes[indices[i]]}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]")
            cmds.connectAttr(f"{pm}.outputMatrix", f"{mult_matrix}.matrixIn[2]")
            cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{local_trn}.offsetParentMatrix", force=True)
            cmds.setAttr(f"{local_trn}.inheritsTransform", 1)


    def out_skinning_joints(self):

        # Create skinning joints using de Boor's algorithm
        sel_upper = [f"{ctl}.worldMatrix[0]" for ctl in self.upper_controllers]
        self.upper_skinning_jnt_trn = de_boors_002.de_boor_ribbon(cvs=sel_upper, name=f"{self.side}_eyelidUpper", aim_axis='x', up_axis='y', num_joints=len(self.upper_guides), parent=self.skeleton_grp)
        upper_joints = cmds.listRelatives(self.upper_skinning_jnt_trn, children=True, type="joint")

        cmds.addAttr(self.eye_direct_ctl, ln="EXTRA_CONTROLLERS", at="enum", en="____", k=True) # Create attribute to control visibility of extra controllers
        cmds.setAttr(f"{self.eye_direct_ctl}.EXTRA_CONTROLLERS", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.eye_direct_ctl, longName="Extra_Controllers_Visibility", attributeType="bool", keyable=False)
        cmds.setAttr(f"{self.eye_direct_ctl}.Extra_Controllers_Visibility", channelBox=True)

        for jnt in self.upper_skinning_jnt_trn: # Create controllers for upper eyelid skinning joints

            jnt_input = cmds.listConnections(f"{jnt}.offsetParentMatrix", s=True, d=False) 
            ctl, grp = curve_tool.controller_creator(name=jnt.replace("_JNT", ""), suffixes=["GRP"], lock=["scaleX", "scaleY", "scaleZ", "visibility"], parent=self.controllers_grp) # Create controller for each joint
            cmds.connectAttr(f"{self.eye_direct_ctl}.Extra_Controllers_Visibility", f"{grp[0]}.visibility")
            cmds.connectAttr(f"{jnt_input[0]}.matrixSum", f"{grp[0]}.offsetParentMatrix")
            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{jnt}.offsetParentMatrix", force=True)
            cmds.matchTransform(jnt, grp[0])

        sel_lower = [f"{ctl_low}.worldMatrix[0]" for ctl_low in self.lower_controllers] 
        self.lower_skinning_jnt_trn = de_boors_002.de_boor_ribbon(cvs=sel_lower, name=f"{self.side}_eyelidLower", aim_axis="x", up_axis="y", num_joints=len(self.lower_guides), parent=self.skeleton_grp)
        
        for jnt in self.lower_skinning_jnt_trn: # Create controllers for lower eyelid skinning joints

            jnt_input = cmds.listConnections(f"{jnt}.offsetParentMatrix", s=True, d=False)
            ctl, grp = curve_tool.controller_creator(name=jnt.replace("_JNT", ""), suffixes=["GRP"], lock=["scaleX", "scaleY", "scaleZ", "visibility"], parent=self.controllers_grp) # Create controller for each joint
            cmds.connectAttr(f"{self.eye_direct_ctl}.Extra_Controllers_Visibility", f"{grp[0]}.visibility")
            cmds.connectAttr(f"{jnt_input[0]}.matrixSum", f"{grp[0]}.offsetParentMatrix")
            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{jnt}.offsetParentMatrix", force=True)
            cmds.matchTransform(jnt, grp[0])


    
    def attributes(self):

        """
        Add custom attributes to the eyelid controllers.
        """

        self.eye_direct_ctl, self.eye_direct_nodes = curve_tool.controller_creator(name=f"{self.side}_eyeDirect", suffixes=["GRP"], parent=self.controllers_grp, lock=["scaleX", "scaleY", "scaleZ", "visibility"])
        # cmds.parent(self.eye_direct_nodes[0], self.head_ctl)
        cmds.matchTransform(self.eye_direct_nodes[0], self.eye_joint)
        cmds.select(self.eye_direct_nodes[0])
        cmds.move(0, 0, 3, relative=True, objectSpace=True, worldSpaceDistance=True)

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

        for i, jnt in enumerate(self.upper_skinning_jnt_trn):
            
            blend_matrix = cmds.createNode("blendMatrix", name=jnt.replace("_JNT", "_BLM"), ss=True)
            cmds.connectAttr(f"{self.blink_guides[i]}.worldMatrix[0]", f"{blend_matrix}.inputMatrix")
            cmds.connectAttr(f"{self.up_blink_guides[i]}.worldMatrix[0]", f"{blend_matrix}.target[0].targetMatrix")
            cmds.connectAttr(f"{self.eye_direct_ctl}.Upper_Blink", f"{blend_matrix}.target[0].weight")
            # cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{jnt}.offsetParentMatrix", force=True)

                

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
    
    def constraints_callback(self, driven, drivers=[]):

        """
        Create a parent constraint between a driven object and multiple driver objects with equal weights.
        Args:
            driven (str): The name of the driven object.
            drivers (list): A list of driver objects.
        """
        suffix = driven.split("_")[-1]
        parent_matrix = cmds.createNode("parentMatrix", name=driven.replace(suffix, "PMT"), ss=True)
        cmds.connectAttr(f"{drivers[0]}.worldMatrix[0]", f"{parent_matrix}.target[0].targetMatrix")
        cmds.connectAttr(f"{drivers[1]}.worldMatrix[0]", f"{parent_matrix}.target[1].targetMatrix")
        cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", cmds.getAttr(f"{drivers[0]}.worldInverseMatrix"), type="matrix")
        cmds.setAttr(f"{parent_matrix}.target[1].offsetMatrix", cmds.getAttr(f"{drivers[1]}.worldInverseMatrix"), type="matrix")
        cmds.setAttr(f"{parent_matrix}.target[0].weight", 0.7)
        cmds.setAttr(f"{parent_matrix}.target[1].weight", 0.3)
        cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{driven}.offsetParentMatrix", force=True)
        cmds.setAttr(f"{driven}.inheritsTransform", 0)

        return parent_matrix


            
cmds.file(new=True, force=True)
# core.DataManager.set_guide_data("C:/3ero/TFG/puiastre_tools/guides/AYCHEDRAL_008.guides")
# core.DataManager.set_ctls_data("C:/3ero/TFG/puiastre_tools/curves/AYCHEDRAL_curves_001.json")

core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/AYCHEDRAL_010.guides")
core.DataManager.set_ctls_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/curves/AYCHEDRAL_curves_001.json")


basic_structure.create_basic_structure()
a = EyelidModule("L_eye_GUIDE").make()
