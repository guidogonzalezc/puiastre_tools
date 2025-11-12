#Python libraries import
from maya import cmds
from importlib import reload
import maya.api.OpenMaya as om
import math

# Local imports
from puiastreTools.utils.curve_tool import controller_creator
from puiastreTools.utils.guide_creation import guide_import
from puiastreTools.utils import data_export
from puiastreTools.utils import core
from puiastreTools.utils.core import get_offset_matrix
from puiastreTools.utils import basic_structure
from puiastreTools.utils import de_boor_core_002
from puiastreTools.utils.space_switch import fk_switch

reload(data_export)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}

class EyebrowModule():
    """
    Class to create a neck module in a Maya rigging setup.
    This module handles the creation of neck joints, controllers, and various systems such as stretch, reverse, offset, squash, and volume preservation.
    """
    def __init__(self):
        """
        Initializes the NeckModule class, setting up paths and data exporters.
        
        Args:
            self: Instance of the NeckModule class.
        """
        
        self.data_exporter = data_export.DataExport()


        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")
        self.muscle_locators = self.data_exporter.get_data("basic_structure", "muscleLocators_GRP")



    def make(self, guide_name):
        """
        Creates the neck module, including the neck chain, controllers, and various systems.

        Args:
            self: Instance of the NeckModule class.
        """

        self.guide_name = guide_name

        self.side = self.guide_name.split("_")[0]

        if self.side == "L":
            self.primary_aim_vector = om.MVector(AXIS_VECTOR["z"])
            self.secondary_aim_vector = om.MVector(AXIS_VECTOR["-x"])
        else:
            self.primary_aim_vector = om.MVector(AXIS_VECTOR["-z"])
            self.secondary_aim_vector = om.MVector(AXIS_VECTOR["-x"])


        self.module_trn = cmds.createNode("transform", name=f"{self.side}_eyebrowModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_eyebrowControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.tangent_controllers_trn = cmds.createNode("transform", name=f"{self.side}_eyebrowTangentControllers_GRP", ss=True, parent=self.controllers_trn)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_eyebrowSkinning_GRP", ss=True, p=self.skel_grp)

        self.create_chain()

        self.data_exporter.append_data(f"C_eyebrowModule", 
                                    {"skinning_transform": self.skinning_trn,

                                    }
                                  )
            
    def curve_attachment(self, name, curve_shape, u_value):

        point_on_surface = cmds.createNode("pointOnCurveInfo", name=f"{name}_POCI", ss=True)
        cmds.setAttr(f"{point_on_surface}.parameter", u_value)

        cmds.connectAttr(f"{curve_shape}.worldSpace[0]", f"{point_on_surface}.inputCurve", force=True)

        matrix_node = cmds.createNode('fourByFourMatrix', name=f"{name}_FBF", ss=True)

        self.eye_rotation_4b4(matrix_node)

        cmds.connectAttr(f"{point_on_surface}.positionX", f"{matrix_node}.in30", force=True)
        cmds.connectAttr(f"{point_on_surface}.positionY", f"{matrix_node}.in31", force=True)
        cmds.connectAttr(f"{point_on_surface}.positionZ", f"{matrix_node}.in32", force=True)

        pickMatrix = cmds.createNode("pickMatrix", name=f"{name}_PMX", ss=True)
        cmds.connectAttr(f"{matrix_node}.output", f"{pickMatrix}.inputMatrix", force=True)
        cmds.setAttr(f"{pickMatrix}.useScale", 0)
        cmds.setAttr(f"{pickMatrix}.useShear", 0)

        return pickMatrix


    def create_chain(self):
        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        self.curves = []
        self.nurbsSurface = None

        for item in self.guides:
            try:
                relative = cmds.listRelatives(item, shapes=True)
                if cmds.objectType(relative, isType="nurbsCurve"):
                    self.curves.append(item)
                elif cmds.objectType(relative, isType="nurbsSurface"):
                    self.nurbsSurface = item
            except:
                pass

        if not self.nurbsSurface:
            om.MGlobal.displayError("No NURBS surface found in the eyebrow guide. Please create one to proceed.")
            return
        if not self.curves:
            om.MGlobal.displayError("No NURBS curves found in the eyebrow guide. Please create at least one to proceed.")
            return
        
        for curve in self.curves:
            self.side = curve.split("_")[0]
            rebuilded = cmds.rebuildCurve(curve, ch=0, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=4, d=3, tol=0.01)
            cmds.parent(rebuilded, self.module_trn)

            for i, cv in enumerate(cmds.ls(f"{rebuilded}.cv[*]", fl=True)):
                
                ctl, ctl_grp = controller_creator(
                    name=f"{self.side}_",
                    suffixes=["GRP", "ANM"],
                    lock=["sx", "sy", "sz", "visibility"],
                    ro=False,
                    parent= self.controllers_trn
                )

                pos = cmds.xform(cv, q=True, ws=True, t=True)
                closest_point = cmds.createNode("closestPointOnSurface", name=f"{cv}_CPOS", ss=True)
                cmds.connectAttr(f"{self.nurbsSurface}.worldSpace[0]", f"{closest_point}.inputSurface", force=True)
                cmds.setAttr(f"{closest_point}.inPosition", pos[0], pos[1], pos[2], type="double3")

                new_pos = cmds.getAttr(f"{closest_point}.position")[0]
                cmds.xform(cv, ws=True, t=new_pos)

