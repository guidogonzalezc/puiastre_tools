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
        self.skin_curves()
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
        upper_linear_shape = cmds.listRelatives(self.linear_upper_curve, shapes=True)[0]
        up_cvs = cmds.ls(self.linear_upper_curve + ".cv[*]", fl=True)

        for i, cv in enumerate(up_cvs):
            four_by_four_matrix = cmds.createNode("fourByFourMatrix", name=f"{self.side}_upperEyelid0{i}_F4X4", ss=True)
            cmds.connectAttr(f"{upper_linear_shape}.editPoints[{i}].xValueEp", f"{four_by_four_matrix}.in30") # X
            cmds.connectAttr(f"{upper_linear_shape}.editPoints[{i}].yValueEp", f"{four_by_four_matrix}.in31") # Y
            cmds.connectAttr(f"{upper_linear_shape}.editPoints[{i}].zValueEp", f"{four_by_four_matrix}.in32") # Z
            if self.side == "R":
                float_constant = cmds.createNode("floatConstant", name=f"{self.side}_upperEyelid0{i}_FLC", ss=True)
                cmds.setAttr(f"{float_constant}.inFloat", -1)
                cmds.connectAttr(f"{float_constant}.outFloat", f"{four_by_four_matrix}.in00") # -1 Scale X for mirroring
            self.upper_guides.append(four_by_four_matrix) # Append the four by four matrix to the upper guides list


        self.lower_guides = [] # Store lower eyelid guide transforms
        lower_linear_shape = cmds.listRelatives(self.linear_lower_curve, shapes=True)[0]
        down_cvs = cmds.ls(self.linear_lower_curve + ".cv[*]", fl=True)
        for i, cv in enumerate(down_cvs):
            four_by_four_matrix = cmds.createNode("fourByFourMatrix", name=f"{self.side}_lowerEyelid0{i}_F4X4", ss=True)
            cmds.connectAttr(f"{lower_linear_shape}.editPoints[{i}].xValueEp", f"{four_by_four_matrix}.in30") # X
            cmds.connectAttr(f"{lower_linear_shape}.editPoints[{i}].yValueEp", f"{four_by_four_matrix}.in31") # Y
            cmds.connectAttr(f"{lower_linear_shape}.editPoints[{i}].zValueEp", f"{four_by_four_matrix}.in32") # Z
            if self.side == "R":
                float_constant = cmds.createNode("floatConstant", name=f"{self.side}_lowerEyelid0{i}_FLC", ss=True)
                cmds.setAttr(f"{float_constant}.inFloat", -1)
                cmds.connectAttr(f"{float_constant}.outFloat", f"{four_by_four_matrix}.in00") # -1 Scale X for mirroring
            self.lower_guides.append(four_by_four_matrix) # Append the four by four matrix to the lower guides list

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
        self.upper_local_jnts = []

       
        upper_guides = [ 
            self.upper_guides[0],
            self.upper_guides[len(self.upper_guides) // 4],
            self.upper_guides[len(self.upper_guides) // 2],
            self.upper_guides[(len(self.upper_guides) * 3) // 4],
            self.upper_guides[-1]
        ] # Select 5 guides for the upper eyelid controllers
        
        lower_guides = [
            self.lower_guides[0],
            self.lower_guides[len(self.lower_guides) // 4],
            self.lower_guides[len(self.lower_guides) // 2],
            self.lower_guides[(len(self.lower_guides) * 3) // 4],
            self.lower_guides[-1]
        ] # Select 5 guides for the lower eyelid controllers
         
        ctl_names = ["eyelidIn", "eyelidIn", "eyelid", "eyelidOut", "eyelidOut"]

        for i, guide in enumerate(upper_guides): # Create upper eyelid controllers

            if i == 1 or i == 2 or i == 3:
                ctl, nodes = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Up", suffixes=["GRP","OFF","ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                if i == 2:
                    cmds.connectAttr(f"{guide}.output", f"{nodes[0]}.offsetParentMatrix", force=True) # Directly connect the mid guide to the middle controller
                
                joint_local = self.local(ctl, guide)
                cmds.parent(joint_local, self.module_trn)
                self.upper_local_jnts.append(joint_local)

            else:
                ctl, nodes = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}", suffixes=["GRP","OFF","ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                blend_matrix = cmds.createNode("blendMatrix", name=ctl.replace("CTL", "BLM"), ss=True) # create a blend matrix to blend between the upper00 and lower00 guides
                cmds.connectAttr(f"{guide}.output", f"{blend_matrix}.inputMatrix")
                cmds.connectAttr(f"{lower_guides[i]}.output", f"{blend_matrix}.target[0].targetMatrix")
                cmds.setAttr(f"{blend_matrix}.target[0].weight", 0.5) # Set weight to 0.5 for equal influence
                cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{nodes[0]}.offsetParentMatrix", force=True) # Connect the blend matrix to the controller
                local_jnt = self.local(ctl, guide) # Create local transform for the controller
                cmds.parent(local_jnt, self.module_trn)
                self.upper_local_jnts.append(local_jnt)

            if i == 0 or i == 2 or i == 4:
                if i == 2:
                    ctlSub, nodesSub = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Up01", suffixes=["GRP"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                    cmds.parent(nodesSub[0], ctl)

                else:
                    ctlSub, nodesSub = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}01", suffixes=["GRP"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                    cmds.parent(nodesSub[0], ctl)
                    
                    
                cmds.xform(nodesSub[0], m=om.MMatrix.kIdentity) # Reset transform of the sub controller

            cmds.parent(nodes[0], self.controllers_grp)
            self.upper_controllers.append(ctl)
            self.upper_nodes.append(nodes[0])
            # self.upper_local_jnts.append(joint_local)


        self.lower_controllers = []
        self.lower_nodes = []
        self.lower_local_jnts = []

        self.lower_nodes.append(self.upper_nodes[0])
        self.lower_controllers.append(self.upper_controllers[0])
        self.lower_local_jnts.append(self.upper_local_jnts[0])

        for i, guide in enumerate(lower_guides): # Create lower eyelid controllers
            if i != 0 or i != 4:
                if i == 1 or i == 2 or i == 3:
                    ctl, nodes = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Down", suffixes=["GRP","OFF","ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"], parent=self.controllers_grp)
                    if i == 2:
                        cmds.connectAttr(f"{guide}.output", f"{nodes[0]}.offsetParentMatrix", force=True) # Directly connect the mid guide to the middle controller
                    self.lower_nodes.append(nodes[0])
                    self.lower_controllers.append(ctl)
                    joint_local = self.local(ctl, guide) # Create local transform for the controller
                    cmds.parent(joint_local, self.module_trn)
                    self.lower_local_jnts.append(joint_local)

                if i == 2:
                    ctlSub, nodesSub = curve_tool.controller_creator(name=f"{self.side}_{ctl_names[i]}Down01", suffixes=["GRP","OFF","ANM"], lock=["scaleX", "scaleY", "scaleZ", "visibility"])
                    cmds.parent(nodesSub[0], self.lower_controllers[-1])
                    

        self.lower_nodes.append(self.upper_nodes[-1])
        self.lower_controllers.append(self.upper_controllers[-1])
        self.lower_local_jnts.append(self.upper_local_jnts[-1])


        #Constraints between controllers
        self.constraints_callback(guide=upper_guides[1], driven=self.upper_nodes[1], drivers=[self.upper_controllers[2], self.upper_controllers[0]]) # Must change the offset matrix to work
        self.constraints_callback(guide=upper_guides[-2], driven=self.upper_nodes[-2], drivers=[self.upper_controllers[2], self.upper_controllers[-1]]) # Must change the offset matrix to work
        self.constraints_callback(guide=lower_guides[1], driven=self.lower_nodes[1], drivers=[self.lower_controllers[2], self.lower_controllers[0]]) # Must change the offset matrix to work
        self.constraints_callback(guide=lower_guides[-2], driven=self.lower_nodes[-2], drivers=[self.lower_controllers[2], self.lower_controllers[-1]]) # Must change the offset matrix to work

    

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
        cmds.addAttr(self.eye_direct_ctl, ln="Upper_Blink", at="float", min=-1, max=1, dv=0, k=True)
        cmds.addAttr(self.eye_direct_ctl, ln="Lower_Blink", at="float", min=-1, max=1, dv=0, k=True)
        cmds.addAttr(self.eye_direct_ctl, ln="Blink_Height", at="float", min=0, max=1, dv=0.2, k=True)

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
        # Upper Blink
        upper_blink = cmds.blendShape(self.blink_curve, self.upper_curve , self.upper_n_blink, self.upper_rebuild_curve, name=f"{self.side}_upperEyelidBlink_BLS")[0] # Blend between blink curve and upper eyelid curve
        clamp_node = cmds.createNode("clamp", name=f"{self.side}_upperBlink_CLMP", ss=True)
        cmds.setAttr(f"{clamp_node}.minR", 0)
        cmds.setAttr(f"{clamp_node}.minG", -1)
        cmds.setAttr(f"{clamp_node}.maxR", 1)
        cmds.setAttr(f"{clamp_node}.maxG", 0)
        cmds.connectAttr(f"{self.eye_direct_ctl}.Upper_Blink", f"{clamp_node}.inputR") # Connect upper blink attribute to clamp
        cmds.connectAttr(f"{self.eye_direct_ctl}.Upper_Blink", f"{clamp_node}.inputG") # Connect upper blink attribute to clamp
        cmds.connectAttr(f"{clamp_node}.outputR", f"{upper_blink}.{self.blink_curve[0]}") # Connect clamp output to blend shape weight [0]
        reverse_node = cmds.createNode("reverse", name=f"{self.side}_upperBlink_REV", ss=True)
        cmds.connectAttr(f"{clamp_node}.outputR", f"{reverse_node}.inputX") # Connect clamp output to reverse
        cmds.connectAttr(f"{reverse_node}.outputX", f"{upper_blink}.{self.upper_curve[0]}") # Connect reverse output to blend shape weight [1]
        negate_node = cmds.createNode("negate", name=f"{self.side}_upperBlink_NEG", ss=True)
        cmds.connectAttr(f"{clamp_node}.outputG", f"{negate_node}.input") # Connect clamp output to negate
        cmds.connectAttr(f"{negate_node}.output", f"{upper_blink}.{self.upper_n_blink[0]}") # Connect negate output to blend shape weight [2]
        
        # Lower Blink
        lower_blink = cmds.blendShape(self.blink_curve, self.lower_curve , self.lower_n_blink, self.lower_rebuild_curve, name=f"{self.side}_lowerEyelidBlink_BLS")[0] # Blend between blink curve and lower eyelid curve
        clamp_node = cmds.createNode("clamp", name=f"{self.side}_lowerBlink_CLMP", ss=True)
        cmds.setAttr(f"{clamp_node}.minR", 0)
        cmds.setAttr(f"{clamp_node}.minG", -1)
        cmds.setAttr(f"{clamp_node}.maxR", 1)
        cmds.setAttr(f"{clamp_node}.maxG", 0)
        cmds.connectAttr(f"{self.eye_direct_ctl}.Lower_Blink", f"{clamp_node}.inputR") # Connect lower blink attribute to clamp
        cmds.connectAttr(f"{self.eye_direct_ctl}.Lower_Blink", f"{clamp_node}.inputG") # Connect lower blink attribute to clamp
        cmds.connectAttr(f"{clamp_node}.outputR", f"{lower_blink}.{self.blink_curve[0]}") # Connect clamp output to blend shape weight [0]
        reverse_node = cmds.createNode("reverse", name=f"{self.side}_lowerBlink_REV", ss=True)
        cmds.connectAttr(f"{clamp_node}.outputR", f"{reverse_node}.inputX") # Connect clamp output to reverse
        cmds.connectAttr(f"{reverse_node}.outputX", f"{lower_blink}.{self.lower_curve[0]}") # Connect reverse output to blend shape weight [1]
        negate_node = cmds.createNode("negate", name=f"{self.side}_lowerBlink_NEG", ss=True)
        cmds.connectAttr(f"{clamp_node}.outputG", f"{negate_node}.input") # Connect clamp output to negate
        cmds.connectAttr(f"{negate_node}.output", f"{lower_blink}.{self.lower_n_blink[0]}") # Connect negate output to blend shape weight [2]
        
        # Blink Height
        blink_blend = cmds.blendShape(self.upper_curve, self.lower_curve, self.blink_curve, name=f"{self.side}_eyelidBlink_BLS")[0] # Blend between blink curve and upper eyelid curve
        cmds.connectAttr(f"{self.eye_direct_ctl}.Blink_Height", f"{blink_blend}.{self.upper_curve[0]}") # Connect upper blink attribute to blend shape weight
        reverse_node = cmds.createNode("reverse", name=f"{self.side}_blinkHeight_REV", ss=True)
        cmds.connectAttr(f"{self.eye_direct_ctl}.Blink_Height", f"{reverse_node}.inputX") # Connect blink height attribute to reverse
        cmds.connectAttr(f"{reverse_node}.outputX", f"{blink_blend}.{self.lower_curve[0]}") # Connect reverse output to blend shape weight
        
    def skin_curves(self):

        """
        Create a tracking system for the eyelid module.
        """
        # Skin the linear curves with the local joints
        self.upper_skin_cluster = cmds.skinCluster(*self.upper_local_jnts, self.upper_rebuild_curve, toSelectedBones=True, bindMethod=0, skinMethod=0, normalizeWeights=1, name=f"{self.side}_upperEyelid_SKIN")[0]
        self.lower_skin_cluster = cmds.skinCluster(*self.lower_local_jnts, self.lower_rebuild_curve, toSelectedBones=True, bindMethod=0, skinMethod=0, normalizeWeights=1, name=f"{self.side}_lowerEyelid_SKIN")[0]
    
        cmds.skinPercent(self.upper_skin_cluster, f"{self.upper_rebuild_curve}.cv[0]", tv=[(self.upper_local_jnts[0], 1.0)])
        cmds.skinPercent(self.upper_skin_cluster, f"{self.upper_rebuild_curve}.cv[1]", tv=[(self.upper_local_jnts[0], 0.3), (self.upper_local_jnts[1], 0.7)])
        cmds.skinPercent(self.upper_skin_cluster, f"{self.upper_rebuild_curve}.cv[2]", tv=[(self.upper_local_jnts[1], 1.0)])
        cmds.skinPercent(self.upper_skin_cluster, f"{self.upper_rebuild_curve}.cv[3]", tv=[(self.upper_local_jnts[2], 1)])
        cmds.skinPercent(self.upper_skin_cluster, f"{self.upper_rebuild_curve}.cv[4]", tv=[(self.upper_local_jnts[2], 0.7), (self.upper_local_jnts[-2], 0.3)])
        cmds.skinPercent(self.upper_skin_cluster, f"{self.upper_rebuild_curve}.cv[5]", tv=[(self.upper_local_jnts[-2], 1.0)])
        cmds.skinPercent(self.upper_skin_cluster, f"{self.upper_rebuild_curve}.cv[6]", tv=[(self.upper_local_jnts[-1], 1.0)])

        cmds.skinPercent(self.lower_skin_cluster, f"{self.lower_rebuild_curve}.cv[0]", tv=[(self.lower_local_jnts[0], 1.0)])
        cmds.skinPercent(self.lower_skin_cluster, f"{self.lower_rebuild_curve}.cv[1]", tv=[(self.lower_local_jnts[0], 0.3), (self.lower_local_jnts[1], 0.7)])
        cmds.skinPercent(self.lower_skin_cluster, f"{self.lower_rebuild_curve}.cv[2]", tv=[(self.lower_local_jnts[1], 1.0)])
        cmds.skinPercent(self.lower_skin_cluster, f"{self.lower_rebuild_curve}.cv[3]", tv=[(self.lower_local_jnts[2], 1)])
        cmds.skinPercent(self.lower_skin_cluster, f"{self.lower_rebuild_curve}.cv[4]", tv=[(self.lower_local_jnts[2], 0.7), (self.lower_local_jnts[-2], 0.3)])
        cmds.skinPercent(self.lower_skin_cluster, f"{self.lower_rebuild_curve}.cv[5]", tv=[(self.lower_local_jnts[-2], 1.0)])
        cmds.skinPercent(self.lower_skin_cluster, f"{self.lower_rebuild_curve}.cv[6]", tv=[(self.lower_local_jnts[-1], 1.0)])

    def skinning_joints(self):
        
        """
        Output the skinning joints for the eyelid module, creating one for each vertex on the upper and lower eyelid curves.
        """

        self.upper_skin_joints = []
        self.lower_skin_joints = []

        upper_cvs = cmds.ls(self.linear_upper_curve + ".cv[*]", fl=True)
        lower_cvs = cmds.ls(self.linear_lower_curve + ".cv[*]", fl=True)

        for i, cv in enumerate(upper_cvs):

            cv_pos = cmds.xform(cv, q=True, t=True, ws=True)
            parameter = self.getClosestParamToPosition(self.upper_rebuild_curve, cv_pos) # Get the closest parameter on the curve to the CV position

            mtp = cmds.createNode("motionPath", name=f"{self.side}_upperEyelid0{i}_MTP", ss=True)
            four_by_four_matrix = cmds.createNode("fourByFourMatrix", name=f"{self.side}_upperEyelid0{i}_F4X4", ss=True)

            cmds.setAttr(f"{mtp}.uValue", parameter) # Set the parameter value
            cmds.connectAttr(f"{self.upper_rebuild_curve}.worldSpace[0]", f"{mtp}.geometryPath")

            cmds.connectAttr(f"{mtp}.allCoordinates.xCoordinate", f"{four_by_four_matrix}.in30", f=True)
            cmds.connectAttr(f"{mtp}.allCoordinates.yCoordinate", f"{four_by_four_matrix}.in31", f=True)
            cmds.connectAttr(f"{mtp}.allCoordinates.zCoordinate", f"{four_by_four_matrix}.in32", f=True)

            if self.side == "R":
                float_constant = cmds.createNode("floatConstant", name=f"{self.side}_upperEyelid0{i}_FLC", ss=True)
                cmds.setAttr(f"{float_constant}.inFloat", -1) 
                cmds.connectAttr(f"{float_constant}.outFloat", f"{four_by_four_matrix}.in00") # -1 Scale X for mirroring

            parent_matrix = cmds.createNode("parentMatrix", name=f"{self.side}_upperEyelid0{i}_PMT", ss=True)
            four_by_four_matrix_origin = cmds.createNode("fourByFourMatrix", name=f"{self.side}_upperEyelid0{i}Origin_F4X4", ss=True)
            cmds.connectAttr(f"{self.linear_upper_curve}Shape.editPoints[{i}].xValueEp", f"{four_by_four_matrix_origin}.in30", f=True)
            cmds.connectAttr(f"{self.linear_upper_curve}Shape.editPoints[{i}].yValueEp", f"{four_by_four_matrix_origin}.in31", f=True)
            cmds.connectAttr(f"{self.linear_upper_curve}Shape.editPoints[{i}].zValueEp", f"{four_by_four_matrix_origin}.in32", f=True)

            cmds.connectAttr(f"{four_by_four_matrix_origin}.output", f"{parent_matrix}.inputMatrix") # Connect the four by four matrix to the parent matrix input
            cmds.connectAttr(f"{four_by_four_matrix}.output", f"{parent_matrix}.target[0].targetMatrix") # Connect the origin four by four matrix to the parent matrix target
            
            jnt_aim = cmds.createNode("joint", name=f"{self.side}_upperEyelid0{i}Center_JNT", ss=True, p=self.skeleton_grp) # Create aim joint for orientation reference
            jnt = cmds.createNode("joint", name=f"{self.side}_upperEyelid0{i}Tip_JNT", ss=True, p=jnt_aim) # Create skinning joint
            
            aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_upperEyelid0{i}_AIM", ss=True)
            cmds.connectAttr(f"{self.eye_guide[0]}.worldMatrix[0]", f"{aim_matrix}.inputMatrix")
            cmds.setAttr(f"{aim_matrix}.primaryInputAxis", 0, 0, 1)
            cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{aim_matrix}.primaryTargetMatrix")
            cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{jnt_aim}.offsetParentMatrix") # Connect the aim matrix to the four by four matrix
            temp_trn = cmds.createNode("transform", name=f"{self.side}_upperEyelid0{i}_TEMP", ss=True)
            cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{temp_trn}.offsetParentMatrix")
            cmds.matchTransform(jnt, temp_trn)
            cmds.delete(temp_trn)

            self.upper_skin_joints.append(jnt)

        for i, cv in enumerate(lower_cvs):
            cv_pos = cmds.xform(cv, q=True, t=True, ws=True)
            parameter = self.getClosestParamToPosition(self.lower_rebuild_curve, cv_pos)
            mtp = cmds.createNode("motionPath", name=f"{self.side}_lowerEyelid0{i}_MTP", ss=True)
            four_by_four_matrix = cmds.createNode("fourByFourMatrix", name=f"{self.side}_lowerEyelid0{i}_F4X4", ss=True)
            cmds.setAttr(f"{mtp}.uValue", parameter) # Set the parameter value
            cmds.connectAttr(f"{self.lower_rebuild_curve}.worldSpace[0]", f"{mtp}.geometryPath")
            cmds.connectAttr(f"{mtp}.allCoordinates.xCoordinate", f"{four_by_four_matrix}.in30", f=True)
            cmds.connectAttr(f"{mtp}.allCoordinates.yCoordinate", f"{four_by_four_matrix}.in31", f=True)
            cmds.connectAttr(f"{mtp}.allCoordinates.zCoordinate", f"{four_by_four_matrix}.in32", f=True)
            if self.side == "R":
                float_constant = cmds.createNode("floatConstant", name=f"{self.side}_lowerEyelid0{i}_FLC", ss=True)
                cmds.setAttr(f"{float_constant}.inFloat", -1) 
                cmds.connectAttr(f"{float_constant}.outFloat", f"{four_by_four_matrix}.in00")
            parent_matrix = cmds.createNode("parentMatrix", name=f"{self.side}_lowerEyelid0{i}_PMT", ss=True)
            four_by_four_matrix_origin = cmds.createNode("fourByFourMatrix", name=f"{self.side}_lowerEyelid0{i}Origin_F4X4", ss=True)
            cmds.connectAttr(f"{self.linear_lower_curve}Shape.editPoints[{i}].xValueEp", f"{four_by_four_matrix_origin}.in30", f=True)
            cmds.connectAttr(f"{self.linear_lower_curve}Shape.editPoints[{i}].yValueEp", f"{four_by_four_matrix_origin}.in31", f=True)
            cmds.connectAttr(f"{self.linear_lower_curve}Shape.editPoints[{i}].zValueEp", f"{four_by_four_matrix_origin}.in32", f=True)
            cmds.connectAttr(f"{four_by_four_matrix_origin}.output", f"{parent_matrix}.inputMatrix") # Connect the four by four matrix to the parent matrix input
            cmds.connectAttr(f"{four_by_four_matrix}.output", f"{parent_matrix}.target[0].targetMatrix") # Connect the origin four by four matrix to the parent matrix target
            jnt_aim = cmds.createNode("joint", name=f"{self.side}_lowerEyelid0{i}Center_JNT", ss=True, p=self.skeleton_grp) # Create aim joint for orientation reference
            jnt = cmds.createNode("joint", name=f"{self.side}_lowerEyelid0{i}Tip_JNT", ss=True, p=jnt_aim) # Create skinning joint
            aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_lowerEyelid0{i}_AIM", ss=True)
            cmds.connectAttr(f"{self.eye_guide[0]}.worldMatrix[0]", f"{aim_matrix}.inputMatrix")
            cmds.setAttr(f"{aim_matrix}.primaryInputAxis", 0, 0, 1)
            cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{aim_matrix}.primaryTargetMatrix")
            cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{jnt_aim}.offsetParentMatrix") # Connect the aim matrix to the four by four matrix
            temp_trn = cmds.createNode("transform", name=f"{self.side}_lowerEyelid0{i}_TEMP", ss=True)
            cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{temp_trn}.offsetParentMatrix")
            cmds.matchTransform(jnt, temp_trn)
            cmds.delete(temp_trn)
            self.lower_skin_joints.append(jnt)

        

    def get_offset_matrix(self, child, parent):

        """
        Calculate the offset matrix between a child and parent transform in Maya.
        Args:
            child (str): The name of the child transform.
            parent (str): The name of the parent transform. 
        Returns:
            om.MMatrix: The offset matrix that transforms the child into the parent's space.
        """
        # om.MGlobal.getSelectionListByName("aads")

        child_dag = om.MSelectionList().add(child).getDagPath(0)
        parent_dag = om.MSelectionList().add(parent).getDagPath(0)

        child_world_matrix = child_dag.inclusiveMatrix()
        parent_world_matrix = parent_dag.inclusiveMatrix()
        
        offset_matrix = child_world_matrix * parent_world_matrix.inverse()

        
        return offset_matrix
    
       
    
    def local(self, ctl, guide):

        """
        Create a local transform node for a controller.
        Args:
            ctl (str): The name of the controller.
        Returns:
            str: The name of the local transform node.
        """

        grp = ctl.replace("_CTL", "_GRP")
        local_jnt = cmds.createNode("joint", name=ctl.replace("_CTL", "_JNT"), ss=True)
        mult_matrix = cmds.createNode("multMatrix", name=ctl.replace("_CTL", "Local_MMT"))
        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{mult_matrix}.matrixIn[0]")
        cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]") 
        cmds.connectAttr(f"{guide}.output", f"{mult_matrix}.matrixIn[2]") # Connect the four by four matrix of the guide to the mult matrix
        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{local_jnt}.offsetParentMatrix")

        return local_jnt
    
    def constraints_callback(self, guide, driven, drivers=[]):

        """
        Create a parent constraint between a driven object and multiple driver objects with equal weights.
        Args:
            driven (str): The name of the driven object.
            drivers (list): A list of driver objects.
        """
        suffix = driven.split("_")[-1]
        driven_ctl = driven.replace(suffix, "CTL")
        driven_jnt = driven.replace(suffix, "JNT")
        parent_matrix = cmds.createNode("parentMatrix", name=driven.replace(suffix, "PMT"), ss=True)
        cmds.connectAttr(f"{guide}.output", f"{parent_matrix}.inputMatrix")
        cmds.connectAttr(f"{drivers[0]}.worldMatrix[0]", f"{parent_matrix}.target[0].targetMatrix")
        cmds.connectAttr(f"{drivers[1]}.worldMatrix[0]", f"{parent_matrix}.target[1].targetMatrix")
        cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{driven}.offsetParentMatrix", force=True)
        cmds.setAttr(f"{parent_matrix}.target[0].weight", 0.7) # Up or Down controllers have more influence
        cmds.setAttr(f"{parent_matrix}.target[1].weight", 0.3) # In or Out controllers have less influence
        
        cmds.setAttr(f"{driven}.inheritsTransform", 0)
        cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", self.get_offset_matrix(driven, drivers[0]), type="matrix") # Calculate offset matrix between driven and driver
        cmds.setAttr(f"{parent_matrix}.target[1].offsetMatrix", self.get_offset_matrix(driven, drivers[1]), type="matrix") # Calculate offset matrix between driven and driver
        
        cmds.connectAttr(f"{driven_ctl}.worldMatrix[0]", f"{driven_jnt}.offsetParentMatrix", force=True)


        return parent_matrix
    
    def getClosestParamToPosition(self, curve, position):
        """
        Returns the closest parameter (u) on the given NURBS curve to a world-space position.
        
        Args:
            curve (str or MObject or MDagPath): The curve to evaluate.
            position (list or tuple): A 3D world-space position [x, y, z].

        Returns:
            float: The parameter (u) value on the curve closest to the given position.
        """
        if isinstance(curve, str):
            sel = om.MSelectionList()
            sel.add(curve)
            curve_dag_path = sel.getDagPath(0)
        elif isinstance(curve, om.MObject):
            curve_dag_path = om.MDagPath.getAPathTo(curve)
        elif isinstance(curve, om.MDagPath):
            curve_dag_path = curve
        else:
            raise TypeError("Curve must be a string name, MObject, or MDagPath.")

        curve_fn = om.MFnNurbsCurve(curve_dag_path)

        point = om.MPoint(*position)

        closest_point, paramU = curve_fn.closestPoint(point, space=om.MSpace.kWorld)

        return paramU

            
cmds.file(new=True, force=True)
# core.DataManager.set_guide_data("C:/3ero/TFG/puiastre_tools/guides/AYCHEDRAL_009.guides")
# core.DataManager.set_ctls_data("C:/3ero/TFG/puiastre_tools/curves/AYCHEDRAL_curves_001.json")

core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/AYCHEDRAL_015.guides")
core.DataManager.set_ctls_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/curves/AYCHEDRAL_curves_001.json")


basic_structure.create_basic_structure()
a = EyelidModule("L_eye_GUIDE").make()
