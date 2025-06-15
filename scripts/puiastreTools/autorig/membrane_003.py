"""
Finger module for dragon rigging system
"""
import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
import re
from puiastreTools.utils import data_export
from importlib import reload
reload(data_export)    

class MembraneModule():
    def __init__(self):
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
        self.attr_ctl = self.data_exporter.get_data(f"{self.side}_fingerThumb", "settingsAttr") 

        # self.module_trn = cmds.createNode("transform", name=f"{self.side}_membraneModule_GRP", ss=True, parent=self.modules_grp)
        self.module_trn = cmds.createNode("transform", name=f"{self.side}_membraneModule_GRP", ss=True)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_membraneControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_membraneSkinning_GRP", ss=True, p=self.skel_grp)

        fingers_chains = []

        print(self.attr_ctl)

        cmds.addAttr(self.attr_ctl, longName='Dynamics______', attributeType='enum', enumName='_______')

        cmds.addAttr(self.attr_ctl, longName='enable_dynamics', attributeType='bool', keyable=True)

        cmds.addAttr(self.attr_ctl, longName='display_sim_curves', attributeType='bool', keyable=True)

        cmds.addAttr(self.attr_ctl, longName='sim_space', attributeType='enum', enumName='Local:World', keyable=True)

        cmds.addAttr(self.attr_ctl, longName='point_lock', attributeType='enum', enumName='No Attach:Base:Tip:BothEnds', keyable=True)

        cmds.addAttr(self.attr_ctl, longName='Values_______', attributeType='enum', enumName='_______')

        cmds.addAttr(self.attr_ctl, longName='start_frame', attributeType='float', defaultValue=1.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='anim_follow_base', attributeType='float', defaultValue=1.0, minValue=0.0, maxValue=1.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='anim_follow_tip', attributeType='float', defaultValue=0.2, minValue=0.0, maxValue=1.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='anim_follow_damp', attributeType='float', defaultValue=0.2, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='mass', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='drag', attributeType='float', defaultValue=0.05, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='damp', attributeType='float', defaultValue=0.0, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='stiffness', attributeType='float', defaultValue=0.15, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='Turbulence_______', attributeType='enum', enumName='_______')

        cmds.addAttr(self.attr_ctl, longName='turbulence_intensity', attributeType='float', defaultValue=0.0, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='turbulence_frequency', attributeType='float', defaultValue=0.2, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='turbulence_speed', attributeType='float', defaultValue=0.2, minValue=0.0, keyable=True)

        for enum in ["Dynamics______", "Values_______", "Turbulence_______"]:
            cmds.setAttr(f"{self.attr_ctl}.{enum}", channelBox=True, lock=True)


        for name in [self.thumb_joints, self.index_joints, self.middle_joints, self.ring_joints, self.pinky_joints]:
            if name:
                fingers_chains.append(name)


        for i in range(len(fingers_chains)-1):

            if fingers_chains[i+1]:
                joint01 = fingers_chains[i]
                joint02 = fingers_chains[i+1]

                self.create_nurbs_curve(joint01, joint02)


    def create_nurbs_curve(self, joint01, joint02):

        
        def build_finger_string(joint_names):
            return ''.join(re.search(r'finger([A-Za-z]+)\d', name).group(1) for name in joint_names if re.search(r'finger([A-Za-z]+)\d', name))

        result = build_finger_string([joint01[0], joint02[0]])

        points = [(i + 1, 0, 0) for i in range(len(joint01) // 2)]

        curve = cmds.curve(d=1, p=points, name=f"{self.side}_membrane{result}_CRV")
        cmds.delete(curve, ch=True)  


        


        hairSystem = cmds.createNode("hairSystem", name=f"{self.side}_membrane{result}_HS", ss=True)
        if cmds.objExists("time1"):
            time = "time1"  
        else:   
            time = cmds.createNode("time", name="time1", ss=True)

        follicle = cmds.createNode("follicle", name=f"{self.side}_membrane{result}_FOL", ss=True)

        curve_shape = cmds.listRelatives(curve, shapes=True)[0]
        dupe = cmds.duplicate(curve_shape, name=f"{self.side}_membrane{result}_Shape", rr=True)

        cmds.connectAttr(f"{time}.outTime", f"{hairSystem}.currentTime")
        cmds.connectAttr(f"{hairSystem}.outputHair[0]", f"{follicle}.currentPosition")

        cmds.connectAttr(f"{curve_shape}.local", f"{follicle}.startPosition")
        cmds.connectAttr(f"{follicle}.outHair", f"{hairSystem}.inputHair[0]")
        cmds.connectAttr(f"{follicle}.outCurve", f"{dupe[0]}.create")


        nurbs_joints = []
        for i in range(1, len(joint01), 2):
            wta = cmds.createNode("wtAddMatrix", name=f"{self.side}_membran{result}0{i}_WTA", ss=True)
            cmds.connectAttr(f"{joint01[i]}.worldMatrix", f"{wta}.wtMatrix[0].matrixIn")
            cmds.connectAttr(f"{joint02[i]}.worldMatrix", f"{wta}.wtMatrix[1].matrixIn")
            cmds.setAttr(f"{wta}.wtMatrix[0].weightIn", 0.5)
            cmds.setAttr(f"{wta}.wtMatrix[1].weightIn", 0.5)
            dcp = cmds.createNode("decomposeMatrix", name=f"{self.side}_membran{result}0{i}_DCP", ss=True)
            cmds.connectAttr(f"{wta}.matrixSum", f"{dcp}.inputMatrix")

            cmds.connectAttr(f"{dcp}.outputTranslate", f"{curve}.controlPoints[{i//2}]")

            cmds.select(clear=True)
            joint = cmds.joint(name=f"{self.side}_membrane{result}0{i}_JNT")
            cmds.connectAttr(f"{wta}.matrixSum", f"{joint}.offsetParentMatrix")
            nurbs_joints.append(joint)

        dupe_skinning = cmds.duplicate(dupe[0], name=f"{self.side}_membrane{result}_SkinningShape", rr=True)

        skincluster = cmds.skinCluster(nurbs_joints , dupe_skinning[0], tsb=True, name=f"{self.side}_membrane{result}_SKIN", maximumInfluences=1, normalizeWeights=1)
