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
from puiastreTools.utils import basic_structure
from puiastreTools.utils import guide_creation

from puiastreTools.utils.space_switch import fk_switch

reload(data_export)
reload(guide_creation)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}


class JawModule():
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

        self.primary_aim = "z"
        self.primary_aim_vector = AXIS_VECTOR[self.primary_aim]
        self.secondary_aim = "y"
        self.secondary_aim_vector = AXIS_VECTOR[self.secondary_aim]

        self.side = self.guide_name.split("_")[0]

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_jawModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_jawControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_jawSkinning_GRP", ss=True, p=self.skel_grp)

        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)


        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        self.jaw_module()

        # cmds.setAttr("guides_GRP.visibility", 1) # To visualize guides while working on the rig
        # cmds.setAttr("C_preferences_CTL.showModules", 1) # To visualize guides while working on the rig

        for joint in cmds.ls(type="joint"):
            cmds.setAttr(f"{joint}.radius", 10)


        self.data_exporter.append_data(f"{self.side}_jawModule", 
                                    {"skinning_transform": self.skinning_trn,
                                    # "neck_ctl": self.main_controllers[0],

                                    }
                                  )

    def local_setup(self, grp, ctl):

        local_mult_matrix = cmds.createNode("multMatrix", name=ctl.replace("_CTL", "_MMX"), ss=True)
        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{local_mult_matrix}.matrixIn[0]")
        cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{local_mult_matrix}.matrixIn[1]")
        grp_world_matrix = cmds.getAttr(f"{grp}.worldMatrix[0]")
        cmds.setAttr(f"{local_mult_matrix}.matrixIn[2]", grp_world_matrix, type="matrix")

        return f"{local_mult_matrix}.matrixSum"

    def get_offset_matrix(self, child, parent, matrix=False):
        """
        Calculate the offset matrix between a child and parent transform in Maya.
        Args:
            child (str): The name of the child transform.
            parent (str): The name of the parent transform. 
        Returns:
            om.MMatrix: The offset matrix that transforms the child into the parent's space.
        """
        if not matrix:
            child_dag = om.MSelectionList().add(child).getDagPath(0)
            child_world_matrix = child_dag.inclusiveMatrix()
        else:
            child_world_matrix = om.MMatrix(child)

        parent_dag = om.MSelectionList().add(parent).getDagPath(0)
        
        parent_world_matrix = parent_dag.inclusiveMatrix()
        
        offset_matrix = child_world_matrix * parent_world_matrix.inverse()

        return offset_matrix
    
    import maya.api.OpenMaya as om

    def getClosestParamToPosition(self, curve, position):
        """
        Returns the closest parameter (u) on the given NURBS curve to a world-space position.
        
        Args:
            curve (str or MObject or MDagPath): The curve to evaluate.
            position (list or tuple): A 3D world-space position [x, y, z].

        Returns:
            float: The parameter (u) value on the curve closest to the given position.
        """
        if isinstance(curve, str):
            sel = om.MSelectionList()
            sel.add(curve)
            curve_dag_path = sel.getDagPath(0)
        elif isinstance(curve, om.MObject):
            curve_dag_path = om.MDagPath.getAPathTo(curve)
        elif isinstance(curve, om.MDagPath):
            curve_dag_path = curve
        else:
            raise TypeError("Curve must be a string name, MObject, or MDagPath.")

        curve_fn = om.MFnNurbsCurve(curve_dag_path)

        point = om.MPoint(*position)

        closest_point, paramU = curve_fn.closestPoint(point, space=om.MSpace.kWorld)

        return paramU


    def jaw_module(self):
        """
        Creates the neck joint chain by importing guides and parenting the first joint to the module transform.

        Args:
            self: Instance of the neckModule class.
        """
        jaw_guide = self.guides[0]

        self.jaw_ctl, self.jaw_ctl_grp = controller_creator(
                name=f"{self.side}_jaw",
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn,
            )
        
        cmds.connectAttr(f"{jaw_guide}.worldMatrix[0]", f"{self.jaw_ctl_grp[0]}.offsetParentMatrix")

        local_jaw = self.local_setup(self.jaw_ctl_grp[0], self.jaw_ctl)

        cmds.addAttr(self.jaw_ctl, shortName="extraSep", niceName="EXTRA ATTRIBUTES ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.jaw_ctl+".extraSep", channelBox=True, lock=True)
        cmds.addAttr(self.jaw_ctl, shortName="collision", niceName="Collision", maxValue=1, minValue=0,defaultValue=1, keyable=True)

        self.upper_jaw_ctl, self.upper_jaw_ctl_grp = controller_creator(
                name=f"{self.side}_upperJaw",
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn,
            )
        
        
        cmds.connectAttr(f"{jaw_guide}.worldMatrix[0]", f"{self.upper_jaw_ctl_grp[0]}.offsetParentMatrix")
        local_upper_jaw = self.local_setup(self.upper_jaw_ctl_grp[0], self.upper_jaw_ctl)

        jaws_rotation_sum = cmds.createNode("sum", name=f"{self.side}_jawsRotation_SUM", ss=True)
        cmds.connectAttr(f"{self.jaw_ctl}.rotateX", f"{jaws_rotation_sum}.input[0]")
        cmds.connectAttr(f"{self.upper_jaw_ctl}.rotateX", f"{jaws_rotation_sum}.input[1]")

        collision_clamp = cmds.createNode("clamp", name=f"{self.side}_collision_CLAMP", ss=True)
        cmds.connectAttr(f"{jaws_rotation_sum}.output", f"{collision_clamp}.inputR")
        cmds.setAttr(f"{collision_clamp}.minR", -360)
        cmds.connectAttr(f"{self.upper_jaw_ctl}.rotateX", f"{collision_clamp}.maxR")

        collision_bta = cmds.createNode("blendTwoAttr", name=f"{self.side}_collision_BTA", ss=True)
        cmds.connectAttr(f"{collision_clamp}.outputR", f"{collision_bta}.input[1]")
        cmds.connectAttr(f"{self.jaw_ctl}.collision", f"{collision_bta}.attributesBlender")
        cmds.setAttr(f"{collision_bta}.input[0]", 0)

        collision_compose = cmds.createNode("composeMatrix", name=f"{self.side}_collision_CPM", ss=True)
        cmds.connectAttr(f"{collision_bta}.output", f"{collision_compose}.inputRotateX")

        cmds.connectAttr(f"{collision_compose}.outputMatrix", f"{self.upper_jaw_ctl}.offsetParentMatrix")

        self.jaw_local_joint = cmds.createNode("joint", name=f"{self.side}_jaw_JNT", ss=True, parent=self.skinning_trn)
        cmds.connectAttr(local_jaw, f"{self.jaw_local_joint}.offsetParentMatrix")

        self.upper_jaw_local_joint = cmds.createNode("joint", name=f"{self.side}_upperJaw_JNT", ss=True, parent=self.skinning_trn)
        cmds.connectAttr(local_upper_jaw, f"{self.upper_jaw_local_joint}.offsetParentMatrix")

        self.jaw_surface = None
        for guides in self.guides:
            if cmds.listRelatives(guides, shapes=True, type="nurbsSurface"):
                    self.jaw_surface = guides

        if self.jaw_surface:
            self.jaw_skin_cluster = cmds.skinCluster(
                self.jaw_surface,
                self.jaw_local_joint,
                self.upper_jaw_local_joint,
                toSelectedBones=True,
                bindMethod=0,
                normalizeWeights=1,
                weightDistribution=0,
                maximumInfluences=2,
                dropoffRate=4,
                removeUnusedInfluence=False
            )[0]

            u_spans = cmds.getAttr(f"{self.jaw_surface}.spansU")
            v_spans = cmds.getAttr(f"{self.jaw_surface}.spansV")
            degU = cmds.getAttr(f"{self.jaw_surface}.degreeU")
            degV = cmds.getAttr(f"{self.jaw_surface}.degreeV")

            u_count = u_spans + degU
            v_count = v_spans + degV

            for u in range(u_count):
                for v in range(v_count):
                    t = float(v) / (v_count - 1)
                    jaw_w = 1.0 - t
                    upper_w = t
                    
                    cv = f"{self.jaw_surface}.cv[{u}][{v}]"
                    
                    cmds.skinPercent(self.jaw_skin_cluster, cv, transformValue=[
                        (self.jaw_local_joint, jaw_w),
                        (self.upper_jaw_local_joint, upper_w)
                    ])



        self.lips_setup()

    def lips_setup(self):

        self.linear_curves = []
        for guides in self.guides:
            if cmds.listRelatives(guides, shapes=True, type="nurbsCurve"):
                cv_pos = cmds.xform(f"{guides}.cv[0]", q=True, ws=True, t=True)
                if cv_pos[0] > 0:
                    cmds.reverseCurve(guides, ch=False, rpo=True)
                self.linear_curves.append(guides)

        for index, curve in enumerate(self.linear_curves):
            rebuilded_curve = cmds.rebuildCurve(
                    curve,
                    ch=0,
                    rpo=0,
                    rt=0,
                    end=1,
                    kr=0,
                    kcp=0,
                    kep=1,
                    kt=0,
                    s=4,
                    d=3,
                    tol=0.01,
                    name=curve.replace("Curve_GUIDE", "Rebuild_CRV")
                )[0]
            
            cmds.parent(rebuilded_curve, self.module_trn)

            # Create lip corner controllers

            if index == 0:

                self.r_side_jaw_ctl, self.r_side_jaw_ctl_grp = controller_creator(
                    name=f"R_lipCorner",
                    suffixes=["GRP", "OFF", "ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn,
                )

                cmds.addAttr(self.r_side_jaw_ctl, shortName="extraSep", niceName="EXTRA ATTRIBUTES ———", enumName="———",attributeType="enum", keyable=True)
                cmds.setAttr(self.r_side_jaw_ctl+".extraSep", channelBox=True, lock=True)
                cmds.addAttr(self.r_side_jaw_ctl, shortName="height", niceName="Height", maxValue=1, minValue=0,defaultValue=0.5, keyable=True)

                r_lip_corner_4b4 = cmds.createNode("fourByFourMatrix", name="R_lipCorner_4B4", ss=True)
                cmds.connectAttr(f"{curve}.editPoints[0].xValueEp", f"{r_lip_corner_4b4}.in30")
                cmds.connectAttr(f"{curve}.editPoints[0].yValueEp", f"{r_lip_corner_4b4}.in31")
                cmds.connectAttr(f"{curve}.editPoints[0].zValueEp", f"{r_lip_corner_4b4}.in32")
                cmds.setAttr(f"{r_lip_corner_4b4}.in00", -1)

                cmds.connectAttr(f"{r_lip_corner_4b4}.output", f"{self.r_side_jaw_ctl_grp[0]}.offsetParentMatrix")


                parent_matrix_r_side = cmds.createNode("parentMatrix", name="R_lipCorner_PMX", ss=True)
                cmds.connectAttr(f"{self.jaw_ctl}.worldMatrix[0]", f"{parent_matrix_r_side}.target[0].targetMatrix")
                cmds.connectAttr(f"{self.upper_jaw_ctl}.worldMatrix[0]", f"{parent_matrix_r_side}.target[1].targetMatrix")
                cmds.connectAttr(f"{self.r_side_jaw_ctl}.height", f"{parent_matrix_r_side}.target[1].weight")
                reverse = cmds.createNode("reverse", name="R_lipCorner_REV", ss=True)
                cmds.connectAttr(f"{self.r_side_jaw_ctl}.height", f"{reverse}.inputX")
                cmds.connectAttr(f"{reverse}.outputX", f"{parent_matrix_r_side}.target[0].weight")
                jaw_offset_r = self.get_offset_matrix(cmds.getAttr(f"{r_lip_corner_4b4}.output"), self.jaw_ctl, matrix=True)
                cmds.setAttr(f"{parent_matrix_r_side}.target[0].offsetMatrix", jaw_offset_r, type="matrix")
                cmds.setAttr(f"{parent_matrix_r_side}.target[1].offsetMatrix", jaw_offset_r, type="matrix")

                cmds.connectAttr(f"{r_lip_corner_4b4}.output", f"{parent_matrix_r_side}.inputMatrix")

                jaw_offset_child = cmds.createNode("multMatrix", name="R_lipCornerOffset_MMX", ss=True)
                cmds.connectAttr(f"{parent_matrix_r_side}.outputMatrix", f"{jaw_offset_child}.matrixIn[0]")
                cmds.connectAttr(f"{self.r_side_jaw_ctl_grp[0]}.parentInverseMatrix[0]", f"{jaw_offset_child}.matrixIn[1]")

                cmds.connectAttr(f"{jaw_offset_child}.matrixSum", f"{self.r_side_jaw_ctl_grp[1]}.offsetParentMatrix", f=True)

                self.l_side_jaw_ctl, self.l_side_jaw_ctl_grp = controller_creator(
                    name=f"L_lipCorner",
                    suffixes=["GRP", "OFF", "ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn,
                )

                cmds.addAttr(self.l_side_jaw_ctl, shortName="extraSep", niceName="EXTRA ATTRIBUTES ———", enumName="———",attributeType="enum", keyable=True)
                cmds.setAttr(self.l_side_jaw_ctl+".extraSep", channelBox=True, lock=True)
                cmds.addAttr(self.l_side_jaw_ctl, shortName="height", niceName="Height", maxValue=1, minValue=0,defaultValue=0.5, keyable=True)

                last_cv = len(cmds.ls(f"{curve}.cv[*]", flatten=True))-1
                l_lip_corner_4b4 = cmds.createNode("fourByFourMatrix", name="L_lipCorner_4B4", ss=True)
                cmds.connectAttr(f"{curve}.editPoints[{last_cv}].xValueEp", f"{l_lip_corner_4b4}.in30")
                cmds.connectAttr(f"{curve}.editPoints[{last_cv}].yValueEp", f"{l_lip_corner_4b4}.in31")
                cmds.connectAttr(f"{curve}.editPoints[{last_cv}].zValueEp", f"{l_lip_corner_4b4}.in32")

                parent_matrix_l_side = cmds.createNode("parentMatrix", name="L_lipCorner_PMX", ss=True)
                cmds.connectAttr(f"{self.jaw_ctl}.worldMatrix[0]", f"{parent_matrix_l_side}.target[0].targetMatrix")
                cmds.connectAttr(f"{self.upper_jaw_ctl}.worldMatrix[0]", f"{parent_matrix_l_side}.target[1].targetMatrix")
                cmds.connectAttr(f"{self.l_side_jaw_ctl}.height", f"{parent_matrix_l_side}.target[1].weight")
                reverse = cmds.createNode("reverse", name="L_lipCorner_REV", ss=True)
                cmds.connectAttr(f"{self.l_side_jaw_ctl}.height", f"{reverse}.inputX")
                cmds.connectAttr(f"{reverse}.outputX", f"{parent_matrix_l_side}.target[0].weight")
                jaw_offset_l = self.get_offset_matrix(cmds.getAttr(f"{l_lip_corner_4b4}.output"), self.jaw_ctl, matrix=True)
                cmds.setAttr(f"{parent_matrix_l_side}.target[0].offsetMatrix", jaw_offset_l, type="matrix")
                cmds.setAttr(f"{parent_matrix_l_side}.target[1].offsetMatrix", jaw_offset_l, type="matrix")

                cmds.connectAttr(f"{l_lip_corner_4b4}.output", f"{self.l_side_jaw_ctl_grp[0]}.offsetParentMatrix")

                jaw_offset_child = cmds.createNode("multMatrix", name="L_lipCornerOffset_MMX", ss=True)
                cmds.connectAttr(f"{parent_matrix_l_side}.outputMatrix", f"{jaw_offset_child}.matrixIn[0]")
                cmds.connectAttr(f"{self.l_side_jaw_ctl_grp[0]}.parentInverseMatrix[0]", f"{jaw_offset_child}.matrixIn[1]")

                cmds.connectAttr(f"{jaw_offset_child}.matrixSum", f"{self.l_side_jaw_ctl_grp[1]}.offsetParentMatrix", f=True)

                self.r_corner_local = self.local_setup(ctl = self.r_side_jaw_ctl, grp = self.r_side_jaw_ctl_grp[0])
                self.l_corner_local = self.local_setup(ctl = self.l_side_jaw_ctl, grp = self.l_side_jaw_ctl_grp[0])

                mouth_sliding_shape = cmds.listRelatives(self.jaw_surface, shapes=True, noIntermediate=True)[0]

                self.corner_projected_joints = []

                for local in [self.r_corner_local, self.l_corner_local]:
                    local_side = local.split("_")[0]
                    row_projection = cmds.createNode("rowFromMatrix", name=f"{local_side}_mouthSlidingProjection_ROW", ss=True)
                    cmds.connectAttr(local, f"{row_projection}.matrix")
                    cmds.setAttr(f"{row_projection}.input", 3)
                    closes_point_on_surface = cmds.createNode("closestPointOnSurface", name=f"{local_side}_mouthSlidingProjection_CPOS", ss=True)
                    cmds.connectAttr(f"{mouth_sliding_shape}.worldSpace[0]", f"{closes_point_on_surface}.inputSurface")
                    cmds.connectAttr(f"{row_projection}.outputX", f"{closes_point_on_surface}.inPositionX")
                    cmds.connectAttr(f"{row_projection}.outputY", f"{closes_point_on_surface}.inPositionY")
                    cmds.connectAttr(f"{row_projection}.outputZ", f"{closes_point_on_surface}.inPositionZ")
                    joint = cmds.createNode("joint", name=f"{local_side}_lipCorner_JNT", ss=True, parent=self.module_trn)
                    cmds.connectAttr(f"{closes_point_on_surface}.position", f"{joint}.translate")
                    self.corner_projected_joints.append(joint)


            main_mid_name = "upper" if "upper" in curve else "lower"
            jaw_controller = self.jaw_ctl if "lower" in curve else self.upper_jaw_ctl

            self.main_mid_ctl, self.main_mid_ctl_grp = controller_creator(
                    name=f"C_{main_mid_name}Lip",
                    suffixes=["GRP", "OFF", "ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn,
                )
            last_cv = int((len(cmds.ls(f"{curve}.cv[*]", flatten=True))-1)//2)
            mid_pos_4b4 = cmds.createNode("fourByFourMatrix", name=f"C_{main_mid_name}MidLip_4B4", ss=True)
            cmds.connectAttr(f"{curve}.editPoints[{last_cv}].xValueEp", f"{mid_pos_4b4}.in30")
            cmds.connectAttr(f"{curve}.editPoints[{last_cv}].yValueEp", f"{mid_pos_4b4}.in31")
            cmds.connectAttr(f"{curve}.editPoints[{last_cv}].zValueEp", f"{mid_pos_4b4}.in32")

            parent_matrix_mid = cmds.createNode("parentMatrix", name=f"C_{main_mid_name}Lip_PMX", ss=True)
            cmds.connectAttr(f"{mid_pos_4b4}.output", f"{parent_matrix_mid}.inputMatrix")
            cmds.connectAttr(f"{jaw_controller}.worldMatrix[0]", f"{parent_matrix_mid}.target[0].targetMatrix")
            jaw_offset_r = self.get_offset_matrix(cmds.getAttr(f"{mid_pos_4b4}.output"), jaw_controller, matrix=True)
            cmds.setAttr(f"{parent_matrix_mid}.target[0].offsetMatrix", jaw_offset_r, type="matrix")

            jaw_offset_child = cmds.createNode("multMatrix", name=f"C_{main_mid_name}Lip_MMX", ss=True)
            cmds.connectAttr(f"{parent_matrix_mid}.outputMatrix", f"{jaw_offset_child}.matrixIn[0]")
            cmds.connectAttr(f"{self.main_mid_ctl_grp[0]}.worldInverseMatrix[0]", f"{jaw_offset_child}.matrixIn[1]")

            cmds.connectAttr(f"{jaw_offset_child}.matrixSum", f"{self.main_mid_ctl_grp[1]}.offsetParentMatrix", f=True)

            cmds.connectAttr(f"{mid_pos_4b4}.output", f"{self.main_mid_ctl_grp[0]}.offsetParentMatrix")

            self.mid_local = self.local_setup(ctl = self.main_mid_ctl, grp = self.main_mid_ctl_grp[0])
            
            mid_local_joint = cmds.createNode("joint", name=f"C_{main_mid_name}Lip_JNT", ss=True, parent=self.module_trn)
            cmds.connectAttr(self.mid_local, f"{mid_local_joint}.offsetParentMatrix")

            joint_list = [self.corner_projected_joints[0], self.corner_projected_joints[1] , mid_local_joint]

            rebuilded_skinned_curve = cmds.skinCluster(
                joint_list,
                rebuilded_curve,
                toSelectedBones=True,
                bindMethod=0,
                normalizeWeights=1,
                weightDistribution=0,
                maximumInfluences=2,
                dropoffRate=4,
                removeUnusedInfluence=False
            )[0]

            cv_names = cmds.ls(f"{rebuilded_curve}.cv[*]", flatten=True)

            cmds.skinPercent(rebuilded_skinned_curve, cv_names[0], transformValue=[(self.corner_projected_joints[0], 1)])
            cmds.skinPercent(rebuilded_skinned_curve, cv_names[-1], transformValue=[(self.corner_projected_joints[1], 1)])

            mid_index = int(len(cv_names) // 2)
            cmds.skinPercent(rebuilded_skinned_curve, cv_names[mid_index], transformValue=[(mid_local_joint, 1)])

            cmds.skinPercent(rebuilded_skinned_curve, cv_names[1], transformValue=[(self.corner_projected_joints[0], 0.5), (mid_local_joint, 0.5)])
            cmds.skinPercent(rebuilded_skinned_curve, cv_names[-2], transformValue=[(self.corner_projected_joints[1], 0.5), (mid_local_joint, 0.5)])

            cmds.skinPercent(rebuilded_skinned_curve, cv_names[2], transformValue=[(self.corner_projected_joints[0], 0.2), (mid_local_joint, 0.8)])
            cmds.skinPercent(rebuilded_skinned_curve, cv_names[-3], transformValue=[(self.corner_projected_joints[1], 0.2), (mid_local_joint, 0.8)])

            bezierCurve = cmds.duplicate(rebuilded_curve, name=rebuilded_curve.replace("Rebuild", "Bezier"), renameChildren=True)[0]
            cmds.select(bezierCurve, r=True)
            cmds.nurbsCurveToBezier()
            cmds.select(clear=True)

            rebuilded_curve_shape = cmds.listRelatives(rebuilded_curve, shapes=True)[0]

            path_joints = []
            ctls = []
            clts_grps = []

            for i, cv in enumerate(cmds.ls(f"{bezierCurve}.cv[*]", flatten=True)):
                if i % 3 == 0:
                    name = "secondary"
                else:
                    name = "secondaryTan"
                position = cmds.xform(cv, q=True, ws=True, t=True)
                parameter = self.getClosestParamToPosition(rebuilded_curve, position)

                cv_side = "C" if position[0] == 0 else ("R" if position[0] < 0 else "L")

                motionPath = cmds.createNode("motionPath", n=f"{cv_side}_{name}{main_mid_name.capitalize()}0{i}_MPA", ss=True)
                joint = cmds.createNode("joint", n=f"{cv_side}_{name}{main_mid_name.capitalize()}0{i}_JNT", ss=True, p=self.module_trn)
                fourByFourMatrix = cmds.createNode("fourByFourMatrix", n=f"{cv_side}_{name}{main_mid_name.capitalize()}0{i}_4B4", ss=True)

                ctl, ctl_grp = controller_creator(
                    name=f"{cv_side}_{name}{main_mid_name.capitalize()}0{i}",
                    suffixes=["GRP", "OFF", "ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn,
                )

                cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{joint}.offsetParentMatrix")

                if i % 3 == 0:
                    print(ctl)
                    cmds.addAttr(ctl, shortName="extraSep", niceName="EXTRA ATTRIBUTES ———", enumName="———",attributeType="enum", keyable=True)
                    cmds.setAttr(ctl+".extraSep", channelBox=True, lock=True)
                    cmds.addAttr(ctl, shortName="tangentVisibility", niceName="Tangent Visibility", attributeType="bool", keyable=False)
                    cmds.setAttr(f"{ctl}.tangentVisibility", keyable=False, channelBox=True)



                ctls.append(ctl)
                clts_grps.append(ctl_grp)
                
                cmds.connectAttr(f"{rebuilded_curve_shape}.worldSpace[0]", f"{motionPath}.geometryPath", f=True)
                
                cmds.setAttr(f"{motionPath}.uValue", parameter)
                
                cmds.connectAttr(f"{motionPath}.allCoordinates.xCoordinate", f"{fourByFourMatrix}.in30", f=True)
                cmds.connectAttr(f"{motionPath}.allCoordinates.yCoordinate", f"{fourByFourMatrix}.in31", f=True)
                cmds.connectAttr(f"{motionPath}.allCoordinates.zCoordinate", f"{fourByFourMatrix}.in32", f=True)
                if cv_side == "R":
                    cmds.setAttr(f"{fourByFourMatrix}.in00", -1)

                cmds.connectAttr(f"{fourByFourMatrix}.output", f"{ctl_grp[0]}.offsetParentMatrix", f=True)
                
                path_joints.append(joint)

            for i, joint in enumerate(path_joints):
                if "Tan" in joint:
                    closest_main_joint_index = None
                    for jnt in path_joints:
                        if not "Tan" in jnt:
                            if closest_main_joint_index is None or abs(path_joints.index(jnt) - path_joints.index(joint)) < abs(closest_main_joint_index - path_joints.index(joint)):
                                closest_main_joint_index = path_joints.index(jnt)
                                    
                    offset_input = cmds.listConnections(f"{clts_grps[i][0]}.offsetParentMatrix", s=True, d=False, plugs=True)[0]
                    multMatrix = cmds.createNode("multMatrix", name=joint.replace("_JNT", "Parent_MMX"), ss=True)
                    cmds.connectAttr(offset_input, f"{multMatrix}.matrixIn[1]")
                    cmds.connectAttr(f"{ctls[closest_main_joint_index]}.matrix", f"{multMatrix}.matrixIn[0]")

                    cmds.connectAttr(f"{multMatrix}.matrixSum", f"{clts_grps[i][0]}.offsetParentMatrix", f=True)

                    cmds.connectAttr(f"{ctls[closest_main_joint_index]}.tangentVisibility", f"{clts_grps[i][0]}.visibility", f=True)


            bezier_skinned_curve = cmds.skinCluster(
                path_joints,
                bezierCurve,
                toSelectedBones=True,
                bindMethod=0,
                normalizeWeights=1,
                weightDistribution=0,
                maximumInfluences=1,
                dropoffRate=4,
                removeUnusedInfluence=False
            )[0]

            bezier_shape = cmds.listRelatives(bezierCurve, shapes=True, type="bezierCurve")[0]

            for i, cv in enumerate(cmds.ls(f"{curve}.cv[*]", flatten=True)):
                cv_pos = cmds.xform(cv, q=True, ws=True, t=True)
                parameter = self.getClosestParamToPosition(bezierCurve, cv_pos)


                motionPath = cmds.createNode("motionPath", n=f"{cv_side}_{name}{main_mid_name.capitalize()}0{i}_MPA", ss=True)
                fourByFourMatrix = cmds.createNode("fourByFourMatrix", n=f"{cv_side}_{name}{main_mid_name.capitalize()}0{i}_4B4", ss=True)

                cmds.connectAttr(f"{bezier_shape}.worldSpace[0]", f"{motionPath}.geometryPath", f=True)
                
                cmds.setAttr(f"{motionPath}.uValue", parameter)
                
                cmds.connectAttr(f"{motionPath}.allCoordinates.xCoordinate", f"{fourByFourMatrix}.in30", f=True)
                cmds.connectAttr(f"{motionPath}.allCoordinates.yCoordinate", f"{fourByFourMatrix}.in31", f=True)
                cmds.connectAttr(f"{motionPath}.allCoordinates.zCoordinate", f"{fourByFourMatrix}.in32", f=True)
                if cv_side == "R":
                    cmds.setAttr(f"{fourByFourMatrix}.in00", -1)

                fourOrigPos = cmds.createNode("fourByFourMatrix", name=f"{cv_side}_{name}{main_mid_name.capitalize()}0{i}Orig_4B4", ss=True)
                parent_matrix = cmds.createNode("parentMatrix", name=f"{cv_side}_{name}{main_mid_name.capitalize()}0{i}_PMX", ss=True)
                cmds.connectAttr(f"{curve}Shape.editPoints[{i}].xValueEp", f"{fourOrigPos}.in30", f=True)
                cmds.connectAttr(f"{curve}Shape.editPoints[{i}].yValueEp", f"{fourOrigPos}.in31", f=True)
                cmds.connectAttr(f"{curve}Shape.editPoints[{i}].zValueEp", f"{fourOrigPos}.in32", f=True)

                cmds.connectAttr(f"{fourByFourMatrix}.output", f"{parent_matrix}.target[0].targetMatrix", f=True)
                cmds.connectAttr(f"{fourOrigPos}.output", f"{parent_matrix}.inputMatrix", f=True)
                joint = cmds.createNode("joint", n=f"{cv_side}_{name}{main_mid_name.capitalize()}0{i}Skinning_JNT", ss=True, parent = self.skinning_trn)
                cmds.connectAttr(f"{fourByFourMatrix}.output", f"{joint}.offsetParentMatrix", f=True)

                cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", self.get_offset_matrix(cmds.getAttr(f"{fourOrigPos}.output"), joint, matrix=True), type="matrix")




                cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{joint}.offsetParentMatrix", f=True)




        

        


cmds.file(new=True, force=True)

core.DataManager.set_guide_data(r"D:\git\maya\puiastre_tools\guides\AYCHEDRAL_002.guides")
core.DataManager.set_ctls_data(r"D:\git\maya\puiastre_tools\curves\AYCHEDRAL_curves_001.json")

basic_structure.create_basic_structure(asset_name="elephant_04")
a = JawModule().make("C_jaw_GUIDE")