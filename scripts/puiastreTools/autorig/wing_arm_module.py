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
        self.soft_stretch()
        self.handles_setup()


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
        cmds.move(100, 0, 0, self.settings_curve_grp[0], r=True, os=True)
        
        self.arm_fk_controllers_trn = cmds.createNode("transform", n=f"{self.side}_wingArmFKControllers_GRP")
        self.arm_ik_controllers_trn = cmds.createNode("transform", n=f"{self.side}_wingArmIKControllers_GRP")

        reverse_vis = cmds.createNode("reverse", n=f"{self.side}_wingArmReverseVis_REV")
        cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{reverse_vis}.inputX")
        cmds.connectAttr(f"{reverse_vis}.outputX", f"{self.arm_ik_controllers_trn}.visibility")
        cmds.connectAttr(f"{self.settings_curve_ctl}.Switch IK --> FK", f"{self.arm_fk_controllers_trn}.visibility")
        cmds.parent(self.arm_fk_controllers_trn, self.arm_ik_controllers_trn, self.controllers_trn)


        # --- FK/IK Controllers ---
        self.arm_fk_controllers = []
        self.arm_fk_trns = []

        for i, joint in enumerate(self.fk_chain):
            ctl, grp = curve_tool.controller_creator(f"{self.side}_wingArm{i+1}Fk_CTL", suffixes=["GRP", "OFF"])
            cmds.parent(grp, self.arm_fk_controllers_trn)
            cmds.matchTransform(ctl, joint, pos=True, rot=True, scl=False)
            cmds.parentConstraint(ctl, joint, mo=False)
            self.lock_attrs(ctl, ["sx", "sy", "sz", "v"])
            if self.arm_fk_controllers:
                cmds.parent(grp, self.arm_fk_controllers[-1])
            self.arm_fk_trns.append(grp)
            self.arm_fk_controllers.append(ctl)


        self.arm_ik_controllers = []

        self.root_ctl, self.root_grp = curve_tool.controller_creator(f"{self.side}_wingArmRoot", suffixes=["GRP", "OFF"])
        self.lock_attrs(self.root_ctl, ["sx", "sy", "sz", "v"])
        self.wrist_ik_ctl, self.wrist_ik_grp = curve_tool.controller_creator(f"{self.side}_wingArmWrist", suffixes=["GRP", "OFF"])
        self.lock_attrs(self.wrist_ik_ctl, ["sx", "sy", "sz", "v"])
        cmds.matchTransform(self.root_grp[0], self.ik_chain[0], pos=True, rot=True) 
        cmds.matchTransform(self.wrist_ik_grp[0], self.ik_chain[-1], pos=True, rot=True)
        cmds.parent(self.root_grp, self.wrist_ik_grp, self.arm_ik_controllers_trn)

   
    def soft_stretch(self):

        # --- Stretchy FK Controllers ---
        for ctl in self.arm_fk_controllers:
            cmds.addAttr(ctl, shortName="STRETCHY____", type="enum", enumName="____", keyable=True)
            cmds.setAttr(f"{ctl}.STRETCHY____", lock=True, keyable=False)
            cmds.addAttr(ctl, shortName="Stretch", minValue=0, defaultValue=0, keyable=True)

        self.upper_double_mult_linear = cmds.createNode("multDoubleLinear", n=f"{self.side}_wingArmUpperDoubleMultLinear_MDL")
        self.lower_double_mult_linear = cmds.createNode("multDoubleLinear", n=f"{self.side}_wingArmLowerDoubleMultLinear_MDL")
        cmds.connectAttr(f"{self.arm_fk_controllers[0]}.Stretch", f"{self.upper_double_mult_linear}.input1")
        cmds.connectAttr(f"{self.arm_fk_controllers[1]}.Stretch", f"{self.lower_double_mult_linear}.input1")
        cmds.setAttr(f"{self.arm_fk_controllers_trn[1]}.translateX", f"{self.upper_double_mult_linear}.input2")
        cmds.setAttr(f"{self.arm_fk_controllers_trn[2]}.translateX", f"{self.lower_double_mult_linear}.input2")
        cmds.connectAttr(f"{self.upper_double_mult_linear}.output", f"{self.arm_fk_trns[3]}.Stretch")
        cmds.connectAttr(f"{self.lower_double_mult_linear}.output", f"{self.arm_fk_trns[-2]}.Stretch")


        # --- Stretchy IK Controllers ---
        cmds.addAttr(self.wrist_ik_ctl, shortName="STRETCHY____", type="enum", enumName="____", keyable=True)
        cmds.setAttr(f"{self.wrist_ik_ctl}.STRETCHY____", lock=True, keyable=False)
        cmds.addAttr(self.wrist_ik_ctl, shortName="Stretch", minValue=0, defaultValue=0, keyable=True)
        cmds.addAttr(self.wrist_ik_ctl, shortName="SOFT____", type="enum", enumName="____", keyable=True)
        cmds.setAttr(f"{self.wrist_ik_ctl}.SOFT____", lock=True, keyable=False)
        cmds.addAttr(self.wrist_ik_ctl, shortName="Soft", minValue=0, defaultValue=0, maxValue=1, keyable=True)

        masterwalk = "C_masterwalk_CTL" # Change this to the actual masterwalk controller name

        self.soft_off = cmds.createNode("transform", name=f"{self.side}_legSoft_OFF", p=self.module_trn)
        cmds.pointConstraint(self.arm_ik_controllers[0], self.soft_off)
        cmds.aimConstraint(self.ikHandleManager, self.soft_off, aimVector=(1,0,0), upVector= (0,0,1), worldUpType ="none", maintainOffset=False)

        self.soft_trn = cmds.createNode("transform", name=f"{self.side}_legSoft_TRN", p=self.soft_off)



        nodes_to_create = {
            f"{self.side}_legDistanceToControl_DBT": ("distanceBetween", None), #0
            f"{self.side}_legDistanceToControlNormalized_FLM": ("floatMath", 3), #1
            f"{self.side}_legUpperLength_FLM": ("floatMath", 2), #2
            f"{self.side}_legFullLength_FLM": ("floatMath", 0), #3
            f"{self.side}_legLowerLength_FLM": ("floatMath", 2), #4
            f"{self.side}_legSoftValue_RMV": ("remapValue", None), #5
            f"{self.side}_legSoftDistance_FLM": ("floatMath", 1), #6
            f"{self.side}_legDistanceToControlMinusSoftDistance_FLM": ("floatMath", 1), #7
            f"{self.side}_legDistanceToControlMinusSoftDistanceDividedBySoftValue_FLM": ("floatMath", 3),#8
            f"{self.side}_legDistanceToControlMinusSoftDistanceDividedBySoftValueNegate_FLM": ("floatMath", 2), #9
            f"{self.side}_legSoftEPower_FLM": ("floatMath", 6), #10
            f"{self.side}_legSoftOneMinusEPower_FLM": ("floatMath", 1), #11
            f"{self.side}_legSoftOneMinusEPowerSoftValueEnable_FLM": ("floatMath", 2), #12
            f"{self.side}_legSoftConstant_FLM": ("floatMath", 0), #13
            f"{self.side}_legSoftRatio_FLM": ("floatMath", 3), #14
            f"{self.side}_legLengthRatio_FLM": ("floatMath", 3), #15
            f"{self.side}_legDistanceToControlDividedByTheLengthRatio_FLM": ("floatMath", 3), #16
            f"{self.side}_legSoftEffectorDistance_FLM": ("floatMath", 2), #17
            f"{self.side}_legSoftCondition_CON": ("condition", None), #18
            f"{self.side}_legDistanceToControlDividedByTheSoftEffectorMinusOne_FLM": ("floatMath", 1), #19 
            f"{self.side}_legDistanceToControlDividedByTheSoftEffectorMinusOneMultipliedByTheStretch_FLM": ("floatMath", 2), #20 
            f"{self.side}_legStretchFactor_FLM": ("floatMath", 0), #21 
            f"{self.side}_legSoftEffectStretchDistance_FLM": ("floatMath", 2), #22 
            f"{self.side}_legUpperLengthStretch_FLM": ("floatMath", 2), #23 
            f"{self.side}_legLowerLengthStretch_FLM": ("floatMath", 2), #24 
            f"{self.side}_legDistanceToControlDividedByTheSoftEffector_FLM": ("floatMath", 3), #25
            f"{self.side}_legUpperPin_DBT": ("distanceBetween", None), #26
            f"{self.side}_legLowerPin_DBT": ("distanceBetween", None), #27
            f"{self.side}_legUpperPin_BTA": ("blendTwoAttr", None), #28
            f"{self.side}_legLowerPin_BTA": ("blendTwoAttr", None), #29
            f"{self.side}_legMiddleLength_FLM": ("floatMath", 2), #30
            f"{self.side}_legFullLengthUpperPart_FLM": ("floatMath", 0), #31
            f"{self.side}_legSoftCondition_CON": ("condition", None), #32
            
        }



        created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        # Connections between selected nodes
        cmds.connectAttr(created_nodes[0] + ".distance", created_nodes[1]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[15]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[7]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[16]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[18]+".firstTerm")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[18]+".colorIfFalseR")
        cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[18]+".colorIfFalseG")
        cmds.connectAttr(created_nodes[3] + ".outFloat", created_nodes[14]+".floatB")
        cmds.connectAttr(created_nodes[3] + ".outFloat", created_nodes[6]+".floatA")
        cmds.connectAttr(created_nodes[3] + ".outFloat", created_nodes[15]+".floatB")
        cmds.connectAttr(created_nodes[4] + ".outFloat", created_nodes[18]+".colorIfFalseB")
        cmds.connectAttr(created_nodes[5] + ".outValue", created_nodes[8]+".floatB")
        cmds.connectAttr(created_nodes[5] + ".outValue", created_nodes[6]+".floatB")
        cmds.connectAttr(created_nodes[5] + ".outValue", created_nodes[12]+".floatA")
        cmds.connectAttr(created_nodes[6] + ".outFloat", created_nodes[13]+".floatB")
        cmds.connectAttr(created_nodes[6] + ".outFloat", created_nodes[7]+".floatB")
        cmds.connectAttr(created_nodes[6] + ".outFloat", created_nodes[18]+".secondTerm")
        cmds.connectAttr(created_nodes[7] + ".outFloat", created_nodes[8]+".floatA")
        cmds.connectAttr(created_nodes[8] + ".outFloat", created_nodes[9]+".floatA")
        cmds.connectAttr(created_nodes[9] + ".outFloat", created_nodes[10]+".floatB")
        cmds.connectAttr(created_nodes[10] + ".outFloat", created_nodes[11]+".floatB")
        cmds.connectAttr(created_nodes[11] + ".outFloat", created_nodes[12]+".floatB")
        cmds.connectAttr(created_nodes[12] + ".outFloat", created_nodes[13]+".floatA")
        cmds.connectAttr(created_nodes[13] + ".outFloat", created_nodes[14]+".floatA")
        cmds.connectAttr(created_nodes[14] + ".outFloat", created_nodes[17]+".floatA")
        cmds.connectAttr(created_nodes[15] + ".outFloat", created_nodes[16]+".floatB")
        cmds.connectAttr(created_nodes[16] + ".outFloat", created_nodes[17]+".floatB")

        cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[31]+".floatA")
        cmds.connectAttr(created_nodes[30] + ".outFloat", created_nodes[31]+".floatB")
        cmds.connectAttr(created_nodes[4] + ".outFloat", created_nodes[3]+".floatB")
        cmds.connectAttr(created_nodes[31] + ".outFloat", created_nodes[3]+".floatA")
        

        cmds.connectAttr(created_nodes[19] + ".outFloat", created_nodes[20]+".floatA")
        cmds.connectAttr(created_nodes[20] + ".outFloat", created_nodes[21]+".floatA")
        cmds.connectAttr(created_nodes[21] + ".outFloat", created_nodes[23]+".floatA")
        cmds.connectAttr(created_nodes[21] + ".outFloat", created_nodes[22]+".floatB")
        cmds.connectAttr(created_nodes[21] + ".outFloat", created_nodes[24]+".floatB")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[25]+".floatA")
        cmds.connectAttr(created_nodes[17] + ".outFloat", created_nodes[25]+".floatB")
        cmds.connectAttr(created_nodes[17] + ".outFloat", created_nodes[22]+".floatA")

        cmds.connectAttr(created_nodes[25] + ".outFloat", created_nodes[19]+".floatA")

        cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[23]+".floatB")
        cmds.connectAttr(created_nodes[4] + ".outFloat", created_nodes[24]+".floatA")


        cmds.connectAttr(self.ik_ctls[2] + ".stretch", created_nodes[20]+".floatB")

        cmds.connectAttr(created_nodes[22] + ".outFloat", created_nodes[18]+".colorIfTrueR")
        cmds.connectAttr(created_nodes[23] + ".outFloat", created_nodes[18]+".colorIfTrueG")
        cmds.connectAttr(created_nodes[24] + ".outFloat", created_nodes[18]+".colorIfTrueB")


    
    def handles_setup(self):

        # --- Ik Handle ---
        self.main_ik_handle = cmds.ikHandle(
            n=f"{self.side}_wingArmIkHandle",
            sj=self.ik_chain[0],
            ee=self.ik_chain[-1],
            sol="rotatePlaneSolver",
        )[0]
        # Later parent cosntraint to the armSoft TRN
        cmds.parentConstraint(self.soft_off, self.main_ik_handle, mo=True)
         
       
        self.upper_non_roll_jnt = cmds.joint(n=f"{self.side}_wingArmUpperNonRoll_JNT")
        self.upper_non_roll_end_jnt = cmds.joint(n=f"{self.side}_wingArmUpperNonRollEnd_JNT")
        cmds.parent(self.upper_non_roll_end_jnt, self.upper_non_roll_jnt)
        cmds.matchTransform(self.upper_non_roll_jnt, self.ik_chain[0], pos=True, rot=True)
        cmds.matchTransform(self.upper_non_roll_end_jnt, self.ik_chain[1], pos=True, rot=True)

        self.upper_roll_jnt = cmds.joint(n=f"{self.side}_wingArmUpperRoll_JNT")
        self.upper_roll_end_jnt = cmds.joint(n=f"{self.side}_wingArmUpperRollEnd_JNT")
        cmds.parent(self.upper_roll_end_jnt, self.upper_roll_jnt)
        cmds.matchTransform(self.upper_roll_jnt, self.ik_chain[1], pos=True, rot=True)
        cmds.matchTransform(self.upper_roll_end_jnt, self.ik_chain[2], pos=True, rot=True)
        cmds.parent(self.upper_roll_jnt, self.upper_non_roll_end_jnt)
    
        
        self.upper_non_roll_ik_handle = cmds.ikHandle(
            n=f"{self.side}_wingArmUpperNonRollIkHandle",
            sj=self.upper_non_roll_jnt,
            ee=self.upper_non_roll_end_jnt,
            sol="ikSCsolver",
        )[0]
        cmds.parentConstraint(self.blend_chain[1], self.upper_non_roll_ik_handle, mo=True)
        self.upper_roll_ik_handle_grp = cmds.ikHandle(
            n=f"{self.side}_wingArmUpperRollIkHandle",
            sj=self.upper_roll_jnt,
            ee=self.upper_roll_end_jnt,
            sol="ikSCsolver",
        )[0]
        cmds.parentConstraint(self.blend_chain[2], self.upper_roll_ik_handle_grp, mo=True)

        # --- Lower Roll Ik Handle ---
        self.lower_roll_jnt = cmds.joint(n=f"{self.side}_wingArmLowerRoll_JNT")
        self.lower_roll_end_jnt = cmds.joint(n=f"{self.side}_wingArmLowerRollEnd_JNT")
        cmds.parent(self.lower_roll_end_jnt, self.lower_roll_jnt)
        cmds.matchTransform(self.lower_roll_jnt, self.ik_chain[1], pos=True, rot=True)
        cmds.matchTransform(self.lower_roll_end_jnt, self.ik_chain[-1], pos=True, rot=True)

        self.lower_roll_handle = cmds.ikHandle(
            n=f"{self.side}_wingArmLowerRollIkHandle",
            sj=self.lower_roll_jnt,
            ee=self.lower_roll_end_jnt,
            sol="ikSCsolver",
        )[0]



