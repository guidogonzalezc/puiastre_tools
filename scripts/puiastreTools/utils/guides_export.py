import maya.cmds as cmds
import maya.OpenMaya as om
import os
import json

class GuidesExport():

    def guides_export(self, guides):
        self.guides_folder = cmds.ls(guides)
        if self.guides_folder:
            guides_descendents = cmds.listRelatives(self.guides_folder[0], allDescendents=True, type="joint")
            left_guides = []
            right_guides = []
            for guide in guides_descendents:
                if guide.split("_")[0] == "L":
                    left_guides.append(guide)
                if guide.split("_")[0] == "R":
                    right_guides.append(guide)
            for left_guide in left_guides:
                splited_guide = left_guide.split("_")[1]
                if splited_guide in right_guides:
                    om.MGlobal.displayInfo("Guides are symmetrical.")         
            
            if len(left_guides) == len(right_guides):
                    om.MGlobal.displayInfo("Guides are symmetrical.")      
            else:
                om.MGlobal.displayWarning("Guides are not symmetrical.")
                return

            self.guides_positions = {}
            self.guides_rotations = {}
            self.guides_parents = {}
            self.guides_joint_orient = {}
            for position in guides_descendents: #Get the position of each guide
                    posi = cmds.xform(position, t=True, ws=True, query=True)
                    self.guides_positions[position] = posi
            for rotation in guides_descendents: #Get the rotation of each guide
                    rot = cmds.xform(rotation, ro=True, ws=True, query=True)
                    self.guides_rotations[rotation] = rot
            for parent in guides_descendents: #Get the parent of each guide
                    par = cmds.listRelatives(parent, parent=True)[0]
                    self.guides_parents[parent] = par
            for joint_orient in guides_descendents: #Get the joint orient of each guide
                    joint_or = cmds.getAttr(f"{joint_orient}.jointOrient")
                    self.guides_joint_orient[joint_orient] = joint_or

            
        elif len(self.guides_folder) > 1:
                om.MGlobal.displayError("More than one guides_grp found in the scene.")
                return
        else:
                om.MGlobal.displayError("No guides found in the scene.")
                return

GuidesExport().guides_export("C_guides_GRP")