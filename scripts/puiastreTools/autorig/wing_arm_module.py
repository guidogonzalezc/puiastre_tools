"""
Arm system for the dragon wing.

"""

import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
# from puiastreTools.tools.curve_tool import controller_creator
import maya.mel as mel
import math
import os
from importlib import reload
import math
reload(guides_manager)
reload(curve_tool)
# reload(controller_creator)

class WingArmModule(object):
    def __init__(self):
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "arm_guides_v001.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "arm_ctl.json")
    
    def make(self, side):
        
        self.side = side

        self.module_trn = cmds.createNode("transform", n=f"{self.side}_wingArmModule_GRP")
        self.controllers_trn = cmds.createNode("transform", n=f"{self.side}_wingArmControllers_GRP")
        self.skinning_trn = cmds.createNode("transform", n=f"{self.side}_wingArmSkinningJoints_GRP", p=self.module_trn)

        self.duplicate_guides()
        self.pair_blends()
        self.set_controllers()
        self.handles_setup()
        self.soft_stretch()
        self.pole_vector_setup()
        self.bendy_curves_setup()
        self.hooks()
        self.twists_setup()
        


    def lock_attrs(self, ctl, attrs):
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def duplicate_guides(self):
        
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
                all_descendents=True,
                filePath=self.guides_path
            )
            cmds.parent(guides[0], self.module_trn)

            for joint in guides:
                chain.append(cmds.rename(joint, joint.replace('_JNT', f'{name}_JNT')))

    def pair_blends(self):

        for i, joint in enumerate(self.blend_chain):
            
            self.pair_blend_node = cmds.createNode("pairBlend", n=f"{joint.replace('_JNT', '_PBL')}")
            cmds.connectAttr(f"{self.ik_chain[i]}.translate", f"{self.pair_blend_node}.inTranslate1")
            cmds.connectAttr(f"{self.fk_chain[i]}.translate", f"{self.pair_blend_node}.inTranslate2")
            cmds.connectAttr(f"{self.ik_chain[i]}.rotate", f"{self.pair_blend_node}.inRotate1")
            cmds.connectAttr(f"{self.fk_chain[i]}.rotate", f"{self.pair_blend_node}.inRotate2")
            cmds.connectAttr(f"{self.pair_blend_node}.outTranslate", f"{joint}.translate")
            cmds.connectAttr(f"{self.pair_blend_node}.outRotate", f"{joint}.rotate")



    def set_controllers(self):
        
        # --- FK/IK Switch Controller ---
        self.settings_curve_ctl, self.settings_curve_grp = curve_tool.controller_creator(f"{self.side}_ArmSettings", suffixes = ["GRP"])
        cmds.addAttr(self.settings_curve_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.matchTransform(self.settings_curve_grp[0], self.fk_chain[0], pos=True, rot=True)
        cmds.move(0, 100, 0, self.settings_curve_grp[0], r=True, os=True)
        self.lock_attrs(self.settings_curve_ctl, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"])
        cmds.parent(self.settings_curve_grp[0], self.controllers_trn)
        
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
        cmds.matchTransform(self.root_grp[0], self.ik_chain[0], pos=True, rot=True) 
        cmds.matchTransform(self.wrist_ik_grp[0], self.ik_chain[-1], pos=True, rot=True)
        self.arm_ik_controllers.append(self.root_ctl)
        self.arm_ik_controllers.append(self.wrist_ik_ctl)
        cmds.parent(self.root_grp[0], self.wrist_ik_grp[0], self.arm_ik_controllers_trn)

    def handles_setup(self):

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
        cmds.matchTransform(self.upper_roll_jnt, self.ik_chain[1], pos=True, rot=True)
        cmds.matchTransform(self.upper_roll_end_jnt, self.ik_chain[2], pos=True, rot=True)
        cmds.parent(self.upper_roll_jnt, self.upper_non_roll_jnt)
    
        
        self.upper_non_roll_ik_handle = cmds.ikHandle(
            n=f"{self.side}_wingArmUpperNonRoll_HDL",
            sj=self.upper_non_roll_jnt,
            ee=self.upper_non_roll_end_jnt,
            sol="ikSCsolver",
        )[0]
        cmds.pointConstraint(self.blend_chain[1], self.upper_non_roll_ik_handle, mo=True)

        self.upper_roll_ik_handle = cmds.ikHandle(
            n=f"{self.side}_wingArmUpperRoll_HDL",
            sj=self.upper_roll_jnt,
            ee=self.upper_roll_end_jnt,
            sol="ikSCsolver",
        )[0]
        cmds.parentConstraint(self.blend_chain[2], self.upper_roll_ik_handle, mo=True)

        # --- Lower Roll Ik Handle ---
        
        self.lower_roll_offset = cmds.createNode("transform", n=f"{self.side}_wingArmLowerRollOffset_GRP")
        cmds.select(clear=True)
        self.lower_roll_jnt = cmds.joint(n=f"{self.side}_wingArmLowerRoll_JNT")
        self.lower_roll_end_jnt = cmds.joint(n=f"{self.side}_wingArmLowerRollEnd_JNT")
        cmds.parent(self.lower_roll_jnt, self.lower_roll_offset)
        cmds.matchTransform(self.lower_roll_offset, self.ik_chain[1], pos=True, rot=True)
        cmds.matchTransform(self.lower_roll_end_jnt, self.ik_chain[-1], pos=True, rot=True)

        

        self.lower_roll_handle = cmds.ikHandle(
            n=f"{self.side}_wingArmLowerRoll_HDL",
            sj=self.lower_roll_jnt,
            ee=self.lower_roll_end_jnt,
            sol="ikSCsolver",
        )[0]
        cmds.parentConstraint(self.blend_chain[-1], self.lower_roll_handle, mo=True)

        cmds.parent(self.lower_roll_handle, self.main_ik_handle, self.upper_non_roll_ik_handle, self.upper_roll_ik_handle, self.lower_roll_offset, self.upper_non_roll_jnt, self.module_trn)

   
    def soft_stretch(self):

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
        cmds.aimConstraint(self.wrist_ik_ctl, self.soft_off, aimVector=(1, 0, 0), upVector=(0, 0, 1), worldUpType="None", mo=True)

        self.soft_trn = cmds.createNode("transform", name=f"{self.side}_armSoft_TRN", p=self.soft_off)
        cmds.matchTransform(self.soft_trn, self.ik_chain[-1], pos=True, rot=True)



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
        cmds.setAttr(f"{self.created_nodes[4]}.floatB", cmds.getAttr(f"{self.ik_chain[1]}.translateX"))
        cmds.setAttr(f"{self.created_nodes[10]}.floatB", cmds.getAttr(f"{self.ik_chain[-1]}.translateX"))
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


        cmds.parentConstraint(self.soft_trn, self.main_ik_handle, mo=True)

    def pole_vector_setup(self):
        # --- Pole Vector ---
        self.pole_vector_ctl, self.pole_vector_grp = curve_tool.controller_creator(f"{self.side}_wingArmPV", suffixes=["GRP", "OFF"])
        cmds.matchTransform(self.pole_vector_grp[0], self.ik_chain[1], pos=True, rot=True)
        cmds.move(0, 0, -1000, self.pole_vector_grp[0], r=True, os=True)
        cmds.parent(self.pole_vector_grp[0], self.arm_ik_controllers_trn)
        cmds.poleVectorConstraint(self.pole_vector_ctl, self.main_ik_handle)
        self.lock_attrs(self.pole_vector_ctl, ["sx", "sy", "sz", "v"])
        
        
        cmds.addAttr(self.pole_vector_ctl, shortName="ELBOW_PINNING____", attributeType="enum", enumName="____", keyable=True)
        cmds.setAttr(f"{self.pole_vector_ctl}.ELBOW_PINNING____", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.pole_vector_ctl, shortName="Pin", minValue=0, defaultValue=0, maxValue=1, keyable=True)

        
        self.upper_pin_attrblender = cmds.createNode("blendTwoAttr", n=f"{self.side}_wingArmUpperPin_BTA")
        self.lower_pin_attrblender = cmds.createNode("blendTwoAttr", n=f"{self.side}_wingArmLowerPin_BTA")

        cmds.connectAttr(self.created_nodes[18] + ".outColorG", f"{self.upper_pin_attrblender}.input[0]")
        cmds.connectAttr(self.created_nodes[0] + ".distance", f"{self.upper_pin_attrblender}.input[1]")
        cmds.connectAttr(self.pole_vector_ctl + ".Pin", f"{self.upper_pin_attrblender}.attributesBlender")
        cmds.connectAttr(self.upper_pin_attrblender + ".output", self.ik_chain[1] + ".translateX")

        cmds.connectAttr(self.created_nodes[18] + ".outColorB", f"{self.lower_pin_attrblender}.input[0]")
        cmds.connectAttr(self.created_nodes[0] + ".distance", f"{self.lower_pin_attrblender}.input[1]")
        cmds.connectAttr(self.pole_vector_ctl + ".Pin", f"{self.lower_pin_attrblender}.attributesBlender")
        cmds.connectAttr(self.lower_pin_attrblender + ".output", self.ik_chain[-1] + ".translateX")

    def bendy_curves_setup(self):
        # --- Bendy Setup ---
        self.bendy_module_trn = cmds.createNode("transform", n=f"{self.side}_wingArmBendyModule_GRP", p=self.module_trn)

        self.upper_bendy_module = cmds.createNode("transform", n=f"{self.side}_wingArmUpperBendyModule_GRP", p=self.bendy_module_trn)
        self.lower_bendy_module = cmds.createNode("transform", n=f"{self.side}_wingArmLowerBendyModule_GRP", p=self.bendy_module_trn)

        #--- Bendy Curves ---
        self.arm_degree2_crv = cmds.curve(
            n=f"{self.side}_wingArmDegree2_CRV", 
            d=1,

            p=[
                cmds.xform(self.ik_chain[0], q=True, ws=True, t=True),
                cmds.xform(self.ik_chain[1], q=True, ws=True, t=True),
                cmds.xform(self.ik_chain[2], q=True, ws=True, t=True),
                
            ]
        )

        cmds.rebuildCurve(self.arm_degree2_crv, kr=0, s=2,d=1, kcp=1)
        cmds.parent(self.arm_degree2_crv, self.bendy_module_trn)

        self.arm_degree2_crv_shape = cmds.listRelatives(self.arm_degree2_crv, s=True)[0]
        
        detached_curves = cmds.detachCurve(
            self.arm_degree2_crv_shape,
            p=0.5,
            ch=1,
            rpo=False
        )
        
        self.upper_segment_crv = cmds.rename(detached_curves[0], f"{self.side}_wingArmUpperSegment_CRV")
        cmds.parent(self.upper_segment_crv, self.upper_bendy_module)
        self.lower_segment_crv = cmds.rename(detached_curves[1], f"{self.side}_wingArmLowerSegment_CRV")
        cmds.parent(self.lower_segment_crv, self.lower_bendy_module)

        cmds.rebuildCurve(self.upper_segment_crv, ch=1, rpo=1, rt=0, end=1, kr=1, kcp=0, kep=1, kt=0, fr=0, s=1, d=2, tol=0.01)
        cmds.rebuildCurve(self.lower_segment_crv, ch=1, rpo=1, rt=0, end=1, kr=1, kcp=0, kep=1, kt=0, fr=0, s=1, d=2, tol=0.01)

        shoulder_bendy_dpm = cmds.createNode("decomposeMatrix", n=(self.blend_chain[0].replace('JNT', 'DPM')), ss=True)
        cmds.connectAttr(f"{self.blend_chain[0]}.worldMatrix[0]", f"{shoulder_bendy_dpm}.inputMatrix")
        elbow_bendy_dpm = cmds.createNode("decomposeMatrix", n=(self.blend_chain[1].replace('JNT', 'DPM')), ss=True)
        cmds.connectAttr(f"{self.blend_chain[1]}.worldMatrix[0]", f"{elbow_bendy_dpm}.inputMatrix")
        wrist_bendy_dpm = cmds.createNode("decomposeMatrix", n=(self.blend_chain[2].replace('JNT', 'DPM')), ss=True)
        cmds.connectAttr(f"{self.blend_chain[2]}.worldMatrix[0]", f"{wrist_bendy_dpm}.inputMatrix")

        cmds.connectAttr(f"{shoulder_bendy_dpm}.outputTranslate", f"{self.arm_degree2_crv}.controlPoints[0]")
        cmds.connectAttr(f"{elbow_bendy_dpm}.outputTranslate", f"{self.arm_degree2_crv}.controlPoints[1]")
        cmds.connectAttr(f"{wrist_bendy_dpm}.outputTranslate", f"{self.arm_degree2_crv}.controlPoints[2]")



    def hooks(self):

        # --- Hooks ---
        hook_parameters = [0.001, 0.5, 0.999]
        self.upper_bendy_joints = []
        self.lower_bendy_joints = []

        for i, part in enumerate(["Upper", "Lower"]):
            for ii, joint in enumerate(["Root", "Mid", "Tip"]):

                cmds.select(clear=True)
                hook_joint = cmds.joint(n=f"{self.side}_wingArm{part}Bendy{joint}_JNT")
                self.upper_bendy_joints.append(hook_joint) if i == 0 else self.lower_bendy_joints.append(hook_joint)
                
                motion_path = cmds.createNode("motionPath", n=f"{self.side}_wingArm{part}Bendy{joint}{i}_MPT")
                cmds.setAttr(f"{motion_path}.frontAxis", 0)
                cmds.setAttr(f"{motion_path}.upAxis", 1)
                cmds.setAttr(f"{motion_path}.worldUpType", 2)
                cmds.setAttr(f"{motion_path}.fractionMode", 1)

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
                    self.lock_attrs(bendy_ctl, ["sy", "sz", "v"])
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
                        cmds.parentConstraint(bendy_ctl, bendy_joint, mo=True)
                        cmds.scaleConstraint(bendy_ctl, bendy_joint, mo=True)

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
                        cmds.parentConstraint(bendy_ctl, bendy_joint, mo=True)
                        cmds.scaleConstraint(bendy_ctl, bendy_joint, mo=True)

                cmds.setAttr(f"{hook_joint}.inheritsTransform", 0)



        self.upper_bendy_bezier = cmds.curve(n=f"{self.side}_wingArmUpperBendyBezier_CRV",d=1,p=[cmds.xform(self.upper_bendy_joints[0], q=True, ws=True, t=True),cmds.xform(self.upper_bendy_joints[1], q=True, ws=True, t=True),cmds.xform(self.upper_bendy_joints[2], q=True, ws=True, t=True)])
        self.upper_bendy_bezier = cmds.rebuildCurve(self.upper_bendy_bezier, rpo=1, rt=0, end=1, kr=0, kep=1, kt=0, fr=0, s=2, d=3, tol=0.01, ch=False)
            
        self.upper_bendy_bezier_shape = cmds.listRelatives(self.upper_bendy_bezier, s=True)[0]
        cmds.select(self.upper_bendy_bezier_shape)
        cmds.nurbsCurveToBezier()

        cmds.select(f"{self.upper_bendy_bezier[0]}.cv[6]", f"{self.upper_bendy_bezier[0]}.cv[0]")
        cmds.bezierAnchorPreset(p=2)
        cmds.select(f"{self.upper_bendy_bezier[0]}.cv[3]")
        cmds.bezierAnchorPreset(p=1)
        
        cmds.parent(self.upper_bendy_bezier, self.upper_bendy_module)
        upper_bendy_skin_cluster = cmds.skinCluster(self.upper_bendy_joints[0], self.upper_bendy_joints[1], self.upper_bendy_joints[2], self.upper_bendy_bezier,n=f"{self.side}_wingArmUpperBendyBezier_SKIN")
        
        cmds.skinPercent(upper_bendy_skin_cluster[0], f"{self.upper_bendy_bezier[0]}.cv[0]", transformValue=[self.upper_bendy_joints[0], 1])
        cmds.skinPercent(upper_bendy_skin_cluster[0], f"{self.upper_bendy_bezier[0]}.cv[2]", transformValue=[self.upper_bendy_joints[1], 1])
        cmds.skinPercent(upper_bendy_skin_cluster[0], f"{self.upper_bendy_bezier[0]}.cv[3]", transformValue=[self.upper_bendy_joints[1], 1])
        cmds.skinPercent(upper_bendy_skin_cluster[0], f"{self.upper_bendy_bezier[0]}.cv[4]", transformValue=[self.upper_bendy_joints[1], 1])
        cmds.skinPercent(upper_bendy_skin_cluster[0], f"{self.upper_bendy_bezier[0]}.cv[6]", transformValue=[self.upper_bendy_joints[2], 1])


        self.lower_bendy_bezier = cmds.curve(n=f"{self.side}_wingArmLowerBendyBezier_CRV",d=1,p=[cmds.xform(self.lower_bendy_joints[0], q=True, ws=True, t=True),cmds.xform(self.lower_bendy_joints[1], q=True, ws=True, t=True),cmds.xform(self.lower_bendy_joints[2], q=True, ws=True, t=True)])
        self.lower_bendy_bezier = cmds.rebuildCurve(self.lower_bendy_bezier, rpo=1, rt=0, end=1, kr=0, kep=1, kt=0, fr=0, s=2, d=3, tol=0.01, ch=False)  
        
        self.lower_bendy_bezier_shape = cmds.listRelatives(self.lower_bendy_bezier, s=True)[0]

        cmds.select(self.lower_bendy_bezier_shape)
        cmds.nurbsCurveToBezier()

        cmds.select(f"{self.lower_bendy_bezier[0]}.cv[0]", f"{self.lower_bendy_bezier[0]}.cv[6]")
        cmds.bezierAnchorPreset(p=2)
        cmds.select(f"{self.lower_bendy_bezier[0]}.cv[3]")
        cmds.bezierAnchorPreset(p=1)

        cmds.parent(self.lower_bendy_bezier, self.lower_bendy_module)
        lower_bendy_skin_cluster = cmds.skinCluster(self.lower_bendy_joints[0], self.lower_bendy_joints[1], self.lower_bendy_joints[2], self.lower_bendy_bezier, tsb=True, n=f"{self.side}_wingArmLowerBendyBezier_SKIN")
        
        cmds.skinPercent(lower_bendy_skin_cluster[0], f"{self.lower_bendy_bezier[0]}.cv[0]", transformValue=[self.lower_bendy_joints[0], 1])
        cmds.skinPercent(lower_bendy_skin_cluster[0], f"{self.lower_bendy_bezier[0]}.cv[2]", transformValue=[self.lower_bendy_joints[1], 1])
        cmds.skinPercent(lower_bendy_skin_cluster[0], f"{self.lower_bendy_bezier[0]}.cv[3]", transformValue=[self.lower_bendy_joints[1], 1])
        cmds.skinPercent(lower_bendy_skin_cluster[0], f"{self.lower_bendy_bezier[0]}.cv[4]", transformValue=[self.lower_bendy_joints[1], 1])
        cmds.skinPercent(lower_bendy_skin_cluster[0], f"{self.lower_bendy_bezier[0]}.cv[6]", transformValue=[self.lower_bendy_joints[2], 1])


    def twists_setup(self):

        # --- Twists ---
        self.upper_bendy_off_curve = cmds.offsetCurve(self.lower_bendy_bezier, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=1.5, tol=0.01, sd=0, ugn=False, name=f"{self.side}_wingArmUpperBendyBezierOffset_CRV", normal=[0, 0, 1])
        cmds.connectAttr(f"{self.upper_bendy_bezier[0]}.worldSpace[0]", f"{self.upper_bendy_off_curve[1]}.inputCurve", f=True)
        cmds.parent(self.upper_bendy_off_curve[0], self.upper_bendy_module)

        self.upper_offset_curve_skin_cluster = cmds.skinCluster(self.lower_bendy_joints[0], self.lower_bendy_joints[1], self.lower_bendy_joints[2], self.upper_bendy_off_curve[0], tsb=True, n=f"{self.side}_UpperBendyOffset_SKIN")

        cmds.skinPercent(self.upper_offset_curve_skin_cluster[0], f"{self.upper_bendy_off_curve[0]}.cv[0]", transformValue=[self.lower_bendy_joints[0], 1])
        cmds.skinPercent(self.upper_offset_curve_skin_cluster[0], f"{self.upper_bendy_off_curve[0]}.cv[2]", transformValue=[self.lower_bendy_joints[1], 1])
        cmds.skinPercent(self.upper_offset_curve_skin_cluster[0], f"{self.upper_bendy_off_curve[0]}.cv[3]", transformValue=[self.lower_bendy_joints[1], 1])
        cmds.skinPercent(self.upper_offset_curve_skin_cluster[0], f"{self.upper_bendy_off_curve[0]}.cv[4]", transformValue=[self.lower_bendy_joints[1], 1])
        cmds.skinPercent(self.upper_offset_curve_skin_cluster[0], f"{self.upper_bendy_off_curve[0]}.cv[6]", transformValue=[self.lower_bendy_joints[2], 1])


        self.lower_bendy_off_curve = cmds.offsetCurve(self.upper_bendy_bezier, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=1.5, tol=0.01, sd=0, ugn=False, name=f"{self.side}_wingArmLowerBendyBezierOffset_CRV", normal=[0, 0, 1])
        cmds.connectAttr(f"{self.lower_bendy_bezier[0]}.worldSpace[0]", f"{self.lower_bendy_off_curve[1]}.inputCurve", f=True)
        cmds.parent(self.lower_bendy_off_curve[0], self.lower_bendy_module)

        self.lower_offset_curve_skin_cluster = cmds.skinCluster(self.lower_bendy_joints[0], self.lower_bendy_joints[1], self.lower_bendy_joints[2], self.lower_bendy_off_curve[0], tsb=True, n=f"{self.side}_LowerBendyOffset_SKIN")

        cmds.skinPercent(self.lower_offset_curve_skin_cluster[0], f"{self.lower_bendy_off_curve[0]}.cv[0]", transformValue=[self.lower_bendy_joints[0], 1])
        cmds.skinPercent(self.lower_offset_curve_skin_cluster[0], f"{self.lower_bendy_off_curve[0]}.cv[2]", transformValue=[self.lower_bendy_joints[1], 1])
        cmds.skinPercent(self.lower_offset_curve_skin_cluster[0], f"{self.lower_bendy_off_curve[0]}.cv[3]", transformValue=[self.lower_bendy_joints[1], 1])
        cmds.skinPercent(self.lower_offset_curve_skin_cluster[0], f"{self.lower_bendy_off_curve[0]}.cv[4]", transformValue=[self.lower_bendy_joints[1], 1])
        cmds.skinPercent(self.lower_offset_curve_skin_cluster[0], f"{self.lower_bendy_off_curve[0]}.cv[6]", transformValue=[self.lower_bendy_joints[2], 1])
        
        #--- Bendy Aim Helpers ---
        self.upper_aim_helper = cmds.createNode("transform", n=f"{self.side}_wingArmUpperBendyAimHelper04_TRN", p=self.upper_bendy_module)
        self.lower_aim_helper = cmds.createNode("transform", n=f"{self.side}_wingArmLowerBendyAimHelper04_TRN", p=self.lower_bendy_module)



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
                    cmds.connectAttr(f"{self.lower_bendy_off_curve[0]}.worldSpace[0]", f"{mpa}.geometryPath")
                    cmds.parent(aim_trn, self.upper_aim_transform_grp)
                else:
                    cmds.connectAttr(f"{self.lower_bendy_off_curve[0]}.worldSpace[0]", f"{mpa}.geometryPath")
                    cmds.parent(aim_trn, self.lower_aim_transform_grp)

                self.aim_transforms.append(aim_trn)
                cmds.setAttr(f"{aim_trn}.inheritsTransform", 0)


        print(self.skinning_joints)
        for i, joint in enumerate(self.skinning_joints):
            if i < 4:
                if self.side == "L":
                    cmds.aimConstraint(self.skinning_joints[i+1], joint, aim=[1, 0, 0], u=[0, 1, 0], wut="objectrotation", wuo=self.aim_transforms[i], mo=True)
                elif self.side == "R":
                    cmds.aimConstraint(self.skinning_joints[i+1], joint, aim=[-1, 0, 0], u=[0, 1, 0], wut="objectrotation", wuo=self.aim_transforms[i], mo=True)
        
            else:
                if self.side == "L":
                    if "Upper" in joint:
                        cmds.aimConstraint(self.upper_aim_helper, joint, aim=[1, 0, 0], u=[0, 1, 0], wut="objectrotation", wuo=self.aim_transforms[i], mo=True)
                    else:
                        cmds.aimConstraint(self.lower_aim_helper, joint, aim=[1, 0, 0], u=[0, 1, 0], wut="objectrotation", wuo=self.aim_transforms[i], mo=True)
                elif self.side == "R":
                    if "Upper" in joint:
                        cmds.aimConstraint(self.upper_aim_helper, joint, aim=[-1, 0, 0], u=[0, 1, 0], wut="objectrotation", wuo=self.aim_transforms[i], mo=True)
                    else:
                        cmds.aimConstraint(self.lower_aim_helper, joint, aim=[-1, 0, 0], u=[0, 1, 0], wut="objectrotation", wuo=self.aim_transforms[i], mo=True)


            
        for joint in self.skinning_joints:
            cmds.setAttr(f"{joint}.radius", 30)
            
            





          
            




        



        
        
        


        
    
    



