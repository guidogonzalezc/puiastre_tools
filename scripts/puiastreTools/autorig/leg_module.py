"""
Leg module for dragon rigging system
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import basic_structure
from puiastreTools.utils import data_export
import maya.mel as mel
import math
import os
from importlib import reload
reload(guides_manager)
reload(basic_structure)
reload(curve_tool)    
reload(data_export)    

class LegModule():
    def __init__(self):
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "dragon_guides_template_01.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "foot_ctl.json") 

        data_exporter = data_export.DataExport()

        self.modules_grp = data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = data_exporter.get_data("basic_structure", "masterWalk_CTL")

    def make(self, side):

        self.side = side    

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_legModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_legControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_legSkinning_GRP", ss=True, parent=self.skel_grp)
        self.bendy_module = cmds.createNode("transform", name=f"{self.side}_legBendyModule_GRP", ss=True, p=self.module_trn)

        self.duplicate_leg()
        self.set_controllers()
        self.pairBlends()
        self.soft_stretch()
        self.reverse_foot()
        self.call_bendys()

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

        self.ik_trn = cmds.createNode("transform", name=f"{self.side}_legIkControllers_GRP", parent=self.controllers_trn, ss=True)
        self.fk_trn = cmds.createNode("transform", name=f"{self.side}_legFkControllers_GRP", parent=self.controllers_trn, ss=True)

        self.settings_curve_ctl, self.settings_curve_grp = curve_tool.controller_creator(f"{self.side}_LegSettings", suffixes = ["GRP"])
        position, rotation = guides_manager.guide_import(joint_name=f"{self.side}_legSwitch", filePath=self.guides_path)
        cmds.xform(self.settings_curve_ctl, ws=True, translation=position)
        cmds.xform(self.settings_curve_ctl, ws=True, rotation=rotation)
        cmds.addAttr(self.settings_curve_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        self.lock_attr(self.settings_curve_ctl, ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{self.fk_trn}.visibility")
        rev = cmds.createNode("reverse", name=f"{self.side}_legFkVisibility_REV", ss=True)
        cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{rev}.inputX")
        cmds.connectAttr(f"{rev}.outputX", f"{self.ik_trn}.visibility")
        cmds.parent(self.settings_curve_grp[0], self.controllers_trn)

        # -- FK CONTROLLER -- #

        self.fk_ctl_list = []
        self.fk_grp_list = []

        for i, joint in enumerate(self.fk_chain[:-1]):
            fk_ctl, fk_grp = curve_tool.controller_creator(joint.replace('_JNT', ''), suffixes = ["GRP", "OFF"])
            self.fk_ctl_list.append(fk_ctl)
            self.fk_grp_list.append(fk_grp)

            if "foot" in joint:
                cmds.matchTransform(fk_grp[0], joint, pos=True)
            else:
                cmds.matchTransform(fk_grp[0], joint)

            cmds.parentConstraint(fk_ctl, joint, mo=True)

            if i > 0:
                cmds.parent(fk_grp[0], self.fk_ctl_list[i - 1])
            else:
                cmds.parent(fk_grp[0], self.fk_trn)
            
            self.lock_attr(fk_ctl)


        #-- IK CONTROLLER -- #
        if not cmds.pluginInfo("ikSpringSolver", query=True, loaded=True):
            cmds.loadPlugin("ikSpringSolver")
        
        mel.eval("ikSpringSolver")

        self.ikHandleManager = cmds.createNode("transform", name=f"{self.side}_legIkHandleManager_GRP", p=self.module_trn, ss=True)
        cmds.matchTransform(self.ikHandleManager, self.ik_chain[3], pos=True)

        self.springIkHandle = cmds.ikHandle(
            name=f"{self.side}_legIk_HDL",
            startJoint=self.ik_chain[0],
            endEffector=self.ik_chain[3],
            solver="ikSpringSolver",
        )[0]

        cmds.setAttr(f"{self.springIkHandle}.poleVectorX", 0)
        cmds.setAttr(f"{self.springIkHandle}.poleVectorY", 0)
        cmds.setAttr(f"{self.springIkHandle}.poleVectorZ", 1)


        self.ballIkHandle = cmds.ikHandle( 
            name=f"{self.side}_legBallIk_HDL",
            startJoint=self.ik_chain[3],
            endEffector=self.ik_chain[4],
            solver="ikSCsolver",
        )[0]

        self.tipIkHandle = cmds.ikHandle(
            name=f"{self.side}_legTipIk_HDL",
            startJoint=self.ik_chain[4],
            endEffector=self.ik_chain[5],
            solver="ikSCsolver",
        )[0]

        cmds.parent(self.springIkHandle, self.ballIkHandle, self.tipIkHandle, self.module_trn)

        ik_controllers = {
            self.ik_chain[0]: [f"{self.side}_rootIk",True, [self.ik_chain[0]]],
            self.ik_chain[1]: [f"{self.side}_legPv", False, [self.springIkHandle]],
            self.ik_chain[2]: [None, False, False],
            self.ik_chain[3]: [f"{self.side}_legIk", False, False],
            self.ik_chain[4]: [f"{self.side}_ballIk", True, [self.ballIkHandle, self.ikHandleManager]],
            self.ik_chain[5]: [f"{self.side}_toeIk", True, [self.tipIkHandle]],  

        }

        self.ik_ctl_grps = []
        self.ik_ctls = []

        for name, data in ik_controllers.items():
            if data[0]:
                ik_ctl, ik_grp = curve_tool.controller_creator(data[0], suffixes = ["GRP", "SDK"])
                cmds.parent(ik_grp[0], self.ik_trn)
                self.ik_ctl_grps.append(ik_grp)
                self.ik_ctls.append(ik_ctl)
                self.lock_attr(ik_ctl)

            else:
                continue
            if data[0]:
                match_pos = not data[1]
                cmds.matchTransform(ik_grp[0], name, pos=match_pos)

            if data[2]:
                if name == self.ik_chain[1]:
                    arm_pos = om.MVector(cmds.xform(self.ik_chain[0], q=True, rp=True, ws=True))
                    elbow_pos = om.MVector(cmds.xform(self.ik_chain[1], q=True, rp=True, ws=True))
                    wrist_pos = om.MVector(cmds.xform(self.ik_chain[2], q=True, rp=True, ws=True))

                    arm_to_wrist = wrist_pos - arm_pos
                    arm_to_wrist_scaled = arm_to_wrist / 2
                    mid_point = arm_pos + arm_to_wrist_scaled
                    mid_point_to_elbow_vec = elbow_pos - mid_point
                    mid_point_to_elbow_vec_scaled = mid_point_to_elbow_vec * 2
                    mid_point_to_elbow_point = mid_point + mid_point_to_elbow_vec_scaled

                    cmds.xform(ik_grp[0], translation=mid_point_to_elbow_point)

                    cmds.poleVectorConstraint(ik_ctl, data[2])    
                else:
                    for child_constraints in data[2]:
                        cmds.parentConstraint(ik_ctl, child_constraints, mo=True)
                        


        for item in [f"{self.side}_bankIn", f"{self.side}_bankOut", f"{self.side}_heel"]:
            position, rotation = guides_manager.guide_import(joint_name=item, filePath=self.guides_path)
            ctl, clt_grp = curve_tool.controller_creator(item, suffixes = ["GRP", "SDK"])
            cmds.xform(clt_grp, ws=True, translation=position)
            cmds.xform(clt_grp, ws=True, rotation=rotation)
            self.ik_ctls.append(ctl)
            self.ik_ctl_grps.append(clt_grp)

        cmds.parent(self.ik_ctl_grps[3][0], self.ik_ctls[4])
        cmds.parent(self.ik_ctl_grps[4][0], self.ik_ctls[7])
        cmds.parent(self.ik_ctl_grps[7][0], self.ik_ctls[6])
        cmds.parent(self.ik_ctl_grps[6][0], self.ik_ctls[5])
        cmds.parent(self.ik_ctl_grps[5][0], self.ik_ctls[2])

        cmds.addAttr(self.ik_ctls[2], shortName="strechySep", niceName="STRECHY_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.ik_ctls[2]+".strechySep", channelBox=True, lock=True)
        cmds.addAttr(self.ik_ctls[2], shortName="upperLengthMult", niceName="Upper Length Mult",minValue=0.001,defaultValue=1, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="middleLengthMult", niceName="Middle Length Mult",minValue=0.001,defaultValue=1, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="lowerLengthMult", niceName="Lower Length Mult",minValue=0.001,defaultValue=1, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="stretch", niceName="Stretch",minValue=0,maxValue=1,defaultValue=0, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="softSep", niceName="SOFT_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.ik_ctls[2]+".softSep", channelBox=True, lock=True)
        cmds.addAttr(self.ik_ctls[2], shortName="soft", niceName="Soft",minValue=0,maxValue=1,defaultValue=0, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="extraSep", niceName="EXTRA_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.ik_ctls[2]+".extraSep", channelBox=True, lock=True)
        cmds.addAttr(self.ik_ctls[2], shortName="roll", niceName="Roll",defaultValue=0, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="rollLiftAngle", niceName="Roll Lift Angle",minValue=0,defaultValue=45, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="rollStraightAngle", niceName="Roll Straight Angle",minValue=0,defaultValue=90, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="bank", niceName="Bank",defaultValue=0, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="ankleTwist", niceName="Ankle Twist",defaultValue=0, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="ballTwist", niceName="Ball Twist",defaultValue=0, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="tipTwist", niceName="Tip Twist",defaultValue=0, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="heelTwist", niceName="Heel Twist",defaultValue=0, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="springSolverBias01", niceName="Spring Solver Bias 01",defaultValue=0.5,minValue=0, maxValue=1, keyable=True)
        cmds.addAttr(self.ik_ctls[2], shortName="springSolverBias02", niceName="Spring Solver Bias 02",defaultValue=0.5,minValue=0, maxValue=1, keyable=True)
        cmds.connectAttr(f"{self.ik_ctls[2]}.springSolverBias01", f"{self.springIkHandle}.springAngleBias[0].springAngleBias_FloatValue")
        cmds.connectAttr(f"{self.ik_ctls[2]}.springSolverBias02", f"{self.springIkHandle}.springAngleBias[1].springAngleBias_FloatValue")

    def pairBlends(self):
        for i, joint in enumerate(self.blend_chain):
            pairblend_node = cmds.createNode("pairBlend", name=f"{joint.replace('JNT', 'PBL')}", ss=True)
            cmds.connectAttr(f"{self.ik_chain[i]}.translate", f"{pairblend_node}.inTranslate1")
            cmds.connectAttr(f"{self.fk_chain[i]}.translate", f"{pairblend_node}.inTranslate2")
            cmds.connectAttr(f"{pairblend_node}.outTranslate", f"{joint}.translate")
            cmds.connectAttr(f"{self.ik_chain[i]}.rotate", f"{pairblend_node}.inRotate1")
            cmds.connectAttr(f"{self.fk_chain[i]}.rotate", f"{pairblend_node}.inRotate2")
            cmds.connectAttr(f"{pairblend_node}.outRotate", f"{joint}.rotate")
            cmds.connectAttr(f"{self.settings_curve_ctl}.switchIkFk", f"{pairblend_node}.weight")
        
        cmds.select(clear=True)
        ball_skinning_joint = cmds.joint(name=f"{self.side}_ball_JNT")
        cmds.connectAttr(f"{self.blend_chain[4]}.worldMatrix[0]", f"{ball_skinning_joint}.offsetParentMatrix")
        cmds.parent(ball_skinning_joint, self.skinning_trn)

    def soft_stretch(self):

        masterwalk = self.masterWalk_ctl# Change this to the actual masterwalk controller name

        self.soft_off = cmds.createNode("transform", name=f"{self.side}_legSoft_OFF", p=self.module_trn, ss=True)
        cmds.pointConstraint(self.ik_ctls[0], self.soft_off)
        cmds.aimConstraint(self.ikHandleManager, self.soft_off, aimVector=(1,0,0), upVector= (0,0,1), worldUpType ="none", maintainOffset=False)

        self.soft_trn = cmds.createNode("transform", name=f"{self.side}_legSoft_TRN", p=self.soft_off, ss=True)



        nodes_to_create = {
            f"{self.side}_legDistanceToControl_DBT": ("distanceBetween", None), #0
            f"{self.side}_legDistanceToControlNormalized_FLM": ("floatMath", 3), #1
            f"{self.side}_legUpperLength_FLM": ("floatMath", 2), #2
            f"{self.side}_legFullLength_PMA": ("plusMinusAverage", 1), #3
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
            f"{self.side}_legSoftCondition_CON": ("condition", 2), #18
            f"{self.side}_legDistanceToControlDividedByTheSoftEffectorMinusOne_FLM": ("floatMath", 1), #19 
            f"{self.side}_legDistanceToControlDividedByTheSoftEffectorMinusOneMultipliedByTheStretch_FLM": ("floatMath", 2), #20 
            f"{self.side}_legStretchFactor_FLM": ("floatMath", 0), #21 
            f"{self.side}_legSoftEffectStretchDistance_FLM": ("floatMath", 2), #22 
            f"{self.side}_legUpperLengthStretch_FLM": ("floatMath", 2), #23 
            f"{self.side}_legLowerLengthStretch_FLM": ("floatMath", 2), #24 
            f"{self.side}_legDistanceToControlDividedByTheSoftEffector_FLM": ("floatMath", 3), #25
            f"{self.side}_legMiddleLength_FLM": ("floatMath", 2), #30 - 26
            f"{self.side}_legStretchCondition_CON": ("condition", 2), #32 - 27
            f"{self.side}_legMiddleLengthStretch_FLM": ("floatMath", 2), #28

            
        }






        created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name, ss=True)
            created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        # Connections between selected nodes
        cmds.connectAttr(created_nodes[0] + ".distance", created_nodes[1]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[15]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[7]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[16]+".floatA")
        cmds.connectAttr(created_nodes[3] + ".output1D", created_nodes[14]+".floatB")
        cmds.connectAttr(created_nodes[3] + ".output1D", created_nodes[6]+".floatA")
        cmds.connectAttr(created_nodes[3] + ".output1D", created_nodes[15]+".floatB")
        cmds.connectAttr(created_nodes[5] + ".outValue", created_nodes[8]+".floatB")
        cmds.connectAttr(created_nodes[5] + ".outValue", created_nodes[6]+".floatB")
        cmds.connectAttr(created_nodes[5] + ".outValue", created_nodes[12]+".floatA")
        cmds.connectAttr(created_nodes[6] + ".outFloat", created_nodes[13]+".floatB")
        cmds.connectAttr(created_nodes[6] + ".outFloat", created_nodes[7]+".floatB")
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
        # cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[31]+".floatA")
        # cmds.connectAttr(created_nodes[30] + ".outFloat", created_nodes[31]+".floatB")
        cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[3]+".input1D[0]")
        cmds.connectAttr(created_nodes[4] + ".outFloat", created_nodes[3]+".input1D[1]")
        cmds.connectAttr(created_nodes[26] + ".outFloat", created_nodes[3]+".input1D[2]")
        cmds.connectAttr(created_nodes[19] + ".outFloat", created_nodes[20]+".floatA")
        cmds.connectAttr(created_nodes[20] + ".outFloat", created_nodes[21]+".floatA")
        cmds.connectAttr(created_nodes[21] + ".outFloat", created_nodes[23]+".floatA")
        cmds.connectAttr(created_nodes[21] + ".outFloat", created_nodes[22]+".floatB")
        cmds.connectAttr(created_nodes[21] + ".outFloat", created_nodes[24]+".floatB")
        cmds.connectAttr(created_nodes[21] + ".outFloat", created_nodes[28]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[25]+".floatA")
        cmds.connectAttr(created_nodes[17] + ".outFloat", created_nodes[25]+".floatB")
        cmds.connectAttr(created_nodes[17] + ".outFloat", created_nodes[22]+".floatA")
        cmds.connectAttr(created_nodes[25] + ".outFloat", created_nodes[19]+".floatA")
        cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[23]+".floatB")
        cmds.connectAttr(created_nodes[4] + ".outFloat", created_nodes[24]+".floatA")
        cmds.connectAttr(created_nodes[26] + ".outFloat", created_nodes[28]+".floatB")




        cmds.connectAttr(self.ik_ctls[2] + ".stretch", created_nodes[20]+".floatB")


        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[18]+".firstTerm")
        cmds.connectAttr(created_nodes[6] + ".outFloat", created_nodes[18]+".secondTerm")

        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[18]+".colorIfFalseR")
        cmds.connectAttr(created_nodes[22] + ".outFloat", created_nodes[18]+".colorIfTrueR")


        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[27]+".firstTerm")
        cmds.connectAttr(created_nodes[6] + ".outFloat", created_nodes[27]+".secondTerm")

        cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[27]+".colorIfFalseR")
        cmds.connectAttr(created_nodes[4] + ".outFloat", created_nodes[27]+".colorIfFalseB")
        cmds.connectAttr(created_nodes[26] + ".outFloat", created_nodes[27]+".colorIfFalseG")

        cmds.connectAttr(created_nodes[23] + ".outFloat", created_nodes[27]+".colorIfTrueR")
        cmds.connectAttr(created_nodes[24] + ".outFloat", created_nodes[27]+".colorIfTrueB")
        cmds.connectAttr(created_nodes[28] + ".outFloat", created_nodes[27]+".colorIfTrueG")



        # Connections TRN and nodes



        cmds.connectAttr(f"{self.ik_ctls[0]}.worldMatrix", f"{created_nodes[0]}.inMatrix1")
        cmds.connectAttr(f"{self.ikHandleManager}.worldMatrix", f"{created_nodes[0]}.inMatrix2")
        cmds.connectAttr(f"{self.ik_ctls[2]}.lowerLengthMult", f"{created_nodes[4]}.floatA")
        cmds.connectAttr(f"{self.ik_ctls[2]}.upperLengthMult", f"{created_nodes[2]}.floatA")
        cmds.connectAttr(f"{self.ik_ctls[2]}.middleLengthMult", f"{created_nodes[26]}.floatA")
        cmds.connectAttr(f"{self.ik_ctls[2]}.soft", f"{created_nodes[5]}.inputValue")
        cmds.connectAttr(f"{masterwalk}.globalScale", f"{created_nodes[1]}.floatB")
        cmds.connectAttr(f"{created_nodes[18]}.outColorR",f"{self.soft_trn}.translateX")

        # setAttr nodes



        cmds.setAttr(f"{created_nodes[2]}.floatB", abs(cmds.getAttr(f"{self.ik_chain[1]}.translateX")))
        cmds.setAttr(f"{created_nodes[4]}.floatB", abs(cmds.getAttr(f"{self.ik_chain[3]}.translateX")))
        cmds.setAttr(f"{created_nodes[26]}.floatB", abs(cmds.getAttr(f"{self.ik_chain[2]}.translateX")))

        cmds.setAttr(f"{created_nodes[9]}.floatB", -1)
        cmds.setAttr(f"{created_nodes[10]}.floatA", math.e)
        cmds.setAttr(f"{created_nodes[11]}.floatA", 1)
        cmds.setAttr(f"{created_nodes[5]}.inputMin", 0.001)
        cmds.setAttr(f"{created_nodes[5]}.outputMax", (cmds.getAttr(f"{created_nodes[3]}.output1D") - cmds.getAttr(f"{created_nodes[1]}.outFloat")))
        cmds.setAttr(f"{created_nodes[19]}.floatB", 1)

        if self.side == "R":
            negate = cmds.createNode("multiplyDivide", name=f"{self.side}_legSoftDistanceNegate_MDN", ss=True)
            cmds.setAttr(f"{negate}.input2X", -1)
            cmds.setAttr(f"{negate}.input2Y", -1)
            cmds.setAttr(f"{negate}.input2Z", -1)
            cmds.connectAttr(f"{created_nodes[27]}.outColorR",f"{negate}.input1X")
            cmds.connectAttr(f"{created_nodes[27]}.outColorG",f"{negate}.input1Y")
            cmds.connectAttr(f"{created_nodes[27]}.outColorB",f"{negate}.input1Z")
            cmds.connectAttr(f"{negate}.outputX",f"{self.ik_chain[1]}.translateX")
            cmds.connectAttr(f"{negate}.outputY",f"{self.ik_chain[2]}.translateX")
            cmds.connectAttr(f"{negate}.outputZ",f"{self.ik_chain[3]}.translateX")
            


        if self.side == "L":
            cmds.connectAttr(f"{created_nodes[27]}.outColorR",f"{self.ik_chain[1]}.translateX")
            cmds.connectAttr(f"{created_nodes[27]}.outColorG",f"{self.ik_chain[2]}.translateX")
            cmds.connectAttr(f"{created_nodes[27]}.outColorB",f"{self.ik_chain[3]}.translateX")
        

        cmds.parentConstraint(self.soft_trn, self.springIkHandle, mo=True)


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
            node = cmds.createNode(node_type, name=node_name, ss=True)
            created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        # Connections between selected nodes and transform nodes
        cmds.connectAttr(created_nodes[0] + ".outValue", f"{created_nodes[4]}.input1X")
        cmds.connectAttr(created_nodes[0] + ".outValue", f"{created_nodes[2]}.inputX")
        cmds.connectAttr(f"{self.ik_ctls[2]}.roll", created_nodes[0] + ".inputValue")
        cmds.connectAttr(f"{self.ik_ctls[2]}.rollLiftAngle", created_nodes[0] + ".inputMin")
        cmds.connectAttr(f"{self.ik_ctls[2]}.rollStraightAngle", created_nodes[0] + ".inputMax")
        cmds.connectAttr(f"{self.ik_ctls[2]}.roll", created_nodes[1] + ".inputValue")
        cmds.connectAttr(f"{self.ik_ctls[2]}.roll", created_nodes[7] + ".inputR")
        cmds.connectAttr(f"{self.ik_ctls[2]}.roll", created_nodes[5] + ".input2X")
        cmds.connectAttr(f"{self.ik_ctls[2]}.roll", created_nodes[4] + ".input2X")
        cmds.connectAttr(f"{self.ik_ctls[2]}.rollLiftAngle", created_nodes[1] + ".inputMax")
        cmds.connectAttr(f"{self.ik_ctls[2]}.bank", created_nodes[8] + ".inputG")
        cmds.connectAttr(f"{self.ik_ctls[2]}.bank", created_nodes[8] + ".inputR")
        cmds.setAttr(f"{created_nodes[6]}.input2X", 1)
        cmds.setAttr(f"{created_nodes[9]}.input2X", 1)
        cmds.setAttr(f"{created_nodes[7]}.minR", -360)
        if self.side == "L":
            cmds.setAttr(f"{created_nodes[8]}.minG", -360)
            cmds.setAttr(f"{created_nodes[8]}.maxR", 360)
        elif self.side == "R":
            cmds.setAttr(f"{created_nodes[8]}.minR", -360)
            cmds.setAttr(f"{created_nodes[8]}.maxG", 360)
        cmds.connectAttr(created_nodes[1] + ".outValue", f"{created_nodes[3]}.input2X")
        cmds.connectAttr(created_nodes[2] + ".outputX", f"{created_nodes[3]}.input1X")
        cmds.connectAttr(created_nodes[3] + ".outputX", f"{created_nodes[5]}.input1X")
        cmds.connectAttr(created_nodes[4] + ".outputX", f"{created_nodes[6]}.input1X")
        cmds.connectAttr(created_nodes[5] + ".outputX", f"{created_nodes[9]}.input1X")
        cmds.connectAttr(created_nodes[8] + ".outputR", f"{self.ik_ctl_grps[5][1]}.rotateZ")
        cmds.connectAttr(created_nodes[8] + ".outputG", f"{self.ik_ctl_grps[6][1]}.rotateZ")
        cmds.connectAttr(created_nodes[7] + ".outputR", f"{self.ik_ctl_grps[7][1]}.rotateX")
        cmds.connectAttr(created_nodes[6] + ".outputX", f"{self.ik_ctl_grps[4][1]}.rotateX")
        cmds.connectAttr(created_nodes[9] + ".outputX", f"{self.ik_ctl_grps[3][1]}.rotateX")
        cmds.connectAttr(f"{self.ik_ctls[2]}.heelTwist", f"{self.ik_ctl_grps[7][1]}.rotateY")
        cmds.connectAttr(f"{self.ik_ctls[2]}.tipTwist", f"{self.ik_ctl_grps[4][1]}.rotateY")
        cmds.connectAttr(f"{self.ik_ctls[2]}.ballTwist", f"{self.ik_ctl_grps[3][1]}.rotateY")
        cmds.connectAttr(f"{self.ik_ctls[2]}.ankleTwist", self.ik_ctl_grps[2][1] + ".rotateY")

    def call_bendys(self):
        normals = (0, 0, 1)
        bendy = Bendys(self.side, self.blend_chain[0], self.blend_chain[1], self.bendy_module, self.skinning_trn, normals, self.controllers_trn)
        bendy.upper_twist_setup()
        bendy = Bendys(self.side, self.blend_chain[1], self.blend_chain[2], self.bendy_module, self.skinning_trn, normals, self.controllers_trn)
        bendy.lower_twists_setup()
        bendy = Bendys(self.side, self.blend_chain[2], self.blend_chain[3], self.bendy_module, self.skinning_trn, normals, self.controllers_trn)
        bendy.lower_twists_setup()

        cmds.select(clear=True)
        ankle_joint = cmds.joint(name=f"{self.side}_ankle_JNT")
        cmds.connectAttr(f"{self.blend_chain[3]}.worldMatrix[0]", f"{ankle_joint}.offsetParentMatrix")
        cmds.parent(ankle_joint, self.skinning_trn)

        



class Bendys(object):
    def __init__(self, side, upper_joint, lower_joint, bendy_module, skinning_trn, normals, controls_trn):
        self.normals = normals
        self.skinning_trn = skinning_trn
        self.side = side
        self.upper_joint = upper_joint
        self.lower_joint = lower_joint
        self.part = self.upper_joint.split("_")[1]
        self.bendy_module = cmds.createNode("transform", name=f"{self.side}_legBendy{self.part}Module_GRP", p=bendy_module, ss=True)
        self.controls_trn = controls_trn

    def upper_twist_setup(self):
        self.twist_joints = []
        twist_end_joints = []
        ik_handle = []


        for i, name in enumerate(["NoRoll", "Roll"]):
            duplicated_twist_joints = cmds.duplicate(self.upper_joint, renameChildren=True)
            cmds.delete(duplicated_twist_joints[2])
            self.twist_joints.append(cmds.rename(duplicated_twist_joints[0], f"{self.side}_legUpper{name}_JNT"))
            twist_end_joints.append(cmds.rename(duplicated_twist_joints[1], f"{self.side}_legUpper{name}End_JNT"))
            cmds.parent(self.twist_joints[i], self.bendy_module)
            
            ik_handle.append(cmds.ikHandle(sj=self.twist_joints[i], ee=twist_end_joints[i], solver="ikSCsolver", name=f"{self.side}legUpper{name}_HDL")[0])
            if name == "NoRoll":
                self.noRoll_transform = cmds.createNode("transform", name=f"{self.side}_legUpperNoRoll_TRN", parent=self.bendy_module, ss=True)
                cmds.parent(ik_handle[i], self.noRoll_transform) 
            else:
                cmds.parent(ik_handle[i], self.bendy_module) 


            if i == 0:
                cmds.pointConstraint(f"{self.upper_joint}", self.twist_joints[0], maintainOffset=False)
                cmds.pointConstraint(f"{self.lower_joint}", ik_handle[i], maintainOffset=False)
            elif i == 1:
                cmds.parentConstraint(f"{self.lower_joint}", ik_handle[i], maintainOffset=False)
    
        cmds.parent(self.twist_joints[1], self.twist_joints[0])
        self.twist_joints = self.twist_joints[1]

        self.hooks()

    
    def lower_twists_setup(self):

        duplicated_twist_joints = cmds.duplicate(self.upper_joint, renameChildren=True)
        cmds.delete(duplicated_twist_joints[2])
        self.twist_joints = cmds.rename(duplicated_twist_joints[0], f"{self.side}_leg{self.part}Roll_JNT")
        twist_end_joints = cmds.rename(duplicated_twist_joints[1], f"{self.side}_{self.part}LowerRollEnd_JNT")

        roll_offset_trn = cmds.createNode("transform", name=f"{self.side}_{self.part}LowerRollOffset_TRN", parent=self.bendy_module, ss=True)
        cmds.delete(cmds.parentConstraint(self.upper_joint, roll_offset_trn, maintainOffset=False))
        cmds.parent(self.twist_joints, roll_offset_trn)
        cmds.parentConstraint(self.upper_joint, roll_offset_trn, maintainOffset=False)

        ik_handle = cmds.ikHandle(sj=self.twist_joints, ee=twist_end_joints, solver="ikSCsolver", name=f"{self.side}_{self.part}LowerRoll_HDL")[0]
        cmds.parent(ik_handle, self.bendy_module)
        
        cmds.parentConstraint(f"{self.lower_joint}", ik_handle, maintainOffset=True)

        self.hooks()

    def hooks(self):
        self.hook_joints = []
        parametric_lenght = [0.001, 0.5, 0.999]

        cmds.select(clear=True)
        curve = cmds.curve(degree=1, point=[
            cmds.xform(self.upper_joint, query=True, worldSpace=True, translation=True),
            cmds.xform(self.lower_joint, query=True, worldSpace=True, translation=True)
        ])
        curve = cmds.rename(curve, f"{self.side}_{self.part}Bendy_CRV")
        cmds.parent(curve, self.bendy_module)
        cmds.delete(curve, ch=True)
        dcpm = cmds.createNode("decomposeMatrix", name=f"{self.side}_{self.part}Bendy01_DPM", ss=True)
        dcpm02 = cmds.createNode("decomposeMatrix", name=f"{self.side}_{self.part}Bendy02_DPM", ss=True)
        cmds.connectAttr(f"{self.upper_joint}.worldMatrix[0]", f"{dcpm}.inputMatrix")
        cmds.connectAttr(f"{dcpm}.outputTranslate", f"{curve}.controlPoints[0]")
        cmds.connectAttr(f"{self.lower_joint}.worldMatrix[0]", f"{dcpm02}.inputMatrix")
        cmds.connectAttr(f"{dcpm02}.outputTranslate", f"{curve}.controlPoints[1]")
        for i, joint in enumerate(["Root", "Mid", "Tip"]):
            self.hook_joints.append(cmds.joint(name=f"{self.side}_{self.part}LowerBendy{joint}Hook_JNT"))
            cmds.setAttr(self.hook_joints[i] + ".inheritsTransform", 0)
            mpa = cmds.createNode("motionPath", name=f"{self.side}_{self.part}LowerBendy{joint}Hook_MPA", ss=True)
            flm = cmds.createNode("floatMath", name=f"{self.side}_{self.part}LowerBendy{joint}Hook_FLM", ss=True)
            flc = cmds.createNode("floatConstant", name=f"{self.side}_{self.part}LowerBendy{joint}Hook_FLC", ss=True)
            cmds.connectAttr(f"{curve}.worldSpace[0]", f"{mpa}.geometryPath")
            cmds.setAttr(f"{flc}.inFloat", parametric_lenght[i])
            cmds.connectAttr(f"{flm}.outFloat", f"{mpa}.frontTwist")
            cmds.connectAttr(f"{flc}.outFloat", f"{mpa}.uValue")
            cmds.connectAttr(f"{flc}.outFloat", f"{flm}.floatA")
            cmds.connectAttr(f"{self.twist_joints}.rotateX", f"{flm}.floatB")
            cmds.setAttr(f"{flm}.operation", 2)
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{self.hook_joints[i]}.translate")
            cmds.connectAttr(f"{mpa}.rotate", f"{self.hook_joints[i]}.rotate")
            cmds.setAttr(f"{mpa}.frontAxis", 0)
            cmds.setAttr(f"{mpa}.upAxis", 1)
            cmds.setAttr(f"{mpa}.worldUpType", 2)
            cmds.connectAttr(f"{self.upper_joint}.worldMatrix[0]", f"{mpa}.worldUpMatrix")
            cmds.setAttr(f"{mpa}.fractionMode", True)
            if self.side == "R_":
                cmds.setAttr(f"{mpa}.inverseFront", True)


        for joint in self.hook_joints:
            cmds.parent(joint, self.bendy_module)

        self.bendy_setup()

    def bendy_setup(self):
        bendyCurve = cmds.curve(p=(cmds.xform(self.upper_joint, query=True, worldSpace=True, translation=True),cmds.xform(self.lower_joint, query=True, worldSpace=True, translation=True)) , d=1, n=f"{self.side}_{self.part}Bendy_CRV")

        cmds.rebuildCurve(bendyCurve, ch=False, rpo=True, rt=0, end=True, kr=False, kcp=False, kep=True, kt=False, fr=False, s=2, d=1, tol=0.01)
        cmds.select(bendyCurve)
        bezier = cmds.nurbsCurveToBezier()

        cmds.select(f"{bendyCurve}.cv[6]", f"{bendyCurve}.cv[0]")
        cmds.bezierAnchorPreset(p=2)

        cmds.select(f"{bendyCurve}.cv[3]")
        cmds.bezierAnchorPreset(p=1)

        bendyDupe = cmds.duplicate(bendyCurve, name=f"{self.side}_{self.part}BendyDupe_CRV", )

        off_curve = cmds.offsetCurve(bendyDupe, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=1.5, tol=0.01, sd=0, ugn=False, name=f"{self.side}_{self.part}BendyOffset_CRV", normal=self.normals)
        
        off_curve[1] = cmds.rename(off_curve[1], f"{self.side}_{self.part}Bendy_OFC")
        cmds.setAttr(f"{off_curve[1]}.useGivenNormal", 1)
        cmds.setAttr(f"{off_curve[1]}.normal", 0,0,1)
        
        cmds.connectAttr(f"{bezier[0]}.worldSpace[0]", f"{off_curve[1]}.inputCurve", f=True)
        cmds.delete(bendyDupe)
        bendyCtl, bendyCtlGRP = curve_tool.controller_creator(f"{self.side}_{self.part}Bendy", suffixes=["GRP"])  
        cmds.parent(bendyCtlGRP[0], self.controls_trn)
        cmds.delete(cmds.parentConstraint(self.hook_joints[1], bendyCtlGRP[0], maintainOffset=False))
        upper_bendy_joint = cmds.duplicate(self.hook_joints[1], renameChildren=True, parentOnly=True, name = f"{self.side}_{self.part}Bendy_JNT")
        cmds.parentConstraint(bendyCtl, upper_bendy_joint, maintainOffset=False)
        cmds.scaleConstraint(bendyCtl, upper_bendy_joint, maintainOffset=False)
        cmds.parentConstraint(self.hook_joints[1], bendyCtlGRP[0], maintainOffset=False)

        for attr in ["scaleY", "scaleZ", "visibility"]:
            cmds.setAttr(f"{bendyCtl}.{attr}", lock=True, keyable=False, channelBox=False)

        bendy_skin_cluster = cmds.skinCluster(upper_bendy_joint, self.hook_joints[0], self.hook_joints[2], bendyCurve, tsb=True, omi=False, rui=False, name=f"{self.side}_{self.part}Bendy_SKN") 

        cmds.skinPercent(bendy_skin_cluster[0], f"{bendyCurve}.cv[2]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_skin_cluster[0], f"{bendyCurve}.cv[3]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_skin_cluster[0], f"{bendyCurve}.cv[4]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_skin_cluster[0], f"{bendyCurve}.cv[0]", transformValue=(self.hook_joints[0], 1))
        cmds.skinPercent(bendy_skin_cluster[0], f"{bendyCurve}.cv[6]", transformValue=(self.hook_joints[2], 1))

        origin_shape = cmds.listRelatives(bendyCurve, allDescendents=True)
        origin_shape.remove(bezier[0])

        cmds.connectAttr(f"{origin_shape[0]}.worldSpace[0]", f"{off_curve[1]}.inputCurve", f=True)

        bendy_offset_skin_cluster = cmds.skinCluster(upper_bendy_joint, self.hook_joints[0], self.hook_joints[2], off_curve[0], tsb=True, omi=False, rui=False, name=f"{self.side}_{self.part}BendyOffset_SKN") 

        cmds.skinPercent(bendy_offset_skin_cluster[0], f"{off_curve[0]}.cv[2]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_offset_skin_cluster[0], f"{off_curve[0]}.cv[3]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_offset_skin_cluster[0], f"{off_curve[0]}.cv[4]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_offset_skin_cluster[0], f"{off_curve[0]}.cv[0]", transformValue=(self.hook_joints[0], 1))
        cmds.skinPercent(bendy_offset_skin_cluster[0], f"{off_curve[0]}.cv[6]", transformValue=(self.hook_joints[2], 1))

        bendy_helper_transform = cmds.createNode("transform", name=f"{self.side}_{self.part}BendyHelperAim04_TRN", ss=True)
        cmds.setAttr(f"{bendy_helper_transform}.inheritsTransform", 0)
        cmds.select(clear=True)

        bendy_joint = []
        blendy_up_trn = []

        for i, value in enumerate([0, 0.25, 0.5, 0.75, 0.95]):
            bendy_joint.append(cmds.joint(name=f"{self.side}_{self.part}Bendy0{i}_JNT"))
            mpa = cmds.createNode("motionPath", name=f"{self.side}_{self.part}Bendy0{i}_MPA", ss=True)
            cmds.setAttr(f"{mpa}.fractionMode", True)
            cmds.setAttr(f"{mpa}.uValue", value)
            cmds.connectAttr(f"{bendyCurve}.worldSpace[0]", f"{mpa}.geometryPath")
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{bendy_joint[i]}.translate")
            if i == 3:
                cmds.connectAttr(f"{mpa}.allCoordinates", f"{bendy_helper_transform}.translate")
            cmds.parent(bendy_joint[i], self.skinning_trn)
        
        bendy_up_module = cmds.createNode("transform", name=f"{self.side}_{self.part}BendyUpModule_GRP", p=self.bendy_module, ss=True) 
        for i, value in enumerate([0, 0.25, 0.5, 0.75, 0.95]):
            blendy_up_trn.append(cmds.createNode("transform", name=f"{self.side}_{self.part}BendyUp0{i}_TRN"))
            cmds.setAttr(f"{blendy_up_trn[i]}.inheritsTransform", 0)
            mpa = cmds.createNode("motionPath", name=f"{self.side}_{self.part}BendyUp0{i}_MPA", ss=True)
            cmds.setAttr(f"{mpa}.fractionMode", True)
            cmds.setAttr(f"{mpa}.uValue", value)
            cmds.connectAttr(f"{off_curve[0]}.worldSpace[0]", f"{mpa}.geometryPath")
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{blendy_up_trn[i]}.translate")
            cmds.parent(blendy_up_trn[i], bendy_up_module)
        
        if self.side == "L":
            upvector = (0, 0, -1)
            aimVector = (1,0,0)
            reverseAim = (-1,0,0)

        elif self.side == "R":
            upvector = (0, 0, 1)
            aimVector = (-1,0,0)
            reverseAim = (1,0,0)

        for i, joint in enumerate(bendy_joint):
            if i != 4:
                aim = cmds.aimConstraint(bendy_joint[i+1], joint, aimVector=aimVector, upVector=upvector, worldUpType="object", worldUpObject=blendy_up_trn[i], maintainOffset=False)
                cmds.delete(aim)
                cmds.makeIdentity(joint, apply=True, r=1)
                cmds.aimConstraint(bendy_joint[i+1], joint, aimVector=aimVector, upVector=upvector, worldUpType="object", worldUpObject=blendy_up_trn[i], maintainOffset=False)
            else:
                aim = cmds.aimConstraint(bendy_helper_transform, joint, aimVector=reverseAim, upVector=upvector, worldUpType="object", worldUpObject=blendy_up_trn[i], maintainOffset=False)
                cmds.delete(aim)
                cmds.makeIdentity(joint, apply=True, r=1)
                cmds.aimConstraint(bendy_helper_transform, joint, aimVector=reverseAim, upVector=upvector, worldUpType="object", worldUpObject=blendy_up_trn[i], maintainOffset=False)



        cmds.parent(bendyCurve, self.bendy_module)
        cmds.parent(off_curve[0], self.bendy_module)
        cmds.parent(bendy_helper_transform, self.bendy_module)

                            
