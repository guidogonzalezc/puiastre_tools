#Python libraries import
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

class LimbModule(object):

    def __init__(self, side="L"):

        self.side = side
        self.module_name = "arm"
        self.guides = []
        self.scapula_guide = None
        self.enum_str = None

        self.primary_aim = (1, 0, 0)
        self.secondary_aim = (0, 0, 1) 

        self.default_ik = 1
        self.oriented_ik = False

        self.ikHandleEnabled = False


        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")


    def make(self):

        """
        Create a limb rig with controllers and constraints.
        This function sets up the basic structure for a limb, including controllers and constraints.
        """      

        self.individual_module_grp = cmds.createNode("transform", name=f"{self.side}_{self.module_name}Module_GRP", parent=self.modules_grp, ss=True)
        self.individual_controllers_grp = cmds.createNode("transform", name=f"{self.side}_{self.module_name}Controllers_GRP", parent=self.masterWalk_ctl, ss=True)
        self.skinnging_grp = cmds.createNode("transform", name=f"{self.side}_{self.module_name}SkinningJoints_GRP", parent=self.skel_grp, ss=True)
        
        self.primary_aim_vector = om.MVector(AXIS_VECTOR[self.primary_aim])
        self.secondary_aim_vector = om.MVector(AXIS_VECTOR[self.secondary_aim])

        cmds.addAttr(self.skinnging_grp, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        #Position Joints
        order = [[self.guides[0], self.guides[1], self.guides[2]], [self.guides[1], self.guides[2], self.guides[0]]]

        aim_matrix_guides = []

        for i in range(len(self.guides)-1):

            aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{self.module_name}Guide0{i+1}_AMX", ss=True)
            multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}GuideOffset0{i+1}_MMX", ss=True)

            cmds.setAttr(aim_matrix + ".primaryInputAxis", *self.primary_aim_vector, type="double3")
            cmds.setAttr(aim_matrix + ".secondaryInputAxis", *self.secondary_aim_vector, type="double3")
            
            cmds.setAttr(aim_matrix + ".primaryMode", 1)
            cmds.setAttr(aim_matrix + ".secondaryMode", 1)

            cmds.connectAttr(order[i][0] + ".worldMatrix[0]", aim_matrix + ".inputMatrix")
            cmds.connectAttr(order[i][1] + ".worldMatrix[0]", aim_matrix + ".primaryTargetMatrix")
            cmds.connectAttr(order[i][2] + ".worldMatrix[0]", aim_matrix + ".secondaryTargetMatrix")

            aim_matrix_guides.append(aim_matrix)

        
        blend_matrix = cmds.createNode("blendMatrix", name=f"{self.side}_{self.module_name}Guide03_BLM", ss=True)
        cmds.connectAttr(f"{aim_matrix_guides[1]}.outputMatrix", f"{blend_matrix}.inputMatrix", force=True)
        cmds.connectAttr(f"{self.guides[2]}.worldMatrix[0]", f"{blend_matrix}.target[0].targetMatrix", force=True)
        cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].rotateWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].shearWeight", 0)

        self.guides_matrix = [aim_matrix_guides[0], aim_matrix_guides[1], blend_matrix]

        self.fk_rig()


    def fk_rig(self):
        """
        Create FK chain for the limb.
        This function creates a forward kinematics chain for the limb, including controllers and constraints.
        """
        self.fk_ctls = []
        self.fk_grps = []
        self.fk_offset = []
        for i, guide in enumerate(self.guides_matrix):

            ctl, ctl_grp = controller_creator(
                name=self.guides[i].replace("_GUIDE", "Fk"),
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
            )

            cmds.parent(ctl_grp[0], self.fk_ctls[-1] if self.fk_ctls else self.individual_controllers_grp)

            if not i == 2:
                cmds.addAttr(ctl, shortName="strechySep", niceName="Strechy ———", enumName="———",attributeType="enum", keyable=True)
                cmds.setAttr(ctl+".strechySep", channelBox=True, lock=True)
                cmds.addAttr(ctl, shortName="stretch", niceName="Stretch",minValue=1,defaultValue=1, keyable=True)

                

            if not i == 0:
                subtract = cmds.createNode("subtract", name=f"{self.side}_{self.module_name}FkOffset0{i}_SUB", ss=True)
                cmds.connectAttr(f"{self.fk_ctls[-1]}.stretch", f"{subtract}.input1")
                cmds.setAttr( f"{subtract}.input2", 1)
                cmds.connectAttr(f"{subtract}.output", f"{ctl_grp[0]}.tx")
                

                offset_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}FkOffset0{i+1}_MMX", ss=True)
                inverse_matrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{self.module_name}FkOffset0{i+1}_IMX", ss=True)
                cmds.connectAttr(f"{guide}.outputMatrix", f"{offset_multMatrix}.matrixIn[0]")

                cmds.connectAttr(f"{self.guides_matrix[i-1]}.outputMatrix", f"{inverse_matrix}.inputMatrix")

                cmds.connectAttr(f"{inverse_matrix}.outputMatrix", f"{offset_multMatrix}.matrixIn[1]")
            

                cmds.connectAttr(f"{offset_multMatrix}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix")


                for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
                    try:
                        cmds.setAttr(f"{ctl_grp[0]}.{attr}", 0)
                    except:
                        pass

            else:
                cmds.connectAttr(f"{guide}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix")




            self.fk_ctls.append(ctl)
            self.fk_grps.append(ctl_grp) 

        # cmds.addAttr(self.fk_ctls[0], shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———",attributeType="enum", keyable=True)
        # cmds.setAttr(self.fk_ctls[0]+".extraAttr", channelBox=True, lock=True)
        # cmds.addAttr(self.fk_ctls[0], shortName="upperTwist", niceName="Upper Twist",defaultValue=0, keyable=True)
        # cmds.addAttr(self.fk_ctls[0], shortName="curvature", niceName="Curvature", maxValue=1, minValue=0,defaultValue=0, keyable=True)

        self.fk_wm = [f"{self.fk_ctls[0]}.worldMatrix[0]", f"{self.fk_ctls[1]}.worldMatrix[0]", f"{self.fk_ctls[2]}.worldMatrix[0]"]

        self.ik_rig()

    def create_matrix_pole_vector(self, m1_attr, m2_attr, m3_attr, pole_distance=1.0, name="poleVector_LOC"):
        """
        Given three matrix attributes (e.g. joint.worldMatrix[0]), compute a proper pole vector
        position using Maya matrix and math nodes (no Python vector math).
        """
        def matrix_to_translation(matrix_attr, prefix):
            dm = cmds.createNode('rowFromMatrix', name=f"{self.side}_{self.module_name}Pv{prefix.capitalize()}Offset_RFM", ss=True)
            cmds.connectAttr(matrix_attr, f'{dm}.matrix')
            cmds.setAttr(f'{dm}.input', 3)
            return f'{dm}.output'

        def create_vector_subtract(name, inputA, inputB):
            node = cmds.createNode('plusMinusAverage', name=f"{self.side}_{self.module_name}Pv{name.capitalize()}_PMA", ss=True)
            cmds.setAttr(f'{node}.operation', 2)
            for i, input in enumerate([inputA, inputB]):
                try:
                    cmds.connectAttr(input, f'{node}.input3D[{i}]')
                except:
                    for attr in ["X", "Y", "Z"]:
                        cmds.connectAttr(f'{input}.output{attr}', f'{node}.input3D[{i}].input3D{attr.lower()}')
            return node, f'{node}.output3D'

        def normalize_vector(input_vec, name):
            vp = cmds.createNode('normalize', name=f"{self.side}_{self.module_name}Pv{name.capitalize()}_NRM", ss=True)
            cmds.connectAttr(input_vec, f'{vp}.input')
            return f'{vp}.output'

        def scale_vector(input_vec, scalar_attr, name):
            md = cmds.createNode('multiplyDivide', name=f"{self.side}_{self.module_name}Pv{name.capitalize()}_MDV", ss=True)
            cmds.setAttr(f'{md}.operation', 1)
            cmds.connectAttr(input_vec, f'{md}.input1')
            for axis in 'XYZ':
                cmds.connectAttr(scalar_attr, f'{md}.input2{axis}')
            return md, f'{md}.output'

        def add_vectors(vecA, vecB, name):
            node = cmds.createNode('plusMinusAverage', name=f"{self.side}_{self.module_name}Pv{name.capitalize()}_PMA", ss=True)
            for i, vector in enumerate([vecA, vecB]):
                try:
                    cmds.connectAttr(vector, f'{node}.input3D[{i}]')
                except:
                    for attr in ["X", "Y", "Z"]:
                        cmds.connectAttr(f'{vector}.output{attr}', f'{node}.input3D[{i}].input3D{attr.lower()}')
            return node, f'{node}.output3D'

        vec1_attr = matrix_to_translation(m1_attr, 'vec1')
        vec2_attr = matrix_to_translation(m2_attr, 'vec2')
        vec3_attr = matrix_to_translation(m3_attr, 'vec3')

        dist1 = cmds.createNode('distanceBetween', name=f"{self.side}_{self.module_name}PvVec1Vec2_DBT", ss=True)
        for attr in ["X", "Y", "Z"]:
            cmds.connectAttr(f'{vec1_attr}{attr}', f'{dist1}.point1{attr}')
            cmds.connectAttr(f'{vec2_attr}{attr}', f'{dist1}.point2{attr}')

        dist2 = cmds.createNode('distanceBetween', name=f"{self.side}_{self.module_name}PvVec2Vec3_DBT", ss=True)
        for attr in ["X", "Y", "Z"]:
            cmds.connectAttr(f'{vec2_attr}{attr}', f'{dist2}.point1{attr}')
            cmds.connectAttr(f'{vec3_attr}{attr}', f'{dist2}.point2{attr}')

        avg = cmds.createNode('sum', name=f"{self.side}_{self.module_name}PvAvgDist_SUM", ss=True)
        cmds.connectAttr(f'{dist1}.distance', f'{avg}.input[0]')
        cmds.connectAttr(f'{dist2}.distance', f'{avg}.input[1]')

        half = cmds.createNode('divide', name=f"{self.side}_{self.module_name}PvHalfDist_DIV", ss=True)
        cmds.setAttr(f'{half}.input2', 2.0 / pole_distance)
        cmds.connectAttr(f'{avg}.output', f'{half}.input1')

        vec1_sub_node, vec1_sub = create_vector_subtract('vec1MinusVec2', vec1_attr, vec2_attr)
        vec1_norm = normalize_vector(vec1_sub, 'vec1Norm')

        vec3_sub_node, vec3_sub = create_vector_subtract('vec3MinusVec2', vec3_attr, vec2_attr)
        vec3_norm = normalize_vector(vec3_sub, 'vec3Norm')

        vec1_scaled_node, vec1_scaled = scale_vector(vec1_norm, f'{half}.output', 'vec1Scaled')
        vec3_scaled_node, vec3_scaled = scale_vector(vec3_norm, f'{half}.output', 'vec3Scaled')

        vec1_final_node, vec1_final = add_vectors(vec2_attr, vec1_scaled, 'vec1Final')
        vec3_final_node, vec3_final = add_vectors(vec2_attr, vec3_scaled, 'vec3Final')

        proj_dir_node, proj_dir = create_vector_subtract('projDir', vec3_final, vec1_final)

        proj_dir_norm = normalize_vector(proj_dir, 'projDirNorm')

        vec_to_project_node, vec_to_project = create_vector_subtract('vecToProject', vec2_attr, vec1_final)

        dot_node = cmds.createNode('vectorProduct', name=f"{self.side}_{self.module_name}PvDot_VCP", ss=True)
        cmds.setAttr(f'{dot_node}.operation', 1)
        cmds.connectAttr(vec_to_project, f'{dot_node}.input1')
        cmds.connectAttr(proj_dir_norm, f'{dot_node}.input2')

        proj_vec_node, proj_vec = scale_vector(proj_dir_norm, f'{dot_node}.outputX', 'projVector')

        mid_node, mid = add_vectors(vec1_final, proj_vec, 'midPoint')

        pointer_node, pointer_vec = create_vector_subtract('pointerVec', vec2_attr, mid)

        pointer_norm = normalize_vector(pointer_vec, 'pointerNorm')
        pointer_scaled_node, pointer_scaled = scale_vector(pointer_norm, f'{half}.output', 'pointerScaled')

        pole_pos_node, pole_pos = add_vectors(vec2_attr, pointer_scaled, 'poleVectorPos')

        fourByFour = cmds.createNode('fourByFourMatrix', name=f"{self.side}_{self.module_name}PvFourByFour_FBM", ss=True)
        cmds.connectAttr(f"{pole_pos}.output3Dx", f'{fourByFour}.in30')
        cmds.connectAttr(f"{pole_pos}.output3Dy", f'{fourByFour}.in31')
        cmds.connectAttr(f"{pole_pos}.output3Dz", f'{fourByFour}.in32')

        aim_matrix = cmds.createNode('aimMatrix', name=f"{self.side}_{self.module_name}PvAim_AMX", ss=True)
        cmds.setAttr(f'{aim_matrix}.primaryInputAxis', 0, 0, 1, type='double3')
        cmds.setAttr(f'{aim_matrix}.secondaryInputAxis', 1, 0, 0, type='double3')
        cmds.setAttr(f'{aim_matrix}.secondaryTargetVector', 1, 0, 0, type='double3')
        cmds.setAttr(f'{aim_matrix}.primaryMode', 1)
        cmds.setAttr(f'{aim_matrix}.secondaryMode', 2)
        cmds.connectAttr(f'{fourByFour}.output', f'{aim_matrix}.inputMatrix')
        cmds.connectAttr(f'{m2_attr}', f"{aim_matrix}.primaryTargetMatrix")
        cmds.connectAttr(f'{m2_attr}', f'{aim_matrix}.secondaryTargetMatrix')

        blend_matrix = cmds.createNode('blendMatrix', name=f"{self.side}_{self.module_name}PvBlend_BLM", ss=True)
        cmds.connectAttr(f'{fourByFour}.output', f'{blend_matrix}.inputMatrix')
        cmds.connectAttr(f'{aim_matrix}.outputMatrix', f'{blend_matrix}.target[0].targetMatrix')

        return blend_matrix

    def ik_rig(self):
        """
        Create IK chain for the limb.
        This function creates an inverse kinematics chain for the limb, including controllers and constraints.
        """
        self.ik_controllers = cmds.createNode("transform", name=f"{self.side}_{self.module_name}IkControllers_GRP", parent=self.individual_controllers_grp, ss=True)

        self.root_ik_ctl, self.root_ik_ctl_grp = controller_creator(
            name=f"{self.side}_{self.module_name}RootIk",
            suffixes=["GRP", "ANM"],
            lock=["rx", "ry", "rz", "sx","sz","sy","visibility"],
            ro=True,
            parent=self.ik_controllers
        )
        self.pv_ik_ctl, self.pv_ik_ctl_grp = controller_creator(
            name=f"{self.side}_{self.module_name}PV",
            suffixes=["GRP", "ANM"],
            lock=["rx", "ry", "rz", "sx","sz","sy","visibility"],
            ro=False,
            parent=self.ik_controllers

        )
        self.hand_ik_ctl, self.hand_ik_ctl_grp = controller_creator(
            name=f"{self.side}_{self.module_name}Ik",
            suffixes=["GRP", "ANM"],
            lock=["visibility"],
            ro=True,
            parent=self.ik_controllers

        )

        cmds.connectAttr(self.guides[2] + ".worldMatrix[0]", f"{self.hand_ik_ctl_grp[0]}.offsetParentMatrix")

        cmds.addAttr(self.pv_ik_ctl, shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.pv_ik_ctl+".extraAttr", channelBox=True, lock=True)
        cmds.addAttr(self.pv_ik_ctl, shortName="pvOrientation", niceName="Pv Orientation",defaultValue=0, minValue=0, maxValue=1, keyable=True)

        cmds.addAttr(self.pv_ik_ctl, shortName="poleVectorPinning", niceName="Pole Vector Pinning ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.pv_ik_ctl+".poleVectorPinning", channelBox=True, lock=True)
        cmds.addAttr(self.pv_ik_ctl, shortName="pin", niceName="Pin",minValue=0,maxValue=1,defaultValue=0, keyable=True)
        
        cmds.connectAttr(f"{self.guides_matrix[0]}.outputMatrix", f"{self.root_ik_ctl_grp[0]}.offsetParentMatrix")      

        cmds.addAttr(self.hand_ik_ctl, shortName="softSettings", niceName="Soft Settings  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.hand_ik_ctl+".softSettings", channelBox=True, lock=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="soft", niceName="Soft",minValue=0,maxValue=1,defaultValue=0, keyable=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="softStart", niceName="Soft Start",minValue=0,maxValue=1,defaultValue=0.8, keyable=True)

        cmds.addAttr(self.hand_ik_ctl, shortName="strechySep", niceName="Strechy  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.hand_ik_ctl+".strechySep", channelBox=True, lock=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="upperLengthMult", niceName="Upper Length Mult",minValue=0.001,defaultValue=1, keyable=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="lowerLengthMult", niceName="Lower Length Mult",minValue=0.001,defaultValue=1, keyable=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="stretch", niceName="Stretch",minValue=0,maxValue=1,defaultValue=0, keyable=True)

        pv_pos = self.create_matrix_pole_vector(
            f"{self.guides_matrix[0]}.outputMatrix",
            f"{self.guides_matrix[1]}.outputMatrix",
            f"{self.guides_matrix[2]}.outputMatrix",
            name=f"{self.side}_{self.module_name}PV"
        )

        cmds.connectAttr(f"{self.pv_ik_ctl}.pvOrientation", f"{pv_pos}.target[0].weight")
        cmds.connectAttr(f"{pv_pos}.outputMatrix", f"{self.pv_ik_ctl_grp[0]}.offsetParentMatrix")

        name = [f"{self.side}_{self.module_name}UpperInitialLength", f"{self.side}_{self.module_name}LowerInitialLength", f"{self.side}_{self.module_name}CurrentLength"]

        if self.ikHandleEnabled:
            manager = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}IkHandleManager_MMX", ss=True)
            cmds.connectAttr(f"{self.guides_matrix[2]}.outputMatrix", f"{manager}.matrixIn[0]")
            cmds.connectAttr(f"{self.leg_guides[0].replace('.worldMatrix[0]', '.worldInverseMatrix[0]')}", f"{manager}.matrixIn[1]")

            self.ikHandleManager = f"{manager}.matrixSum"
        else:
            self.ikHandleManager = f"{self.hand_ik_ctl}.worldMatrix[0]"

        self.distance_between_output = []
        for i, (first, second) in enumerate(zip([f"{self.guides[0]}.worldMatrix[0]", f"{self.guides[1]}.worldMatrix[0]", f"{self.root_ik_ctl}.worldMatrix[0]"], [f"{self.guides[1]}.worldMatrix[0]", f"{self.guides[2]}.worldMatrix[0]", f"{self.ikHandleManager}"])):
            distance = cmds.createNode("distanceBetween", name=f"{name[i]}_DB", ss=True)
            cmds.connectAttr(f"{first}", f"{distance}.inMatrix1")
            cmds.connectAttr(f"{second}", f"{distance}.inMatrix2")

            if i == 2:
                global_scale_divide = cmds.createNode("divide", name=f"{self.side}_{self.module_name}GlobalScaleFactor_DIV", ss=True)
                cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", f"{global_scale_divide}.input2")
                cmds.connectAttr(f"{distance}.distance", f"{global_scale_divide}.input1")
                self.distance_between_output.append(f"{global_scale_divide}.output")
            else:
                self.distance_between_output.append(f"{distance}.distance")
            
        sum_distance = cmds.createNode("sum", name=f"{self.side}_{self.module_name}InitialLenght_SUM")
        cmds.connectAttr(self.distance_between_output[0], f"{sum_distance}.input[0]")
        cmds.connectAttr(self.distance_between_output[1], f"{sum_distance}.input[1]")

        divide = cmds.createNode("divide", name=f"{self.side}_{self.module_name}LengthRatio_DIV", ss=True)
        cmds.connectAttr(f"{sum_distance}.output", f"{divide}.input2")
        cmds.connectAttr(f"{self.distance_between_output[2]}", f"{divide}.input1")

        max = cmds.createNode("max", name=f"{self.side}_{self.module_name}Scalar_MAX", ss=True)
        cmds.connectAttr(f"{divide}.output", f"{max}.input[0]")
        cmds.setAttr(f"{max}.input[1]", 1)  ############### QUIZAS SE HA DE PONER UN FLOATCONSTANT PROBAR SI GUARDA EL VALOR

        scalar_remap = cmds.createNode("remapValue", name=f"{self.side}_{self.module_name}LengthRatio_REMAP", ss=True)
        cmds.connectAttr(f"{self.hand_ik_ctl}.stretch", f"{scalar_remap}.inputValue")
        cmds.connectAttr(f"{max}.output", f"{scalar_remap}.outputMax")
        cmds.setAttr(f"{scalar_remap}.outputMin", 1)

        stretch_multiply_nodes = []
        for i, name in enumerate(["upperLength", "lowerLength"]):
            multiply = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}StretchLenght0{i}_MULT", ss=True)
            cmds.connectAttr(f"{self.distance_between_output[i]}", f"{multiply}.input[0]")
            cmds.connectAttr(f"{scalar_remap}.outValue", f"{multiply}.input[1]")
            cmds.connectAttr(f"{self.hand_ik_ctl}.{name}Mult", f"{multiply}.input[2]")
            stretch_multiply_nodes.append(multiply)

        # --- STRETCH --- #

        arm_length = cmds.createNode("sum", name=f"{self.side}_{self.module_name}Length_SUM", ss=True)
        cmds.connectAttr(f"{stretch_multiply_nodes[0]}.output", f"{arm_length}.input[0]")
        cmds.connectAttr(f"{stretch_multiply_nodes[1]}.output", f"{arm_length}.input[1]")

        arm_length_min = cmds.createNode("min", name=f"{self.side}_{self.module_name}ClampedLength_MIN", ss=True)
        cmds.connectAttr(f"{arm_length}.output", f"{arm_length_min}.input[0]")
        cmds.connectAttr(f"{self.distance_between_output[2]}", f"{arm_length_min}.input[1]")


        # Soft Values pre-build
        soft_upper_length_scaled = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}SoftUpperLengthScaled_MUL", ss=True)
        soft_lower_length_scaled = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}SoftLowerLengthScaled_MUL", ss=True)

        cmds.connectAttr(f"{stretch_multiply_nodes[0]}.output", f"{soft_upper_length_scaled}.input[0]")
        cmds.connectAttr(f"{stretch_multiply_nodes[1]}.output", f"{soft_lower_length_scaled}.input[0]")

        # --- CUSTOM SOLVER --- #

        upper_divide, upper_arm_acos, power_mults = core.law_of_cosine(sides = [f"{soft_upper_length_scaled}.output", f"{soft_lower_length_scaled}.output", f"{arm_length_min}.output"], name = f"{self.side}_{self.module_name}Upper", acos=True)
        lower_divide, lower_power_mults, negate_cos_value = core.law_of_cosine(sides = [f"{soft_upper_length_scaled}.output", f"{arm_length_min}.output", f"{soft_lower_length_scaled}.output"],
                                                                             power = [power_mults[0], power_mults[2], power_mults[1]],
                                                                             name = f"{self.side}_{self.module_name}Lower", 
                                                                             negate=True)

        soft_cosValue, soft_power_mults = core.law_of_cosine(sides = [f"{stretch_multiply_nodes[0]}.output", f"{stretch_multiply_nodes[1]}.output", f"{arm_length_min}.output"], name = f"{self.side}_{self.module_name}SoftArm")

        # --- SOFT ARM --- #

        soft_cosValueSquared = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}SoftCosValueSquared_MUL", ss=True)
        cmds.connectAttr(f"{soft_cosValue}.output", f"{soft_cosValueSquared}.input[0]")
        cmds.connectAttr(f"{soft_cosValue}.output", f"{soft_cosValueSquared}.input[1]")

        soft_height_squared = cmds.createNode("subtract", name=f"{self.side}_{self.module_name}SoftHeightSquared_SUB", ss=True)
        cmds.setAttr( f"{soft_height_squared}.input1", 1)
        cmds.connectAttr(f"{soft_cosValueSquared}.output", f"{soft_height_squared}.input2")

        soft_height_squared_clamped = cmds.createNode("max", name=f"{self.side}_{self.module_name}SoftHeightSquaredClamped_MAX", ss=True)
        cmds.setAttr(f"{soft_height_squared_clamped}.input[0]", 0)
        cmds.connectAttr(f"{soft_height_squared}.output", f"{soft_height_squared_clamped}.input[1]")

        soft_height = cmds.createNode("power", name=f"{self.side}_{self.module_name}SoftHeight_POW", ss=True)
        cmds.setAttr(f"{soft_height}.exponent", 0.5)
        cmds.connectAttr(f"{soft_height_squared_clamped}.output", f"{soft_height}.input")

        soft_linear_target_height = cmds.createNode("subtract", name=f"{self.side}_{self.module_name}SoftLinearTargetHeight_SUB", ss=True)
        cmds.setAttr(f"{soft_linear_target_height}.input1", 1)
        cmds.connectAttr(f"{soft_cosValue}.output", f"{soft_linear_target_height}.input2")

        soft_quadratic_target_height = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}SoftQuadraticTargetHeight_MUL", ss=True)
        cmds.connectAttr(f"{soft_linear_target_height}.output", f"{soft_quadratic_target_height}.input[0]")
        cmds.connectAttr(f"{soft_linear_target_height}.output", f"{soft_quadratic_target_height}.input[1]")

        soft_remapStart = cmds.createNode("remapValue", name=f"{self.side}_{self.module_name}SoftRemapStart_RMV", ss=True)
        cmds.connectAttr(f"{self.hand_ik_ctl}.softStart", f"{soft_remapStart}.inputMin")
        cmds.connectAttr(f"{soft_cosValue}.output", f"{soft_remapStart}.inputValue")
        cmds.setAttr(f"{soft_remapStart}.outputMin", 0)
        cmds.setAttr(f"{soft_remapStart}.outputMax", 1)
        cmds.setAttr(f"{soft_remapStart}.inputMax", 1)

        setup_blend_value = cmds.createNode("smoothStep", name=f"{self.side}_{self.module_name}SetupBlendValue_SMOOTH", ss=True)
        cmds.connectAttr(f"{soft_remapStart}.outValue", f"{setup_blend_value}.input")
        cmds.setAttr(f"{setup_blend_value}.leftEdge", 0)
        cmds.setAttr(f"{setup_blend_value}.rightEdge", 1)

        cubic_target_height = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}CubicTargetHeight_MUL", ss=True)
        cmds.connectAttr(f"{soft_quadratic_target_height}.output", f"{cubic_target_height}.input[0]")
        cmds.connectAttr(f"{soft_quadratic_target_height}.output", f"{cubic_target_height}.input[1]")
        cmds.connectAttr(f"{soft_quadratic_target_height}.output", f"{cubic_target_height}.input[2]")

        blend_choice = cmds.createNode("blendTwoAttr", name=f"{self.side}_{self.module_name}SoftBlendChoice_CH", ss=True)
        cmds.connectAttr(f"{self.hand_ik_ctl}.soft", f"{blend_choice}.attributesBlender")
        cmds.connectAttr(f"{setup_blend_value}.output", f"{blend_choice}.input[1]")
        cmds.connectAttr(f"{cubic_target_height}.output", f"{blend_choice}.input[0]")

        blend_twoAttrs = cmds.createNode("blendTwoAttr", name=f"{self.side}_{self.module_name}SoftHeight_BLT", ss=True)
        cmds.connectAttr(f"{blend_choice}.output", f"{blend_twoAttrs}.attributesBlender")
        cmds.connectAttr(f"{soft_height}.output", f"{blend_twoAttrs}.input[0]")
        cmds.connectAttr(f"{soft_quadratic_target_height}.output", f"{blend_twoAttrs}.input[1]")

        soft_blended_height_squared = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}SoftBlendedHeightSquared_MUL", ss=True)
        cmds.connectAttr(f"{blend_twoAttrs}.output", f"{soft_blended_height_squared}.input[0]")
        cmds.connectAttr(f"{blend_twoAttrs}.output", f"{soft_blended_height_squared}.input[1]")

        soft_scaler_squared = cmds.createNode("sum", name=f"{self.side}_{self.module_name}SoftScalerSquared_SUM", ss=True)
        cmds.connectAttr(f"{soft_blended_height_squared}.output", f"{soft_scaler_squared}.input[0]")
        cmds.connectAttr(f"{soft_cosValueSquared}.output", f"{soft_scaler_squared}.input[1]")

        # Upper arm output
        upper_soft_scaler = cmds.createNode("power", name=f"{self.side}_{self.module_name}UpperSoftScaler_POW", ss=True)
        cmds.setAttr(f"{upper_soft_scaler}.exponent", 0.5)
        cmds.connectAttr(f"{soft_scaler_squared}.output", f"{upper_soft_scaler}.input")

        cmds.connectAttr(f"{upper_soft_scaler}.output", f"{soft_upper_length_scaled}.input[1]")

        #Lower arm
        segmentLengthRatio = cmds.createNode("divide", name=f"{self.side}_{self.module_name}SoftSegmentLengthRatio_DIV", ss=True)
        cmds.connectAttr(f"{stretch_multiply_nodes[0]}.output", f"{segmentLengthRatio}.input1")
        cmds.connectAttr(f"{stretch_multiply_nodes[1]}.output", f"{segmentLengthRatio}.input2")

        lower_soft_height = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}LowerSoftHeight_MUL", ss=True)
        cmds.connectAttr(f"{segmentLengthRatio}.output", f"{lower_soft_height}.input[1]")
        cmds.connectAttr(f"{soft_height}.output", f"{lower_soft_height}.input[0]")

        lower_soft_blended_height = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}LowerSoftBlendedHeight_MUL", ss=True)
        cmds.connectAttr(f"{segmentLengthRatio}.output", f"{lower_soft_blended_height}.input[1]")
        cmds.connectAttr(f"{blend_twoAttrs}.output", f"{lower_soft_blended_height}.input[0]")

        lower_height_squared = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}LowerSoftHeightSquared_MUL", ss=True)
        cmds.connectAttr(f"{lower_soft_height}.output", f"{lower_height_squared}.input[0]")
        cmds.connectAttr(f"{lower_soft_height}.output", f"{lower_height_squared}.input[1]")

        lower_cos_value_squared = cmds.createNode("subtract", name=f"{self.side}_{self.module_name}LowerSoftCosValueSquared_SUB", ss=True)
        cmds.connectAttr(f"{lower_height_squared}.output", f"{lower_cos_value_squared}.input2")
        cmds.setAttr(f"{lower_cos_value_squared}.input1", 1)

        lower_blended_height_squared = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}LowerSoftBlendedHeightSquared_MUL", ss=True)
        cmds.connectAttr(f"{lower_soft_blended_height}.output", f"{lower_blended_height_squared}.input[0]")
        cmds.connectAttr(f"{lower_soft_blended_height}.output", f"{lower_blended_height_squared}.input[1]")

        soft_lower_scaler_squared = cmds.createNode("sum", name=f"{self.side}_{self.module_name}SoftLowerScalerSquared_SUM", ss=True)
        cmds.connectAttr(f"{lower_blended_height_squared}.output", f"{soft_lower_scaler_squared}.input[1]")
        cmds.connectAttr(f"{lower_cos_value_squared}.output", f"{soft_lower_scaler_squared}.input[0]")

        # Upper arm output
        lower_soft_scaler = cmds.createNode("power", name=f"{self.side}_{self.module_name}LowerSoftScaler_POW", ss=True)
        cmds.setAttr(f"{lower_soft_scaler}.exponent", 0.5)
        cmds.connectAttr(f"{soft_lower_scaler_squared}.output", f"{lower_soft_scaler}.input")

        cmds.connectAttr(f"{lower_soft_scaler}.output", f"{soft_lower_length_scaled}.input[1]")

        # --- Aligns --- #
 
        upper_arm_ik_aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{self.module_name}UpperIk_AIM", ss=True)
        cmds.connectAttr(f"{self.ikHandleManager}", f"{upper_arm_ik_aim_matrix}.primaryTargetMatrix")
        cmds.connectAttr(f"{self.pv_ik_ctl}.worldMatrix", f"{upper_arm_ik_aim_matrix}.secondaryTargetMatrix")
        cmds.connectAttr(f"{self.root_ik_ctl}.worldMatrix", f"{upper_arm_ik_aim_matrix}.inputMatrix")
        cmds.setAttr(f"{upper_arm_ik_aim_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")

        self.upperArmIkWM = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}UpperIkWM_MMX", ss=True)
        fourByfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.module_name}UpperIkLocal_F4X", ss=True)
        sin = cmds.createNode("sin", name=f"{self.side}_{self.module_name}UpperIkWM_SIN", ss=True)
        negate = cmds.createNode("negate", name=f"{self.side}_{self.module_name}UpperIkWM_NEGATE", ss=True)

        cmds.connectAttr(f"{upper_arm_ik_aim_matrix}.outputMatrix", f"{self.upperArmIkWM}.matrixIn[1]")
        cmds.connectAttr(f"{fourByfour}.output", f"{self.upperArmIkWM}.matrixIn[0]")

        cmds.connectAttr(f"{upper_divide}.output", f"{fourByfour}.in11")
        cmds.connectAttr(f"{upper_divide}.output", f"{fourByfour}.in00")
        cmds.connectAttr(f"{sin}.output", f"{fourByfour}.in01")
        cmds.connectAttr(f"{negate}.output", f"{fourByfour}.in10")

        cmds.connectAttr(f"{upper_arm_acos}.output", f"{sin}.input")
        cmds.connectAttr(f"{sin}.output", f"{negate}.input")

        cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryMode", 1)
            
        # Lower

        cosValueSquared = cmds.createNode("multiply", name=f"{self.side}_{self.module_name}LowerCosValueSquared_MUL", ss=True)
        cmds.connectAttr(f"{lower_divide}.output", f"{cosValueSquared}.input[0]")
        cmds.connectAttr(f"{lower_divide}.output", f"{cosValueSquared}.input[1]")

        lower_sin_value_squared = cmds.createNode("subtract", name=f"{self.side}_{self.module_name}LowerSinValueSquared_SUB", ss=True)
        cmds.connectAttr(f"{cosValueSquared}.output", f"{lower_sin_value_squared}.input2")
        cmds.setAttr(f"{lower_sin_value_squared}.input1", 1)

        lower_sin_value_squared_clamped = cmds.createNode("max", name=f"{self.side}_{self.module_name}LowerSinValueSquared_MAX", ss=True)
        cmds.connectAttr(f"{lower_sin_value_squared}.output", f"{lower_sin_value_squared_clamped}.input[1]")
        cmds.setAttr(f"{lower_sin_value_squared_clamped}.input[0]", 0)

        lower_sin = cmds.createNode("power", name=f"{self.side}_{self.module_name}LowerSin_POW", ss=True)
        cmds.connectAttr(f"{lower_sin_value_squared_clamped}.output", f"{lower_sin}.input")
        cmds.setAttr(f"{lower_sin}.exponent", 0.5)

        negate = cmds.createNode("negate", name=f"{self.side}_{self.module_name}LowerSin_NEGATE", ss=True)
        cmds.connectAttr(f"{lower_sin}.output", f"{negate}.input")

        fourByfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.module_name}LowerIkLocal_F4X", ss=True)
      
        cmds.connectAttr(f"{negate_cos_value}.output", f"{fourByfour}.in11")
        cmds.connectAttr(f"{negate_cos_value}.output", f"{fourByfour}.in00")
        cmds.connectAttr(f"{lower_sin}.output", f"{fourByfour}.in10")
        cmds.connectAttr(f"{negate}.output", f"{fourByfour}.in01")

        if self.side == "R":
            translate_negate = cmds.createNode("negate", name=f"{self.side}_{self.module_name}UpperTranslate_NEGATE", ss=True)
            cmds.connectAttr(f"{soft_upper_length_scaled}.output", f"{translate_negate}.input")
            cmds.connectAttr(f"{translate_negate}.output", f"{fourByfour}.in30")
            cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryInputAxis", 0, -1, 0, type="double3") ########################## CAMBIO QUIZAS

        else:
            cmds.connectAttr(f"{soft_upper_length_scaled}.output", f"{fourByfour}.in30")
            cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryInputAxis", 0, 1, 0, type="double3") ########################## CAMBIO QUIZAS


        lower_wm_multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}LowerIkWM_MMX", ss=True)
        cmds.connectAttr(f"{fourByfour}.output", f"{lower_wm_multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{self.upperArmIkWM}.matrixSum", f"{lower_wm_multmatrix}.matrixIn[1]")

        # Hand

        lower_inverse_matrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{self.module_name}LowerIkInverse_MTX", ss=True)
        cmds.connectAttr(f"{lower_wm_multmatrix}.matrixSum", f"{lower_inverse_matrix}.inputMatrix")

        hand_local_matrix_multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}EndBaseLocal_MMX", ss=True)
        cmds.connectAttr(f"{self.ikHandleManager}", f"{hand_local_matrix_multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{lower_inverse_matrix}.outputMatrix", f"{hand_local_matrix_multmatrix}.matrixIn[1]")

        hand_local_matrix = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.module_name}EndLocal_F4X", ss=True)

        hand_wm_multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}EndWM_MMX", ss=True)
        cmds.connectAttr(f"{hand_local_matrix}.output", f"{hand_wm_multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{lower_wm_multmatrix}.matrixSum", f"{hand_wm_multmatrix}.matrixIn[1]")


        for i in range(0, 3):
            row_from_matrix = cmds.createNode("rowFromMatrix", name=f"{self.side}_{self.module_name}EndLocalAxis{i}_RFM", ss=True)
            cmds.connectAttr(f"{hand_local_matrix_multmatrix}.matrixSum", f"{row_from_matrix}.matrix")
            cmds.setAttr(f"{row_from_matrix}.input", i)
            for z, attr in enumerate(["X", "Y", "Z", "W"]):
                cmds.connectAttr(f"{row_from_matrix}.output{attr}", f"{hand_local_matrix}.in{i}{z}")

        if self.side == "R":
            translate_negate = cmds.createNode("negate", name=f"{self.side}_{self.module_name}LowerTranslate_NEGATE", ss=True)
            cmds.connectAttr(f"{soft_lower_length_scaled}.output", f"{translate_negate}.input")
            cmds.connectAttr(f"{translate_negate}.output", f"{hand_local_matrix}.in30")
        else:
            cmds.connectAttr(f"{soft_lower_length_scaled}.output", f"{hand_local_matrix}.in30")

        self.ik_wm = [f"{self.upperArmIkWM}.matrixSum", f"{lower_wm_multmatrix}.matrixSum", f"{hand_wm_multmatrix}.matrixSum"]

        self.pairblends()

    def pairblends(self):
        self.switch_ctl, self.switch_ctl_grp = controller_creator(
            name=f"{self.side}_{self.module_name}Switch",
            suffixes=["GRP"],
            lock=["tx","ty","tz","rx","ry","rz","sx", "sy", "sz", "visibility"],
            ro=False,
            parent=self.individual_controllers_grp
        )

        self.switch_pos = guide_import(f"{self.side}_{self.module_name}Settings_GUIDE", all_descendents=False)[0]
        self.switch_pos_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}SwitchPos_MMX", ss=True)
        cmds.connectAttr(f"{self.switch_pos}.worldMatrix[0]", f"{self.switch_pos_multMatrix}.matrixIn[0]")
        inverse_guide = cmds.createNode("inverseMatrix", name=f"{self.side}_{self.module_name}SwitchPosInverse_MTX", ss=True)
        cmds.connectAttr(f"{self.guides_matrix[0]}.outputMatrix", f"{inverse_guide}.inputMatrix")
        cmds.connectAttr(f"{inverse_guide}.outputMatrix", f"{self.switch_pos_multMatrix}.matrixIn[1]")
        cmds.connectAttr(f"{self.switch_pos_multMatrix}.matrixSum", f"{self.switch_ctl_grp[0]}.offsetParentMatrix")
        cmds.setAttr(f"{self.switch_ctl_grp[0]}.inheritsTransform", 0)

        cmds.addAttr(self.switch_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=self.default_ik, keyable=True)
        cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{self.fk_grps[0][0]}.visibility", force=True)
        rev = cmds.createNode("reverse", name=f"{self.side}_{self.module_name}FkVisibility_REV", ss=True)
        cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{rev}.inputX")
        cmds.connectAttr(f"{rev}.outputX", f"{self.ik_controllers}.visibility")

        self.blend_wm = []
        for i, (fk, ik) in enumerate(zip(self.fk_wm, self.ik_wm)):
            name = fk.replace("Fk_CTL.worldMatrix[0]", "")

            blendMatrix = cmds.createNode("blendMatrix", name=f"{name}_BLM", ss=True)
            cmds.connectAttr(ik, f"{blendMatrix}.inputMatrix")
            cmds.connectAttr(fk, f"{blendMatrix}.target[0].targetMatrix")
            cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{blendMatrix}.target[0].weight")

            self.blend_wm.append(f"{blendMatrix}.outputMatrix")

        name = self.blend_wm[0].replace("_BLM.outputMatrix", "")
        
        nonRollAlign = cmds.createNode("blendMatrix", name=f"{name}NonRollAlign_BLM", ss=True)
        nonRollPick = cmds.createNode("pickMatrix", name=f"{name}NonRollPick_PIM", ss=True)
        nonRollAim = cmds.createNode("aimMatrix", name=f"{name}NonRollAim_AMX", ss=True)

        cmds.connectAttr(f"{self.root_ik_ctl_grp[0]}.worldMatrix[0]", f"{nonRollAlign}.inputMatrix")
        cmds.connectAttr(f"{self.fk_grps[0][0]}.worldMatrix[0]", f"{nonRollAlign}.target[0].targetMatrix")
        cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{nonRollAlign}.target[0].weight")

        cmds.connectAttr(f"{self.blend_wm[0]}", f"{nonRollPick}.inputMatrix")
        cmds.connectAttr(f"{nonRollPick}.outputMatrix", f"{nonRollAim}.inputMatrix")
        cmds.connectAttr(f"{nonRollAlign}.outputMatrix", f"{nonRollAim}.secondaryTargetMatrix")
        cmds.connectAttr(f"{self.blend_wm[1]}", f"{nonRollAim}.primaryTargetMatrix")
        cmds.setAttr(f"{nonRollAim}.primaryInputAxis", *self.primary_aim_vector, type="double3")
        cmds.setAttr(f"{nonRollAim}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{nonRollAim}.secondaryTargetVector", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{nonRollAim}.secondaryMode", 2)

        cmds.setAttr(f"{nonRollPick}.useRotate", 0)

        cmds.connectAttr(f"{self.blend_wm[0]}", f"{self.switch_pos_multMatrix}.matrixIn[2]")

        self.shoulder_rotate_matrix = self.blend_wm[0]
        self.blend_wm[0] = f"{nonRollAim}.outputMatrix"

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

    def bendys(self):
        self.bendy_controllers = cmds.createNode("transform", name=f"{self.side}_{self.module_name}BendyControllers_GRP", parent=self.individual_controllers_grp, ss=True)
        cmds.setAttr(f"{self.bendy_controllers}.inheritsTransform", 0)
        

        for i, bendy in enumerate(["UpperBendy", "MiddleBendy", "LowerBendy"]):
            ctl, ctl_grp = controller_creator(
                name=f"{self.side}_{self.module_name}{bendy}",
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
            )

            cmds.addAttr(ctl, shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———",attributeType="enum", keyable=True)
            cmds.setAttr(ctl+".extraAttr", channelBox=True, lock=True)
            cmds.addAttr(ctl, shortName="secondaryControllersHeight", niceName="secondary Controllers Height", maxValue=1, minValue=0,defaultValue=1, keyable=True)

            cmds.parent(ctl_grp[0], self.bendy_controllers)

            initial_matrix = self.shoulder_rotate_matrix if i == 0 else self.blend_wm[i]

            blendMatrix = cmds.createNode("blendMatrix", name=f"{self.side}_{self.module_name}{bendy}_BLM", ss=True)
            cmds.connectAttr(f"{initial_matrix}", f"{blendMatrix}.inputMatrix")
            cmds.connectAttr(f"{self.blend_wm[i+1]}", f"{blendMatrix}.target[0].targetMatrix")
            cmds.setAttr(f"{blendMatrix}.target[0].scaleWeight", 0)
            cmds.setAttr(f"{blendMatrix}.target[0].translateWeight", 0.5)
            cmds.setAttr(f"{blendMatrix}.target[0].rotateWeight", 0)
            cmds.setAttr(f"{blendMatrix}.target[0].shearWeight", 0)

            if i == 0:
                cmds.connectAttr(f"{self.blend_wm[i]}", f"{blendMatrix}.target[1].targetMatrix")
                cmds.setAttr(f"{blendMatrix}.target[1].scaleWeight", 0)
                cmds.setAttr(f"{blendMatrix}.target[1].translateWeight", 0)
                cmds.setAttr(f"{blendMatrix}.target[1].rotateWeight", 0.5)
                cmds.setAttr(f"{blendMatrix}.target[1].shearWeight", 0)

            cmds.connectAttr(f"{blendMatrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix") 
    
            cvMatrices = [self.blend_wm[i], f"{ctl}.worldMatrix[0]", self.blend_wm[i+1]]

            self.twist_number = 5

            t_values = []
            for index in range(self.twist_number):
                t = 0.95 if index == self.twist_number - 1 else index / (float(self.twist_number) - 1)
                t_values.append(t)

            axis_change = True if i == 0 else False 

            de_boors_002.de_boor_ribbon(aim_axis=self.primary_aim, up_axis=self.secondary_aim, cvs=cvMatrices, num_joints=self.twist_number, name=f"{self.side}_{self.module_name}{bendy}", parent=self.skinnging_grp, custom_parm=t_values, axis_change=axis_change)

            if bendy == "LowerBendy":
                joint = cmds.createNode("joint", name=f"{self.side}_{self.module_name}LowerBendy0{self.twist_number}_JNT", ss=True, parent=self.skinnging_grp)
                cmds.connectAttr(f"{cvMatrices[-1]}", f"{joint}.offsetParentMatrix")
                # t_values.append(1)
                # self.twist_number += 1

    def reverse_foot(self):
        """
        Reverse foot setup for leg module.  
        This method creates the foot controls and sets up the necessary connections.

        """

        # FK CONTROLLERS

        ctl, ctl_grp = controller_creator(
            name=self.leg_guides[0].replace("_GUIDE.worldMatrix[0]", "Fk"),
            suffixes=["GRP", "ANM"],
            lock=["scaleX", "scaleY", "scaleZ", "visibility"],
            ro=True,
        )
        
        cmds.parent(ctl_grp[0], self.fk_ctls[-1])

        offset_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}FkOffset0{1}_MMX", ss=True)
        inverse_matrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{self.module_name}FkOffset0{1}_IMX", ss=True)
        cmds.connectAttr(f"{self.leg_guides[0]}", f"{offset_multMatrix}.matrixIn[0]")

        cmds.connectAttr(f"{self.guides_matrix[2]}.outputMatrix", f"{inverse_matrix}.inputMatrix")

        cmds.connectAttr(f"{inverse_matrix}.outputMatrix", f"{offset_multMatrix}.matrixIn[1]")
    
        cmds.connectAttr(f"{offset_multMatrix}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix")

        for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
            cmds.setAttr(f"{ctl_grp[0]}.{attr}", 0)

        self.fk_ctls.append(ctl)
        self.fk_grps.append(ctl_grp) 


        # IK CONTROLLERS

        self.leg_ik_guides = guide_import(f"{self.side}_bankOut_GUIDE", all_descendents=True, path=None)

        self.ik_leg_guides = [f"{self.leg_ik_guides[0]}.worldMatrix[0]", f"{self.leg_ik_guides[1]}.worldMatrix[0]", f"{self.leg_ik_guides[2]}.worldMatrix[0]", self.leg_guides[1], self.leg_guides[0]]

        self.reverse_ctl = []
        self.reverse_ctl_grp = []

        for guide in self.ik_leg_guides:


            ctl, ctl_grp = controller_creator(
                name=guide.replace("_GUIDE.worldMatrix[0]", "Ik"),
                suffixes=["GRP", "SDK","ANM"],
                lock=["tx","tz","ty","sx","sz","sy","visibility"],
                ro=True,
                parent=self.ik_controllers
            )

            cmds.connectAttr(f"{guide}", f"{ctl_grp[0]}.offsetParentMatrix")

            cmds.parent(ctl_grp[0], self.reverse_ctl[-1] if self.reverse_ctl else self.hand_ik_ctl)                

            self.reverse_ctl.append(ctl)
            self.reverse_ctl_grp.append(ctl_grp)

        cmds.connectAttr(f"{self.reverse_ctl[-1]}.worldMatrix[0]", f"{self.ikHandleManager.replace('matrixSum', 'matrixIn[2]')}", force=True)

        # cmds.transformLimits(self.reverse_ctl[-1], rx=(0, 45), erx=(1, 0))

        # IK HANDLE WIP

        self.frontRoll_ctl, self.frontRoll_grp = controller_creator(
                name=f"{self.side}_{self.module_name}frontRoll",
                suffixes=["GRP", "ANM"],
                lock=["sx","sz","sy","visibility"],
                ro=True,
                parent=self.reverse_ctl[-1]
            )
        for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
            cmds.setAttr(f"{self.frontRoll_grp[0]}.{attr}", 0)

        

        ball_distance = cmds.createNode("distanceBetween", name=f"{self.side}_{self.module_name}BallDistance", ss=True)
        cmds.connectAttr(f"{self.leg_guides[0]}", f"{ball_distance}.inMatrix1")
        cmds.connectAttr(f"{self.guides[-1]}.worldMatrix[0]", f"{ball_distance}.inMatrix2")

        position_forward_fourbyfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.module_name}PositionForward_4B4", ss=True)
        cmds.connectAttr(f"{ball_distance}.distance", f"{position_forward_fourbyfour}.in32") # z axis

        ankle_ball_aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{self.module_name}AnkleBall_AIM", ss=True)
        cmds.connectAttr(f"{self.blend_wm[-1]}", f"{ankle_ball_aim_matrix}.inputMatrix")
        cmds.connectAttr(f"{self.reverse_ctl[-1]}.worldMatrix[0]", f"{ankle_ball_aim_matrix}.primaryTargetMatrix")
        cmds.connectAttr(f"{self.reverse_ctl[-1]}.worldMatrix[0]", f"{ankle_ball_aim_matrix}.secondaryTargetMatrix")
        cmds.setAttr(f"{ankle_ball_aim_matrix}.primaryInputAxis", 0,0,1, type="double3")
        cmds.setAttr(f"{ankle_ball_aim_matrix}.secondaryInputAxis", 0,1,0, type="double3")
        cmds.setAttr(f"{ankle_ball_aim_matrix}.secondaryTargetVector", 0,1,0, type="double3")
        cmds.setAttr(f"{ankle_ball_aim_matrix}.secondaryMode", 2)

        ball_wm_no_rotation = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}BallWMNoRotation_MMX", ss=True)
        cmds.connectAttr(f"{position_forward_fourbyfour}.output", f"{ball_wm_no_rotation}.matrixIn[0]")
        cmds.connectAttr(f"{ankle_ball_aim_matrix}.outputMatrix", f"{ball_wm_no_rotation}.matrixIn[1]")

        ball_wm = cmds.createNode("aimMatrix", name=f"{self.side}_{self.module_name}BallWM_AIM", ss=True)
        cmds.connectAttr(f"{ball_wm_no_rotation}.matrixSum", f"{ball_wm}.inputMatrix")
        cmds.connectAttr(f"{self.reverse_ctl[-2]}.worldMatrix[0]", f"{ball_wm}.primaryTargetMatrix")
        cmds.connectAttr(f"{self.reverse_ctl[-2]}.worldMatrix[0]", f"{ball_wm}.secondaryTargetMatrix")
        cmds.setAttr(f"{ball_wm}.primaryInputAxis", 0,0,1, type="double3")
        cmds.setAttr(f"{ball_wm}.secondaryInputAxis", 0,1,0, type="double3")
        cmds.setAttr(f"{ball_wm}.secondaryTargetVector", 0,1,0, type="double3")
        cmds.setAttr(f"{ball_wm}.secondaryMode", 2)

        front_roll_wm = cmds.createNode("multMatrix", name=f"{self.side}_{self.module_name}FrontRollWM_MMX", ss=True)
        cmds.connectAttr(f"{self.frontRoll_ctl}.worldMatrix[0]", f"{front_roll_wm}.matrixIn[0]")
        cmds.connectAttr(f"{self.frontRoll_grp[0]}.worldInverseMatrix[0]", f"{front_roll_wm}.matrixIn[1]")
        cmds.connectAttr(f"{ball_wm}.outputMatrix", f"{front_roll_wm}.matrixIn[2]")

        cmds.addAttr(self.hand_ik_ctl, shortName="reverseFoot", niceName="Reverse foot  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.hand_ik_ctl+".reverseFoot", channelBox=True, lock=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="roll", niceName="Roll",defaultValue=0, keyable=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="rollLiftAngle", niceName="Roll Lift Angle",minValue=0,defaultValue=45, keyable=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="rollStraightAngle", niceName="Roll Straight Angle",minValue=0,defaultValue=90, keyable=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="bank", niceName="Bank",defaultValue=0, keyable=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="ankleTwist", niceName="Ankle Twist",defaultValue=0, keyable=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="ballTwist", niceName="Ball Twist",defaultValue=0, keyable=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="tipTwist", niceName="Tip Twist",defaultValue=0, keyable=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="heelTwist", niceName="Heel Twist",defaultValue=0, keyable=True)

        # # ----ADDING THE ROLL----#

        # ### GENERATED CODE (direct assignments) ###

        rollStraightAnglePercentage_RMV = cmds.createNode("remapValue", 
            name=f"{self.side}_rollStraightAnglePercentage_RMV", ss=True)

        rollLiftAnglePercentage_RMV = cmds.createNode("remapValue", 
            name=f"{self.side}_rollLiftAnglePercentage_RMV", ss=True)

        rollStraightAnglePercentage_REV = cmds.createNode("reverse", 
            name=f"{self.side}_rollStraightAnglePercentage_REV", ss=True)

        rollLiftAngleEnable_MDN = cmds.createNode("multiplyDivide", 
            name=f"{self.side}_rollLiftAngleEnable_MDN", ss=True)

        rollStrightAngle_MDN = cmds.createNode("multiplyDivide", 
            name=f"{self.side}_rollStrightAngle_MDN", ss=True)

        rollLiftAngle_MDN = cmds.createNode("multiplyDivide", 
            name=f"{self.side}_rollLiftAngle_MDN", ss=True)

        rollStrightAngleNegate_MDN = cmds.createNode("multiplyDivide", 
            name=f"{self.side}_rollStrightAngleNegate_MDN", ss=True)

        rollHeel_CLM = cmds.createNode("clamp", 
            name=f"{self.side}_rollHeel_CLM", ss=True)

        footBank_CLM = cmds.createNode("clamp", 
            name=f"{self.side}_footBank_CLM", ss=True)

        rollLiftAngleNegate_MDN = cmds.createNode("multiplyDivide", 
            name=f"{self.side}_rollLiftAngleNegate_MDN", ss=True)


        # ---------------- CONNECTIONS ---------------- #

        cmds.connectAttr(rollStraightAnglePercentage_RMV + ".outValue", rollStrightAngle_MDN + ".input1X")
        cmds.connectAttr(rollStraightAnglePercentage_RMV + ".outValue", rollStraightAnglePercentage_REV + ".inputX")
        cmds.connectAttr(f"{self.hand_ik_ctl}.roll", rollStraightAnglePercentage_RMV + ".inputValue")
        cmds.connectAttr(f"{self.hand_ik_ctl}.rollLiftAngle", rollStraightAnglePercentage_RMV + ".inputMin")
        cmds.connectAttr(f"{self.hand_ik_ctl}.rollStraightAngle", rollStraightAnglePercentage_RMV + ".inputMax")

        cmds.connectAttr(f"{self.hand_ik_ctl}.roll", rollLiftAnglePercentage_RMV + ".inputValue")
        cmds.connectAttr(f"{self.hand_ik_ctl}.roll", rollHeel_CLM + ".inputR")
        cmds.connectAttr(f"{self.hand_ik_ctl}.roll", rollLiftAngle_MDN + ".input2X")
        cmds.connectAttr(f"{self.hand_ik_ctl}.roll", rollStrightAngle_MDN + ".input2X")

        cmds.connectAttr(f"{self.hand_ik_ctl}.rollLiftAngle", rollLiftAnglePercentage_RMV + ".inputMax")
        cmds.connectAttr(f"{self.hand_ik_ctl}.bank", footBank_CLM + ".inputG")
        cmds.connectAttr(f"{self.hand_ik_ctl}.bank", footBank_CLM + ".inputR")

        cmds.setAttr(rollStrightAngleNegate_MDN + ".input2X", 1)
        cmds.setAttr(rollLiftAngleNegate_MDN + ".input2X", 1)
        cmds.setAttr(rollHeel_CLM + ".minR", -360)

        if self.side == "L":
            cmds.setAttr(footBank_CLM + ".minG", -360)
            cmds.setAttr(footBank_CLM + ".maxR", 360)
        elif self.side == "R":
            cmds.setAttr(footBank_CLM + ".minR", 360)
            cmds.setAttr(footBank_CLM + ".maxG", -360)

        cmds.connectAttr(rollLiftAnglePercentage_RMV + ".outValue", rollLiftAngleEnable_MDN + ".input2X")
        cmds.connectAttr(rollStraightAnglePercentage_REV + ".outputX", rollLiftAngleEnable_MDN + ".input1X")
        cmds.connectAttr(rollLiftAngleEnable_MDN + ".outputX", rollLiftAngle_MDN + ".input1X")
        cmds.connectAttr(rollStrightAngle_MDN + ".outputX", rollStrightAngleNegate_MDN + ".input1X")
        cmds.connectAttr(rollLiftAngle_MDN + ".outputX", rollLiftAngleNegate_MDN + ".input1X")

        cmds.connectAttr(footBank_CLM + ".outputR", f"{self.reverse_ctl_grp[1][1]}.rotateZ")
        cmds.connectAttr(footBank_CLM + ".outputG", f"{self.reverse_ctl_grp[0][1]}.rotateZ")
        cmds.connectAttr(rollHeel_CLM + ".outputR", f"{self.reverse_ctl_grp[2][1]}.rotateX")
        cmds.connectAttr(rollStrightAngleNegate_MDN + ".outputX", f"{self.reverse_ctl_grp[3][1]}.rotateX")
        cmds.connectAttr(rollLiftAngleNegate_MDN + ".outputX", f"{self.reverse_ctl_grp[4][1]}.rotateX")

        cmds.connectAttr(f"{self.hand_ik_ctl}.heelTwist", f"{self.reverse_ctl_grp[2][1]}.rotateY")
        cmds.connectAttr(f"{self.hand_ik_ctl}.tipTwist", f"{self.reverse_ctl_grp[3][1]}.rotateY")
        cmds.connectAttr(f"{self.hand_ik_ctl}.ballTwist", f"{self.reverse_ctl_grp[4][1]}.rotateY")
        cmds.connectAttr(f"{self.hand_ik_ctl}.ankleTwist", self.hand_ik_ctl_grp[1] + ".rotateY")

        blendMatrix = cmds.createNode("blendMatrix", name=f"{self.side}_{self.module_name}Ball_BLM", ss=True)
        cmds.connectAttr(f"{front_roll_wm}.matrixSum", f"{blendMatrix}.inputMatrix")
        cmds.connectAttr(f"{self.fk_ctls[-1]}.worldMatrix[0]", f"{blendMatrix}.target[0].targetMatrix")
        cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{blendMatrix}.target[0].weight")

        self.blend_wm.append(f"{blendMatrix}.outputMatrix")

        # ball_joint = cmds.createNode("joint", name=f"{self.side}_{self.module_name}Ball_JNT", ss=True, parent=self.skinnging_grp)

        # cmds.connectAttr(f"{blendMatrix}.outputMatrix", f"{ball_joint}.offsetParentMatrix") 

        # cmds.select(clear=True)
        # joint_blend = cmds.joint(name=self.fk_joints[-1].replace("Fk_JNT", "Blend_JNT"), rad=0.5)
        # blendMatrix = cmds.createNode("blendMatrix", name=f"{self.side}_{self.module_name}0{i+1}_BLM", ss=True)
        # cmds.connectAttr(f"{self.feet_joints[1]}.worldMatrix[0]", f"{blendMatrix}.inputMatrix")
        # cmds.connectAttr(f"{self.fk_joints[-1]}.worldMatrix[0]", f"{blendMatrix}.target[0].targetMatrix")
        # cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{blendMatrix}.target[0].weight")
        
        # cmds.connectAttr(f"{blendMatrix}.outputMatrix", f"{joint_blend}.offsetParentMatrix")

        # cmds.parent(joint_blend, self.individual_module_grp)

        # cmds.select(clear=True)
        # joint = cmds.joint(name=joint_blend.replace("Blend_JNT", "Foot_JNT"), rad=0.5)
        # cmds.parent(joint, self.skinnging_grp)
        # cmds.connectAttr(f"{joint_blend}.worldMatrix[0]", f"{joint}.offsetParentMatrix")


        # self.blend_chain.append(joint)

        # skin_joints = cmds.listRelatives(self.skinnging_grp, type="joint", allDescendents=True)[0]

        # ss.fk_switch(self.switch_ctl, sources = [skin_joints])


class BackLegModule(LimbModule):
    """
    Class for moditifying limb module specific to legs.
    Inherits from LimbModule.
    """

    def __init__(self, guide_name):
        side = guide_name.split("_")[0]
        super().__init__(side)

        self.module_name = "backLeg"

        self.guides = guide_import(guide_name, all_descendents=True, path=None)
        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]

        if len(self.guides) > 3:
            self.leg_guides = [f"{self.guides[3]}.worldMatrix[0]", f"{self.guides[4]}.worldMatrix[0]"]
            self.guides = [self.guides[0], self.guides[1], self.guides[2]]

        self.oriented_ik = True
        self.ikHandleEnabled = True

        # Leg-specific setup
        if self.side == "L":
            self.primary_aim = "x"
            self.secondary_aim = "-y"

        elif self.side == "R":
            self.primary_aim = "-x"
            self.secondary_aim = "y"

        self.default_ik = 0



    def make(self):
        super().make()
        self.reverse_foot()
        self.bendys()


        self.data_exporter.append_data(
            f"{self.side}_{self.module_name}Module",
            {
                "skinning_transform": self.skinnging_grp,
                "fk_ctl": self.fk_ctls,
                "pv_ctl": self.pv_ik_ctl,   
                "root_ctl": self.root_ik_ctl,
                "end_ik": self.hand_ik_ctl,
            }
        )


# cmds.file(new=True, force=True)

# core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/test_03.guides")
# core.DataManager.set_ctls_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/curves/AYCHEDRAL_curves_001.json")

# basic_structure.create_basic_structure()
# a = BackLegModule("L_hip_GUIDE").make()
