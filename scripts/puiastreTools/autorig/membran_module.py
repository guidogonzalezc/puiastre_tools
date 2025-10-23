#Python libraries import
from unicodedata import name
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

class MembraneModule(object):

    def __init__(self):
        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")
        self.muscle_locators = self.data_exporter.get_data("basic_structure", "muscleLocators_GRP")
    
    def number_to_ordinal_word(self, n):
        base_ordinal = {
            1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth',
            6: 'sixth', 7: 'seventh', 8: 'eighth', 9: 'ninth', 10: 'tenth',
            11: 'eleventh', 12: 'twelfth', 13: 'thirteenth', 14: 'fourteenth',
            15: 'fifteenth', 16: 'sixteenth', 17: 'seventeenth', 18: 'eighteenth',
            19: 'nineteenth'
        }
        tens = {
            20: 'twentieth', 30: 'thirtieth', 40: 'fortieth',
            50: 'fiftieth', 60: 'sixtieth', 70: 'seventieth',
            80: 'eightieth', 90: 'ninetieth'
        }
        tens_prefix = {
            20: 'twenty', 30: 'thirty', 40: 'forty', 50: 'fifty',
            60: 'sixty', 70: 'seventy', 80: 'eighty', 90: 'ninety'
        }
        if n <= 19:
            return base_ordinal[n]
        elif n in tens:
            return tens[n]
        elif n < 100:
            ten = (n // 10) * 10
            unit = n % 10
            return tens_prefix[ten] + "-" + base_ordinal[unit]
        else:
            return str(n)

    def make(self, guide_name):

        """
        Create a limb rig with controllers and constraints.
        This function sets up the basic structure for a limb, including controllers and constraints.
        """      
        self.side = guide_name.split("_")[0]

        if self.side == "L":
            self.primary_aim = "x"
            self.secondary_aim = "y"
        
        elif self.side == "R":
            self.primary_aim = "-x"
            self.secondary_aim = "y"

        self.individual_module_grp = cmds.createNode("transform", name=f"{self.side}_membraneModule_GRP", parent=self.modules_grp, ss=True)
        self.individual_controllers_grp = cmds.createNode("transform", name=f"{self.side}_membraneControllers_GRP", parent=self.masterWalk_ctl, ss=True)
        self.skinnging_grp = cmds.createNode("transform", name=f"{self.side}_membraneSkinningJoints_GRP", parent=self.skel_grp, ss=True)
        cmds.setAttr(f"{self.individual_controllers_grp}.inheritsTransform", 0)
        
        self.primary_aim_vector = om.MVector(AXIS_VECTOR[self.primary_aim])
        self.secondary_aim_vector = om.MVector(AXIS_VECTOR[self.secondary_aim])

        self.guides = guide_import(guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]

        cmds.addAttr(self.skinnging_grp, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        # self.secondary_membranes()

        self.main_membrane()


        self.data_exporter.append_data(
            f"{self.side}_membraneModule",
            {
                "skinning_transform": self.skinnging_grp,
            }
        )

    def get_closest_transform(self, main_transform, transform_list):
        """
        Returns the transform from transform_list that is closest to main_transform.
        
        Args:
            main_transform (str): Name of the main transform.
            transform_list (list): List of transform names to compare.

        Returns:
            str: Name of the closest transform.
        """
        main_pos = om.MVector(main_transform)
        
        closest_obj = None
        closest_dist = float('inf')
        
        for t in transform_list:
            if not cmds.objExists(t):
                continue
            
            pos = om.MVector(cmds.xform(t, q=True, ws=True, t=True))
            dist = (pos - main_pos).length()
            
            if dist < closest_dist:
                closest_dist = dist
                closest_obj = t

        return closest_obj


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

    def main_membrane(self):
        data_exporter = data_export.DataExport()

        spine_joints = cmds.listRelatives(data_exporter.get_data("C_spineModule", "skinning_transform"), allDescendents=True, type="joint")
        tail_joints = cmds.listRelatives(data_exporter.get_data("C_tailModule", "skinning_transform"), allDescendents=True, type="joint")
        arm_joints = cmds.listRelatives(data_exporter.get_data(f"{self.side}_armModule", "skinning_transform"), allDescendents=True, type="joint")
        membran_joints = cmds.listRelatives(data_exporter.get_data(f"{self.side}_firstMetacarpalModule", "skinning_transform"), allDescendents=True, type="joint")

        ctls = []

        shapes = cmds.listRelatives(self.guides[0], shapes=True, noIntermediate=True) or []
        guide_shape = shapes[0] if shapes else self.guides[0]
        main_controller_guide_pos = cmds.pointPosition(f"{guide_shape}.cv[1][3]", world=True)
        main_controller_guide = cmds.createNode("transform", name=f"{self.side}_MainMembrane_GUIDE", parent=self.guides_grp, ss=True)
        cmds.xform(main_controller_guide, ws=True, t=main_controller_guide_pos)

        main_controller, main_controller_grp = controller_creator(
            name=f"{self.side}_MainMembrane",
            suffixes=["GRP", "ANM"],
            lock=["scaleX", "scaleY", "scaleZ", "visibility"],
            ro=True,
            parent=self.individual_controllers_grp
        )

        first_row_closest = [arm_joints[1]]

        for i in range(1, 4):

            closest_pos = cmds.pointPosition(f"{guide_shape}.cv[0][{i}]", world=True)
            search_list = spine_joints
            search_list.extend(tail_joints)

            closest_transform = self.get_closest_transform(closest_pos, search_list)
            first_row_closest.append(closest_transform)


        parentMatrix = cmds.createNode("parentMatrix", name=f"{self.side}_MainMembrane_PM", ss=True)
        cmds.connectAttr(f"{main_controller_guide}.worldMatrix[0]", f"{parentMatrix}.inputMatrix")
        cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{main_controller_grp[0]}.offsetParentMatrix")

        temp_transform = cmds.createNode("transform", name=f"{self.side}_MainMembrane_TEMP", ss=True)
        for i, joint in enumerate([membran_joints[-1], first_row_closest[-1]]):

            pickMatrix = cmds.createNode("pickMatrix", name=f"{self.side}_MainMembraneNoRotation0{i}_PMX", ss=True)

            cmds.connectAttr(f"{pickMatrix}.outputMatrix", f"{parentMatrix}.target[{i}].targetMatrix")
            cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{pickMatrix}.inputMatrix")
            cmds.setAttr(f"{pickMatrix}.useRotate", 0)

            cmds.connectAttr(f"{pickMatrix}.outputMatrix", f"{temp_transform}.offsetParentMatrix", f=True)
            offset_masterwalk = self.get_offset_matrix(main_controller_guide, temp_transform)
            cmds.setAttr(f"{parentMatrix}.target[{i}].offsetMatrix", offset_masterwalk, type="matrix")


        main_joint = cmds.createNode("joint", name=f"{self.side}_MainMembrane_JNT", ss=True, parent=self.modules_grp)
        cmds.connectAttr(f"{main_controller}.worldMatrix[0]", f"{main_joint}.offsetParentMatrix")

        third_row_closest = [arm_joints[-1]]

        for i in range(1, 4):

            closest_pos = cmds.pointPosition(f"{guide_shape}.cv[2][{i}]", world=True)
            search_list = membran_joints

            closest_transform = self.get_closest_transform(closest_pos, search_list)
            third_row_closest.append(closest_transform)

        skinning_list = first_row_closest
        skinning_list.extend(third_row_closest)
        skinning_list.append(arm_joints[6])
        skinning_list.append(main_joint)

        nurbs_skincluster = cmds.skinCluster(skinning_list, self.guides[0], toSelectedBones=True, maximumInfluences=1, normalizeWeights=1, name=f"{self.side}_MainMembrane_SKN")[0]

        cmds.skinPercent(nurbs_skincluster, f"{self.guides[0]}.cv[1][1]", transformValue=[(arm_joints[6], 0.75), (main_joint, 0.25)])
        cmds.skinPercent(nurbs_skincluster, f"{self.guides[0]}.cv[1][2]", transformValue=[(arm_joints[6], 0.25), (main_joint, 0.75)])

        for i, (u_value, name) in enumerate([(0.25, "Inner"), (0.5, "Middle"), (0.75, "Outer")]):
            for index, v_value in enumerate([0.25, 0.5, 0.75]):
                point_on_surface = cmds.createNode("pointOnSurfaceInfo", name=f"{self.side}_{name}Membrane0{index}_POSI", ss=True)
                cmds.setAttr(f"{point_on_surface}.parameterU", u_value)
                cmds.setAttr(f"{point_on_surface}.parameterV", v_value)

                cmds.connectAttr(f"{guide_shape}.worldSpace[0]", f"{point_on_surface}.inputSurface", force=True)

                matrix_node = cmds.createNode('fourByFourMatrix', name=f"Joint_4B4M_{self.side}_{name}Membrane0{index}", ss=True)

                cmds.connectAttr(f"{point_on_surface}.normalizedNormalX", f"{matrix_node}.in10", force=True)
                cmds.connectAttr(f"{point_on_surface}.normalizedNormalY", f"{matrix_node}.in11", force=True)
                cmds.connectAttr(f"{point_on_surface}.normalizedNormalZ", f"{matrix_node}.in12", force=True)

                cmds.connectAttr(f"{point_on_surface}.normalizedTangentVX", f"{matrix_node}.in00", force=True)
                cmds.connectAttr(f"{point_on_surface}.normalizedTangentVY", f"{matrix_node}.in01", force=True)
                cmds.connectAttr(f"{point_on_surface}.normalizedTangentVZ", f"{matrix_node}.in02", force=True)

                cmds.connectAttr(f"{point_on_surface}.normalizedTangentUX", f"{matrix_node}.in20", force=True)
                cmds.connectAttr(f"{point_on_surface}.normalizedTangentUY", f"{matrix_node}.in21", force=True)
                cmds.connectAttr(f"{point_on_surface}.normalizedTangentUZ", f"{matrix_node}.in22", force=True)

                cmds.connectAttr(f"{point_on_surface}.positionX", f"{matrix_node}.in30", force=True)
                cmds.connectAttr(f"{point_on_surface}.positionY", f"{matrix_node}.in31", force=True)
                cmds.connectAttr(f"{point_on_surface}.positionZ", f"{matrix_node}.in32", force=True)

                joint = cmds.createNode("joint", name=f"{self.side}_{name}Membrane0{index}_JNT", ss=True, parent=self.skinnging_grp)
                cmds.connectAttr(f"{matrix_node}.output", f"{joint}.offsetParentMatrix", force=True)

    def secondary_membranes(self):

        input_val = 0
        skinning_joints = []
        while True:
            joint_name = f"{self.side}_{self.number_to_ordinal_word(input_val + 1)}MetacarpalModule"
            joint = self.data_exporter.get_data(joint_name, "skinning_transform")
            if joint is None:
                break
            skinning_joints.append(joint)
            input_val += 1

        for i in range(len(skinning_joints)-1):
            joint_list_one = cmds.listRelatives(skinning_joints[i], children=True, type="joint")
            joint_list_two = cmds.listRelatives(skinning_joints[i+1], children=True, type="joint")

            if joint_list_one and joint_list_two:
                len_one = len(joint_list_one)
                split_indices = [
                    1,
                    len_one // 4,
                    len_one // 2,
                    3 * len_one // 4
                ]
                split_points_one = [joint_list_one[idx] for idx in split_indices if idx > 0 and idx <= len_one]
                split_points_two = [joint_list_two[idx] for idx in split_indices if idx > 0 and idx <= len(joint_list_two)]
                

            for values in [0.33, 0.66]:

                ctls = []
                ctls_grp = []
                secondary_ctls = []
                pick_matrix_nodes = []
                membranes_wm_aim = []
                mid_positions = []
                for index, (joint_one, joint_two) in enumerate(zip(split_points_one, split_points_two)):
                    if values == 0.33:
                        name = "Inner"
                    elif values == 0.66:
                        name = "Outer"
                    y_axis_aim = cmds.createNode("aimMatrix", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}_AMX", ss=True)
                    cmds.connectAttr(f"{joint_two}.worldMatrix[0]", f"{y_axis_aim}.inputMatrix")
                    cmds.connectAttr(f"{joint_one}.worldMatrix[0]", f"{y_axis_aim}.primaryTargetMatrix")
                    cmds.connectAttr(f"{joint_one}.worldMatrix[0]", f"{y_axis_aim}.secondaryTargetMatrix")
                    cmds.setAttr(f"{y_axis_aim}.primaryInputAxis", *self.primary_aim_vector, type="double3")
                    cmds.setAttr(f"{y_axis_aim}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
                    cmds.setAttr(f"{y_axis_aim}.secondaryTargetVector", *self.secondary_aim_vector, type="double3")
                    cmds.setAttr(f"{y_axis_aim}.secondaryMode", 2)

                    y_axis_aim_translate = cmds.createNode("blendMatrix", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}_BMX", ss=True)
                    cmds.connectAttr(f"{y_axis_aim}.outputMatrix", f"{y_axis_aim_translate}.inputMatrix")
                    cmds.connectAttr(f"{joint_one}.worldMatrix[0]", f"{y_axis_aim_translate}.target[0].targetMatrix")
                    cmds.setAttr(f"{y_axis_aim_translate}.target[0].scaleWeight", 0)
                    cmds.setAttr(f"{y_axis_aim_translate}.target[0].translateWeight", values) # Cambiar valor para 0.25 0.5 0.75
                    cmds.setAttr(f"{y_axis_aim_translate}.target[0].rotateWeight", 0)
                    cmds.setAttr(f"{y_axis_aim_translate}.target[0].shearWeight", 0)

                    mult_side = 1 if self.side == "L" else -1

                    y_axis_aim_end_pos = cmds.createNode("multMatrix", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}_MMX", ss=True)
                    cmds.setAttr(f"{y_axis_aim_end_pos}.matrixIn[0]",   1, 0, 0, 0, 
                                                                        0, 1, 0, 0, 
                                                                        0, 0, 1, 0, 
                                                                        0, 50*mult_side, 0, 1, type="matrix")
                    cmds.connectAttr(f"{y_axis_aim_translate}.outputMatrix", f"{y_axis_aim_end_pos}.matrixIn[1]")   

                    mid_position = cmds.createNode("wtAddMatrix", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}_WTM", ss=True)
                    cmds.connectAttr(f"{joint_one}.worldMatrix[0]", f"{mid_position}.wtMatrix[0].matrixIn")
                    cmds.connectAttr(f"{joint_two}.worldMatrix[0]", f"{mid_position}.wtMatrix[1].matrixIn")
                    cmds.setAttr(f"{mid_position}.wtMatrix[0].weightIn", values) # Cambiar valor para 0.25 0.5 0.75
                    cmds.setAttr(f"{mid_position}.wtMatrix[1].weightIn", 1-values) # Cambiar valor para 0.25 0.5 0.75

                    front_offset_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}FrontOffset_MMX", ss=True)
                    cmds.setAttr(f"{front_offset_multMatrix}.matrixIn[0]",   1, 0, 0, 0, 
                                                                            0, 1, 0, 0,
                                                                            0, 0, 1, 0,
                                                                            10, 0, 0, 1, type="matrix")
                    cmds.connectAttr(f"{mid_position}.matrixSum", f"{front_offset_multMatrix}.matrixIn[1]")

                    membran_wm_aim = cmds.createNode("aimMatrix", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}End_AMX", ss=True)
                    cmds.connectAttr(f"{mid_position}.matrixSum", f"{membran_wm_aim}.inputMatrix")
                    cmds.connectAttr(f"{y_axis_aim_end_pos}.matrixSum", f"{membran_wm_aim}.secondaryTargetMatrix")

                    cmds.setAttr(f"{membran_wm_aim}.primaryInputAxis", *self.primary_aim_vector, type="double3")
                    cmds.setAttr(f"{membran_wm_aim}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
                    cmds.setAttr(f"{membran_wm_aim}.secondaryTargetVector", *self.secondary_aim_vector, type="double3")
                    cmds.setAttr(f"{membran_wm_aim}.secondaryMode", 1)

                    if index != 0:
                        ctl, ctl_grp = controller_creator(
                        name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}",
                        suffixes=["GRP", "ANM"],
                        lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                        ro=True,
                        parent=self.individual_controllers_grp
                        )
                    

                    pick_matrix = cmds.createNode("pickMatrix", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}_PMX", ss=True)

                    cmds.connectAttr(f"{membran_wm_aim}.outputMatrix", f"{pick_matrix}.inputMatrix")
                    cmds.setAttr(f"{pick_matrix}.useScale", 0)

                    joint = cmds.createNode("joint", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}_JNT", ss=True, parent=self.skinnging_grp)
                    

                    if ctls:
                        multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}Offset_MMX", ss=True)
                        multMatrix_wm = cmds.createNode("multMatrix", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}WM_MMX", ss=True)
                        inverseMatrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{self.number_to_ordinal_word(i+1)}Membran0{index+1}{name}_IMX", ss=True)
                        cmds.connectAttr(f"{pick_matrix_nodes[-1]}.outputMatrix", f"{inverseMatrix}.inputMatrix")

                        cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{multMatrix}.matrixIn[0]")
                        cmds.connectAttr(f"{inverseMatrix}.outputMatrix", f"{multMatrix}.matrixIn[1]")
                        cmds.connectAttr(f"{multMatrix}.matrixSum", f"{multMatrix_wm}.matrixIn[0]")
                        cmds.connectAttr(f"{ctls[-1]}.worldMatrix[0]", f"{multMatrix_wm}.matrixIn[1]")
                        cmds.connectAttr(f"{multMatrix_wm}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix")

                    elif not ctls and index != 0:
                        cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix")

                    else:
                        cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{joint}.offsetParentMatrix")

                    if index != 0:
                        ctls_grp.append(ctl_grp)
                        ctls.append(ctl)
                        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{joint}.offsetParentMatrix")

                    pick_matrix_nodes.append(pick_matrix)
                    membranes_wm_aim.append(membran_wm_aim)
                    mid_positions.append(mid_position)

                for aim_loop, wm_aim in enumerate(membranes_wm_aim):
                    try:
                        cmds.connectAttr(f"{mid_positions[aim_loop+1]}.matrixSum", f"{wm_aim}.primaryTargetMatrix")
                    except IndexError:
                        cmds.connectAttr(f"{mid_positions[aim_loop-1]}.matrixSum", f"{wm_aim}.primaryTargetMatrix")
                        pv = self.primary_aim_vector * -1
                        cmds.setAttr(f"{membran_wm_aim}.primaryInputAxis", pv.x, pv.y, pv.z, type="double3")


