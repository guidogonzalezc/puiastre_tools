"""
Leg module for dragon rigging system
"""
import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
import maya.mel as mel
import math
import os
from importlib import reload
reload(guides_manager)
reload(curve_tool)    

class LegModule():
    def __init__(self):
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "leg_guides_template_01.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "foot_ctl.json") 

    def make(self, side):

        self.side = side    

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_legModule_GRP")
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_legControllers_GRP")
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_legSkinning_GRP")

        self.duplicate_leg()
        self.set_controllers()
        # self.pairBlends()
        # self.reverse_foot()
        # self.soft_stretch()

    def lock_attr(self, ctl, attrs = ["scaleX", "scaleY", "scaleZ", "visibility"]):
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", keyable=False, channelBox=False, lock=True)

    def duplicate_leg(self):

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
                joint_name=f"{self.side}_hip_JNT",
                all_descendents=True,
                filePath=self.guides_path
            )
            cmds.parent(guides[0], self.module_trn)

            for joint in guides:
                chain.append(cmds.rename(joint, joint.replace("_JNT", f"{name}_JNT")))





    def set_controllers(self):

        # -- IK/FK SWITCHCONTROLLER -- # 

        self.ik_trn = cmds.createNode("transform", name=f"{self.side}_legIk_GRP", parent=self.controllers_trn)
        self.fk_trn = cmds.createNode("transform", name=f"{self.side}_legFk_GRP", parent=self.controllers_trn)

        self.settings_curve_ctl, self.settings_curve_grp = curve_tool.controller_creator(f"{self.side}_LegSettings")
        cmds.matchTransform(self.settings_curve_grp[0], self.ik_chain[0], pos=True)
        cmds.move(100, 0, 0, self.settings_curve_grp[0], r=True, os=True)
        cmds.addAttr(self.settings_curve_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        self.lock_attr(self.settings_curve_ctl, ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{self.fk_trn}.visibility")
        rev = cmds.createNode("reverse", name=f"{self.side}_legFkVisibility_REV")
        cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{rev}.inputX")
        cmds.connectAttr(f"{rev}.outputX", f"{self.ik_trn}.visibility")
        cmds.parent(self.settings_curve_grp[0], self.controllers_trn)

        # -- FK CONTROLLER -- #

        self.fk_ctl_list = []
        self.fk_grp_list = []

        for i, joint in enumerate(self.fk_chain[:-1]):
            fk_ctl, fk_grp = curve_tool.controller_creator(joint.replace('_JNT', ''))
            self.fk_ctl_list.append(fk_ctl)
            self.fk_grp_list.append(fk_grp)

            if "foot" in joint:
                cmds.matchTransform(fk_grp[0], joint, pos=True)
            else:
                cmds.matchTransform(fk_grp[0], joint)

            cmds.parentConstraint(fk_grp[0], joint, mo=True)

            if i > 0:
                cmds.parent(fk_grp[0], self.fk_ctl_list[i - 1])
            else:
                cmds.parent(fk_grp[0], self.fk_trn)
            
            self.lock_attr(fk_ctl)


        #-- IK CONTROLLER -- #

        if not cmds.pluginInfo("ikSpringSolver", query=True, loaded=True):
            cmds.loadPlugin("ikSpringSolver")

        self.ikHandleManager = cmds.createNode("transform", name=f"{self.side}_legIkHandleManager_GRP", p=self.module_trn)

        self.springIkHandle = cmds.ikHandle(
            name=f"{self.side}_legIkHandle",
            startJoint=self.ik_chain[0],
            endEffector=self.ik_chain[3],
            solver="ikSpringSolver",
        )[0]

        cmds.setAttr(f"{self.springIkHandle}.poleVectorX", 0)
        cmds.setAttr(f"{self.springIkHandle}.poleVectorY", 0)
        cmds.setAttr(f"{self.springIkHandle}.poleVectorZ", 1)

        self.ballIkHandle = cmds.ikHandle( 
            name=f"{self.side}_legBallIkHandle",
            startJoint=self.ik_chain[3],
            endEffector=self.ik_chain[4],
            solver="ikSCsolver",
        )[0]

        self.tipIkHandle = cmds.ikHandle(
            name=f"{self.side}_legTipIkHandle",
            startJoint=self.ik_chain[4],
            endEffector=self.ik_chain[5],
            solver="ikSCsolver",
        )[0]


        ik_controllers = {
            self.ik_chain[0]: ["rootIk",True, self.ik_chain[0]],
            self.ik_chain[1]: ["legPv", False, self.springIkHandle],
            self.ik_chain[2]: [None, False, False],
            self.ik_chain[3]: ["legIk", False, False],
            self.ik_chain[4]: ["ballIk", True, self.ballIkHandle],
            self.ik_chain[5]: ["toeIk", True, self.tipIkHandle],  

        }

        self.ik_ctl_grps = []
        self.ik_ctls = []

        for name, data in ik_controllers.items():
            print (name, data)
            if data[0]:
                ik_ctl, ik_grp = curve_tool.controller_creator(data[0])
                cmds.parent(ik_grp[0], self.ik_trn)
                
            else:
                continue
            if data[0]:
                match_pos = not data[1]
                cmds.matchTransform(ik_grp[0], name, pos=match_pos)

            if data[2]:
                if name == self.ik_chain[1]:
                    cmds.move(0, 0, 150, ik_grp[0], r=True, ws=True)
                    cmds.poleVectorConstraint(ik_ctl, data[2])    
                else:
                   cmds.parentConstraint(ik_ctl, data[2], mo=True)


            self.ik_ctl_grps.append(ik_grp[0])
            self.ik_ctls.append(ik_ctl)





        # cmds.addAttr(self.ik_ankle_ctl, shortName="strechySep", niceName="STRECHY_____", enumName="_____",attributeType="enum", keyable=True)
        # cmds.setAttr(self.ik_ankle_ctl+".strechySep", channelBox=True, lock=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="upperLengthMult", niceName="Upper Length Mult",minValue=0.001,defaultValue=1, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="middleLengthMult", niceName="Middle Length Mult",minValue=0.001,defaultValue=1, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="lowerLengthMult", niceName="Lower Length Mult",minValue=0.001,defaultValue=1, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="stretch", niceName="Stretch",minValue=0,maxValue=1,defaultValue=0, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="softSep", niceName="SOFT_____", enumName="_____",attributeType="enum", keyable=True)
        # cmds.setAttr(self.ik_ankle_ctl+".softSep", channelBox=True, lock=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="soft", niceName="Soft",minValue=0,maxValue=1,defaultValue=0, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="extraSep", niceName="EXTRA_____", enumName="_____",attributeType="enum", keyable=True)
        # cmds.setAttr(self.ik_ankle_ctl+".extraSep", channelBox=True, lock=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="roll", niceName="Roll",defaultValue=0, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="rollLiftAngle", niceName="Roll Lift Angle",minValue=0,defaultValue=45, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="rollStraightAngle", niceName="Roll Straight Angle",minValue=0,defaultValue=90, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="bank", niceName="Bank",defaultValue=0, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="ankleTwist", niceName="Ankle Twist",defaultValue=0, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="ballTwist", niceName="Ball Twist",defaultValue=0, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="tipTwist", niceName="Tip Twist",defaultValue=0, keyable=True)
        # cmds.addAttr(self.ik_ankle_ctl, shortName="heelTwist", niceName="Heel Twist",defaultValue=0, keyable=True)

    def pairBlends(self):
        for i, joint in enumerate(self.foot_joints):
            pairblend_node = cmds.createNode("pairBlend", name=f"{joint.replace('JNT', 'PBL')}", ss=True)
            cmds.connectAttr(f"{self.ik_chain[i]}.translate", f"{pairblend_node}.inTranslate1")
            cmds.connectAttr(f"{self.fk_chain[i]}.translate", f"{pairblend_node}.inTranslate2")
            cmds.connectAttr(f"{pairblend_node}.outTranslate", f"{joint}.translate")
            cmds.connectAttr(f"{self.ik_chain[i]}.rotate", f"{pairblend_node}.inRotate1")
            cmds.connectAttr(f"{self.fk_chain[i]}.rotate", f"{pairblend_node}.inRotate2")
            cmds.connectAttr(f"{pairblend_node}.outRotate", f"{joint}.rotate")
            cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{pairblend_node}.weight")

    def soft_stretch(self):

        masterwalk = "C_masterwalk_CTL"

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

        cmds.connectAttr(self.ik_ankle_ctl + ".stretch", created_nodes[20]+".floatB")

        cmds.connectAttr(created_nodes[22] + ".outFloat", created_nodes[18]+".colorIfTrueR")
        cmds.connectAttr(created_nodes[23] + ".outFloat", created_nodes[18]+".colorIfTrueG")
        cmds.connectAttr(created_nodes[24] + ".outFloat", created_nodes[18]+".colorIfTrueB")


        # cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[32]+".firstTerm")
        # cmds.connectAttr(created_nodes[6] + ".outFloat", created_nodes[32]+".secondTerm")


        # Connections TRN and nodes

        cmds.connectAttr(f"{self.root_ctl}.worldMatrix", f"{created_nodes[0]}.inMatrix1")
        cmds.connectAttr(f"{self.ikHandleManager}.worldMatrix", f"{created_nodes[0]}.inMatrix2")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.lowerLengthMult", f"{created_nodes[4]}.floatA")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.upperLengthMult", f"{created_nodes[2]}.floatA")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.middleLengthMult", f"{created_nodes[30]}.floatA")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.soft", f"{created_nodes[5]}.inputValue")
        cmds.connectAttr(f"{masterwalk}.globalScale", f"{created_nodes[1]}.floatB")
        cmds.connectAttr(f"{created_nodes[18]}.outColorR",f"{self.trn_node}.translateX")

        # setAttr nodes



        cmds.setAttr(f"{created_nodes[2]}.floatB", cmds.getAttr(f"{self.ik_chain[1]}.translateX"))
        cmds.setAttr(f"{created_nodes[4]}.floatB", cmds.getAttr(f"{self.ik_chain[2]}.translateX"))
        cmds.setAttr(f"{created_nodes[30]}.floatB", cmds.getAttr(f"{self.ik_chain[3]}.translateX"))
    
        cmds.setAttr(f"{created_nodes[9]}.floatB", -1)
        cmds.setAttr(f"{created_nodes[10]}.floatA", math.e)
        cmds.setAttr(f"{created_nodes[11]}.floatA", 1)
        cmds.setAttr(f"{created_nodes[5]}.inputMin", 0.001)
        cmds.setAttr(f"{created_nodes[5]}.outputMax", (cmds.getAttr(f"{created_nodes[3]}.outFloat") - cmds.getAttr(f"{created_nodes[1]}.outFloat")))
        cmds.setAttr(f"{created_nodes[18]}.operation", 2)
        cmds.setAttr(f"{created_nodes[19]}.floatB", 1)


   


        cmds.parentConstraint(self.trn_node, self.ik_handle_spring[0], mo=True)

               

        # # FK STRETCH WIP

        # upper_mult = cmds.createNode("multDoubleLinear", name=f"{self.side}_legFkUpperLengthMult_MDL")
        # lower_mult = cmds.createNode("multDoubleLinear", name=f"{self.side}_legFkLowerLengthMult_MDL")



        # cmds.setAttr(f"{upper_mult}.input2", cmds.getAttr(f"{self.joint_defaule_names[1]}.translateX"))
        # cmds.setAttr(f"{lower_mult}.input2", cmds.getAttr(f"{self.joint_defaule_names[2]}.translateX"))


        # cmds.connectAttr(f"{shoulderFkCtl}.stretch", upper_mult+".input1")
        # cmds.connectAttr(f"{elbowFkCtl}.stretch", lower_mult+".input1")
        # cmds.connectAttr(f"{upper_mult}.output", f"{elbowFkGrp}.translateX")
        # cmds.connectAttr(f"{lower_mult}.output", f"{wristFkGrp}.translateX")


        # shoulderFkCtl = self.created_ctls[0] 
        # elbowFkCtl = self.created_ctls[1]
        # elbowFkGrp = self.fk_ctl_transforms[1]
        # wristFkGrp = self.fk_ctl_transforms[2]

    def reverse_foot(self):
        #----ADDING THE ROLL----#

        ### GENERATED CODE ###
        nodes_to_create = [
            (f"{self.side}_rollStraightAnglePercentage_RMV", "remapValue", None), #0
            (f"{self.side}_rollLiftAnglePercentage_RMV", "remapValue", None),  #1
            (f"{self.side}_rollStraightAnglePercentage_REV", "reverse", None),  #2 
            (f"{self.side}_rollLiftAngleEnable_MDN", "multiplyDivide", None),  #3
            (f"{self.side}_rollStrightAngle_MDN", "multiplyDivide", None), #4
            (f"{self.side}_rollLiftAngle_MDN", "multiplyDivide", None),    #5
            (f"{self.side}_rollStrightAngleNegate_MDN", "multiplyDivide", None),   #6
            (f"{self.side}_rollHeel_CLM", "clamp", None),  #7
            (f"{self.side}_footBank_CLM", "clamp", None),  #8
            (f"{self.side}_rollLiftAngleNegate_MDN", "multiplyDivide", None),  #9
        ]

        created_nodes = []
        for node_name, node_type, operation in nodes_to_create:
            node = cmds.createNode(node_type, name=node_name)
            created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        # Connections between selected nodes and transform nodes
        cmds.connectAttr(created_nodes[0] + ".outValue", f"{created_nodes[4]}.input1X")
        cmds.connectAttr(created_nodes[0] + ".outValue", f"{created_nodes[2]}.inputX")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.roll", created_nodes[0] + ".inputValue")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.rollLiftAngle", created_nodes[0] + ".inputMin")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.rollStraightAngle", created_nodes[0] + ".inputMax")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.roll", created_nodes[1] + ".inputValue")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.roll", created_nodes[7] + ".inputR")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.roll", created_nodes[5] + ".input2X")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.roll", created_nodes[4] + ".input2X")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.rollLiftAngle", created_nodes[1] + ".inputMax")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.bank", created_nodes[8] + ".inputG")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.bank", created_nodes[8] + ".inputR")
        cmds.setAttr(f"{created_nodes[6]}.input2X", 1)
        cmds.setAttr(f"{created_nodes[9]}.input2X", 1)
        cmds.setAttr(f"{created_nodes[7]}.minR", -360)
        if self.side == "L_":
            cmds.setAttr(f"{created_nodes[8]}.minG", -360)
            cmds.setAttr(f"{created_nodes[8]}.maxR", 360)
        elif self.side == "R_":
            cmds.setAttr(f"{created_nodes[8]}.minR", -360)
            cmds.setAttr(f"{created_nodes[8]}.maxG", 360)
        cmds.connectAttr(created_nodes[1] + ".outValue", f"{created_nodes[3]}.input2X")
        cmds.connectAttr(created_nodes[2] + ".outputX", f"{created_nodes[3]}.input1X")
        cmds.connectAttr(created_nodes[3] + ".outputX", f"{created_nodes[5]}.input1X")
        cmds.connectAttr(created_nodes[4] + ".outputX", f"{created_nodes[6]}.input1X")
        cmds.connectAttr(created_nodes[5] + ".outputX", f"{created_nodes[9]}.input1X")
        cmds.connectAttr(created_nodes[8] + ".outputR", f"{self.ik_bankIn_grp[3]}.rotateZ")
        cmds.connectAttr(created_nodes[8] + ".outputG", f"{self.bankOut_grp[3]}.rotateZ")
        cmds.connectAttr(created_nodes[7] + ".outputR", f"{self.ik_heel_grp[3]}.rotateX")
        cmds.connectAttr(created_nodes[6] + ".outputX", f"{self.ik_tip_grp[3]}.rotateY")
        cmds.connectAttr(created_nodes[9] + ".outputX", f"{self.ik_toe_grp[3]}.rotateY")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.heelTwist", f"{self.ik_heel_grp[3]}.rotateY")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.tipTwist", f"{self.ik_tip_grp[3]}.rotateZ")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.ballTwist", f"{self.ik_toe_grp[3]}.rotateZ")
        cmds.connectAttr(f"{self.ik_ankle_ctl}.ankleTwist", self.ik_ankle_grp[3] + ".rotateY")

        cmds.setAttr(f"{created_nodes[7]}.maxR", 360)
        cmds.setAttr(f"{created_nodes[7]}.minR", -360)

        cmds.parentConstraint(self.ik_toe_ctl, self.ikHandleManager, maintainOffset=True)


