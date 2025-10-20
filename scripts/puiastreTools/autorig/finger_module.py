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
import re


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
        self.foot_rotation = data_exporter.get_data(f"{self.side}_backLegModule", "frontRoll")
        self.ikSwitch_ctl = data_exporter.get_data(f"{self.side}_backLegModule", "ikFkSwitch")


        parent_matrix = cmds.createNode("parentMatrix", name=f"{self.side}_legFingersParent_PMX", ss=True)
        cmds.connectAttr(self.leg_ball_blm + ".worldMatrix[0]", parent_matrix + ".target[0].targetMatrix")
        cmds.connectAttr(self.foot_rotation + ".worldMatrix[0]", parent_matrix + ".target[1].targetMatrix")
        cmds.connectAttr(self.ikSwitch_ctl + ".switchIkFk", parent_matrix + ".target[0].weight")
        reverse = cmds.createNode("reverse", name=f"{self.side}_legFingers_IKFK_REV", ss=True)
        cmds.connectAttr(self.ikSwitch_ctl + ".switchIkFk", reverse + ".inputX")
        cmds.connectAttr(reverse + ".outputX", parent_matrix + ".target[1].weight")

        offset_matrix = self.get_offset_matrix(self.controllers_grp, self.leg_ball_blm)
        temp_transform = cmds.createNode("transform", name=f"{self.side}_legFingersTempOffset_GRP", parent=self.controllers_grp, ss=True)
        cmds.connectAttr(self.foot_rotation + ".worldMatrix[0]", temp_transform + ".offsetParentMatrix")
        offset_matrix02 = self.get_offset_matrix(self.controllers_grp, temp_transform)

        cmds.delete(temp_transform)

        cmds.setAttr(parent_matrix + ".target[0].offsetMatrix", *offset_matrix, type="matrix")
        cmds.setAttr(parent_matrix + ".target[1].offsetMatrix", *offset_matrix02, type="matrix")

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
        # self.attributes_setup()

        self.data_exporter.append_data(
            f"{self.side}_footFingersModule",
            {
                "skinning_transform": self.skinning_grp,
                "ik_controllers": self.ik_controllers,
            }
        )
    
    def import_guides(self, guide_name):

        """
        Import the guides for the fingers module
        :param guide_name: name of the guide to import
        """

        self.fingers = guide_import(guide_name, all_descendents=True, path=None)
        self.side = self.fingers[0].split("_")[0]
        self.controllers_grp = cmds.createNode("transform", name=f"{self.side}_legFingersControllers_GRP", parent=self.masterWalk_ctl)
        self.individual_module_grp = cmds.createNode("transform", name=f"{self.side}_footFingerModule_GRP", parent=self.modules_grp, ss=True)
        self.skinning_grp = cmds.createNode("transform", name=f"{self.side}_footFingerSkinningJoints_GRP", parent=self.skel_grp, ss=True)
        self.controllers_grp_ik = cmds.createNode("transform", name=f"{self.side}_legFingersIkControllers_GRP", parent=self.masterWalk_ctl)


        cmds.setAttr(self.controllers_grp + ".inheritsTransform", 0)
    
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
        self.finger_attributes_ctl, self.finger_attributes_nodes, = controller_creator(name=f"{self.side}_fingersAttributes", suffixes=["GRP"], parent=self.controllers_grp, lock=["tx", "ty", "tz" ,"rx", "ry", "rz", "sx", "sy", "sz", "visibility"], ro=False)

        cmds.addAttr(self.finger_attributes_ctl, shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.finger_attributes_ctl+".extraAttr", channelBox=True, lock=True)
        cmds.addAttr(self.finger_attributes_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="FingerAttributes", attributeType="enum", enumName="____")
        cmds.setAttr(f"{self.finger_attributes_ctl}.FingerAttributes", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="Curl", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="Spread", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="Twist", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="Fan", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="ThumbAttributes", attributeType="enum", enumName="____")
        cmds.setAttr(f"{self.finger_attributes_ctl}.ThumbAttributes", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.finger_attributes_ctl, ln="Thumb_Curl", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, ln="Thumb_Spread", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, ln="Thumb_Twist", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, ln="Thumb_Fan", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)

        thumb_guides = [finger for finger in self.fingers if "thumb" in finger]
        index_guides = [finger for finger in self.fingers if "index" in finger]
        middle_guides = [finger for finger in self.fingers if "middle" in finger]
        pinky_guides = [finger for finger in self.fingers if "pinky" in finger]

        self.controllers = []

        self.ik_controllers = []

        for i, finger in enumerate([thumb_guides, index_guides, middle_guides, pinky_guides]):
            finger_name = ''.join([c for c in finger[0].split('_')[1] if not c.isdigit()])
            

            controllers = []
            aim_matrix_guides = []
            self.sdk_thumb_nodes = []
            self.sdk_index_nodes = []
            self.sdk_middle_nodes = []
            self.sdk_pinky_nodes = []

            for index in range(0, 2):
                aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{finger_name}Guide0{index+1}_AMX", ss=True)

                cmds.setAttr(aim_matrix + ".primaryInputAxis", *self.primary_aim_vector, type="double3")
                cmds.setAttr(aim_matrix + ".secondaryInputAxis", *self.secondary_aim_vector, type="double3")
                cmds.setAttr(aim_matrix + ".secondaryTargetVector", *self.secondary_aim_vector, type="double3")
                
                cmds.setAttr(aim_matrix + ".primaryMode", 1)
                cmds.setAttr(aim_matrix + ".secondaryMode", 1)

                next_index = index + 2 if (index + 2) < len(finger) else 0

                cmds.connectAttr(finger[index] + ".worldMatrix[0]", aim_matrix + ".inputMatrix")
                cmds.connectAttr(finger[index+1] + ".worldMatrix[0]", aim_matrix + ".primaryTargetMatrix")
                cmds.connectAttr(finger[next_index] + ".worldMatrix[0]", aim_matrix + ".secondaryTargetMatrix")

                aim_matrix_guides.append(aim_matrix)

            aim_matrix_guides.append(cmds.createNode("blendMatrix", name=f"{self.side}_{finger_name}Guide0{index+2}_BLM", ss=True))
            cmds.connectAttr(finger[-1] + ".worldMatrix[0]", aim_matrix_guides[-1] + ".inputMatrix")
            cmds.connectAttr(aim_matrix_guides[1] + ".outputMatrix", aim_matrix_guides[-1] + ".target[0].targetMatrix")
            cmds.setAttr(aim_matrix_guides[-1] + ".target[0].translateWeight", 0)

            controller_matrices = []
            fk_grps = []
            for j, guide in enumerate(aim_matrix_guides):


                finger_name = guide.split('_')[1].replace('Guide', '')

                ctl, grp = controller_creator(
                    name=f"{self.side}_{finger_name}",
                    suffixes=["GRP", "SDK", "ANM"],
                    lock=["tx", "ty", "tz" ,"sx", "sy", "sz", "visibility"],
                    ro=False,
                    parent= controllers[-1] if controllers else self.controllers_grp
                )
                if i == 0:
                    if j == 0:
                        self.fingers_attributes_callback(grp[1], finger_values=[0,0,0,0,0,0, 0,0], thumb_values=[0,0,0,0,0,0, 10, -10])
                    else:
                        self.fingers_attributes_callback(grp[1], finger_values=[0,0,0,0,0,0, 0,0], thumb_values=[-90, 20, -20, 20, 20, -20, 0, 0])
                if i == 1: 
                    if j == 0:
                        self.fingers_attributes_callback(grp[1], finger_values=[-90, 20, -25, 15, 20, -20, 30, -30], thumb_values=[0,0,0,0,0,0, 0,0])
                    elif i == 1:
                        self.fingers_attributes_callback(grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                    elif i == 2:
                        self.fingers_attributes_callback(grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                if i == 2: 
                    if j == 0:
                        self.fingers_attributes_callback(grp[1], finger_values=[-90, 20, 2, -2, 20, -20, -2, 2], thumb_values=[0,0,0,0,0,0, 0,0])
                    elif j == 1:
                        self.fingers_attributes_callback(grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                    elif j == 2:
                        self.fingers_attributes_callback(grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                if i == 3: 
                    if j == 0:
                        self.fingers_attributes_callback(grp[1], finger_values=[-90, 20, 30, -15, 20, -20, -50, 50], thumb_values=[0,0,0,0,0,0, 0,0])
                    elif j == 1:
                        self.fingers_attributes_callback(grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                    elif j == 2:
                        self.fingers_attributes_callback(grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])

                if controllers:
                    offset_matrix = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}_MLT", ss=True)
                    inverse = cmds.createNode("inverseMatrix", name=f"{self.side}_{finger_name}_INV", ss=True)
                    cmds.connectAttr(aim_matrix_guides[j-1] + ".outputMatrix", inverse + ".inputMatrix")
                    cmds.connectAttr(guide + ".outputMatrix", offset_matrix + ".matrixIn[0]")
                    cmds.connectAttr(controllers[-1] + ".worldInverseMatrix[0]", offset_matrix + ".matrixIn[1]")
                    cmds.connectAttr(controllers[-1] + ".worldMatrix[0]", offset_matrix + ".matrixIn[2]")
                    cmds.connectAttr(inverse + ".outputMatrix", offset_matrix + ".matrixIn[3]")
                    cmds.connectAttr(offset_matrix + ".matrixSum", grp[0] + ".offsetParentMatrix")
                else:
                    cmds.connectAttr(guide + ".outputMatrix", grp[0] + ".offsetParentMatrix")                

                cmds.setAttr(f"{grp[0]}.rotate", 0,0,0, type="double3")
                cmds.setAttr(f"{grp[0]}.translate", 0,0,0, type="double3")

                controller_matrices.append(ctl + ".worldMatrix[0]")
                fk_grps.append(grp)
                controllers.append(ctl)
                self.controllers.append(ctl)


            ik_matrices, grp_ik = self.ik_setup(aim_matrix_guides, finger_name)

            self.pairblends(ik_matrices, controller_matrices, fk_grps, finger_name, grp_ik)

        point_temp = cmds.pointConstraint(self.controllers[3], self.controllers[4], self.controllers[6], self.controllers[7], self.finger_attributes_nodes[0], mo=False) # Position the main attr grp
        cmds.delete(point_temp)

    def pairblends(self, ik, fk, fk_grp, finger_name, ctl_ik):

        finger_name_chain = re.sub(r'\d+', '', finger_name)
        finger_name_chain = finger_name_chain.replace('Guide', '').strip('_')

        finger_name = finger_name_chain

        cmds.connectAttr(f"{self.finger_attributes_ctl}.switchIkFk", f"{fk_grp[0][0]}.visibility", force=True)
        self.ik_visibility_rev = cmds.createNode("reverse", name=f"{self.side}_FkVisibility_REV", ss=True)
        cmds.connectAttr(f"{self.finger_attributes_ctl}.switchIkFk", f"{self.ik_visibility_rev}.inputX")
        cmds.connectAttr(f"{self.ik_visibility_rev}.outputX", f"{ctl_ik}.visibility")


        self.blend_wm = []
        for i, (fk, ik) in enumerate(zip(fk, ik)):

            blendMatrix = cmds.createNode("blendMatrix", name=f"{self.side}_{finger_name.replace('Guide', '')}0{i+1}_BLM", ss=True)
            cmds.connectAttr(ik, f"{blendMatrix}.inputMatrix")
            cmds.connectAttr(fk, f"{blendMatrix}.target[0].targetMatrix")
            cmds.connectAttr(f"{self.finger_attributes_ctl}.switchIkFk", f"{blendMatrix}.target[0].weight")

            self.blend_wm.append(f"{blendMatrix}.outputMatrix")

            joint = cmds.createNode("joint", name=f"{self.side}_{finger_name.replace('Guide', '')}0{i+1}_JNT", parent=self.skinning_grp, ss=True)
            cmds.connectAttr(blendMatrix + ".outputMatrix", joint + ".offsetParentMatrix")
        
    
  

    def ik_setup(self, guides_list, finger_name):
        self.side = guides_list[0].split("_")[0]

        root_wm = cmds.createNode("parentMatrix", name=f"{self.side}_legFingersParent_PMX", ss=True)
        cmds.connectAttr(guides_list[0] + ".outputMatrix", root_wm + ".inputMatrix")
        cmds.connectAttr(self.leg_ball_blm + ".worldMatrix[0]", root_wm + ".target[0].targetMatrix")
        cmds.connectAttr(self.foot_rotation + ".worldMatrix[0]", root_wm + ".target[1].targetMatrix")
        cmds.connectAttr(self.ikSwitch_ctl + ".switchIkFk", root_wm + ".target[0].weight")
        reverse = cmds.createNode("reverse", name=f"{self.side}_legFingers_IKFK_REV", ss=True)
        cmds.connectAttr(self.ikSwitch_ctl + ".switchIkFk", reverse + ".inputX")
        cmds.connectAttr(reverse + ".outputX", root_wm + ".target[1].weight")

        temp_transform = cmds.createNode("transform", name=f"{self.side}_legFingersTempOffset_GRP", parent=self.controllers_grp, ss=True)
        cmds.connectAttr(guides_list[0] + ".outputMatrix", temp_transform + ".offsetParentMatrix")

        offset_matrix = self.get_offset_matrix(temp_transform, self.leg_ball_blm)
        offset_matrix02 = self.get_offset_matrix(temp_transform, self.foot_rotation)
        cmds.delete(temp_transform)


        cmds.setAttr(root_wm + ".target[0].offsetMatrix", *offset_matrix, type="matrix")
        cmds.setAttr(root_wm + ".target[1].offsetMatrix", *offset_matrix02, type="matrix")

        ctl, grp = controller_creator(
                    name=f"{self.side}_{finger_name}Ik",
                    suffixes=["GRP", "SDK", "ANM"],
                    lock=["sx", "sy", "sz", "visibility"],
                    ro=False,
                    parent= self.controllers_grp_ik
                )
        
        self.ik_controllers.append(ctl)
        
        cmds.connectAttr(guides_list[-1] + ".outputMatrix", grp[0] + ".offsetParentMatrix")

        self.ikHandleManager = f"{ctl}.worldMatrix[0]"

        self.distance_between_output = []
        for i, (first, second) in enumerate(zip([f"{guides_list[0]}.outputMatrix", f"{guides_list[1]}.outputMatrix", f"{root_wm}.outputMatrix"], [f"{guides_list[1]}.outputMatrix", f"{guides_list[2]}.outputMatrix", f"{self.ikHandleManager}"])):
            distance = cmds.createNode("distanceBetween", name=f"{finger_name}_DB", ss=True)
            cmds.connectAttr(f"{first}", f"{distance}.inMatrix1")
            cmds.connectAttr(f"{second}", f"{distance}.inMatrix2")

            if i == 2:
                global_scale_divide = cmds.createNode("divide", name=f"{self.side}_{finger_name}GlobalScaleFactor_DIV", ss=True)
                cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", f"{global_scale_divide}.input2")
                cmds.connectAttr(f"{distance}.distance", f"{global_scale_divide}.input1")
                self.distance_between_output.append(f"{global_scale_divide}.output")
            else:
                self.distance_between_output.append(f"{distance}.distance")
            

        # --- STRETCH --- #

        arm_length = cmds.createNode("sum", name=f"{self.side}_{finger_name}Length_SUM", ss=True)
        cmds.connectAttr(f"{self.distance_between_output[0]}", f"{arm_length}.input[0]")
        cmds.connectAttr(f"{self.distance_between_output[1]}", f"{arm_length}.input[1]")

        arm_length_min = cmds.createNode("min", name=f"{self.side}_{finger_name}ClampedLength_MIN", ss=True)
        cmds.connectAttr(f"{arm_length}.output", f"{arm_length_min}.input[0]")
        cmds.connectAttr(f"{self.distance_between_output[2]}", f"{arm_length_min}.input[1]")



        # --- CUSTOM SOLVER --- #

        upper_divide, upper_arm_acos, power_mults = core.law_of_cosine(sides = [f"{self.distance_between_output[0]}", f"{self.distance_between_output[1]}", f"{arm_length_min}.output"], name = f"{self.side}_{finger_name}Upper", acos=True)
        lower_divide, lower_power_mults, negate_cos_value = core.law_of_cosine(sides = [f"{self.distance_between_output[0]}", f"{arm_length_min}.output", f"{self.distance_between_output[1]}"],
                                                                             power = [power_mults[0], power_mults[2], power_mults[1]],
                                                                             name = f"{self.side}_{finger_name}Lower", 
                                                                             negate=True)

        # --- Aligns --- #
 
        upper_arm_ik_aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{finger_name}UpperIk_AIM", ss=True)
        cmds.connectAttr(f"{self.ikHandleManager}", f"{upper_arm_ik_aim_matrix}.primaryTargetMatrix")
        # cmds.connectAttr(f"{self.pv_ik_ctl}.worldMatrix", f"{upper_arm_ik_aim_matrix}.secondaryTargetMatrix")
        cmds.connectAttr(f"{root_wm}.outputMatrix", f"{upper_arm_ik_aim_matrix}.inputMatrix")
        cmds.setAttr(f"{upper_arm_ik_aim_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")

        self.upperArmIkWM = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}WM_MMX", ss=True)
        fourByfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{finger_name}UpperIkLocal_F4X", ss=True)
        sin = cmds.createNode("sin", name=f"{self.side}_{finger_name}UpperIkWM_SIN", ss=True)
        negate = cmds.createNode("negate", name=f"{self.side}_{finger_name}UpperIkWM_NEGATE", ss=True)

        cmds.connectAttr(f"{upper_arm_ik_aim_matrix}.outputMatrix", f"{self.upperArmIkWM}.matrixIn[1]")
        cmds.connectAttr(f"{fourByfour}.output", f"{self.upperArmIkWM}.matrixIn[0]")

        cmds.connectAttr(f"{upper_divide}.output", f"{fourByfour}.in11")
        cmds.connectAttr(f"{upper_divide}.output", f"{fourByfour}.in00")
        cmds.connectAttr(f"{sin}.output", f"{fourByfour}.in01")
        cmds.connectAttr(f"{negate}.output", f"{fourByfour}.in10")

        cmds.connectAttr(f"{upper_arm_acos}.output", f"{sin}.input")
        cmds.connectAttr(f"{sin}.output", f"{negate}.input")

        # cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryMode", 1)
            
        # Lower

        cosValueSquared = cmds.createNode("multiply", name=f"{self.side}_{finger_name}LowerCosValueSquared_MUL", ss=True)
        cmds.connectAttr(f"{lower_divide}.output", f"{cosValueSquared}.input[0]")
        cmds.connectAttr(f"{lower_divide}.output", f"{cosValueSquared}.input[1]")

        lower_sin_value_squared = cmds.createNode("subtract", name=f"{self.side}_{finger_name}LowerSinValueSquared_SUB", ss=True)
        cmds.connectAttr(f"{cosValueSquared}.output", f"{lower_sin_value_squared}.input2")
        cmds.setAttr(f"{lower_sin_value_squared}.input1", 1)
        self.floatConstant_zero = cmds.createNode("floatConstant", name=f"{self.side}_zero{finger_name}_FLC", ss=True)
        cmds.setAttr(f"{self.floatConstant_zero}.inFloat", 0)
        lower_sin_value_squared_clamped = cmds.createNode("max", name=f"{self.side}_{finger_name}LowerSinValueSquared_MAX", ss=True)
        cmds.connectAttr(f"{lower_sin_value_squared}.output", f"{lower_sin_value_squared_clamped}.input[1]")
        cmds.connectAttr(f"{self.floatConstant_zero}.outFloat", f"{lower_sin_value_squared_clamped}.input[0]")


        lower_sin = cmds.createNode("power", name=f"{self.side}_{finger_name}LowerSin_POW", ss=True)
        cmds.connectAttr(f"{lower_sin_value_squared_clamped}.output", f"{lower_sin}.input")
        cmds.setAttr(f"{lower_sin}.exponent", 0.5)

        negate = cmds.createNode("negate", name=f"{self.side}_{finger_name}LowerSin_NEGATE", ss=True)
        cmds.connectAttr(f"{lower_sin}.output", f"{negate}.input")

        fourByfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{finger_name}LowerIkLocal_F4X", ss=True)
      
        cmds.connectAttr(f"{negate_cos_value}.output", f"{fourByfour}.in11")
        cmds.connectAttr(f"{negate_cos_value}.output", f"{fourByfour}.in00")
        cmds.connectAttr(f"{lower_sin}.output", f"{fourByfour}.in10")
        cmds.connectAttr(f"{negate}.output", f"{fourByfour}.in01")

        if self.side == "R":
            translate_negate = cmds.createNode("negate", name=f"{self.side}_{finger_name}UpperTranslate_NEGATE", ss=True)
            cmds.connectAttr(f"{self.distance_between_output[0]}", f"{translate_negate}.input")
            cmds.connectAttr(f"{translate_negate}.output", f"{fourByfour}.in30")
            cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryInputAxis", 0, -1, 0, type="double3") ########################## CAMBIO QUIZAS

        else:
            cmds.connectAttr(f"{self.distance_between_output[0]}", f"{fourByfour}.in30")
            cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryInputAxis", 0, 1, 0, type="double3") ########################## CAMBIO QUIZAS


        lower_wm_multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}WM_MMX", ss=True)
        cmds.connectAttr(f"{fourByfour}.output", f"{lower_wm_multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{self.upperArmIkWM}.matrixSum", f"{lower_wm_multmatrix}.matrixIn[1]")

        # Hand
        lower_inverse_matrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{finger_name}LowerIkInverse_MTX", ss=True)
        cmds.connectAttr(f"{lower_wm_multmatrix}.matrixSum", f"{lower_inverse_matrix}.inputMatrix")

        hand_local_matrix_multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}EndBaseLocal_MMX", ss=True)
        cmds.connectAttr(f"{self.ikHandleManager}", f"{hand_local_matrix_multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{lower_inverse_matrix}.outputMatrix", f"{hand_local_matrix_multmatrix}.matrixIn[1]")

        hand_local_matrix = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{finger_name}EndLocal_F4X", ss=True)

        hand_wm_multmatrix_end = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}WM_MMX", ss=True)
        cmds.connectAttr(f"{hand_local_matrix}.output", f"{hand_wm_multmatrix_end}.matrixIn[0]")
        cmds.connectAttr(f"{lower_wm_multmatrix}.matrixSum", f"{hand_wm_multmatrix_end}.matrixIn[1]")


        for i in range(0, 3):
            row_from_matrix = cmds.createNode("rowFromMatrix", name=f"{self.side}_{finger_name}EndLocalAxis{i}_RFM", ss=True)
            cmds.connectAttr(f"{hand_local_matrix_multmatrix}.matrixSum", f"{row_from_matrix}.matrix")
            cmds.setAttr(f"{row_from_matrix}.input", i)
            for z, attr in enumerate(["X", "Y", "Z", "W"]):
                cmds.connectAttr(f"{row_from_matrix}.output{attr}", f"{hand_local_matrix}.in{i}{z}")

        if self.side == "R":
            translate_negate = cmds.createNode("negate", name=f"{self.side}_{finger_name}LowerTranslate_NEGATE", ss=True)
            cmds.connectAttr(f"{self.distance_between_output[1]}", f"{translate_negate}.input")
            cmds.connectAttr(f"{translate_negate}.output", f"{hand_local_matrix}.in30")
        else:
            cmds.connectAttr(f"{self.distance_between_output[1]}", f"{hand_local_matrix}.in30")    

        self.ik_wm = [ f"{self.upperArmIkWM}.matrixSum", f"{lower_wm_multmatrix}.matrixSum",f"{hand_wm_multmatrix_end}.matrixSum"]

        return self.ik_wm, grp[0]

        
    def attributes_setup(self):

        """
        Create attributes for finger controls
        """
        
        self.fingers_attributes_callback(self.sdk_thumb_nodes[0], values=[0,0,0,0,0,0, 0,0], thumb_attributes=[0,0,0,0,0,0, 10, -10])
        self.fingers_attributes_callback(self.sdk_thumb_nodes[1], values=[0,0,0,0,0,0, 0,0], thumb_attributes=[-90, 20, -20, 20, 20, -20, 0, 0])
        self.fingers_attributes_callback(self.sdk_thumb_nodes[2], values=[0,0,0,0,0,0, 0,0], thumb_attributes=[-80, 18, 0, 0, 10, -10, 0, 0])

        self.fingers_attributes_callback(self.sdk_index_nodes[1], values=[-90, 20, -25, 15, 20, -20, 30, -30], thumb_attributes=[0,0,0,0,0,0, 0,0])
        self.fingers_attributes_callback(self.sdk_index_nodes[2], values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_attributes=[0,0,0,0,0,0, 0,0])
        self.fingers_attributes_callback(self.sdk_index_nodes[3], values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_attributes=[0,0,0,0,0,0, 0,0])

        self.fingers_attributes_callback(self.sdk_middle_nodes[1], values=[-90, 20, 2, -2, 20, -20, -2, 2], thumb_attributes=[0,0,0,0,0,0, 0,0])
        self.fingers_attributes_callback(self.sdk_middle_nodes[2], values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_attributes=[0,0,0,0,0,0, 0,0])
        self.fingers_attributes_callback(self.sdk_middle_nodes[3], values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_attributes=[0,0,0,0,0,0, 0,0])

        self.fingers_attributes_callback(self.sdk_pinky_nodes[1], values=[-90, 20, 30, -15, 20, -20, -50, 50], thumb_attributes=[0,0,0,0,0,0, 0,0])
        self.fingers_attributes_callback(self.sdk_pinky_nodes[2], values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_attributes=[0,0,0,0,0,0, 0,0])
        self.fingers_attributes_callback(self.sdk_pinky_nodes[3], values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_attributes=[0,0,0,0,0,0, 0,0])

    def fingers_attributes_callback(self, ctl, finger_values=[None], thumb_values=[None]):

        cmds.select(ctl)
        
        cmds.setDrivenKeyframe(at="rz", dv=0, cd=f"{self.finger_attributes_ctl}.Curl", v=0)
        cmds.setDrivenKeyframe(at="rz", dv=10, cd=f"{self.finger_attributes_ctl}.Curl", v=finger_values[0])
        cmds.setDrivenKeyframe(at="rz", dv=-10, cd=f"{self.finger_attributes_ctl}.Curl", v=finger_values[1])

        cmds.setDrivenKeyframe(at="ry", dv=0, cd=f"{self.finger_attributes_ctl}.Spread", v=0)
        cmds.setDrivenKeyframe(at="ry", dv=10, cd=f"{self.finger_attributes_ctl}.Spread", v=finger_values[2])
        cmds.setDrivenKeyframe(at="ry", dv=-10, cd=f"{self.finger_attributes_ctl}.Spread", v=finger_values[3])

        cmds.setDrivenKeyframe(at="rx", dv=0, cd=f"{self.finger_attributes_ctl}.Twist", v=0)
        cmds.setDrivenKeyframe(at="rx", dv=10, cd=f"{self.finger_attributes_ctl}.Twist", v=finger_values[4])
        cmds.setDrivenKeyframe(at="rx", dv=-10, cd=f"{self.finger_attributes_ctl}.Twist", v=finger_values[5])

        cmds.setDrivenKeyframe(at="rz", dv=0, cd=f"{self.finger_attributes_ctl}.Fan", v=0)
        cmds.setDrivenKeyframe(at="rz", dv=10, cd=f"{self.finger_attributes_ctl}.Fan", v=finger_values[6])
        cmds.setDrivenKeyframe(at="rz", dv=-10, cd=f"{self.finger_attributes_ctl}.Fan", v=finger_values[7])

        cmds.select(ctl)
        cmds.setDrivenKeyframe(at="rz", dv=0, cd=f"{self.finger_attributes_ctl}.Thumb_Curl", v=0)
        cmds.setDrivenKeyframe(at="rz", dv=10, cd=f"{self.finger_attributes_ctl}.Thumb_Curl", v=thumb_values[0])
        cmds.setDrivenKeyframe(at="rz", dv=-10, cd=f"{self.finger_attributes_ctl}.Thumb_Curl", v=thumb_values[1])

        cmds.setDrivenKeyframe(at="ry", dv=0, cd=f"{self.finger_attributes_ctl}.Thumb_Spread", v=0)
        cmds.setDrivenKeyframe(at="ry", dv=10, cd=f"{self.finger_attributes_ctl}.Thumb_Spread", v=thumb_values[2])
        cmds.setDrivenKeyframe(at="ry", dv=-10, cd=f"{self.finger_attributes_ctl}.Thumb_Spread", v=thumb_values[3])

        cmds.setDrivenKeyframe(at="rx", dv=0, cd=f"{self.finger_attributes_ctl}.Thumb_Twist", v=0)
        cmds.setDrivenKeyframe(at="rx", dv=10, cd=f"{self.finger_attributes_ctl}.Thumb_Twist", v=thumb_values[4])
        cmds.setDrivenKeyframe(at="rx", dv=-10, cd=f"{self.finger_attributes_ctl}.Thumb_Twist", v=thumb_values[5])

        cmds.setDrivenKeyframe(at="rz", dv=0, cd=f"{self.finger_attributes_ctl}.Thumb_Fan", v=0)
        cmds.setDrivenKeyframe(at="rz", dv=10, cd=f"{self.finger_attributes_ctl}.Thumb_Fan", v=thumb_values[6])
        cmds.setDrivenKeyframe(at="rz", dv=-10, cd=f"{self.finger_attributes_ctl}.Thumb_Fan", v=thumb_values[7])
        
    

