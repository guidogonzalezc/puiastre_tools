"""
Finger module for dragon rigging system
"""
import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import basic_structure
from puiastreTools.utils import data_export
import maya.mel as mel
import math
import os
import re
from importlib import reload
reload(guides_manager)
reload(basic_structure)
reload(curve_tool)    
reload(data_export)    

class MembraneModule():
    def __init__(self):
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "dragon_guides_template_01.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "template_curves_001.json") 

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")


    def make(self, side):

        self.side = side   

        self.thumb_joints = self.data_exporter.get_data(f"{self.side}_fingerThumb", "bendy_joints")
        self.index_joints = self.data_exporter.get_data(f"{self.side}_fingerIndex", "bendy_joints")
        self.middle_joints = self.data_exporter.get_data(f"{self.side}_fingerMiddle", "bendy_joints")
        self.ring_joints = self.data_exporter.get_data(f"{self.side}_fingerRing", "bendy_joints")
        self.pinky_joints = self.data_exporter.get_data(f"{self.side}_fingerPinky", "bendy_joints")
        self.attr_ctl = self.data_exporter.get_data(f"{self.side}_finger", "attr_ctl") 

        cmds.addAttr(self.attr_ctl, shortName="membraneFoldingSep", niceName="Membrane Folding_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.attr_ctl+".membraneFoldingSep", channelBox=True, lock=True)
        cmds.addAttr(self.attr_ctl, shortName="automaticFold", niceName="Automatic Fold", attributeType="bool", keyable=True, defaultValue=True)
        cmds.addAttr(self.attr_ctl, shortName="globalFolding", niceName="Global Folding", minValue=0, defaultValue=1.5, keyable=True)
        cmds.addAttr(self.attr_ctl, shortName="firstSegment", niceName="First Segment",defaultValue=0, keyable=True)
        cmds.addAttr(self.attr_ctl, shortName="secondSegment", niceName="Second Segment", defaultValue=0, keyable=True)
        cmds.addAttr(self.attr_ctl, shortName="thirdSegment", niceName="Third Segment", defaultValue=0, keyable=True)
        cmds.addAttr(self.attr_ctl, shortName="forthSegment", niceName="Forth Segment", defaultValue=0, keyable=True)


        self.module_trn = cmds.createNode("transform", name=f"{self.side}_membraneModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_membraneControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_membraneSkinning_GRP", ss=True, p=self.skel_grp)

        self.call_push()

    def call_push(self):
        """
        Call the push joint creation function
        """
        self.create_push_joint(self.thumb_joints, self.index_joints, ".firstSegment")
        self.create_push_joint(self.index_joints, self.middle_joints, ".secondSegment")
        self.create_push_joint(self.middle_joints, self.ring_joints, ".thirdSegment")
        self.create_push_joint(self.ring_joints, self.pinky_joints, ".forthSegment")     

    def create_push_joint(self, joint_chain01, joint_chain02, attr):
        """
        Create a push joint between two joint chains
        """
        name = re.search(r"finger(.*?)01Bendy", joint_chain01[0]).group(1)
        name01 = re.search(r"finger(.*?)01Bendy", joint_chain02[0]).group(1)
        module_tn_individual = cmds.createNode("transform", name=f"{self.side}_{name.lower()}{name01}Push_GRP", ss=True, p=self.module_trn)
        module_aim_offset= cmds.createNode("transform", name=f"{self.side}_{name.lower()}{name01}AimOffset_GRP", ss=True, p=module_tn_individual)
        aim_trn = []
        aim_ctl = []
        picks = []
        curve_skinning_joints = []
        for i, joint in enumerate(joint_chain01[1:], start=1):
            
            joint1_pos = cmds.xform(joint, query=True, worldSpace=True, translation=True)
            joint2_pos = cmds.xform(joint_chain02[i], query=True, worldSpace=True, translation=True)

            curve_name = f"{self.side}_{name.lower()}{name01}Rotation{i:02d}_CRV"
            rotation_curve = cmds.curve(degree=1, point=[joint1_pos, joint2_pos], name=curve_name)
            cmds.parent(rotation_curve, module_tn_individual)
            rotation_skin_cluster = cmds.skinCluster(joint, joint_chain02[i], rotation_curve, tsb=True, omi=False, rui=False, name=f"{self.side}_{name.lower()}{name01}PushRotation_SKC")

            if cmds.getAttr(f"{joint}.rotateY") < 0 or cmds.getAttr(f"{joint_chain02[i]}.rotateY") < 0:
                normals = (0, 0, -1)

            else:
                normals = (0, 0, 1)
            curve_name = f"{self.side}_{name.lower()}{name01}RotationOffset{i:02d}_CRV"

            off_curve = cmds.offsetCurve(rotation_curve, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=1.5, tol=0.01, sd=0, ugn=False, name=curve_name, normal=normals)

            cmds.setAttr(f"{off_curve[1]}.useGivenNormal", 1)
            cmds.setAttr(f"{off_curve[1]}.normal", 0,0,1)
            cmds.setAttr(f"{off_curve[1]}.distance", 50)

            offset_trn = cmds.createNode("transform", name=f"{self.side}_{name.lower()}{name01}PushOffsetAim{i:02d}_GRP", ss=True, p=module_aim_offset)
            aim_trn.append(offset_trn)
            cmds.parent(off_curve[0], module_tn_individual)
            mpa = cmds.createNode("motionPath", n=f"{self.side}_{name.lower()}{name01}PushOffset{i:02d}_MPA", ss=True)
            cmds.connectAttr(f"{off_curve[0]}.worldSpace[0]", f"{mpa}.geometryPath")
            cmds.setAttr(f"{mpa}.uValue", 0.5)
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{offset_trn}.translate")

            cmds.select(clear=True)
            secondary_joint = cmds.joint(n=f"{self.side}_{name.lower()}{name01}Push{i:02d}_JNT", rad= 50)
            cmds.parent(secondary_joint, module_tn_individual)
            ctl_name = f"{self.side}_{name.lower()}{name01}Push{i:02d}"
            clt, ctl_grp = curve_tool.controller_creator(ctl_name, suffixes = ["GRP", "OFF"])
            aim_ctl.append(ctl_grp[0])
            cmds.parent(ctl_grp[0], self.controllers_trn)
            skinning_joint = cmds.joint(n=f"{self.side}_{name.lower()}{name01}PushSkinning{i:02d}_JNT", rad= 50)
            cmds.parent(skinning_joint, self.skinning_trn)
            cmds.connectAttr(f"{clt}.worldMatrix[0]", f"{skinning_joint}.offsetParentMatrix")
            cmds.connectAttr(f"{clt}.worldMatrix[0]", f"{secondary_joint}.offsetParentMatrix")

            wtadd = cmds.createNode("wtAddMatrix", n=f"{self.side}_{name.lower()}{name01}Push{i:02d}_WTADD", ss=True)    
            cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{wtadd}.wtMatrix[0].matrixIn")
            cmds.connectAttr(f"{joint_chain02[i]}.worldMatrix[0]", f"{wtadd}.wtMatrix[1].matrixIn")
            cmds.setAttr(f"{wtadd}.wtMatrix[0].weightIn", 0.5)
            cmds.setAttr(f"{wtadd}.wtMatrix[1].weightIn", 0.5)
            pick_matrix = cmds.createNode("pickMatrix", n=f"{self.side}_{name.lower()}{name01}Push{i:02d}_PMT", ss=True)
            picks.append(pick_matrix)   
            cmds.connectAttr(f"{wtadd}.matrixSum", f"{pick_matrix}.inputMatrix")
            cmds.setAttr(f"{pick_matrix}.useScale", 0)    
            cmds.setAttr(f"{pick_matrix}.useShear", 0)    
            cmds.setAttr(f"{pick_matrix}.useRotate", 0)    

            pick_matrix_value = cmds.getAttr(f"{pick_matrix}.outputMatrix")
            cmds.setAttr(f"{ctl_grp[0]}.offsetParentMatrix", pick_matrix_value, type="matrix")


            if i == len(joint_chain01)-2:
                trn_aim_helper = cmds.createNode("transform", n=f"{self.side}_{name.lower()}{name01}Push{i:02d}AimHelper_TRN", ss=True, p=module_tn_individual)
                cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{trn_aim_helper}.offsetParentMatrix")


            pma = cmds.createNode("plusMinusAverage", n=f"{self.side}_{name.lower()}{name01}Factor{i:02d}_PMA", ss=True)
            cmds.connectAttr(f"{self.attr_ctl}{attr}", f"{pma}.input1D[0]")
            cmds.connectAttr(f"{self.attr_ctl}.globalFolding", f"{pma}.input1D[1]")


            distance_between = cmds.createNode("distanceBetween", n=f"{self.side}_{name.lower()}{name01}Distance{i:02d}_DSB", ss=True)
            fulldistance = cmds.createNode("floatConstant", n=f"{self.side}_{name.lower()}{name01}FullDistance{i:02d}_FLC", ss=True)
            distance_float = cmds.createNode("floatMath", n=f"{self.side}_{name.lower()}{name01}DistanceFloat{i:02d}_FLM", ss=True)
            space_factor = cmds.createNode("floatMath", n=f"{self.side}_{name.lower()}{name01}SpaceFactor{i:02d}_FLM", ss=True)
            negate = cmds.createNode("floatMath", n=f"{self.side}_{name.lower()}{name01}Negate{i:02d}_FLM", ss=True)
            final_value = cmds.createNode("floatMath", n=f"{self.side}_{name.lower()}{name01}FinalValue{i:02d}_FLM", ss=True)
            con = cmds.createNode("condition", n=f"{self.side}_{name.lower()}{name01}Condition{i:02d}_CND", ss=True)   

            cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{distance_between}.inMatrix1")    
            cmds.connectAttr(f"{joint_chain02[i]}.worldMatrix[0]", f"{distance_between}.inMatrix2")
            cmds.setAttr(f"{fulldistance}.inFloat", cmds.getAttr(f"{distance_between}.distance"))
            cmds.connectAttr(f"{distance_between}.distance", f"{distance_float}.floatB")
            cmds.connectAttr(f"{fulldistance}.outFloat", f"{distance_float}.floatA")
            cmds.setAttr(f"{distance_float}.operation", 1)
            cmds.setAttr(f"{space_factor}.operation", 2)
            cmds.setAttr(f"{negate}.operation", 2)
            cmds.connectAttr(f"{distance_float}.outFloat", f"{space_factor}.floatA")
            cmds.connectAttr(f"{pma}.output1D", f"{space_factor}.floatB")
            cmds.connectAttr(f"{space_factor}.outFloat", f"{negate}.floatA")
            cmds.connectAttr(f"{negate}.outFloat", f"{final_value}.floatB")
            cmds.connectAttr(f"{self.attr_ctl}.automaticFold", f"{final_value}.floatA")
            cmds.setAttr(f"{final_value}.operation", 2)
            cmds.setAttr(f"{negate}.floatB", -1)
            cmds.connectAttr(f"{final_value}.outFloat", f"{con}.colorIfTrueR")
            cmds.setAttr(f"{con}.colorIfFalseR", 0)
            cmds.setAttr(f"{con}.operation", 4)
            cmds.connectAttr(f"{distance_between}.distance", f"{con}.firstTerm")    
            cmds.connectAttr(f"{fulldistance}.outFloat", f"{con}.secondTerm")

            cmds.connectAttr(f"{con}.outColorR", f"{ctl_grp[1]}.translateY")
     


         
            secondary_joint_pos = cmds.xform(secondary_joint, query=True, worldSpace=True, translation=True)

            # Create a degree 1 curve with CVs at the positions
            curve_name = f"{self.side}_{name.lower()}{name01}Push{i:02d}_CRV"
            curve = cmds.curve(degree=1, point=[joint1_pos, secondary_joint_pos, joint2_pos], name=curve_name)
            cmds.select(curve)

            bezier = cmds.nurbsCurveToBezier()[0]

            cmds.select(f"{curve}.cv[6]", f"{curve}.cv[0]")
            cmds.bezierAnchorPreset(p=2)

            cmds.select(f"{curve}.cv[3]")
            cmds.bezierAnchorPreset(p=1)

            curve_skinning_joints.append([joint, secondary_joint, joint_chain02[i], curve])


 
        for i, ctl in enumerate(aim_ctl):
            aimMatrix = cmds.createNode("aimMatrix", n=f"{self.side}_{name.lower()}{name01}PushAimMatrix_AMX", ss=True)    
            cmds.connectAttr(f"{picks[i]}.outputMatrix", f"{aimMatrix}.inputMatrix")
            cmds.connectAttr(f"{aimMatrix}.outputMatrix", f"{ctl}.offsetParentMatrix")
            cmds.connectAttr(f"{aim_trn[i]}.worldMatrix[0]", f"{aimMatrix}.secondary.secondaryTargetMatrix")
            cmds.setAttr(f"{aimMatrix}.primaryMode", 1)
            cmds.setAttr(f"{aimMatrix}.secondaryMode", 1)
            cmds.setAttr(f"{aimMatrix}.secondaryInputAxisX", 0)
            cmds.setAttr(f"{aimMatrix}.secondaryInputAxisY", 1)
            cmds.setAttr(f"{aimMatrix}.secondaryInputAxisZ", 0)

            if i == len(aim_ctl)-1:
                cmds.connectAttr(f"{trn_aim_helper}.worldMatrix[0]", f"{aimMatrix}.primary.primaryTargetMatrix")
                cmds.setAttr(f"{aimMatrix}.primaryInputAxisX", -1)
                cmds.setAttr(f"{aimMatrix}.primaryInputAxisY", 0)
                cmds.setAttr(f"{aimMatrix}.primaryInputAxisZ", 0)

            else:
                cmds.connectAttr(f"{aim_ctl[i + 1]}.worldMatrix[0]", f"{aimMatrix}.primary.primaryTargetMatrix")
                cmds.setAttr(f"{aimMatrix}.primaryInputAxisX", 1)
                cmds.setAttr(f"{aimMatrix}.primaryInputAxisY", 0)
                cmds.setAttr(f"{aimMatrix}.primaryInputAxisZ", 0)

                        # Create a skin cluster for the curve
            
            joint = curve_skinning_joints[i][0]
            secondary_joint = curve_skinning_joints[i][1]
            joint_chain02 = curve_skinning_joints[i][2]
            curve = curve_skinning_joints[i][3]


            skin_cluster = cmds.skinCluster(joint, secondary_joint, joint_chain02, curve, tsb=True, omi=False, rui=False, name=f"{self.side}_{name.lower()}{name01}Push_SKC")

            cmds.parent(curve, module_tn_individual)

            cmds.skinPercent(skin_cluster[0], f"{curve}.cv[0]", transformValue=(joint, 1))
            cmds.skinPercent(skin_cluster[0], f"{curve}.cv[1]", transformValue=(joint, 1))
            cmds.skinPercent(skin_cluster[0], f"{curve}.cv[2]", transformValue=(secondary_joint, 1))
            cmds.skinPercent(skin_cluster[0], f"{curve}.cv[3]", transformValue=(secondary_joint, 1))
            cmds.skinPercent(skin_cluster[0], f"{curve}.cv[4]", transformValue=(secondary_joint, 1))
            cmds.skinPercent(skin_cluster[0], f"{curve}.cv[5]", transformValue=(joint_chain02, 1))
            cmds.skinPercent(skin_cluster[0], f"{curve}.cv[6]", transformValue=(joint_chain02, 1))









    def lock_attr(self, ctl, attrs = ["scaleX", "scaleY", "scaleZ", "visibility"]):
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", keyable=False, channelBox=False, lock=True)

