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
        # cmds.parent(self.upper_non_roll_end_jnt, self.upper_non_roll_jnt)
        cmds.matchTransform(self.upper_non_roll_jnt, self.ik_chain[0], pos=True, rot=True)
        cmds.matchTransform(self.upper_non_roll_end_jnt, self.ik_chain[1], pos=True, rot=True)
        cmds.select(cl=True)

        self.upper_roll_jnt = cmds.joint(n=f"{self.side}_wingArmUpperRoll_JNT")
        self.upper_roll_end_jnt = cmds.joint(n=f"{self.side}_wingArmUpperRollEnd_JNT")
        # cmds.parent(self.upper_roll_end_jnt, self.upper_roll_jnt)
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
        cmds.select(clear=True)
        self.lower_roll_jnt = cmds.joint(n=f"{self.side}_wingArmLowerRoll_JNT")
        self.lower_roll_end_jnt = cmds.joint(n=f"{self.side}_wingArmLowerRollEnd_JNT")
        # cmds.parent(self.lower_roll_end_jnt, self.lower_roll_jnt)
        cmds.matchTransform(self.lower_roll_jnt, self.ik_chain[1], pos=True, rot=True)
        cmds.matchTransform(self.lower_roll_end_jnt, self.ik_chain[-1], pos=True, rot=True)

        self.lower_roll_handle = cmds.ikHandle(
            n=f"{self.side}_wingArmLowerRollIkHandle",
            sj=self.lower_roll_jnt,
            ee=self.lower_roll_end_jnt,
            sol="ikSCsolver",
        )[0]

        cmds.parent(self.lower_roll_handle, self.main_ik_handle, self.upper_non_roll_ik_handle, self.upper_roll_ik_handle, self.module_trn)

   
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

        
    
    



