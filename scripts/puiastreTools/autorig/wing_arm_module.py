"""
Arm system for the dragon wing.

"""

import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import data_export
import maya.api.OpenMaya as om
import math
import os
from importlib import reload
import math
reload(guides_manager)

class WingArmModule(object):

    """
    
    """
    def __init__(self):
        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")

    
    def make(self, side):
        """
        Call all the functions to create the arm module.
        
        """
        self.side = side

        self.module_trn = cmds.createNode("transform", n=f"{self.side}_wingArmModule_GRP", p=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", n=f"{self.side}_wingArmControllers_GRP", p=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", n=f"{self.side}_wingArmSkinningJoints_GRP", p=self.skel_grp)

        self.duplicate_guides()
        self.pair_blends()
        self.set_controllers()
        self.handles_setup()
        self.soft_stretch()
        self.pole_vector_setup()
        self.bendy_curves_setup()
        self.hooks()
        self.twists_setup()

        data_exporter = data_export.DataExport()
        data_exporter.append_data(
            f"{self.side}_armModule",
            {
                "skinning_joints": self.skinning_joints,
                "armIk": self.wrist_ik_ctl,
                "armSettings": self.settings_curve_ctl,
                "armPV": self.pole_vector_ctl,
                "shoulderFK": self.arm_fk_controllers[0],
                "armRoot": self.root_ctl,
            }
        )


    def lock_attrs(self, ctl, attrs):

        """
        Lock and hide attributes on a controller.
        Args:
            ctl (str): The name of the controller.
            attrs (list): A list of attributes to lock and hide.
        """
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def duplicate_guides(self):

        """
        Duplicate the guides for the arm module and rename them according to the naming convention.
        """
        
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
                all_descendents=True)
            cmds.parent(guides[0], self.module_trn)

            for joint in guides:
                chain.append(cmds.rename(joint, joint.replace('_JNT', f'{name}_JNT')))

    def pair_blends(self):

        """
        Create pairBlend nodes for the FK and IK chains to allow blending between them.
        """
        
        self.pair_blend_nodes = []
        for i, joint in enumerate(self.blend_chain):
            
            self.pair_blend_node = cmds.createNode("pairBlend", n=f"{joint.replace('_JNT', '_PBL')}")
            cmds.connectAttr(f"{self.ik_chain[i]}.translate", f"{self.pair_blend_node}.inTranslate1")
            cmds.connectAttr(f"{self.fk_chain[i]}.translate", f"{self.pair_blend_node}.inTranslate2")
            cmds.connectAttr(f"{self.ik_chain[i]}.rotate", f"{self.pair_blend_node}.inRotate1")
            cmds.connectAttr(f"{self.fk_chain[i]}.rotate", f"{self.pair_blend_node}.inRotate2")
            cmds.connectAttr(f"{self.pair_blend_node}.outTranslate", f"{joint}.translate")
            cmds.connectAttr(f"{self.pair_blend_node}.outRotate", f"{joint}.rotate")
            self.pair_blend_nodes.append(self.pair_blend_node)


    def set_controllers(self):

        """
        Create the controllers for the arm module, including FK and IK controllers, and set their attributes.
        """
        
        # --- FK/IK Switch Controller ---
        self.settings_curve_ctl, self.settings_curve_grp = curve_tool.controller_creator(f"{self.side}_ArmSettings", suffixes = ["GRP"])
        
        position, rotation = guides_manager.guide_import(joint_name=f"{self.side}_armSettings")
        cmds.xform(self.settings_curve_grp[0], ws=True, translation=position)
        cmds.xform(self.settings_curve_grp[0], ws=True, rotation=rotation)
        
        cmds.addAttr(self.settings_curve_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        self.lock_attrs(self.settings_curve_ctl, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"])
        cmds.parent(self.settings_curve_grp[0], self.controllers_trn)

        for node in self.pair_blend_nodes:
            cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{node}.weight")

        
        self.arm_fk_controllers_trn = cmds.createNode("transform", n=f"{self.side}_wingArmFKControllers_GRP", p=self.controllers_trn)
        self.arm_ik_controllers_trn = cmds.createNode("transform", n=f"{self.side}_wingArmIKControllers_GRP", p=self.controllers_trn)

        reverse_vis = cmds.createNode("reverse", n=f"{self.side}_wingArmReverseVis_REV")
        cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{reverse_vis}.inputX")
        cmds.connectAttr(f"{reverse_vis}.outputX", f"{self.arm_ik_controllers_trn}.visibility")
        cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{self.arm_fk_controllers_trn}.visibility")
    


        # --- FK/IK Controllers ---
        self.arm_fk_controllers = []
        self.arm_fk_trns = []

        for i, joint in enumerate(self.fk_chain):
            ctl, grp = curve_tool.controller_creator(f"{self.side}_wingArm{i+1}Fk", suffixes=["GRP", "OFF"])
            cmds.parent(grp[0], self.arm_fk_controllers_trn)
            cmds.matchTransform(grp[0], joint, pos=True, rot=True)
            cmds.parentConstraint(ctl, joint, mo=True)
            self.lock_attrs(ctl, ["sx", "sy", "sz", "v"])
            if self.arm_fk_controllers:
                cmds.parent(grp[0], self.arm_fk_controllers[-1])
            self.arm_fk_trns.append(grp)
            self.arm_fk_controllers.append(ctl)



        self.arm_ik_controllers = []

        self.root_ctl, self.root_grp = curve_tool.controller_creator(f"{self.side}_wingArmRoot", suffixes=["GRP", "OFF"])
        self.lock_attrs(self.root_ctl, ["sx", "sy", "sz", "v"])
        self.wrist_ik_ctl, self.wrist_ik_grp = curve_tool.controller_creator(f"{self.side}_wingArmWrist", suffixes=["GRP", "OFF"])
        self.lock_attrs(self.wrist_ik_ctl, ["sx", "sy", "sz", "v"])
        # cmds.orientConstraint(self.wrist_ik_ctl, self.ik_chain[-1], mo=True)
        cmds.matchTransform(self.root_grp[0], self.ik_chain[0], pos=True, rot=True) 
        cmds.matchTransform(self.wrist_ik_grp[0], self.ik_chain[-1], pos=True, rot=True)
        cmds.orientConstraint(self.wrist_ik_ctl, self.ik_chain[-1], mo=True)
        self.arm_ik_controllers.append(self.root_ctl)
        self.arm_ik_controllers.append(self.wrist_ik_ctl)
        cmds.parent(self.root_grp[0], self.wrist_ik_grp[0], self.arm_ik_controllers_trn)

    def handles_setup(self):

        """
        Create the IK handles for the arm module, including the main IK handle and the upper and lower roll IK handles.
        """

        # --- Ik Handle ---
        self.main_ik_handle = cmds.ikHandle(
            n=f"{self.side}_wingArm_HDL",
            sj=self.ik_chain[0],
            ee=self.ik_chain[-1],
            sol="ikRPsolver",
        )[0]
        # Later parent cosntraint to the armSoft TRN
        
        cmds.select(clear=True)
        self.upper_non_roll_jnt = cmds.joint(n=f"{self.side}_wingArmUpperNonRoll_JNT")
        self.upper_non_roll_end_jnt = cmds.joint(n=f"{self.side}_wingArmUpperNonRollEnd_JNT")
        cmds.matchTransform(self.upper_non_roll_jnt, self.ik_chain[0], pos=True, rot=True)
        cmds.matchTransform(self.upper_non_roll_end_jnt, self.ik_chain[1], pos=True, rot=True)
        cmds.select(cl=True)

        self.upper_roll_jnt = cmds.joint(n=f"{self.side}_wingArmUpperRoll_JNT")
        self.upper_roll_end_jnt = cmds.joint(n=f"{self.side}_wingArmUpperRollEnd_JNT")
        cmds.matchTransform(self.upper_roll_jnt, self.ik_chain[0], pos=True, rot=True)
        cmds.matchTransform(self.upper_roll_end_jnt, self.ik_chain[1], pos=True, rot=True)
        cmds.parent(self.upper_roll_jnt, self.upper_non_roll_jnt)
    
        
        self.upper_non_roll_ik_handle = cmds.ikHandle(
            n=f"{self.side}_wingArmUpperNonRoll_HDL",
            sj=self.upper_non_roll_jnt,
            ee=self.upper_non_roll_end_jnt,
            sol="ikSCsolver",
        )[0]
        cmds.parentConstraint(self.blend_chain[1], self.upper_non_roll_ik_handle, mo=False)

        self.upper_roll_ik_handle = cmds.ikHandle(
            n=f"{self.side}_wingArmUpperRoll_HDL",
            sj=self.upper_roll_jnt,
            ee=self.upper_roll_end_jnt,
            sol="ikSCsolver",
        )[0]
        cmds.parentConstraint(self.blend_chain[1], self.upper_roll_ik_handle, mo=False)

        # --- Lower Roll Ik Handle ---
        
        self.lower_roll_offset = cmds.createNode("transform", n=f"{self.side}_wingArmLowerRollOffset_GRP")
        cmds.select(clear=True)
        self.lower_roll_jnt = cmds.joint(n=f"{self.side}_wingArmLowerRoll_JNT")
        self.lower_roll_end_jnt = cmds.joint(n=f"{self.side}_wingArmLowerRollEnd_JNT")
        cmds.parent(self.lower_roll_jnt, self.lower_roll_offset)
        cmds.matchTransform(self.lower_roll_offset, self.ik_chain[1], pos=True, rot=True)
        cmds.matchTransform(self.lower_roll_jnt, self.ik_chain[1], pos=True, rot=True)
        cmds.matchTransform(self.lower_roll_end_jnt, self.ik_chain[-1], pos=True, rot=True)
        cmds.parentConstraint(self.blend_chain[1], self.lower_roll_offset, mo=False)

        

        self.lower_roll_handle = cmds.ikHandle(
            n=f"{self.side}_wingArmLowerRoll_HDL",
            sj=self.lower_roll_jnt,
            ee=self.lower_roll_end_jnt,
            sol="ikSCsolver",
        )[0]
        cmds.parentConstraint(self.blend_chain[-1], self.lower_roll_handle, mo=True)

        cmds.parent(self.lower_roll_handle, self.main_ik_handle, self.upper_non_roll_ik_handle, self.upper_roll_ik_handle, self.lower_roll_offset, self.upper_non_roll_jnt, self.module_trn)

   
    def soft_stretch(self):

        """
        Create the stretchy setup for the arm module, including stretchy FK controllers and stretchy IK controllers.
        """

        # --- Stretchy FK Controllers ---

        for ctl in self.arm_fk_controllers:
            cmds.addAttr(ctl, shortName="STRETCHY____", attributeType="enum", enumName="____", keyable=True)
            cmds.setAttr(f"{ctl}.STRETCHY____", lock=True, keyable=False)
            cmds.addAttr(ctl, shortName="Stretch", minValue=0, defaultValue=1, keyable=True)

        self.upper_double_mult_linear = cmds.createNode("multDoubleLinear", n=f"{self.side}_wingArmUpperDoubleMultLinear_MDL")
        self.lower_double_mult_linear = cmds.createNode("multDoubleLinear", n=f"{self.side}_wingArmLowerDoubleMultLinear_MDL")
        cmds.connectAttr(f"{self.arm_fk_controllers[0]}.Stretch", f"{self.upper_double_mult_linear}.input1")
        cmds.connectAttr(f"{self.arm_fk_controllers[1]}.Stretch", f"{self.lower_double_mult_linear}.input1")

        upper_distance = cmds.getAttr(f"{self.arm_fk_trns[1][0]}.translateX")
        lower_distance = cmds.getAttr(f"{self.arm_fk_trns[-1][0]}.translateX")


        cmds.setAttr(f"{self.upper_double_mult_linear}.input2", upper_distance)
        cmds.setAttr(f"{self.lower_double_mult_linear}.input2", lower_distance)
        cmds.connectAttr(f"{self.upper_double_mult_linear}.output", f"{self.arm_fk_trns[1][0]}.translateX")
        cmds.connectAttr(f"{self.lower_double_mult_linear}.output", f"{self.arm_fk_trns[-1][0]}.translateX")


        # --- Stretchy IK Controllers ---
        cmds.addAttr(self.wrist_ik_ctl, shortName="STRETCHY____", attributeType="enum", enumName="____", keyable=True)
        cmds.setAttr(f"{self.wrist_ik_ctl}.STRETCHY____", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.wrist_ik_ctl, shortName="upperLengthMult", minValue=0.001, defaultValue=1, keyable=True)
        cmds.addAttr(self.wrist_ik_ctl, shortName="lowerLengthMult", minValue=0.001, defaultValue=1, keyable=True)
        cmds.addAttr(self.wrist_ik_ctl, shortName="Stretch", minValue=0, defaultValue=0, maxValue=1, keyable=True)
        cmds.addAttr(self.wrist_ik_ctl, shortName="SOFT____", attributeType="enum", enumName="____", keyable=True)
        cmds.setAttr(f"{self.wrist_ik_ctl}.SOFT____", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.wrist_ik_ctl, shortName="Soft", minValue=0, defaultValue=0, maxValue=1, keyable=True)
        
        
        

        masterwalk = "C_masterwalk_CTL" # Change this to the actual masterwalk controller name

        self.soft_off = cmds.createNode("transform", name=f"{self.side}_armSoft_OFF", p=self.module_trn)
        cmds.pointConstraint(self.arm_ik_controllers[0], self.soft_off)
        cmds.aimConstraint(self.wrist_ik_ctl, self.soft_off, aimVector=(1, 0, 0), upVector=(0, 1, 0), worldUpType="vector", mo=False)

        self.soft_trn = cmds.createNode("transform", name=f"{self.side}_armSoft_TRN", p=self.soft_off)
        cmds.matchTransform(self.soft_trn, self.blend_chain[-1], pos=True)



        nodes_to_create = {
        f"{self.side}_armDistanceToControl_DBT": ("distanceBetween", None),  # 0
        f"{self.side}_armDistanceToControlNormalized_DBT": ("floatMath", 3),  # 1
        f"{self.side}_armSoftValue_RMV": ("remapValue", None),  # 2
        f"{self.side}_armDistanceToControlMinusSoftDistance_FLM": ("floatMath", 1),  # 3
        f"{self.side}_armUpperLength_FLM": ("floatMath", 2),  # 4
        f"{self.side}_armDistanceToControlMinusSoftDistanceDividedBySoftValue_FLM": ("floatMath", 3),  # 5
        f"{self.side}_armFullLength_FLM": ("floatMath", 0),  # 6
        f"{self.side}_armDistanceToControlMinusSoftDistanceDividedBySoftValueNegate_FLM": ("floatMath", 2),  # 7
        f"{self.side}_armSoftDistance_FLM": ("floatMath", 1),  # 8
        f"{self.side}_armSoftEPower_FLM": ("floatMath", 6),  # 9
        f"{self.side}_armLowerLength_FLM": ("floatMath", 2),  # 10
        f"{self.side}_armSoftOneMinusEPower_FLM": ("floatMath", 1),  # 11
        f"{self.side}_armSoftOneMinusEPowerSoftValueEnable_FLM": ("floatMath", 2),  # 12
        f"{self.side}_armSoftConstant_FLM": ("floatMath", 0),  # 13
        f"{self.side}_armLengthRatio_FLM": ("floatMath", 3),  # 14
        f"{self.side}_armSoftRatio_FLM": ("floatMath", 3),  # 15
        f"{self.side}_armDistanceToControlDividedByTheLengthRatio_FLM": ("floatMath", 3),  # 16
        f"{self.side}_armSoftEffectorDistance_FLM": ("floatMath", 2),  # 17
        f"{self.side}_armSoftCondition_CON": ("condition", None),  # 18
        f"{self.side}_armUpperLengthStretch_FLM": ("floatMath", 2),  # 19
        f"{self.side}_armDistanceToControlDividedByTheSoftEffector_FLM": ("floatMath", 3),  # 20
        f"{self.side}_armDistanceToControlDividedByTheSoftEffectorMinusOne_FLM": ("floatMath", 1),  # 21
        f"{self.side}_armDistanceToControlDividedByTheSoftEffectorMinusOneMultipliedByTheStretch_FLM": ("floatMath", 2),  # 22
        f"{self.side}_armStretchFactor_FLM": ("floatMath", 0),  # 23
        f"{self.side}_armSoftEffectStretchDistance_FLM": ("floatMath", 2),  # 24
        f"{self.side}_armLowerLengthStretch_FLM": ("floatMath", 2),  # 25
        }

        self.created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            self.created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        # Connections between selected nodes
        cmds.connectAttr(self.created_nodes[0] + ".distance", self.created_nodes[1]+".floatA")
        cmds.connectAttr(self.created_nodes[1] + ".outFloat", self.created_nodes[14]+".floatA")
        cmds.connectAttr(self.created_nodes[1] + ".outFloat", self.created_nodes[3]+".floatA")
        cmds.connectAttr(self.created_nodes[1] + ".outFloat", self.created_nodes[16]+".floatA")
        cmds.connectAttr(self.created_nodes[1] + ".outFloat", self.created_nodes[18]+".firstTerm")
        cmds.connectAttr(self.created_nodes[1] + ".outFloat", self.created_nodes[18]+".colorIfFalseR")
        cmds.connectAttr(self.created_nodes[1] + ".outFloat", self.created_nodes[20]+".floatA")
        cmds.connectAttr(self.created_nodes[2] + ".outValue", self.created_nodes[5]+".floatB")
        cmds.connectAttr(self.created_nodes[2] + ".outValue", self.created_nodes[8]+".floatB")
        cmds.connectAttr(self.created_nodes[2] + ".outValue", self.created_nodes[12]+".floatA")
        cmds.connectAttr(self.created_nodes[3] + ".outFloat", self.created_nodes[5]+".floatA")
        cmds.connectAttr(self.created_nodes[8] + ".outFloat", self.created_nodes[3]+".floatB")
        cmds.connectAttr(self.created_nodes[4] + ".outFloat", self.created_nodes[18]+".colorIfFalseG")
        cmds.connectAttr(self.created_nodes[4] + ".outFloat", self.created_nodes[6]+".floatA")
        cmds.connectAttr(self.created_nodes[4] + ".outFloat", self.created_nodes[19]+".floatB")
        cmds.connectAttr(self.created_nodes[5] + ".outFloat", self.created_nodes[7]+".floatA")
        cmds.connectAttr(self.created_nodes[6] + ".outFloat", self.created_nodes[15]+".floatB")
        cmds.connectAttr(self.created_nodes[6] + ".outFloat", self.created_nodes[8]+".floatA")
        cmds.connectAttr(self.created_nodes[6] + ".outFloat", self.created_nodes[14]+".floatB")
        cmds.connectAttr(self.created_nodes[10] + ".outFloat", self.created_nodes[6]+".floatB")
        cmds.connectAttr(self.created_nodes[7] + ".outFloat", self.created_nodes[9]+".floatB")
        cmds.connectAttr(self.created_nodes[8] + ".outFloat", self.created_nodes[13]+".floatB")
        cmds.connectAttr(self.created_nodes[8] + ".outFloat", self.created_nodes[18]+".secondTerm")
        cmds.connectAttr(self.created_nodes[9] + ".outFloat", self.created_nodes[11]+".floatB")
        cmds.connectAttr(self.created_nodes[10] + ".outFloat", self.created_nodes[18]+".colorIfFalseB")
        cmds.connectAttr(self.created_nodes[10] + ".outFloat", self.created_nodes[25]+".floatB")
        cmds.connectAttr(self.created_nodes[11] + ".outFloat", self.created_nodes[12]+".floatB")
        cmds.connectAttr(self.created_nodes[12] + ".outFloat", self.created_nodes[13]+".floatA")
        cmds.connectAttr(self.created_nodes[13] + ".outFloat", self.created_nodes[15]+".floatA")
        cmds.connectAttr(self.created_nodes[14] + ".outFloat", self.created_nodes[16]+".floatB")
        cmds.connectAttr(self.created_nodes[15] + ".outFloat", self.created_nodes[17]+".floatA")
        cmds.connectAttr(self.created_nodes[16] + ".outFloat", self.created_nodes[17]+".floatB")
        cmds.connectAttr(self.created_nodes[17] + ".outFloat", self.created_nodes[24]+".floatA")
        cmds.connectAttr(self.created_nodes[17] + ".outFloat", self.created_nodes[20]+".floatB")
        cmds.connectAttr(self.created_nodes[24] + ".outFloat", self.created_nodes[18]+".colorIfTrueR")
        cmds.connectAttr(self.created_nodes[19] + ".outFloat", self.created_nodes[18]+".colorIfTrueG")
        cmds.connectAttr(self.created_nodes[25] + ".outFloat", self.created_nodes[18]+".colorIfTrueB")
        cmds.connectAttr(self.created_nodes[23] + ".outFloat", self.created_nodes[19]+".floatA")
        cmds.connectAttr(self.created_nodes[20] + ".outFloat", self.created_nodes[21]+".floatA")
        cmds.connectAttr(self.created_nodes[21] + ".outFloat", self.created_nodes[22]+".floatA")
        cmds.connectAttr(self.created_nodes[22] + ".outFloat", self.created_nodes[23]+".floatA")
        cmds.connectAttr(self.created_nodes[23] + ".outFloat", self.created_nodes[24]+".floatB")
        cmds.connectAttr(self.created_nodes[23] + ".outFloat", self.created_nodes[25]+".floatA")

        cmds.setAttr(f"{self.created_nodes[9]}.floatA", math.e)
        cmds.setAttr(f"{self.created_nodes[4]}.floatB", abs(cmds.getAttr(f"{self.ik_chain[1]}.translateX")))
        cmds.setAttr(f"{self.created_nodes[10]}.floatB", abs(cmds.getAttr(f"{self.ik_chain[-1]}.translateX")))
        cmds.setAttr(f"{self.created_nodes[2]}.outputMin", 0.001)
        cmds.setAttr(f"{self.created_nodes[2]}.outputMax", 154.162)
        cmds.setAttr(f"{self.created_nodes[7]}.floatB", -1.0)
        cmds.setAttr(f"{self.created_nodes[18]}.operation", 2)

        cmds.connectAttr(f"{self.wrist_ik_ctl}.upperLengthMult", f"{self.created_nodes[4]}.floatA")
        cmds.connectAttr(f"{self.wrist_ik_ctl}.lowerLengthMult", f"{self.created_nodes[10]}.floatA")
        cmds.connectAttr(f"{self.wrist_ik_ctl}.Stretch", f"{self.created_nodes[22]}.floatB")
        cmds.connectAttr(f"{self.wrist_ik_ctl}.worldMatrix[0]", f"{self.created_nodes[0]}.inMatrix2")
        cmds.connectAttr(f"{self.wrist_ik_ctl}.Soft", f"{self.created_nodes[2]}.inputValue")

        cmds.connectAttr(f"{self.root_ctl}.worldMatrix[0]", f"{self.created_nodes[0]}.inMatrix1")
        if cmds.ls(masterwalk):
            cmds.connectAttr(f"{masterwalk}.globalScale", f"{self.created_nodes[1]}.inputB")
        else:
            pass
        

        cmds.connectAttr(f"{self.created_nodes[18]}.outColorR", f"{self.soft_trn}.translateX")
        if self.side == "L":
            cmds.connectAttr(f"{self.created_nodes[18]}.outColorG", f"{self.ik_chain[1]}.translateX")
            cmds.connectAttr(f"{self.created_nodes[18]}.outColorB", f"{self.ik_chain[-1]}.translateX")
        else:
            abs_up = cmds.createNode("floatMath", n=f"{self.side}_wingArmAbsUpper_FLM")
            abs_low = cmds.createNode("floatMath", n=f"{self.side}_wingArmAbsLower_FLM")
            cmds.setAttr(f"{abs_up}.operation", 2)
            cmds.setAttr(f"{abs_low}.operation", 2)
            cmds.setAttr(f"{abs_up}.floatB", -1)
            cmds.setAttr(f"{abs_low}.floatB", -1)
            cmds.connectAttr(f"{self.created_nodes[18]}.outColorG", f"{abs_up}.floatA")
            cmds.connectAttr(f"{self.created_nodes[18]}.outColorB", f"{abs_low}.floatA")
            cmds.connectAttr(f"{abs_up}.outFloat", f"{self.ik_chain[1]}.translateX")
            cmds.connectAttr(f"{abs_low}.outFloat", f"{self.ik_chain[-1]}.translateX")

        cmds.parentConstraint(self.soft_trn, self.main_ik_handle, mo=True)
        cmds.parentConstraint(self.root_ctl, self.ik_chain[0], mo=True)

    def pole_vector_setup(self):

        """
        Create the pole vector controller for the arm module, which will control the elbow position.
        """

        # --- Pole Vector ---
        self.pole_vector_ctl, self.pole_vector_grp = curve_tool.controller_creator(f"{self.side}_wingArmPV", suffixes=["GRP", "OFF"])

        arm_pos = om.MVector(cmds.xform(self.ik_chain[0], q=True, rp=True, ws=True))
        elbow_pos = om.MVector(cmds.xform(self.ik_chain[1], q=True, rp=True, ws=True))
        wrist_pos = om.MVector(cmds.xform(self.ik_chain[2], q=True, rp=True, ws=True))

        arm_to_wrist = wrist_pos - arm_pos
        arm_to_wrist_scaled = arm_to_wrist / 2
        mid_point = arm_pos + arm_to_wrist_scaled
        mid_point_to_elbow_vec = elbow_pos - mid_point
        mid_point_to_elbow_vec_scaled = mid_point_to_elbow_vec * 2
        mid_point_to_elbow_point = mid_point + mid_point_to_elbow_vec_scaled

        cmds.xform(self.pole_vector_grp[0], translation=mid_point_to_elbow_point)



        cmds.parent(self.pole_vector_grp[0], self.arm_ik_controllers_trn)
        cmds.poleVectorConstraint(self.pole_vector_ctl, self.main_ik_handle)
        self.lock_attrs(self.pole_vector_ctl, ["sx", "sy", "sz", "v"])
        

    def bendy_curves_setup(self):

        """
        Create the bendy curves for the arm module, which will be used for the bendy setup.
        """

        # --- Bendy Setup ---
        self.bendy_module_trn = cmds.createNode("transform", n=f"{self.side}_wingArmBendyModule_GRP", p=self.module_trn)

        self.upper_bendy_module = cmds.createNode("transform", n=f"{self.side}_wingArmUpperBendyModule_GRP", p=self.bendy_module_trn)
        cmds.parent(self.upper_non_roll_jnt, self.upper_non_roll_ik_handle, self.upper_roll_ik_handle, self.upper_bendy_module)
        self.lower_bendy_module = cmds.createNode("transform", n=f"{self.side}_wingArmLowerBendyModule_GRP", p=self.bendy_module_trn)
        cmds.parent(self.lower_roll_offset, self.lower_roll_handle, self.lower_bendy_module)

        #--- Bendy Curves ---  
        self.upper_segment_crv = cmds.curve(n=f"{self.side}_wingArmUpperSegment_CRV", d=1, p=[
            cmds.xform(self.ik_chain[0], q=True, ws=True, t=True),
            cmds.xform(self.ik_chain[1], q=True, ws=True, t=True)])
        cmds.parent(self.upper_segment_crv, self.upper_bendy_module)
        self.upper_segment_crv_shape = cmds.rename(cmds.listRelatives(self.upper_segment_crv, s=True), f"{self.side}_wingArmUpperSegment_CRVShape")

        self.lower_segment_crv = cmds.curve(n=f"{self.side}_wingArmLowerSegment_CRV", d=1, p=[
            cmds.xform(self.ik_chain[1], q=True, ws=True, t=True),
            cmds.xform(self.ik_chain[2], q=True, ws=True, t=True)])
        cmds.parent(self.lower_segment_crv, self.lower_bendy_module)
        self.lower_segment_crv_shape = cmds.rename(cmds.listRelatives(self.lower_segment_crv, s=True), f"{self.side}_wingArmLowerSegment_CRVShape")

        shoulder_bendy_dpm = cmds.createNode("decomposeMatrix", n=(self.blend_chain[0].replace('JNT', 'DPM')), ss=True)
        cmds.connectAttr(f"{self.blend_chain[0]}.worldMatrix[0]", f"{shoulder_bendy_dpm}.inputMatrix")
        elbow_bendy_dpm = cmds.createNode("decomposeMatrix", n=(self.blend_chain[1].replace('JNT', 'DPM')), ss=True)
        cmds.connectAttr(f"{self.blend_chain[1]}.worldMatrix[0]", f"{elbow_bendy_dpm}.inputMatrix")
        wrist_bendy_dpm = cmds.createNode("decomposeMatrix", n=(self.blend_chain[2].replace('JNT', 'DPM')), ss=True)
        cmds.connectAttr(f"{self.blend_chain[2]}.worldMatrix[0]", f"{wrist_bendy_dpm}.inputMatrix")

        cmds.connectAttr(f"{shoulder_bendy_dpm}.outputTranslate", f"{self.upper_segment_crv}.controlPoints[0]")
        cmds.connectAttr(f"{elbow_bendy_dpm}.outputTranslate", f"{self.upper_segment_crv}.controlPoints[1]")

        cmds.connectAttr(f"{elbow_bendy_dpm}.outputTranslate", f"{self.lower_segment_crv}.controlPoints[0]")
        cmds.connectAttr(f"{wrist_bendy_dpm}.outputTranslate", f"{self.lower_segment_crv}.controlPoints[1]")



    def hooks(self):
        """
        Create the hooks for the bendy joints, which will allow for bending control.
        """

        # --- Hooks ---
        hook_parameters = [0, 0.5, 1]
        self.upper_bendy_joints = []
        self.lower_bendy_joints = []
        self.bendy_joints = []

        for i, part in enumerate(["Upper", "Lower"]):
            for ii, joint in enumerate(["Root", "Mid", "Tip"]):

                cmds.select(clear=True)
                hook_joint = cmds.joint(n=f"{self.side}_wingArm{part}Bendy{joint}_JNT")
                if i == 0:
                    self.upper_bendy_joints.append(hook_joint)
                else:
                    self.lower_bendy_joints.append(hook_joint)
                
                
                motion_path = cmds.createNode("motionPath", n=f"{self.side}_wingArm{part}Bendy{joint}{i}_MPT")
                cmds.setAttr(f"{motion_path}.frontAxis", 0)
                cmds.setAttr(f"{motion_path}.upAxis", 1)
                cmds.setAttr(f"{motion_path}.worldUpType", 2)
                cmds.setAttr(f"{motion_path}.fractionMode", 1)
                if self.side == "R":
                    cmds.setAttr(f"{motion_path}.inverseFront", 1)

                float_constant = cmds.createNode("floatConstant", n=f"{self.side}_wingArm{part}Bendy{joint}_FCT")
                cmds.setAttr(f"{float_constant}.inFloat", hook_parameters[ii])
                float_math = cmds.createNode("floatMath", n=f"{self.side}_wingArm{part}Bendy{joint}_FLM")
                cmds.setAttr(f"{float_math}.operation", 2)
                cmds.connectAttr(f"{float_constant}.outFloat", f"{float_math}.floatA")
                if i == 0:
                    cmds.connectAttr(f"{self.upper_roll_jnt}.rotateX", f"{float_math}.floatB")
                else:
                    cmds.connectAttr(f"{self.lower_roll_jnt}.rotateX", f"{float_math}.floatB")
                cmds.connectAttr(f"{float_math}.outFloat", f"{motion_path}.frontTwist")
                
                if ii == 1:
                    bendy_ctl, bendy_grp = curve_tool.controller_creator(f"{self.side}_wingArm{part}Bendy{joint}", suffixes=["GRP"])
                    self.lock_attrs(bendy_ctl, ["v"])
                    cmds.parent(bendy_grp[0], self.controllers_trn)

                if i == 0:
                    if ii != 2:
                        cmds.connectAttr(f"{self.blend_chain[0]}.worldMatrix[0]", f"{motion_path}.worldUpMatrix")
                    cmds.parent(hook_joint, self.upper_bendy_module)
                    cmds.connectAttr(f"{float_constant}.outFloat", f"{motion_path}.uValue")
                    cmds.connectAttr(f"{self.upper_segment_crv}.worldSpace[0]", f"{motion_path}.geometryPath")
                    cmds.connectAttr(f"{motion_path}.allCoordinates", f"{hook_joint}.translate")
                    cmds.connectAttr(f"{motion_path}.rotate", f"{hook_joint}.rotate")

                    if ii == 1:
                        cmds.parentConstraint(hook_joint, bendy_grp[0], mo=False)
        
                        bendy_joint = cmds.duplicate(hook_joint, n=f"{self.side}_wingArm{part}Bendy_JNT")
                        self.bendy_joints.append(bendy_joint[0])
                        cmds.parentConstraint(bendy_ctl, bendy_joint, mo=True)
                        cmds.scaleConstraint(bendy_ctl, bendy_joint, mo=True)
                        cmds.setAttr(f"{bendy_joint[0]}.inheritsTransform", 0)

                else:
                    if ii != 2:
                        cmds.connectAttr(f"{self.blend_chain[1]}.worldMatrix[0]", f"{motion_path}.worldUpMatrix")
                    cmds.parent(hook_joint, self.lower_bendy_module)
                    cmds.connectAttr(f"{float_constant}.outFloat", f"{motion_path}.uValue")
                    cmds.connectAttr(f"{self.lower_segment_crv}.worldSpace[0]", f"{motion_path}.geometryPath")
                    cmds.connectAttr(f"{motion_path}.allCoordinates", f"{hook_joint}.translate")
                    cmds.connectAttr(f"{motion_path}.rotate", f"{hook_joint}.rotate")
                    
                    if ii == 1:
                        cmds.parentConstraint(hook_joint, bendy_grp[0], mo=False)

                        bendy_joint = cmds.duplicate(hook_joint, n=f"{self.side}_wingArm{part}Bendy_JNT")
                        self.bendy_joints.append(bendy_joint[0])
                        cmds.parentConstraint(bendy_ctl, bendy_joint, mo=True)
                        cmds.scaleConstraint(bendy_ctl, bendy_joint, mo=True)

                cmds.setAttr(f"{hook_joint}.inheritsTransform", 0)


        self.upper_bendy_bezier = cmds.curve(n=f"{self.side}_wingArmUpperBendyBezier_CRV",d=1,p=[cmds.xform(self.upper_bendy_joints[0], q=True, ws=True, t=True),cmds.xform(self.upper_bendy_joints[1], q=True, ws=True, t=True),cmds.xform(self.upper_bendy_joints[2], q=True, ws=True, t=True)])
        self.upper_bendy_bezier = cmds.rebuildCurve(self.upper_bendy_bezier, rpo=1, rt=0, end=1, kr=0, kep=1, kt=0, fr=0, s=2, d=3, tol=0.01, ch=False)
        self.upper_bendy_bezier_shape = cmds.rename(cmds.listRelatives(self.upper_bendy_bezier, s=True), f"{self.side}_wingArmUpperBendyBezier_CRVShape")
            
        self.upper_bendy_bezier_shape = cmds.listRelatives(self.upper_bendy_bezier, s=True)[0]
        cmds.select(self.upper_bendy_bezier_shape)
        cmds.nurbsCurveToBezier()

        cmds.select(f"{self.upper_bendy_bezier[0]}.cv[6]", f"{self.upper_bendy_bezier[0]}.cv[0]")
        cmds.bezierAnchorPreset(p=2)
        cmds.select(f"{self.upper_bendy_bezier[0]}.cv[3]")
        cmds.bezierAnchorPreset(p=1)
       
        cmds.parent(self.upper_bendy_bezier, self.upper_bendy_module)
        upper_bendy_skin_cluster = cmds.skinCluster(self.upper_bendy_joints[0], self.bendy_joints[0], self.upper_bendy_joints[2], self.upper_bendy_bezier,n=f"{self.side}_wingArmUpperBendyBezier_SKIN")
        
        cmds.skinPercent(upper_bendy_skin_cluster[0], f"{self.upper_bendy_bezier[0]}.cv[0]", transformValue=[self.upper_bendy_joints[0], 1])
        cmds.skinPercent(upper_bendy_skin_cluster[0], f"{self.upper_bendy_bezier[0]}.cv[2]", transformValue=[self.bendy_joints[0], 1])
        cmds.skinPercent(upper_bendy_skin_cluster[0], f"{self.upper_bendy_bezier[0]}.cv[3]", transformValue=[self.bendy_joints[0], 1])
        cmds.skinPercent(upper_bendy_skin_cluster[0], f"{self.upper_bendy_bezier[0]}.cv[4]", transformValue=[self.bendy_joints[0], 1])
        cmds.skinPercent(upper_bendy_skin_cluster[0], f"{self.upper_bendy_bezier[0]}.cv[6]", transformValue=[self.upper_bendy_joints[2], 1])


        self.lower_bendy_bezier = cmds.curve(n=f"{self.side}_wingArmLowerBendyBezier_CRV",d=1,p=[cmds.xform(self.lower_bendy_joints[0], q=True, ws=True, t=True),cmds.xform(self.lower_bendy_joints[1], q=True, ws=True, t=True),cmds.xform(self.lower_bendy_joints[2], q=True, ws=True, t=True)])
        self.lower_bendy_bezier = cmds.rebuildCurve(self.lower_bendy_bezier, rpo=1, rt=0, end=1, kr=0, kep=1, kt=0, fr=0, s=2, d=3, tol=0.01, ch=False)  
        self.lower_bendy_bezier_shape = cmds.rename(cmds.listRelatives(self.lower_bendy_bezier, s=True), f"{self.side}_wingArmLowerBendyBezier_CRVShape")
        
        self.lower_bendy_bezier_shape = cmds.listRelatives(self.lower_bendy_bezier, s=True)[0]

        cmds.select(self.lower_bendy_bezier_shape)
        cmds.nurbsCurveToBezier()

        cmds.select(f"{self.lower_bendy_bezier[0]}.cv[0]", f"{self.lower_bendy_bezier[0]}.cv[6]")
        cmds.bezierAnchorPreset(p=2)
        cmds.select(f"{self.lower_bendy_bezier[0]}.cv[3]")
        cmds.bezierAnchorPreset(p=1)

        cmds.parent(self.lower_bendy_bezier, self.lower_bendy_module)
        
        lower_bendy_skin_cluster = cmds.skinCluster(self.lower_bendy_joints[0], self.bendy_joints[1], self.lower_bendy_joints[2], self.lower_bendy_bezier, tsb=True, n=f"{self.side}_wingArmLowerBendyBezier_SKIN")
        
        cmds.skinPercent(lower_bendy_skin_cluster[0], f"{self.lower_bendy_bezier[0]}.cv[0]", transformValue=[self.lower_bendy_joints[0], 1])
        cmds.skinPercent(lower_bendy_skin_cluster[0], f"{self.lower_bendy_bezier[0]}.cv[2]", transformValue=[self.bendy_joints[1], 1])
        cmds.skinPercent(lower_bendy_skin_cluster[0], f"{self.lower_bendy_bezier[0]}.cv[3]", transformValue=[self.bendy_joints[1], 1])
        cmds.skinPercent(lower_bendy_skin_cluster[0], f"{self.lower_bendy_bezier[0]}.cv[4]", transformValue=[self.bendy_joints[1], 1])
        cmds.skinPercent(lower_bendy_skin_cluster[0], f"{self.lower_bendy_bezier[0]}.cv[6]", transformValue=[self.lower_bendy_joints[2], 1])


    def twists_setup(self):

        """
        Create the twists for the arm module, which will be used for the bendy setup.
        """

        # --- Twists ---
        self.duplicate_bendy_crv = cmds.duplicate(self.upper_bendy_bezier)
        self.upper_bendy_off_curve = cmds.offsetCurve(self.duplicate_bendy_crv, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=1.5, tol=0.01, sd=0, ugn=False, name=f"{self.side}_wingArmUpperBendyBezierOffset_CRV", normal=[0, 0, 1])
        upper_bendy_shape_org = cmds.listRelatives(self.upper_bendy_bezier, allDescendents=True)[-1]
        
        cmds.connectAttr(f"{upper_bendy_shape_org}.worldSpace[0]", f"{self.upper_bendy_off_curve[1]}.inputCurve", f=True)
        cmds.setAttr(f"{self.upper_bendy_off_curve[1]}.useGivenNormal", 1)
        cmds.setAttr(f"{self.upper_bendy_off_curve[1]}.normal", 0, 0, 1, type="double3")
        cmds.parent(self.upper_bendy_off_curve[0], self.upper_bendy_module)
        self.upper_bendy_off_curve_shape = cmds.rename(cmds.listRelatives(self.upper_bendy_off_curve[0], s=True), f"{self.side}_wingArmUpperBendyBezierOffset_CRVShape")
        cmds.delete(self.duplicate_bendy_crv)

        upper_bendy_off_skin_cluster = cmds.skinCluster(self.upper_bendy_joints[0], self.bendy_joints[0], self.upper_bendy_joints[2], self.upper_bendy_off_curve[0], tsb=True, n=f"{self.side}_wingArmUpperBendyBezierOffset_SKIN")

        cmds.skinPercent(upper_bendy_off_skin_cluster[0], f"{self.upper_bendy_off_curve[0]}.cv[0]", transformValue=[self.upper_bendy_joints[0], 1])
        cmds.skinPercent(upper_bendy_off_skin_cluster[0], f"{self.upper_bendy_off_curve[0]}.cv[2]", transformValue=[self.bendy_joints[0], 1])
        cmds.skinPercent(upper_bendy_off_skin_cluster[0], f"{self.upper_bendy_off_curve[0]}.cv[3]", transformValue=[self.bendy_joints[0], 1])
        cmds.skinPercent(upper_bendy_off_skin_cluster[0], f"{self.upper_bendy_off_curve[0]}.cv[4]", transformValue=[self.bendy_joints[0], 1])
        cmds.skinPercent(upper_bendy_off_skin_cluster[0], f"{self.upper_bendy_off_curve[0]}.cv[6]", transformValue=[self.upper_bendy_joints[2], 1])

       
        
        self.duplicate_bendy_crv = cmds.duplicate(self.lower_bendy_bezier)
        self.lower_bendy_off_curve = cmds.offsetCurve(self.duplicate_bendy_crv, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=1.5, tol=0.01, sd=0, ugn=False, name=f"{self.side}_wingArmLowerBendyBezierOffset_CRV", normal=[0, 0, 1])
        lower_bendy_shape_org = cmds.listRelatives(self.lower_bendy_bezier, allDescendents=True)[-1]

        cmds.connectAttr(f"{lower_bendy_shape_org}.worldSpace[0]", f"{self.lower_bendy_off_curve[1]}.inputCurve", f=True)
        cmds.setAttr(f"{self.lower_bendy_off_curve[1]}.useGivenNormal", 1)
        cmds.setAttr(f"{self.lower_bendy_off_curve[1]}.normal", 0, 0, 1, type="double3")
        cmds.parent(self.lower_bendy_off_curve[0], self.lower_bendy_module)
        self.lower_bendy_off_curve_shape = cmds.rename(cmds.listRelatives(self.lower_bendy_off_curve[0], s=True), f"{self.side}_wingArmLowerBendyBezierOffset_CRVShape")
        cmds.delete(self.duplicate_bendy_crv)

        lower_bendy_off_skin_cluster = cmds.skinCluster(self.lower_bendy_joints[0], self.bendy_joints[1], self.lower_bendy_joints[2], self.lower_bendy_off_curve[0], tsb=True, n=f"{self.side}_wingArmLowerBendyBezierOffset_SKIN")

        cmds.skinPercent(lower_bendy_off_skin_cluster[0], f"{self.lower_bendy_off_curve[0]}.cv[0]", transformValue=[self.lower_bendy_joints[0], 1])
        cmds.skinPercent(lower_bendy_off_skin_cluster[0], f"{self.lower_bendy_off_curve[0]}.cv[2]", transformValue=[self.bendy_joints[1], 1])
        cmds.skinPercent(lower_bendy_off_skin_cluster[0], f"{self.lower_bendy_off_curve[0]}.cv[3]", transformValue=[self.bendy_joints[1], 1])
        cmds.skinPercent(lower_bendy_off_skin_cluster[0], f"{self.lower_bendy_off_curve[0]}.cv[4]", transformValue=[self.bendy_joints[1], 1])
        cmds.skinPercent(lower_bendy_off_skin_cluster[0], f"{self.lower_bendy_off_curve[0]}.cv[6]", transformValue=[self.lower_bendy_joints[2], 1])


       
        #--- Bendy Aim Helpers ---
        self.upper_aim_helper = cmds.createNode("transform", n=f"{self.side}_wingArmUpperBendyAimHelper04_TRN", p=self.upper_bendy_module)
        self.lower_aim_helper = cmds.createNode("transform", n=f"{self.side}_wingArmLowerBendyAimHelper04_TRN", p=self.lower_bendy_module)
        cmds.setAttr(f"{self.upper_aim_helper}.inheritsTransform", 0)
        cmds.setAttr(f"{self.lower_aim_helper}.inheritsTransform", 0)



        self.skinning_joints = []

        for i, part in enumerate(["Upper", "Lower"]):
            for ii, value in enumerate([0, 0.25, 0.5, 0.75, 0.95]):
                cmds.select(clear=True)
                joint = cmds.joint(n=f"{self.side}_wingArm{part}Twist0{ii}_JNT")
                cmds.parent(joint, self.skinning_trn)
                mpa = cmds.createNode("motionPath", n=f"{self.side}_wingArm{part}Twist0{ii}_MPT", ss=True)
                cmds.setAttr(f"{mpa}.frontAxis", 1)
                cmds.setAttr(f"{mpa}.upAxis", 2)
                cmds.setAttr(f"{mpa}.worldUpType", 4)
                cmds.setAttr(f"{mpa}.fractionMode", 1)
                cmds.setAttr(f"{mpa}.follow", 1)
                cmds.setAttr(f"{mpa}.uValue", value)
                cmds.connectAttr(f"{mpa}.allCoordinates", f"{joint}.translate")
                if i == 0:
                    cmds.connectAttr(f"{self.upper_bendy_bezier[0]}.worldSpace[0]", f"{mpa}.geometryPath")
                else:
                    cmds.connectAttr(f"{self.lower_bendy_bezier[0]}.worldSpace[0]", f"{mpa}.geometryPath")

                if ii == 3:
                    if i == 0:
                        cmds.connectAttr(f"{mpa}.allCoordinates", f"{self.upper_aim_helper}.translate")
                    
                    else:
                        cmds.connectAttr(f"{mpa}.allCoordinates", f"{self.lower_aim_helper}.translate")

                self.skinning_joints.append(joint)


        self.upper_aim_transform_grp = cmds.createNode("transform", n=f"{self.side}_wingArmUpperTwistAim_GRP", p=self.upper_bendy_module)
        self.lower_aim_transform_grp = cmds.createNode("transform", n=f"{self.side}_wingArmLowerTwistAim_GRP", p=self.lower_bendy_module)

        self.aim_transforms = []
        for i, part in enumerate(["Upper", "Lower"]):
            for ii, value in enumerate([0, 0.25, 0.5, 0.75, 0.95]):
                aim_trn = cmds.createNode("transform", n=f"{self.side}_wingArm{part}Twist0{ii}Aim_TRN")
                mpa = cmds.createNode("motionPath", n=f"{self.side}_wingArm{part}Twist0{ii}Aim_MPT", ss=True)
                cmds.setAttr(f"{mpa}.fractionMode", True)
                cmds.setAttr(f"{mpa}.uValue", value)
                cmds.connectAttr(f"{mpa}.allCoordinates", f"{aim_trn}.translate")
                if i == 3:
                    if self.side == "L":
                        cmds.connectAttr(f"{mpa}.allCoordinates", f"{self.upper_aim_helper}.translate")
                    else:
                        cmds.connectAttr(f"{mpa}.allCoordinates", f"{self.lower_aim_helper}.translate")
                if i == 0:
                    cmds.connectAttr(f"{self.upper_bendy_off_curve[0]}.worldSpace[0]", f"{mpa}.geometryPath")
                    cmds.parent(aim_trn, self.upper_aim_transform_grp)
                else:
                    cmds.connectAttr(f"{self.lower_bendy_off_curve[0]}.worldSpace[0]", f"{mpa}.geometryPath")
                    cmds.parent(aim_trn, self.lower_aim_transform_grp)

                self.aim_transforms.append(aim_trn)
                cmds.setAttr(f"{aim_trn}.inheritsTransform", 0)

        
        for i, joint in enumerate(self.skinning_joints):
            if "04" not in joint:
                    if self.side == "L":
                        aim = cmds.aimConstraint(self.skinning_joints[i+1], joint, aim=[1, 0, 0], u=[0, 1, 0], wut="object", wuo=self.aim_transforms[i], mo=False)
                
                    elif self.side == "R":
                        aim = cmds.aimConstraint(self.skinning_joints[i+1], joint, aim=[-1, 0, 0], u=[0, 1, 0], wut="object", wuo=self.aim_transforms[i], mo=False)
        
            else:
                if self.side == "L":
                    if "Upper" in joint:
                        aim = cmds.aimConstraint(self.upper_aim_helper, joint, aim=[-1, 0, 0], u=[0, 1, 0], wut="object", wuo=self.aim_transforms[i], mo=False)
                    else:
                        aim = cmds.aimConstraint(self.lower_aim_helper, joint, aim=[-1, 0, 0], u=[0, 1, 0], wut="object", wuo=self.aim_transforms[i], mo=False)
                elif self.side == "R":
                    if "Upper" in joint:
                        aim = cmds.aimConstraint(self.upper_aim_helper, joint, aim=[1, 0, 0], u=[0, 1, 0], wut="object", wuo=self.aim_transforms[i], mo=False)
                    else:
                        aim = cmds.aimConstraint(self.lower_aim_helper, joint, aim=[1, 0, 0], u=[0, 1, 0], wut="object", wuo=self.aim_transforms[i], mo=False)

        cmds.select(clear=True)
        end_joint = cmds.joint(name=f"{self.side}_wristSkinning_JNT")
        cmds.connectAttr(f"{self.blend_chain[-1]}.worldMatrix[0]", f"{end_joint}.offsetParentMatrix")
        cmds.parent(end_joint, self.skinning_trn)
        self.skinning_joints.append(end_joint)
        
            
            





          
            




        



        
        
        


        
    
    



