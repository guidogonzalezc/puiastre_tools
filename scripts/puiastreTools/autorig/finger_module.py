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
        self.create_controller()
    
    def import_guides(self, guide_name):

        """
        Import the guides for the fingers module
        :param guide_name: name of the guide to import"""

        self.fingers = guide_import(guide_name, all_descendents=True, path=None)
        self.side = self.fingers[0].split("_")[0]
        self.controllers_grp = cmds.createNode("transform", name=f"{self.side}_legFingersControllers_GRP", parent=self.masterWalk_ctl)

    def create_controller(self):

        """"
        Create controllers for each guide
        :param guide_name: name of the guide to import
        """
        thumb_guides = [finger for finger in self.fingers if "thumb" in finger]
        index_guides = [finger for finger in self.fingers if "index" in finger]
        middle_guides = [finger for finger in self.fingers if "middle" in finger]
        pinky_guides = [finger for finger in self.fingers if "pinky" in finger]

        controllers = []
        grps = []
        
        for i, finger in enumerate([*thumb_guides, *index_guides, *middle_guides, *pinky_guides]):

            finger_name = finger.split("_")[1]

            ctl, grp = controller_creator(
                name=f"{self.side}_{finger_name}",
                suffixes=["GRP", "ANM"],
                lock=["tx", "ty", "tz" ,"sx", "sy", "sz", "visibility"],
                ro=False
            )

            if controllers:
                if "01" in finger: # First joint of each finger, parent to the controllers group
                    cmds.parent(grp[0], self.controllers_grp)
                else:
                    cmds.parent(grp[0], controllers[-1])
            else:
                if "01" in finger:
                    cmds.parent(grp[0], self.controllers_grp)

            if "01" in finger: # First joint of each finger, create a new aim matrix

                aim_matrix_01 = cmds.createNode("aimMatrix", name=finger.replace("GUIDE", "AIM"))
                aim_matrix_02 = cmds.createNode("aimMatrix", name=finger.replace("01_GUIDE", "02_AIM"))
                cmds.setAttr(f"{aim_matrix_01}.primaryInputAxis", 0, 0, 1, type="double3")
                cmds.setAttr(f"{aim_matrix_02}.primaryInputAxis", 0, 0, 1, type="double3")
                cmds.setAttr(f"{aim_matrix_02}.secondaryInputAxis", 0, 1, 0, type="double3")
                cmds.setAttr(f"{aim_matrix_02}.secondaryMode", 1) # Aim
                cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_01}.inputMatrix")
                cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_02}.secondaryTargetMatrix") # Connect the guide to the secondaryTargetMatrix of the aim matrix
                blend_matrix_03 = cmds.createNode("blendMatrix", n=finger.replace("01_GUIDE", "03_BLM"))
                cmds.setAttr(f"{blend_matrix_03}.target[0].scaleWeight", 0)
                cmds.setAttr(f"{blend_matrix_03}.target[0].rotateWeight", 0)
                cmds.setAttr(f"{blend_matrix_03}.target[0].shearWeight", 0)
                cmds.connectAttr(f"{aim_matrix_02}.outputMatrix", f"{blend_matrix_03}.inputMatrix")
                mult_matrix = cmds.createNode("multMatrix", name=finger.replace("02_GUIDE", "02_MLT"))
                cmds.connectAttr(f"{aim_matrix_02}.outputMatrix", f"{mult_matrix}.matrixIn[0]")
                cmds.connectAttr(f"{grp[0]}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]")
                mult_matrix_02 = cmds.createNode("multMatrix", name=finger.replace("02_GUIDE", "03_MLT"))
                cmds.connectAttr(f"{blend_matrix_03}.outputMatrix", f"{mult_matrix_02}.matrixIn[0]")

                cmds.connectAttr(f"{aim_matrix_01}.outputMatrix", f"{grp[0]}.offsetParentMatrix") # Connect the aim matrix to the controller group offset parent matrix, to follow the finger movement
            
            if "02" in finger: # Middle joint of each finger, connect to the first aim matrix

                cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_02}.inputMatrix")
                cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{grp[0]}.offsetParentMatrix") # Connect the aim matrix02 to the controller group offset parent matrix, to follow the finger movement
                cmds.connectAttr(f"{grp[0]}.worldInverseMatrix[0]", f"{mult_matrix_02}.matrixIn[1]")
            
            if "03" in finger: # Last joint of each finger, connect to the last aim matrix
                
                cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_01}.primaryTargetMatrix")
                cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{aim_matrix_02}.primaryTargetMatrix") # Connect the guide to the input matrix of the aim matrix
                cmds.connectAttr(f"{finger}.worldMatrix[0]", f"{blend_matrix_03}.target[0].targetMatrix") # Connect the guide to the second input of the blend matrix

                cmds.connectAttr(f"{mult_matrix_02}.matrixSum", f"{grp[0]}.offsetParentMatrix") # Connect the blend matrix to the controller group offset parent matrix, to follow the finger movement

            

            controllers.append(ctl)
            grps.append(grp)

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

        
    

