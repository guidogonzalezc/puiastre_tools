import maya.cmds as cmds
import maya.OpenMaya as om
import os
import json

class GuidesExport():

    def get_transform_modules(self, guides):
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
            print(left_guides)
            print(right_guides)

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
        
        print(self.guides_positions)
        print(self.guides_rotations)
        print(self.guides_parents)
        print(self.guides_joint_orient)

    # def leg_export(self):
    #     if ("*leg*") in cmds.listRelatives(self.guides_folder):
    #             self.leg_guides = cmds.ls("*leg*")
    #             children_leg = cmds.listRelatives(self.leg_guides, children=True)
    #             # for child in children_leg:
                            
    #     else:
    #             om.MGlobal.displayError("No leg guides found in the scene.")

    # def arm_export(self):
GuidesExport().get_transform_modules("C_guides_GRP")