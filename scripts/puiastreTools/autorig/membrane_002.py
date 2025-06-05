"""
Finger module for dragon rigging system
"""
import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
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

        # self.create_nurbs(joint01 = self.thumb_joints, joint02 = self.index_joints, index=1)
        # self.create_nurbs(joint01 = self.index_joints, joint02 = self.middle_joints, index=2)
        # self.create_nurbs(joint01 = self.middle_joints, joint02 = self.ring_joints, index=3)
        # self.create_nurbs(joint01 = self.ring_joints, joint02 = self.pinky_joints, index=4)

        fingers_chains = []

        for name in [self.thumb_joints, self.index_joints, self.middle_joints, self.ring_joints, self.pinky_joints]:
            if name:
                fingers_chains.append(name)


        for i in range(len(fingers_chains)-1):

            if fingers_chains[i+1]:
                joint01 = fingers_chains[i]
                joint02 = fingers_chains[i+1]


                self.create_nurbs(joint01 = joint01, joint02 = joint02, index=i+1)


                


    def create_nurbs(self, joint01, joint02, index):
        def get_world_positions(joints):
            return [cmds.xform(jnt, q=True, ws=True, t=True) for jnt in joints]

        if self.side == "L":
            thumb_positions = get_world_positions(joint01)
            index_positions = get_world_positions(joint02)
        else:
            thumb_positions = get_world_positions(joint02)
            index_positions = get_world_positions(joint01)

        num_joints = len(thumb_positions)
        loft_curves = []

        for i in range(num_joints):
            ptA = thumb_positions[i]
            ptB = index_positions[i]

            mid = [(a + b) / 2 for a, b in zip(ptA, ptB)]
            mid[1] += 2 

            curve = cmds.curve(d=2, p=[ptA, mid, ptB], name=f"{self.side}_membraneLoftCurve_{i}")
            loft_curves.append(curve)

        membrane_surface = cmds.loft(loft_curves, name=f"{self.side}_membraneSurface0{index}_NBS", ch=1, u=True, c=False, ar=True, d=3, ss=1, rn=False, po=0, reverseSurfaceNormals=True)[0]
        cmds.delete(membrane_surface, ch=True)
        cmds.parent(membrane_surface, self.skinning_trn)

        for c in loft_curves:
            cmds.delete(c)

        surface_shape = cmds.listRelatives(membrane_surface, shapes=True, type="nurbsSurface")[0]

        skin_joints = joint02 + joint01
        skin_cluster = cmds.skinCluster(
            skin_joints,
            membrane_surface,
            toSelectedBones=True,
            normalizeWeights=1,
            name=f"{self.side}_membraneSkinCluster"
        )[0]

        i = 0 
        z = 0  

        if self.side == "R":
            temp = joint01
            joint01 = joint02
            joint02 = temp



        surface_cvs = cmds.ls(f"{membrane_surface}.cv[*][*]", flatten=True)
        for cv in surface_cvs:
            cmds.skinPercent(skin_cluster, cv, transformValue=[(joint02[0], 1.0)])


        while i <= len(joint01)-1:
            cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[0][{z}]", transformValue=[(joint01[i], 1.0)])
            cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint02[i], 1)])
            cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint01[i], 0.5)])
            cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[2][{z}]", transformValue=[(joint02[i], 1.0)])
            if i == 0:
                z += 1
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[0][{z}]", transformValue=[(joint01[i], 1.0)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint02[i], 1)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint01[i], 0.5)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[2][{z}]", transformValue=[(joint02[i], 1.0)])
            if i == len(joint02)-1:
                z += 1
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[0][{z}]", transformValue=[(joint01[i], 1.0)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint02[i], 1)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[1][{z}]", transformValue=[(joint01[i], 0.5)])
                cmds.skinPercent(skin_cluster, f"{membrane_surface}.cv[2][{z}]", transformValue=[(joint02[i], 1.0)])
            
            i += 1
            z += 1

        offset_surface = cmds.offsetSurface(membrane_surface, d=20)
        offset_surface = cmds.rename(offset_surface[0], f"{self.side}_membraneOffsetSurface0{index}_NBS")


        compose_matrices = [[] for _ in range(3)]
        compose_matrices_offset = [[] for _ in range(3)]
        compose_matrices_helper = []
        for i in range(0, 3):
            for j in range(5):

                v_parameter = ((len(joint01)) / 6)* (j) +1
                
                pointOnSurface = cmds.createNode("pointOnSurfaceInfo", name=f"{self.side}_membranePointOnSurface{index}{i}{j}_POS", ss=True)
                cmds.connectAttr(f"{membrane_surface}.worldSpace", f"{pointOnSurface}.inputSurface")
                cmds.setAttr(f"{pointOnSurface}.parameterU", (i + 1) * 0.25)
                cmds.setAttr(f"{pointOnSurface}.parameterV", v_parameter)
                compose_matrix = cmds.createNode("composeMatrix", name=f"{self.side}_membraneComposeMatrix{index}{i}{j}_CM", ss=True)
                cmds.connectAttr(f"{pointOnSurface}.position", f"{compose_matrix}.inputTranslate")

                if j == 4:
                    compose_matrix_helper = cmds.createNode("composeMatrix", name=f"{self.side}_membraneComposeMatrixHelper{index}{i}{j}_CM", ss=True)
                    cmds.connectAttr(f"{pointOnSurface}.position", f"{compose_matrix_helper}.inputTranslate")
                    compose_matrices_helper.append(compose_matrix_helper)



                pointOnSurface_offfset = cmds.createNode("pointOnSurfaceInfo", name=f"{self.side}_membranePointOnSurfaceOffset{index}{i}{j}_POS", ss=True)
                cmds.connectAttr(f"{offset_surface}.worldSpace", f"{pointOnSurface_offfset}.inputSurface")
                cmds.setAttr(f"{pointOnSurface_offfset}.parameterU", (i + 1) * 0.25)
                cmds.setAttr(f"{pointOnSurface_offfset}.parameterV", v_parameter)
                compose_matrix_offset = cmds.createNode("composeMatrix", name=f"{self.side}_membraneComposeMatrixOffset{index}{i}{j}_CM", ss=True)
                cmds.connectAttr(f"{pointOnSurface_offfset}.position", f"{compose_matrix_offset}.inputTranslate")

                compose_matrices[i].append(compose_matrix)
                compose_matrices_offset[i].append(compose_matrix_offset)

        ctls = [[] for _ in range(3)]
        ctls_grp = [[] for _ in range(3)]

        for i in range(0, 3):
            for j in range(5):
                aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_membraneAimMatrix{index}{i}{j}_AM", ss=True)
                cmds.connectAttr(f"{compose_matrices[i][j]}.outputMatrix", f"{aim_matrix}.inputMatrix")
                if j != 4:
                    cmds.connectAttr(f"{compose_matrices[i][j+1]}.outputMatrix", f"{aim_matrix}.primaryTargetMatrix")
                    cmds.setAttr(f"{aim_matrix}.primaryInputAxisX", 1)

                else:
                    cmds.connectAttr(f"{compose_matrices_helper[i]}.outputMatrix", f"{aim_matrix}.primaryTargetMatrix")
                    cmds.setAttr(f"{aim_matrix}.primaryInputAxisX", -1)


                cmds.connectAttr(f"{compose_matrices_offset[i][j]}.outputMatrix", f"{aim_matrix}.secondaryTargetMatrix")
                cmds.setAttr(f"{aim_matrix}.primaryInputAxisY", 0)
                cmds.setAttr(f"{aim_matrix}.primaryInputAxisZ", 0)
                cmds.setAttr(f"{aim_matrix}.secondaryInputAxisX", 0)
                cmds.setAttr(f"{aim_matrix}.secondaryInputAxisY", 1)
                cmds.setAttr(f"{aim_matrix}.secondaryInputAxisZ", 0)
                cmds.setAttr(f"{aim_matrix}.primaryMode", 1)
                cmds.setAttr(f"{aim_matrix}.secondaryMode", 1)

                cmds.select(clear=True)
                joint = cmds.joint(name=f"{self.side}_membraneJoint{index}{i}{j}_JNT")
                cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{joint}.offsetParentMatrix")

                ctl, grp = curve_tool.controller_creator(name=f"{self.side}_membrane{index}{i}{j}", suffixes=["GRP", "OFF"])