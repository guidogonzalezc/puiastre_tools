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
from puiastreTools.utils import de_boor_core_002
from puiastreTools.utils.space_switch import fk_switch

reload(data_export)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}

class EyeModule():
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

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_eyeModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_eyeControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.tangent_controllers_trn = cmds.createNode("transform", name=f"{self.side}_eyeTangentControllers_GRP", ss=True, parent=self.controllers_trn)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_eyeSkinning_GRP", ss=True, p=self.skel_grp)

        self.create_chain()

    #     self.data_exporter.append_data(f"{self.side}_eyeModule", 
    #                                 {"skinning_transform": self.skinning_trn,
    #                                 # "neck_ctl": self.main_controllers[0],

    #                                 }
    #                               )
        

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

    def getClosestParamToWorldMatrix(self, curve, pos, point=False):
        """
        Returns the closest parameter (u) on the curve to the given worldMatrix.
        """
        selection_list = om.MSelectionList()
        selection_list.add(curve)
        curve_dag_path = selection_list.getDagPath(0)

        curveFn = om.MFnNurbsCurve(curve_dag_path)

        point_pos = om.MPoint(*pos)
        closestPoint, paramU = curveFn.closestPoint(point_pos, space=om.MSpace.kWorld)

        if point:
            return closestPoint

        return paramU

    def local_mmx(self, ctl, grp):
        name = ctl.replace("_CTL", "")

        multmatrix = cmds.createNode("multMatrix", name=f"{name}local_MMX", ss=True)
        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{multmatrix}.matrixIn[0]", force=True)
        cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
        cmds.setAttr(f"{multmatrix}.matrixIn[2]", cmds.getAttr(f"{ctl}.worldMatrix[0]"), type="matrix")

        return f"{multmatrix}.matrixSum"
    
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

    def local_space_parent(self, ctl, parents=[], default_weights=0.5):

        name = ctl.replace("_CTL", "")

        parentMatrix = cmds.createNode("parentMatrix", name=f"{name}localSpaceParent_PMX", ss=True)

        grp = ctl.replace("_CTL", "_GRP")
        off = ctl.replace("_CTL", "_OFF")

        cmds.connectAttr(f"{grp}.worldMatrix[0]", f"{parentMatrix}.inputMatrix", force=True)
        cmds.connectAttr(f"{parents[0]}.worldMatrix[0]", f"{parentMatrix}.target[1].targetMatrix", force=True)
        cmds.connectAttr(f"{parents[1]}.worldMatrix[0]", f"{parentMatrix}.target[0].targetMatrix", force=True)
        cmds.setAttr(f"{parentMatrix}.target[1].offsetMatrix", self.get_offset_matrix(grp, parents[0]), type="matrix")
        cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", self.get_offset_matrix(grp, parents[1]), type="matrix")

        multmatrix = cmds.createNode("multMatrix", name=f"{name}localSpaceParent_MMX", ss=True)
        cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{multmatrix}.matrixIn[0]", force=True)
        cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
        cmds.connectAttr(f"{multmatrix}.matrixSum", f"{off}.offsetParentMatrix", force=True)

        cmds.addAttr(ctl, longName="SpaceSwitchSep", niceName = "Space Switches  ———", attributeType="enum", enumName="———", keyable=True)
        cmds.setAttr(f"{ctl}.SpaceSwitchSep", channelBox=True, lock=True)   

        cmds.addAttr(ctl, longName="SpaceFollow", attributeType="float", min=0, max=1, defaultValue=default_weights, keyable=True)
        cmds.connectAttr(f"{ctl}.SpaceFollow", f"{parentMatrix}.target[0].weight", force=True)
        rev = cmds.createNode("reverse", name=f"{name}localSpaceParent_REV", ss=True)
        cmds.connectAttr(f"{ctl}.SpaceFollow", f"{rev}.inputX", force=True)
        cmds.connectAttr(f"{rev}.outputX", f"{parentMatrix}.target[1].weight", force=True)

        return multmatrix

    def eye_rotation_4b4(self, four_by_four):
        reshaped_matrix = [self.eyelid_rotation_matrix[i:i+4] for i in range(0, len(self.eyelid_rotation_matrix), 4)]
        for row in range(4):
            for col in range(4):
                cmds.setAttr(f"{four_by_four}.in{row}{col}", reshaped_matrix[row][col])

    def create_chain(self):
        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        self.curve_guides = []
        self.guides_transforms = []
        for guides in self.guides:
            shape = cmds.listRelatives(guides, shapes=True)[0] if cmds.listRelatives(guides, shapes=True) else None
            if shape and cmds.objectType(shape) == "nurbsCurve":
                self.curve_guides.append(guides)
            else:
                self.guides_transforms.append(guides)

        self.eyelid_rotation = cmds.createNode("aimMatrix", name=f"{self.side}_eyelidRotation_AMX", ss=True)

        

        self.eye_direct_ctl, eye_direct_grp = controller_creator(
                    name=f"{self.side}_eyeDirect",
                    suffixes=["GRP", "ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn
                )

        cmds.connectAttr(f"{self.guides_transforms[0]}.worldMatrix[0]", f"{self.eyelid_rotation}.inputMatrix", force=True)
        cmds.connectAttr(f"{self.guides_transforms[1]}.worldMatrix[0]", f"{self.eyelid_rotation}.primaryTargetMatrix", force=True)
        # cmds.connectAttr(f"{}.worldMatrix[0]", f"{self.eyelid_rotation}.secondaryTargetMatrix", force=True)
        cmds.setAttr(f"{self.eyelid_rotation}.primaryInputAxis", *self.primary_aim_vector, type="double3")
        cmds.setAttr(f"{self.eyelid_rotation}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{self.eyelid_rotation}.secondaryTargetVector", 0, 0, 1, type="double3")
        cmds.setAttr(f"{self.eyelid_rotation}.secondaryMode", 2)

        if self.side == "R":

            multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_eyelidRotation_MMX", ss=True)
            cmds.setAttr(f"{multmatrix}.matrixIn[0]", 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1, type="matrix")
            cmds.connectAttr(f"{self.eyelid_rotation}.outputMatrix", f"{multmatrix}.matrixIn[1]", force=True)
            
            self.eyelid_rotation_matrix = cmds.getAttr(f"{multmatrix}.matrixSum")


            cmds.connectAttr(f"{multmatrix}.matrixSum", f"{eye_direct_grp[0]}.offsetParentMatrix", force=True)

        else:
            self.eyelid_rotation_matrix = cmds.getAttr(f"{self.eyelid_rotation}.outputMatrix")
            cmds.connectAttr(f"{self.eyelid_rotation}.outputMatrix", f"{eye_direct_grp[0]}.offsetParentMatrix", force=True)

        # cmds.delete(self.eyelid_rotation)


        cmds.addAttr(self.eye_direct_ctl, shortName="extraSep", niceName="EXTRA_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.eye_direct_ctl+".extraSep", channelBox=True, lock=True)
        cmds.addAttr(self.eye_direct_ctl, shortName="blinkHeight", niceName="Blink Height",minValue=0,defaultValue=0.2, maxValue = 1, keyable=True)
        cmds.addAttr(self.eye_direct_ctl, shortName="upperBlink", niceName="Upper Blink",minValue=-1,defaultValue=0, maxValue = 1, keyable=True)
        cmds.addAttr(self.eye_direct_ctl, shortName="lowerBlink", niceName="Lower Blink",minValue=-1,defaultValue=0, maxValue = 1, keyable=True)
        cmds.addAttr(self.eye_direct_ctl, shortName="fleshy", niceName="Fleshy",minValue=0,defaultValue=0.1, maxValue = 1, keyable=True)
        cmds.addAttr(self.eye_direct_ctl, shortName="fleshyCorners", niceName="Fleshy Corners",minValue=0,defaultValue=0, maxValue = 1, keyable=True)

        four_by_fours_in_out = []
        blend_matrix_in_out = []
        self.main_ctls = []
        self.main_ctls_grps = []
        for name, item in zip(["Inner", "Outer"], [0, len(cmds.ls(f"{self.curve_guides[0]}.cv[*]", fl=True)) - 1]):

            four_by_four = cmds.createNode("fourByFourMatrix", name=f"{self.side}_eyelid{name}Pos_F4X", ss=True)
            self.eye_rotation_4b4(four_by_four)
            cmds.setAttr(f"{four_by_four}.in30", cmds.pointPosition(f"{self.curve_guides[0]}.cv[{item}]")[0])
            cmds.setAttr(f"{four_by_four}.in31", cmds.pointPosition(f"{self.curve_guides[0]}.cv[{item}]")[1])
            cmds.setAttr(f"{four_by_four}.in32", cmds.pointPosition(f"{self.curve_guides[0]}.cv[{item}]")[2])
            four_by_fours_in_out.append(four_by_four)

            ctl, controller_grp = controller_creator(
                name=f"{self.side}_{name}EyelidCorner",
                suffixes=["GRP", "OFF", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn
            )
            self.main_ctls.append(ctl)
            self.main_ctls_grps.append(controller_grp)

            cmds.connectAttr(f"{four_by_four}.output", f"{controller_grp[0]}.offsetParentMatrix", force=True)

        # cmds.connectAttr(f"{four_by_fours_in_out[0]}.output", f"{self.eyelid_rotation}.inputMatrix", force=True)
        # cmds.connectAttr(f"{four_by_fours_in_out[1]}.output", f"{self.eyelid_rotation}.primaryTargetMatrix", force=True)
        # cmds.connectAttr(f"{self.guides_transforms[0]}.worldMatrix[0]", f"{self.eyelid_rotation}.secondaryTargetMatrix", force=True)
        # cmds.setAttr(f"{self.eyelid_rotation}.primaryInputAxis", 0, 0, -1, type="double3")
        # cmds.setAttr(f"{self.eyelid_rotation}.secondaryInputAxis", -1, 0, 0, type="double3")
        # cmds.setAttr(f"{self.eyelid_rotation}.secondaryTargetVector", 0, 0, 1, type="double3")
        
        # self.eyelid_rotation_matrix = cmds.getAttr(f"{self.eyelid_rotation}.outputMatrix")

        corner_joints = []
        for ctl, grp in zip(self.main_ctls, self.main_ctls_grps):
            curve_skinning_joint = cmds.createNode("joint", name=ctl.replace("_CTL", "_JNT"), ss=True, p=self.module_trn)

            local_mmx = self.local_mmx(ctl, grp[0])

            cmds.connectAttr(f"{local_mmx}", f"{curve_skinning_joint}.offsetParentMatrix", force=True)
            corner_joints.append(curve_skinning_joint)

        rebuilded_curves = []

        for curve in self.curve_guides:
            rebuild_curve = cmds.rebuildCurve(curve, name=curve.replace("Curve_GUIDE", "_CRV") ,ch=False, rpo=False, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=4, d=3)[0]
            cmds.parent(rebuild_curve, self.module_trn)
            rebuilded_curves.append(rebuild_curve)

        blink_ref = cmds.duplicate(rebuilded_curves[0], n=f"{self.side}_blinkRef_CRV") # Tabula esto para Oswald

        blink_ref_bls = cmds.blendShape(rebuilded_curves[1], blink_ref, n=f"{self.side}_blinkHeight_BLS")[0]

        cmds.connectAttr(self.eye_direct_ctl+".blinkHeight", f"{blink_ref_bls}.weight[0]")

        negative_curves = []
        for i, curve in enumerate(rebuilded_curves):
            negative_blink_curve = cmds.duplicate(curve, n=curve.replace("_CRV", f"NegativeBlinkRef_CRV"))
            value = 0 if i != 0 else 1
            bls_tmp = cmds.blendShape(rebuilded_curves[value], negative_blink_curve, n=curve.replace("_CRV", f"NegativeBlinkRef_BLS"))[0]
            cmds.setAttr(f"{bls_tmp}.weight[0]", -1)
            cmds.delete(negative_blink_curve, constructionHistory=True)
            negative_curves.append(negative_blink_curve)

        blink_end_curves = []
        bls_name = []

        for i, curves in enumerate(rebuilded_curves):
            name = curves.replace("_CRV", f"Blink")
            blink_curve = cmds.duplicate(curves, n=curves.replace("_CRV", f"Blink_CRV"))[0]

            blink_bls = cmds.blendShape(blink_ref, curves, negative_curves[i], blink_curve, n=f"{name}_BLS")[0]

            attr = "upperBlink" if "upper" in curves.lower() else "lowerBlink"

            clamp = cmds.createNode("clamp", n=f"{name}_CLP")
            rev = cmds.createNode("reverse", n=f"{name}_REV")
            flm = cmds.createNode("floatMath", n=f"{name}_FLM")
            cmds.connectAttr(f"{self.eye_direct_ctl}.{attr}", clamp+".inputR")
            cmds.connectAttr(f"{self.eye_direct_ctl}.{attr}", clamp+".inputG")
            cmds.setAttr(clamp+".minG", -1)
            cmds.setAttr(clamp+".maxR", 1)
            cmds.connectAttr(clamp+".outputR", f"{blink_bls}.weight[0]")
            cmds.connectAttr(clamp+".outputR", f"{rev}.inputX")
            cmds.connectAttr(rev+".outputX", f"{blink_bls}.weight[1]")
            cmds.connectAttr(clamp+".outputG", f"{flm}.floatA")
            cmds.setAttr(flm+".operation", 2)
            cmds.setAttr(flm+".floatB", -1)
            cmds.connectAttr(flm+".outFloat", f"{blink_bls}.weight[2]")

            blink_end_curves.append(blink_curve)
            bls_name.append(blink_bls)

        for index_main, curve in enumerate(rebuilded_curves):
         
            four_by_four_mid = cmds.createNode("fourByFourMatrix", name=curve.replace("_CRV", f"Middle_F4X"), ss=True)

            pos = self.getClosestParamToWorldMatrix(curve = curve, pos = cmds.pointPosition(f"{curve}.cv[{3}]"), point=True)

            self.eye_rotation_4b4(four_by_four_mid)

            cmds.setAttr(f"{four_by_four_mid}.in30", pos[0])
            cmds.setAttr(f"{four_by_four_mid}.in31", pos[1])
            cmds.setAttr(f"{four_by_four_mid}.in32", pos[2])

            mid_ctl, mid_controller_grp = controller_creator(
                    name=f"{curve.replace('_CRV', 'Mid')}",
                    suffixes=["GRP", "OFF","ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn
                )
            cmds.connectAttr(f"{four_by_four_mid}.output", f"{mid_controller_grp[0]}.offsetParentMatrix", force=True)
           
            joint_skinning_joints = []

            for i, cv_index in enumerate([2, 3, 4]): # 3 6 9
                ctl, controller_grp = controller_creator(
                    name=f"{curve.replace('_CRV', f'Secondary0{i+1}')}",
                    suffixes=["GRP", "OFF","ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn
                )

                four_by_four_mid = cmds.createNode("fourByFourMatrix", name=curve.replace("_CRV", f"Middle_F4X"), ss=True)

                pos = self.getClosestParamToWorldMatrix(curve = curve, pos = cmds.pointPosition(f"{curve}.cv[{cv_index}]"), point=True)

                self.eye_rotation_4b4(four_by_four_mid)

                cmds.setAttr(f"{four_by_four_mid}.in30", pos[0])
                cmds.setAttr(f"{four_by_four_mid}.in31", pos[1])
                cmds.setAttr(f"{four_by_four_mid}.in32", pos[2])

                cmds.connectAttr(f"{four_by_four_mid}.output", f"{controller_grp[0]}.offsetParentMatrix", force=True)

                if cv_index == 2: # 3
                    multmatrix = self.local_space_parent(ctl, parents=[self.main_ctls[0], mid_ctl], default_weights=0.8)
                elif cv_index == 4: # 9
                    multmatrix = self.local_space_parent(ctl, parents=[self.main_ctls[1], mid_ctl], default_weights=0.8)
                else:
                    multmatrix = cmds.createNode("multMatrix", name=f"{curve.replace('_CRV', f'Secondary0{i+1}')}localSpaceParent_MMX", ss=True)
                    cmds.connectAttr(f"{mid_ctl}.worldMatrix[0]", f"{multmatrix}.matrixIn[0]", force=True)
                    cmds.connectAttr(f"{controller_grp[0]}.worldInverseMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
                    cmds.connectAttr(f"{multmatrix}.matrixSum", f"{controller_grp[1]}.offsetParentMatrix", force=True)

                curve_skinning_joint = cmds.createNode("joint", name=ctl.replace("_CTL", f"CurveSkinning_JNT"), ss=True, parent=self.module_trn)

                local_mmx = self.local_mmx(ctl, controller_grp[0])

                cmds.connectAttr(f"{local_mmx}", f"{curve_skinning_joint}.offsetParentMatrix", force=True)

                joint_skinning_joints.append(curve_skinning_joint)

                if i == 2:
                    skinCluster = cmds.skinCluster(joint_skinning_joints, corner_joints, curve, n=curve.replace("_CRV", "_SKC"), toSelectedBones=True, maximumInfluences=1, normalizeWeights=1)[0]

            for i, cv in enumerate(cmds.ls(f"{self.curve_guides[index_main]}.cv[*]", fl=True)):
                name = f"{cv.split('.')[0].replace('Curve_GUIDE', 'Aim')}0{i+1}"
                pick = self.curve_attachment(name=name, curve_shape=blink_end_curves[index_main], u_value=self.getClosestParamToWorldMatrix(curve=blink_end_curves[index_main], pos=cmds.pointPosition(cv)))
                aim_matrix = cmds.createNode("aimMatrix", name=f"{name}_AMX", ss=True)
                cmds.connectAttr(f"{self.guides_transforms[0]}.worldMatrix[0]", f"{aim_matrix}.inputMatrix", force=True)
                cmds.connectAttr(f"{pick}.outputMatrix", f"{aim_matrix}.primaryTargetMatrix", force=True)
                cmds.setAttr(f"{aim_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")
                cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")

                value = (0, 0, 1) if self.side == "L" else (0, 0, -1)

                cmds.setAttr(f"{aim_matrix}.secondaryTargetVector", *value, type="double3")
                cmds.setAttr(f"{aim_matrix}.secondaryMode", 2)

                multmatrix = cmds.createNode("multMatrix", name=f"{name}_MMX", ss=True)
                cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{multmatrix}.matrixIn[1]", force=True)

                fourbyfour = cmds.createNode("fourByFourMatrix", name=f"{name}_F4X", ss=True)
                dist = (om.MVector(*cmds.xform(self.guides_transforms[0], q=1, ws=1, t=1)) - om.MVector(*cmds.xform(self.guides_transforms[1], q=1, ws=1, t=1))).length()
                cmds.setAttr(f"{fourbyfour}.in32", dist if self.side == "L" else -dist)
                cmds.connectAttr(f"{fourbyfour}.output", f"{multmatrix}.matrixIn[0]", force=True)

                joint = cmds.createNode("joint", name=f"{name}_JNT", ss=True, parent=self.skinning_trn)

                cmds.connectAttr(f"{multmatrix}.matrixSum", f"{joint}.offsetParentMatrix", force=True)
