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

        self.create_nurbs()

    def create_nurbs(self):
        def get_world_positions(joints):
            return [cmds.xform(jnt, q=True, ws=True, t=True) for jnt in joints]

        joint_01 = []
        for joint in self.thumb_joints:
            if not "04" in joint:
                joint_01.append(joint)  

        joint_02 = []
        for joint in self.index_joints:
            if not "04" in joint:
                joint_02.append(joint)


        thumb_positions = get_world_positions(joint_01)
        index_positions = get_world_positions(joint_02)

        num_joints = len(thumb_positions)
        loft_curves = []

        for i in range(num_joints):
            ptA = thumb_positions[i]
            ptB = index_positions[i]

            mid = [(a + b) / 2 for a, b in zip(ptA, ptB)]
            mid[1] += 2 

            curve = cmds.curve(d=2, p=[ptA, mid, ptB], name=f"{self.side}_membraneLoftCurve_{i}")
            loft_curves.append(curve)

        membrane_surface = cmds.loft(loft_curves, name=f"{self.side}_membraneSurface", ch=1, u=True, c=False, ar=True, d=3, ss=1, rn=False, po=0, reverseSurfaceNormals=True)[0]
        cmds.delete(membrane_surface, ch=True)
        cmds.parent(membrane_surface, self.skinning_trn)

        for c in loft_curves:
            cmds.delete(c)

                # Obtener shape y crear skinCluster
        surface_shape = cmds.listRelatives(membrane_surface, shapes=True, type="nurbsSurface")[0]

        skin_joints = joint_01 + joint_02
        skin_cluster = cmds.skinCluster(
            skin_joints,
            membrane_surface,
            toSelectedBones=True,
            normalizeWeights=1,
            name=f"{self.side}_membraneSkinCluster"
        )[0]

        i = 0 
        z = 0  


        surface_cvs = cmds.ls(f"{membrane_surface}.cv[*][*]", flatten=True)
        for cv in surface_cvs:
            cmds.skinPercent(skin_cluster, cv, transformValue=[(joint_02[0], 1.0)])


        while i <= len(joint_01)-1:
            cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[0][{z}]", transformValue=[(joint_01[i], 1.0)])
            cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint_02[i], 1)])
            cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint_01[i], 0.5)])
            cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[2][{z}]", transformValue=[(joint_02[i], 1.0)])
            if i == 0:
                z += 1
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[0][{z}]", transformValue=[(joint_01[i], 1.0)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint_02[i], 1)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint_01[i], 0.5)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[2][{z}]", transformValue=[(joint_02[i], 1.0)])
            if i == len(joint_02)-1:
                z += 1
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[0][{z}]", transformValue=[(joint_01[i], 1.0)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint_02[i], 1)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint_01[i], 0.5)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[2][{z}]", transformValue=[(joint_02[i], 1.0)])
            
            i += 1
            z += 1


