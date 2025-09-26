#Python libraries import
import json
from maya import cmds
from importlib import reload
import maya.api.OpenMaya as om
import math

# Local imports
from puiastreTools.utils.curve_tool import controller_creator
from puiastreTools.utils.guide_creation import guide_import
from puiastreTools.utils import data_export

# Dev only imports
from puiastreTools.utils import guide_creation
import puiastreTools.utils.de_boor_core_002 as de_boors_002
from puiastreTools.utils import space_switch as ss
from puiastreTools.utils import core
from puiastreTools.utils import basic_structure


reload(de_boors_002)
reload(guide_creation)
reload(ss)
reload(core)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}

class FingersModule(object):

    def __init__(self):

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")


        

    def make(self, guide_name):

        """
        Make the fingers module
        :param guide_name: name of the guide to import
        """
        data_exporter = data_export.DataExport()
        self.import_guides(guide_name)
        leg_skinning = data_exporter.get_data(f"{self.side}_backLegModule", "skinning_transform")
        self.leg_ball_blm = cmds.listRelatives(leg_skinning, children=True)[-1]

        parent_matrix = cmds.createNode("parentMatrix", name=f"{self.side}_legFingersParent_PMX", ss=True)
        # cmds.connectAttr(self.masterWalk_ctl + ".worldMatrix[0]", parent_matrix + ".inputMatrix")
        cmds.connectAttr(self.leg_ball_blm + ".worldMatrix[0]", parent_matrix + ".target[0].targetMatrix")

        offset_matrix = self.get_offset_matrix(self.controllers_grp, self.leg_ball_blm)

        cmds.setAttr(parent_matrix + ".target[0].offsetMatrix", *offset_matrix, type="matrix")

        cmds.connectAttr(parent_matrix + ".outputMatrix", self.controllers_grp + ".offsetParentMatrix")

        if self.side == "L":
            self.primary_aim = "x"
            self.secondary_aim = "-y"

        elif self.side == "R":
            self.primary_aim = "-x"
            self.secondary_aim = "y"

        self.primary_aim_vector = om.MVector(AXIS_VECTOR[self.primary_aim])
        self.secondary_aim_vector = om.MVector(AXIS_VECTOR[self.secondary_aim])
        self.create_controller()
    
    def import_guides(self, guide_name):

        """
        Import the guides for the fingers module
        :param guide_name: name of the guide to import"""

        self.fingers = guide_import(guide_name, all_descendents=True, path=None)
        self.side = self.fingers[0].split("_")[0]
        self.controllers_grp = cmds.createNode("transform", name=f"{self.side}_legFingersControllers_GRP", parent=self.masterWalk_ctl)
    
    def get_offset_matrix(self, child, parent):
        """
        Calculate the offset matrix between a child and parent transform in Maya.
        Args:
            child (str): The name of the child transform.
            parent (str): The name of the parent transform. 
        Returns:
            om.MMatrix: The offset matrix that transforms the child into the parent's space.
        """
        child_dag = om.MSelectionList().add(child).getDagPath(0)
        parent_dag = om.MSelectionList().add(parent).getDagPath(0)
        
        child_world_matrix = child_dag.inclusiveMatrix()
        parent_world_matrix = parent_dag.inclusiveMatrix()
        
        offset_matrix = child_world_matrix * parent_world_matrix.inverse()

        return offset_matrix
    
    def create_controller(self):

        """"
        Create controllers for each guide
        :param guide_name: name of the guide to import
        """
        thumb_guides = [finger for finger in self.fingers if "thumb" in finger]
        index_guides = [finger for finger in self.fingers if "index" in finger]
        middle_guides = [finger for finger in self.fingers if "middle" in finger]
        pinky_guides = [finger for finger in self.fingers if "pinky" in finger]

        grps = []

        for i, finger in enumerate([thumb_guides, index_guides, middle_guides, pinky_guides]):
            finger_name = ''.join([c for c in finger[0].split('_')[1] if not c.isdigit()])
            

            controllers = []
            aim_matrix_guides = []

            for index in range(0, 2):
                aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{finger_name}Guide0{index+1}_AMX", ss=True)

                cmds.setAttr(aim_matrix + ".primaryInputAxis", *self.primary_aim_vector, type="double3")
                cmds.setAttr(aim_matrix + ".secondaryInputAxis", *self.secondary_aim_vector, type="double3")
                cmds.setAttr(aim_matrix + ".secondaryTargetVector", *self.secondary_aim_vector, type="double3")
                
                cmds.setAttr(aim_matrix + ".primaryMode", 1)
                cmds.setAttr(aim_matrix + ".secondaryMode", 1)

                next_index = index + 2 if (index + 2) < len(finger) else 0
                print(index+2)
                print(len(finger))

                cmds.connectAttr(finger[index] + ".worldMatrix[0]", aim_matrix + ".inputMatrix")
                cmds.connectAttr(finger[index+1] + ".worldMatrix[0]", aim_matrix + ".primaryTargetMatrix")
                cmds.connectAttr(finger[next_index] + ".worldMatrix[0]", aim_matrix + ".secondaryTargetMatrix")

                aim_matrix_guides.append(aim_matrix)

            aim_matrix_guides.append(cmds.createNode("blendMatrix", name=f"{self.side}_{finger_name}Guide0{index+2}_BLM", ss=True))
            cmds.connectAttr(finger[-1] + ".worldMatrix[0]", aim_matrix_guides[-1] + ".inputMatrix")
            cmds.connectAttr(aim_matrix_guides[1] + ".outputMatrix", aim_matrix_guides[-1] + ".target[0].targetMatrix")
            cmds.setAttr(aim_matrix_guides[-1] + ".target[0].translateWeight", 0)

            for j, guide in enumerate(aim_matrix_guides):
                finger_name = f"{guide.split('_')[1]}"

                ctl, grp = controller_creator(
                    name=f"{self.side}_{finger_name}",
                    suffixes=["GRP", "ANM"],
                    lock=["tx", "ty", "tz" ,"sx", "sy", "sz", "visibility"],
                    ro=False,
                    parent=controllers[-1] if controllers else self.controllers_grp 
                )

                if controllers:
                    offset_matrix = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}_MLT", ss=True)
                    inverse = cmds.createNode("inverseMatrix", name=f"{self.side}_{finger_name}_INV", ss=True)
                    cmds.connectAttr(guide + ".outputMatrix", offset_matrix + ".matrixIn[1]")
                    cmds.connectAttr(aim_matrix_guides[j-1] + ".outputMatrix", inverse + ".inputMatrix")
                    cmds.connectAttr(inverse + ".outputMatrix", offset_matrix + ".matrixIn[2]")
                    cmds.connectAttr(controllers[-1] + ".matrix", offset_matrix + ".matrixIn[0]")
                    cmds.connectAttr(offset_matrix + ".matrixSum", grp[0] + ".offsetParentMatrix")
                else:
                    cmds.connectAttr(guide + ".outputMatrix", grp[0] + ".offsetParentMatrix")


                cmds.setAttr(f"{grp[0]}.rotate", 0,0,0, type="double3")
                cmds.setAttr(f"{grp[0]}.translate", 0,0,0, type="double3")

                controllers.append(ctl)


                  


                # if "01" in finger: # First joint of each finger, create a new aim matrix

                #     aim_matrix_01 = cmds.createNode("aimMatrix", name=finger.replace("GUIDE", "AIM"))
                #     aim_matrix_02 = cmds.createNode("aimMatrix", name=finger.replace("01_GUIDE", "02_AIM"))
                #     cmds.setAttr(f"{aim_matrix_01}.primaryInputAxis", 1, 0, 0, type="double3")
                #     cmds.setAttr(f"{aim_matrix_02}.primaryInputAxis", 1, 0, 0, type="double3")
                #     cmds.setAttr(f"{aim_matrix_02}.secondaryInputAxis", 0, 1, 0, type="double3")
                #     cmds.setAttr(f"{aim_matrix_01}.secondaryInputAxis", 0, 1, 0, type="double3")
                #     cmds.setAttr(f"{aim_matrix_01}.secondaryTargetVector", 0, 1, 0, type="double3")
                #     cmds.setAttr(f"{aim_matrix_02}.secondaryTargetVector", 0, 1, 0, type="double3")
                #     cmds.setAttr(f"{aim_matrix_02}.secondaryMode", 1) # Aim
                #     cmds.setAttr(f"{aim_matrix_01}.secondaryMode", 1) # Aim
                #     cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_01}.inputMatrix")
                #     cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_02}.secondaryTargetMatrix") # Connect the guide to the secondaryTargetMatrix of the aim matrix
                #     blend_matrix_03 = cmds.createNode("blendMatrix", n=finger.replace("01_GUIDE", "03_BLM"))
                #     cmds.setAttr(f"{blend_matrix_03}.target[0].scaleWeight", 0)
                #     cmds.setAttr(f"{blend_matrix_03}.target[0].rotateWeight", 0)
                #     cmds.setAttr(f"{blend_matrix_03}.target[0].shearWeight", 0)
                #     cmds.connectAttr(f"{aim_matrix_02}.outputMatrix", f"{blend_matrix_03}.inputMatrix")
                #     mult_matrix = cmds.createNode("multMatrix", name=finger.replace("01_GUIDE", "02_MLT"))
                #     cmds.connectAttr(f"{aim_matrix_02}.outputMatrix", f"{mult_matrix}.matrixIn[0]")
                #     cmds.connectAttr(f"{grp[0]}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]")
                #     mult_matrix_02 = cmds.createNode("multMatrix", name=finger.replace("01_GUIDE", "03_MLT"))
                #     cmds.connectAttr(f"{blend_matrix_03}.outputMatrix", f"{mult_matrix_02}.matrixIn[0]")

                #     cmds.connectAttr(f"{aim_matrix_01}.outputMatrix", f"{grp[0]}.offsetParentMatrix") # Connect the aim matrix to the controller group offset parent matrix, to follow the finger movement
                
                # if "02" in finger: # Middle joint of each finger, connect to the first aim matrix

                #     cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_01}.primaryTargetMatrix")
                #     cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_02}.inputMatrix")
                #     cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{grp[0]}.offsetParentMatrix") # Connect the aim matrix02 to the controller group offset parent matrix, to follow the finger movement
                #     cmds.connectAttr(f"{grp[0]}.worldInverseMatrix[0]", f"{mult_matrix_02}.matrixIn[1]")
                
                # if "03" in finger: # Last joint of each finger, connect to the last aim matrix
                    
                #     cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_01}.secondaryTargetMatrix")
                #     cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_02}.primaryTargetMatrix") # Connect the guide to the input matrix of the aim matrix
                #     cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{blend_matrix_03}.target[0].targetMatrix") # Connect the guide to the second input of the blend matrix

                #     cmds.connectAttr(f"{mult_matrix_02}.matrixSum", f"{grp[0]}.offsetParentMatrix") # Connect the blend matrix to the controller group offset parent matrix, to follow the finger movement

                # cmds.xform(grp[0], m=om.MMatrix.kIdentity)
                # controllers.append(ctl)
                # grps.append(grp)

    def attributes(self, controller):

        pass
    
    def get_offset_matrix(self, child, parent):
        """
        Calculate the offset matrix between a child and parent transform in Maya.
        Args:
            child (str): The name of the child transform.
            parent (str): The name of the parent transform. 
        Returns:
            om.MMatrix: The offset matrix that transforms the child into the parent's space.
        """
        child_dag = om.MSelectionList().add(child).getDagPath(0)
        parent_dag = om.MSelectionList().add(parent).getDagPath(0)
        
        child_world_matrix = child_dag.inclusiveMatrix()
        parent_world_matrix = parent_dag.inclusiveMatrix()
        
        offset_matrix = child_world_matrix * parent_world_matrix.inverse()

        return offset_matrix

        
    

