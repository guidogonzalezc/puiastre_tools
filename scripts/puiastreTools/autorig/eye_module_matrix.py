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
        self.masterwalk_ctl = data_export.DataExport().get_data("basic_structure", "masterWalk_CTL")
        # self.head_ctl = data_export.DataExport().get_data("neck_module", "head_ctl")
        self.guides_grp = data_export.DataExport().get_data("basic_structure", "guides_GRP")
        self.eye_guide = guide_creation.guide_import(guide_name, all_descendents=True) # Get self.side_eye_GUIDE and its children

        # Curve guides
        self.upper_curve = guide_creation.guide_import(f"{self.side}_upperEyelidCurve_GUIDE")
        self.lower_curve = guide_creation.guide_import(f"{self.side}_lowerEyelidCurve_GUIDE")
        self.blink_curve = guide_creation.guide_import(f"{self.side}_eyeBlinkCurve_GUIDE")
        self.upper_n_blink = guide_creation.guide_import(f"{self.side}_upperNegativeBlinkCurve_GUIDE")
        self.lower_n_blink = guide_creation.guide_import(f"{self.side}_lowerNegativeBlinkCurve_GUIDE")

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
        self.controllers_grp = cmds.createNode("transform", name=f"{self.module_name}Controllers_GRP", ss=True, p=self.masterwalk_ctl)

        self.create_curves()
        self.create_main_eye_setup()
        self.create_controllers()
        self.eye_direct_attributes()
        self.blend_curves()
        self.skinning_joints()


    def create_curves(self):

        """
        Create NURBS curves for the upper and lower eyelids based on the guide positions.
        """
        self.linear_upper_curve = cmds.rebuildCurve(self.upper_curve, ch=False, rpo=False, rt=0, end=1, kr=0, kcp=False, kep=True, kt=False, s=15, d=1, tol=0.01, name=f"{self.side}_upperEyelidLinear_CRV")[0]
        self.linear_lower_curve = cmds.rebuildCurve(self.lower_curve, ch=False, rpo=False, rt=0, end=1, kr=0, kcp=False, kep=True, kt=False, s=15, d=1, tol=0.01, name=f"{self.side}_lowerEyelidLinear_CRV")[0]

        cmds.parent(self.linear_upper_curve, self.module_trn)
        cmds.parent(self.linear_lower_curve, self.module_trn)

        self.upper_rebuild_curve = cmds.duplicate(self.upper_curve, name=f"{self.side}_upperBlinkRebuild_CRV")[0]
        self.lower_rebuild_curve = cmds.duplicate(self.lower_curve, name=f"{self.side}_lowerBlinkRebuild_CRV")[0]
        

        self.upper_guides = [] # Store upper eyelid guide transforms
        up_cvs = cmds.ls(self.linear_upper_curve + ".cv[*]", fl=True)
        for i, cv in enumerate(up_cvs):
            pos = cmds.xform(cv, q=True, ws=True, t=True)
            guide_trn = cmds.createNode("transform", name=f"{self.side}_upperEyelid0{i}_GUIDE", ss=True, p=self.module_trn)
            cmds.xform(guide_trn, ws=True, t=pos)
            self.upper_guides.append(guide_trn)
        
        self.lower_guides = [] # Store lower eyelid guide transforms
        down_cvs = cmds.ls(self.linear_lower_curve + ".cv[*]", fl=True)
        for i, cv in enumerate(down_cvs):
            pos = cmds.xform(cv, q=True, ws=True, t=True)
            guide_trn = cmds.createNode("transform", name=f"{self.side}_lowerEyelid0{i}_GUIDE", ss=True, p=self.module_trn)
            cmds.xform(guide_trn, ws=True, t=pos)
            self.lower_guides.append(guide_trn)
        

    def create_main_eye_setup(self):

        """
        Create the main eye setup for the eyelid module.
        """
        self.eye_joint = cmds.joint(name=f"{self.side}_eye_JNT")
        cmds.matchTransform(self.eye_joint, self.eye_guide)
        cmds.parent(self.eye_joint, self.skeleton_grp)

        self.side_aim_ctl, side_aim_nodes = curve_tool.controller_creator(name=f"{self.side}_eye", suffixes=["GRP"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.parent(side_aim_nodes[0], self.controllers_grp)
        cmds.matchTransform(side_aim_nodes[0], self.eye_joint)
        cmds.select(side_aim_nodes[0])
        cmds.move(0, 0, 50, relative=True, objectSpace=True, worldSpaceDistance=True)


        # Aim setup
        self.eye_jnt_matrix = cmds.xform(self.eye_guide, q=True, m=True, ws=True)
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


        self.upper_controllers = []
        self.upper_nodes = []
        upper_local_trns = []
        self.upper_local_jnts = []

        up_positions = cmds.ls(self.upper_rebuild_curve + ".cv[*]", fl=True) # Get CV positions of the rebuilt curves
        down_positions = cmds.ls(self.lower_rebuild_curve + ".cv[*]", fl=True) # Get CV positions of the rebuilt curves

        
        upper_guides = [
            self.upper_guides[0],
            self.upper_guides[len(self.upper_guides) // 4],
            self.upper_guides[len(self.upper_guides) // 2],
            self.upper_guides[(len(self.upper_guides) * 3) // 4],
            self.upper_guides[-1]
        ]
        
        lower_guides = [
            self.lower_guides[0],
            self.lower_guides[len(self.lower_guides) // 4],
            self.lower_guides[len(self.lower_guides) // 2],
            self.lower_guides[(len(self.lower_guides) * 3) // 4],
            self.lower_guides[-1]
        ]
        
        ctl_names = ["eyelidIn", "eyelidIn", "eyelid", "eyelidOut", "eyelidOut"]

        for i, guide in enumerate(upper_guides): # Create upper eyelid controllers
            
            if i == 1 or i == 2 or i == 3:
                ctl, nodes = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Up", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                if i == 2:
                    cmds.connectAttr(f"{guide}.worldMatrix[0]", f"{nodes[0]}.offsetParentMatrix", force=True) # Directly connect the mid guide to the middle controller
                local_trn, joint_local = self.local(ctl, guide)

            else:
                ctl, nodes = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                blend_matrix = cmds.createNode("blendMatrix", name=ctl.replace("CTL", "BLM"), ss=True) # create a blend matrix to blend between the upper00 and lower00 guides
                cmds.connectAttr(f"{guide}.worldMatrix[0]", f"{blend_matrix}.inputMatrix")
                cmds.connectAttr(f"{lower_guides[i]}.worldMatrix[0]", f"{blend_matrix}.target[0].targetMatrix")
                cmds.setAttr(f"{blend_matrix}.target[0].weight", 0.5) # Set weight to 0.5 for equal influence
                cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{nodes[0]}.offsetParentMatrix", force=True) # Connect the blend matrix to the controller
                local_trn, joint_local = self.local(ctl, guide)

            upper_local_trns.append(local_trn)

            if i == 0 or i == 2 or i == 4:
                if i == 2:
                    ctlSub, nodesSub = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Up01", suffixes=["GRP"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                    cmds.parent(nodesSub[0], ctl)
                    local_trn_01, joint_local = self.local(ctlSub, guide, sub=True) # Create local transform for the controller

                else:
                    ctlSub, nodesSub = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}01", suffixes=["GRP"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                    cmds.parent(nodesSub[0], ctl)
                    local_trn_01, joint_local = self.local(ctlSub, guide, sub=True) # Create local transform for the controller
                    upper_local_trns.append(local_trn_01)
                    
                cmds.xform(nodesSub[0], m=om.MMatrix.kIdentity) # Reset transform of the sub controller

            cmds.parent(nodes[0], self.controllers_grp)
            self.upper_controllers.append(ctl)
            self.upper_nodes.append(nodes[0])
            self.upper_local_jnts.append(joint_local)

        
        self.upper_local_jnts = [jnt for jnt in self.upper_local_jnts if jnt != None]

        self.lower_controllers = []
        self.lower_nodes = []
        lower_local_trns = []
        self.lower_local_jnts = []

        self.lower_nodes.append(self.upper_nodes[0])
        lower_local_trns.append(upper_local_trns[0])
        self.lower_controllers.append(self.upper_controllers[0])
        self.lower_local_jnts.append(self.upper_local_jnts[0])

        for i, pos in enumerate(down_positions): # Create lower eyelid controllers
            if i != 0 or i != 4:
                if i == 1 or i == 2 or i == 3:
                    ctl, nodes = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Down", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"], parent=self.controllers_grp)
                    # cmds.xform(nodes[0], t=cmds.xform(down_positions[i+1], q=True, ws=True, t=True), ws=True)
                    if i == 2:
                        cmds.connectAttr(f"{lower_guides[i]}.worldMatrix[0]", f"{nodes[0]}.offsetParentMatrix", force=True) # Directly connect the mid guide to the middle controller
                    self.lower_nodes.append(nodes[0])
                    self.lower_controllers.append(ctl)
                    local_trn, joint_local = self.local(ctl, lower_guides[i]) # Create local transform for the controller
                    lower_local_trns.append(local_trn)
                    self.lower_local_jnts.append(joint_local)
                if i == 2:
                    ctlSub, nodesSub = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Down01", suffixes=["GRP", "ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                    cmds.parent(nodesSub[0], self.lower_controllers[-1])
                    local_trn_01, joint_local = self.local(ctlSub, lower_guides[i], sub=True) # Create local transform for the controller
                    lower_local_trns.append(local_trn_01)
                    self.lower_local_jnts.append(joint_local)

        self.lower_nodes.append(self.upper_nodes[-1])
        self.lower_controllers.append(self.upper_controllers[-1])
        self.lower_local_jnts.append(self.upper_local_jnts[-1])
        lower_local_trns.append(upper_local_trns[-2])

        self.lower_local_jnts.remove(self.lower_local_jnts[2]) # Remove duplicate joint


        #Constraints between controllers
        self.constraints_callback(guide = upper_guides[1], driven=self.upper_nodes[1], drivers=[self.upper_controllers[2], self.upper_controllers[0]]) # Must change the offset matrix to work
        self.constraints_callback(guide=self.upper_guides[-2], driven=self.upper_nodes[-2], drivers=[self.upper_controllers[2], self.upper_controllers[-1]]) # Must change the offset matrix to work
        self.constraints_callback(guide=self.lower_guides[1], driven=self.lower_nodes[1], drivers=[self.lower_controllers[2], self.lower_controllers[0]]) # Must change the offset matrix to work
        self.constraints_callback(guide=self.lower_guides[-2], driven=self.lower_nodes[-2], drivers=[self.lower_controllers[2], self.lower_controllers[-1]]) # Must change the offset matrix to work

        # Local constraints between local transforms
        self.local_constraints_callback(cmds.listConnections(f"{upper_local_trns[2]}.offsetParentMatrix", type="multMatrix")[0], upper_local_trns[2], [upper_local_trns[3], upper_local_trns[0]]) # Must change the offset matrix to work
        self.local_constraints_callback(cmds.listConnections(f"{upper_local_trns[-3]}.offsetParentMatrix", type="multMatrix")[0], upper_local_trns[-3], [upper_local_trns[3], upper_local_trns[-1]]) # Must change the offset matrix to work
        self.local_constraints_callback(cmds.listConnections(f"{lower_local_trns[1]}.offsetParentMatrix", type="multMatrix")[0], lower_local_trns[1], [lower_local_trns[2], lower_local_trns[0]]) # Must change the offset matrix to work
        self.local_constraints_callback(cmds.listConnections(f"{lower_local_trns[-2]}.offsetParentMatrix", type="multMatrix")[0], lower_local_trns[-2], [lower_local_trns[2], lower_local_trns[-1]]) # Must change the offset matrix to work

    def eye_direct_attributes(self):

        """
        Add custom attributes to the eyelid controllers.
        """

        self.eye_direct_ctl, self.eye_direct_nodes = curve_tool.controller_creator(name=f"{self.side}_eyeDirect", suffixes=["GRP"], parent=self.controllers_grp, lock=["scaleX", "scaleY", "scaleZ", "visibility"])
        # cmds.parent(self.eye_direct_nodes[0], self.head_ctl)
        cmds.matchTransform(self.eye_direct_nodes[0], self.eye_guide)
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

    def blend_curves(self):

        """
        Blend shapes between the blink guides and the rebuilt curves to create blink setup.
        """

        pass

    def skinning_joints(self):

        """
        Create a tracking system for the eyelid module.
        """
        # Skin the linear curves with the local joints
        self.upper_skin_cluster = cmds.skinCluster(*self.upper_local_jnts, self.upper_curve, toSelectedBones=True, bindMethod=0, skinMethod=0, normalizeWeights=1, name=f"{self.side}_upperEyelid_SKIN")[0]
        self.lower_skin_cluster = cmds.skinCluster(*self.lower_local_jnts, self.lower_curve, toSelectedBones=True, bindMethod=0, skinMethod=0, normalizeWeights=1, name=f"{self.side}_lowerEyelid_SKIN")[0]

        for i, jnt in enumerate(self.upper_local_jnts):
            if i == 0 or i == len(self.upper_local_jnts) - 1:
                cmds.skinPercent(self.upper_skin_cluster, f"{self.upper_curve[0]}.cv[{i}]", transformValue=[(jnt, 1.0)]) # Assign full weight to each joint for its corresponding CV
            else:
                cmds.skinPercent(self.upper_skin_cluster, f"{self.upper_curve[0]}.cv[{i+1}]", transformValue=[(jnt, 1.0)])

        for i, jnt in enumerate(self.lower_local_jnts):
            if i == 0 or i == len(self.lower_local_jnts) - 1:
                cmds.skinPercent(self.lower_skin_cluster, f"{self.lower_curve[0]}.cv[{i}]", transformValue=[(jnt, 1.0)]) # Assign full weight to each joint for its corresponding CV
            else:
                cmds.skinPercent(self.lower_skin_cluster, f"{self.lower_curve[0]}.cv[{i+1}]", transformValue=[(jnt, 1.0)])

        
        # Create tracker for the rebuilt curves
        for i, guide in enumerate(self.upper_guides):

            motion_path = cmds.createNode("motionPath", name=f"{self.side}_upperEyelid0{i}_MTP", ss=True)
            cmds.setAttr(f"{motion_path}.uValue", i / (len(self.upper_guides) - 1))
            cmds.setAttr(f"{motion_path}.fractionMode", 1)
            cmds.setAttr(f"{motion_path}.worldUpType", 3) # Vector
            cmds.setAttr(f"{motion_path}.frontAxis", 1) # Y
            cmds.setAttr(f"{motion_path}.upAxis", 2) # Z
            cmds.connectAttr(f"{self.upper_curve[0]}.worldSpace[0]", f"{motion_path}.geometryPath") # Connect curve to motion path
            

            four_by_four = cmds.createNode("fourByFourMatrix", name=f"{self.side}_upperEyelid0{i}_F4X4", ss=True) # Create four by four matrix to extract translation
            cmds.connectAttr(f"{motion_path}.allCoordinates.xCoordinate", f"{four_by_four}.in30") # X
            cmds.connectAttr(f"{motion_path}.allCoordinates.yCoordinate", f"{four_by_four}.in31") # Y
            cmds.connectAttr(f"{motion_path}.allCoordinates.zCoordinate", f"{four_by_four}.in32") # Z

            jnt_center = cmds.createNode("joint", name=f"{self.side}_upperEyelid0{i}_JNT", ss=True, p=self.module_trn)
            jnt_tip = cmds.createNode("joint", name=f"{self.side}_upperEyelid0{i}End_JNT", ss=True, p=jnt_center) 
            cmds.connectAttr(f"{four_by_four}.output", f"{jnt_tip}.offsetParentMatrix") # Connect four by four to tip joint
            

            aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_upperEyelid0{i}_AIM", ss=True) # Create aim matrix to aim the center joint to the four by four matrix
            cmds.setAttr(f"{aim_matrix}.primaryInputAxis", 0, 0, 1) # Z
            cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", 0, 1, 0) # Y

            cmds.connectAttr(f"{self.eye_joint}.worldMatrix[0]", f"{aim_matrix}.inputMatrix") # Connect four by four to aim matrix
            cmds.connectAttr(f"{four_by_four}.output", f"{aim_matrix}.primaryTargetMatrix") # Connect four by four to aim matrix
            cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{jnt_center}.offsetParentMatrix") # Connect aim matrix to joint

            skinning_jnt = cmds.createNode("joint", name=f"{self.side}_upperEyelid0{i}Skinning_JNT", ss=True, p=self.skeleton_grp)
            cmds.connectAttr(f"{jnt_tip}.worldMatrix[0]", f"{skinning_jnt}.offsetParentMatrix") # Connect center joint to skinning joint

    
    
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
    
    def local(self, ctl, guide, sub=False):

        """
        Create a local transform node for a controller.
        Args:
            ctl (str): The name of the controller.
        Returns:
            str: The name of the local transform node.
        """

        grp = ctl.replace("_CTL", "_GRP")

        local_trn = cmds.createNode("transform", name=ctl.replace("_CTL", "Local_TRN"), ss=True, p=self.module_trn)
        joint_local = cmds.createNode("joint", name=ctl.replace("_CTL", "Local_JNT"), ss=True, p=local_trn) # Create joint if sub is True
        
        mult_matrix = cmds.createNode("multMatrix", name=ctl.replace("_CTL", "Local_MMT"))
        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{mult_matrix}.matrixIn[0]")
        cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]")

        if sub is False:

            cmds.connectAttr(f"{guide}.worldMatrix[0]", f"{mult_matrix}.matrixIn[2]")

        else:

            father = local_trn.replace("01Local_TRN", "Local_TRN")
            father_jnt = father.replace("Local_TRN", "Local_JNT")
            cmds.delete(father_jnt)
            cmds.parent(local_trn, father)
            cmds.matchTransform(local_trn, father)

        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{local_trn}.offsetParentMatrix")

        return local_trn, joint_local
    
    def constraints_callback(self, guide, driven, drivers=[]):

        """
        Create a parent constraint between a driven object and multiple driver objects with equal weights.
        Args:
            driven (str): The name of the driven object.
            drivers (list): A list of driver objects.
        """
        suffix = driven.split("_")[-1]
        parent_matrix = cmds.createNode("parentMatrix", name=driven.replace(suffix, "PMT"), ss=True)
        cmds.connectAttr(f"{guide}.worldMatrix[0]", f"{parent_matrix}.inputMatrix")
        cmds.connectAttr(f"{drivers[0]}.worldMatrix[0]", f"{parent_matrix}.target[0].targetMatrix")
        cmds.connectAttr(f"{drivers[1]}.worldMatrix[0]", f"{parent_matrix}.target[1].targetMatrix")
        cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", self.get_offset_matrix(driven, drivers[0]), type="matrix")
        cmds.setAttr(f"{parent_matrix}.target[1].offsetMatrix", self.get_offset_matrix(driven, drivers[1]), type="matrix")
        cmds.setAttr(f"{parent_matrix}.target[0].weight", 0.7)
        cmds.setAttr(f"{parent_matrix}.target[1].weight", 0.3)
        cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{driven}.offsetParentMatrix", force=True)
        cmds.setAttr(f"{driven}.inheritsTransform", 0)

        return parent_matrix
    
    def local_constraints_callback(self, mult_matrix, driven, drivers=[]):

        """
        Create a parent constraint between a driven object and multiple driver objects with equal weights.
        Args:
            driven (str): The name of the driven object.
            drivers (list): A list of driver objects.
        """
        suffix = driven.split("_")[-1]
        parent_matrix = cmds.createNode("parentMatrix", name=driven.replace(suffix, "PMT"), ss=True)
        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{parent_matrix}.inputMatrix")
        cmds.connectAttr(f"{drivers[0]}.worldMatrix[0]", f"{parent_matrix}.target[0].targetMatrix")
        cmds.connectAttr(f"{drivers[1]}.worldMatrix[0]", f"{parent_matrix}.target[1].targetMatrix")
        cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", cmds.getAttr(f"{drivers[0]}.worldInverseMatrix"), type="matrix")
        cmds.setAttr(f"{parent_matrix}.target[1].offsetMatrix", cmds.getAttr(f"{drivers[1]}.worldInverseMatrix"), type="matrix")
        cmds.setAttr(f"{parent_matrix}.target[0].weight", 0.7)
        cmds.setAttr(f"{parent_matrix}.target[1].weight", 0.3)
        cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{driven}.offsetParentMatrix", force=True)
        # cmds.setAttr(f"{driven}.inheritsTransform", 0)

        return parent_matrix


            
cmds.file(new=True, force=True)
# core.DataManager.set_guide_data("C:/3ero/TFG/puiastre_tools/guides/AYCHEDRAL_009.guides")
# core.DataManager.set_ctls_data("C:/3ero/TFG/puiastre_tools/curves/AYCHEDRAL_curves_001.json")

core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/AYCHEDRAL_015.guides")
core.DataManager.set_ctls_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/curves/AYCHEDRAL_curves_001.json")


basic_structure.create_basic_structure()
a = EyelidModule("L_eye_GUIDE").make()
