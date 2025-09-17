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

class FalangeModule(object):

    def __init__(self):

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")

    def hand_distribution(self, guide_name):      
        
        self.hand_guide = guide_import(guide_name, all_descendents=False, path=None)[0]
        if cmds.attributeQuery("moduleName", node=self.hand_guide, exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.hand_guide, listEnum=True)[0]
        else:
            self.enum_str = "———"

        self.side = guide_name.split("_")[0]


        self.individual_module_grp = cmds.createNode("transform", name=f"{self.side}_handModule_GRP", parent=self.modules_grp, ss=True)
        self.individual_controllers_grp = cmds.createNode("transform", name=f"{self.side}_handControllers_GRP", parent=self.masterWalk_ctl, ss=True)

        self.switch_ctl, self.switch_ctl_grp = controller_creator(
            name=f"{self.side}_hand",
            suffixes=["GRP"],
            lock=["sx", "sy", "sz", "visibility"],
            ro=False,
            parent=self.individual_controllers_grp
        )

        cmds.connectAttr(f"{self.hand_guide}.worldMatrix[0]", f"{self.switch_ctl_grp[0]}.offsetParentMatrix")

        
        cmds.addAttr(self.switch_ctl, shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.switch_ctl+".extraAttr", channelBox=True, lock=True)
        cmds.addAttr(self.switch_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(self.switch_ctl, shortName="bendysVis", niceName="Bendys Visibility", attributeType="bool", keyable=False)
        self.ik_visibility_rev = cmds.createNode("reverse", name=f"{self.side}_handFkVisibility_REV", ss=True)
        cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{self.ik_visibility_rev}.inputX")

        # Arm-specific setup
        if self.side == "L":
            self.primary_aim = "x"
            self.secondary_aim = "y"

        elif self.side == "R":
            self.primary_aim = "-x"
            self.secondary_aim = "-y"

        final_path = core.DataManager.get_guide_data()


        try:
            with open(final_path, "r") as infile:
                guides_data = json.load(infile)

        except Exception as e:
            om.MGlobal.displayError(f"Error loading guides data: {e}")

        for template_name, guides in guides_data.items():
            if not isinstance(guides, dict):
                continue

            for guide_name, guide_info in guides.items():
                if guide_info.get("parent") == self.hand_guide:
                    guides_pass = guide_import(guide_name, all_descendents=True, path=None)
                    self.names = [name.split("_")[1] for name in guides_pass]

                    self.make(guide_name=guides_pass)

                    
                    self.data_exporter.append_data(f"{self.side}_{self.names[0]}Module", 
                                        {"skinning_transform": self.skinnging_grp,
                                         "fk_ctls": self.fk_ctls,
                                         "pv_ctl": self.pv_ik_ctl,
                                         "root_ctl": self.root_ik_ctl,
                                         "end_ik": self.hand_ik_ctl,
                                         "settings_ctl": self.switch_ctl,
                                        }
                                        )




    def make(self, guide_name):

        self.guides = guide_name

        """
        Create a limb rig with controllers and constraints.
        This function sets up the basic structure for a limb, including controllers and constraints.
        """      
        self.skinnging_grp = cmds.createNode("transform", name=f"{self.side}_{self.names[0]}SkinningJoints_GRP", parent=self.skel_grp, ss=True)
        
        self.primary_aim_vector = om.MVector(AXIS_VECTOR[self.primary_aim])
        self.secondary_aim_vector = om.MVector(AXIS_VECTOR[self.secondary_aim])

        cmds.addAttr(self.skinnging_grp, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        #Position Joints
        order = [[self.guides[0], self.guides[1], self.guides[2]], [self.guides[1], self.guides[2], self.guides[0]], [self.guides[2], self.guides[3], self.guides[1]]]

        aim_matrix_guides = []

        for i in range(len(self.guides)-1):

            aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{self.names[i]}Guide_AMX", ss=True)

            cmds.setAttr(aim_matrix + ".primaryInputAxis", *self.primary_aim_vector, type="double3")
            cmds.setAttr(aim_matrix + ".secondaryInputAxis", *self.secondary_aim_vector, type="double3")
            cmds.setAttr(aim_matrix + ".secondaryTargetVector", 0,1,0, type="double3")
            
            cmds.setAttr(aim_matrix + ".primaryMode", 1)
            cmds.setAttr(aim_matrix + ".secondaryMode", 1)

            cmds.connectAttr(order[i][0] + ".worldMatrix[0]", aim_matrix + ".inputMatrix")
            cmds.connectAttr(order[i][1] + ".worldMatrix[0]", aim_matrix + ".primaryTargetMatrix")
            cmds.connectAttr(order[i][2] + ".worldMatrix[0]", aim_matrix + ".secondaryTargetMatrix")

            aim_matrix_guides.append(aim_matrix)

        
        blend_matrix = cmds.createNode("blendMatrix", name=f"{self.side}_{self.names[-1]}Guide_BLM", ss=True)
        cmds.connectAttr(f"{aim_matrix_guides[-1]}.outputMatrix", f"{blend_matrix}.inputMatrix", force=True)
        cmds.connectAttr(f"{self.guides[-1]}.worldMatrix[0]", f"{blend_matrix}.target[0].targetMatrix", force=True)
        cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].rotateWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].shearWeight", 0)

        self.guides_matrix = [aim_matrix_guides[0], aim_matrix_guides[1], aim_matrix_guides[2], blend_matrix]

        self.fk_rig()

        # self.ik_rig()


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

            if not i ==len(self.guides_matrix)-1:
                cmds.addAttr(ctl, shortName="strechySep", niceName="Strechy ———", enumName="———",attributeType="enum", keyable=True)
                cmds.setAttr(ctl+".strechySep", channelBox=True, lock=True)
                cmds.addAttr(ctl, shortName="stretch", niceName="Stretch",minValue=1,defaultValue=1, keyable=True)

                

            if not i == 0:
                subtract = cmds.createNode("subtract", name=f"{self.side}_{self.names[i]}FkOffset0{i}_SUB", ss=True)
                cmds.connectAttr(f"{self.fk_ctls[-1]}.stretch", f"{subtract}.input1")
                cmds.setAttr( f"{subtract}.input2", 1)
                cmds.connectAttr(f"{subtract}.output", f"{ctl_grp[0]}.tx")
                

                offset_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[i]}FkOffset0{i+1}_MMX", ss=True)
                inverse_matrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{self.names[i]}FkOffset0{i+1}_IMX", ss=True)
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

        self.fk_wm = [f"{ctl}.worldMatrix[0]" for ctl in self.fk_ctls]

        self.ik_rig()

    def ik_rig(self):
        """
        Create IK chain for the limb.
        This function creates an inverse kinematics chain for the limb, including controllers and constraints.
        """
        self.ik_controllers = cmds.createNode("transform", name=f"{self.side}_{self.names[0]}IkControllers_GRP", parent=self.individual_controllers_grp, ss=True)

        self.root_ik_ctl, self.root_ik_ctl_grp = controller_creator(
            name=f"{self.side}_{self.names[0]}RootIk",
            suffixes=["GRP", "ANM"],
            lock=["rx", "ry", "rz", "sx","sz","sy","visibility"],
            ro=True,
            parent=self.ik_controllers
        )
        self.pv_ik_ctl, self.pv_ik_ctl_grp = controller_creator(
            name=f"{self.side}_{self.names[1]}PV",
            suffixes=["GRP", "ANM"],
            lock=["rx", "ry", "rz", "sx","sz","sy","visibility"],
            ro=False,
            parent=self.ik_controllers

        )
        self.hand_ik_ctl, self.hand_ik_ctl_grp = controller_creator(
            name=f"{self.side}_{self.names[-1]}Ik",
            suffixes=["GRP", "ANM"],
            lock=["visibility"],
            ro=True,
            parent=self.ik_controllers

        )

        cmds.addAttr(self.hand_ik_ctl, shortName="attachedFk", niceName="Fk ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.hand_ik_ctl+".attachedFk", channelBox=True, lock=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="attachedFKVis", niceName="Attached FK Visibility", attributeType="bool", keyable=True)

        cmds.connectAttr(self.guides_matrix[-1] + ".outputMatrix", f"{self.hand_ik_ctl_grp[0]}.offsetParentMatrix")

        cmds.addAttr(self.pv_ik_ctl, shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.pv_ik_ctl+".extraAttr", channelBox=True, lock=True)
        
        cmds.connectAttr(f"{self.guides_matrix[0]}.outputMatrix", f"{self.root_ik_ctl_grp[0]}.offsetParentMatrix")      

        pv_pos_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[1]}PVPosition_MMX", ss=True)
        cmds.connectAttr(f"{self.guides_matrix[1]}.outputMatrix", f"{pv_pos_multMatrix}.matrixIn[1]")
        cmds.connectAttr(f"{pv_pos_multMatrix}.matrixSum", f"{self.pv_ik_ctl_grp[0]}.offsetParentMatrix")

        pv_pos_4b4 = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.names[1]}PVPosition_F4X", ss=True)
        cmds.connectAttr(f"{pv_pos_4b4}.output", f"{pv_pos_multMatrix}.matrixIn[0]")


        name = [f"{self.side}_{self.names[1]}SecondaryUpperInitialLength", f"{self.side}_{self.names[2]}SecondaryLowerInitialLength", f"{self.side}_{self.names[3]}SecondaryCurrentLength"]

        self.ikHandleManager = f"{self.hand_ik_ctl}.worldMatrix[0]"

        secondary_root_multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[1]}SecondaryRoot_MMX", ss=True)
        inverse_secondary_root = cmds.createNode("inverseMatrix", name=f"{self.side}_{self.names[1]}SecondaryRoot_IMX", ss=True)
        cmds.connectAttr(f"{self.guides_matrix[1]}.outputMatrix", f"{secondary_root_multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{self.guides_matrix[0]}.outputMatrix", f"{inverse_secondary_root}.inputMatrix")
        cmds.connectAttr(f"{inverse_secondary_root}.outputMatrix", f"{secondary_root_multmatrix}.matrixIn[1]")
        cmds.connectAttr(f"{self.root_ik_ctl}.worldMatrix[0]", f"{secondary_root_multmatrix}.matrixIn[2]")

        self.distance_between_output = []
        for i, (first, second) in enumerate(zip([f"{self.guides[1]}.worldMatrix[0]", f"{self.guides[2]}.worldMatrix[0]", f"{secondary_root_multmatrix}.matrixSum"], [f"{self.guides[2]}.worldMatrix[0]", f"{self.guides[3]}.worldMatrix[0]", f"{self.ikHandleManager}"])):
            distance = cmds.createNode("distanceBetween", name=f"{name[i]}_DB", ss=True)
            cmds.connectAttr(f"{first}", f"{distance}.inMatrix1")
            cmds.connectAttr(f"{second}", f"{distance}.inMatrix2")

            if i == 2:
                global_scale_divide = cmds.createNode("divide", name=f"{self.side}_{self.names[1]}SecondaryGlobalScaleFactor_DIV", ss=True)
                cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", f"{global_scale_divide}.input2")
                cmds.connectAttr(f"{distance}.distance", f"{global_scale_divide}.input1")
                self.distance_between_output.append(f"{global_scale_divide}.output")
            else:
                self.distance_between_output.append(f"{distance}.distance")

        distance_1 = cmds.getAttr(self.distance_between_output[0])
        distance_2 = cmds.getAttr(self.distance_between_output[1])

        pv_pos_sum = cmds.createNode("sum", name=f"{self.side}_{self.names[1]}PVPosition_SUM", ss=True)
        cmds.connectAttr(f"{self.distance_between_output[0]}", f"{pv_pos_sum}.input[0]")
        cmds.connectAttr(f"{self.distance_between_output[1]}", f"{pv_pos_sum}.input[1]")

        if self.side == "R":
            negate = cmds.createNode("negate", name=f"{self.side}_{self.names[1]}PVPosition_NEG", ss=True)
            cmds.connectAttr(f"{pv_pos_sum}.output", f"{negate}.input")
            cmds.connectAttr(f"{negate}.output", f"{pv_pos_4b4}.in31")
        else:
            cmds.connectAttr(f"{pv_pos_sum}.output", f"{pv_pos_4b4}.in31")

        # --- STRETCH --- #

        arm_length = cmds.createNode("sum", name=f"{self.side}_{self.names[1]}SecondaryLength_SUM", ss=True)
        cmds.connectAttr(f"{self.distance_between_output[0]}", f"{arm_length}.input[0]")
        cmds.connectAttr(f"{self.distance_between_output[1]}", f"{arm_length}.input[1]")

        arm_length_min = cmds.createNode("min", name=f"{self.side}_{self.names[1]}SecondaryClampedLength_MIN", ss=True)
        cmds.connectAttr(f"{arm_length}.output", f"{arm_length_min}.input[0]")
        cmds.connectAttr(f"{self.distance_between_output[2]}", f"{arm_length_min}.input[1]")


        # --- CUSTOM SOLVER --- #

        upper_divide, upper_arm_acos, power_mults = core.law_of_cosine(sides = [f"{self.distance_between_output[0]}", f"{self.distance_between_output[1]}", f"{arm_length_min}.output"], name = f"{self.side}_{self.names[1]}Upper", acos=True)
        lower_divide, lower_power_mults, negate_cos_value = core.law_of_cosine(sides = [f"{self.distance_between_output[0]}", f"{arm_length_min}.output", f"{self.distance_between_output[1]}"],
                                                                            power = [power_mults[0], power_mults[2], power_mults[1]],
                                                                            name = f"{self.side}_{self.names[1]}Lower", 
                                                                            negate=True)

        # --- Aligns --- #

        upper_arm_ik_aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{self.names[1]}SecondaryUpperIk_AIM", ss=True)
        cmds.connectAttr(f"{self.ikHandleManager}", f"{upper_arm_ik_aim_matrix}.primaryTargetMatrix")
        cmds.connectAttr(f"{self.pv_ik_ctl}.worldMatrix", f"{upper_arm_ik_aim_matrix}.secondaryTargetMatrix")
        cmds.connectAttr(f"{secondary_root_multmatrix}.matrixSum", f"{upper_arm_ik_aim_matrix}.inputMatrix")
        cmds.setAttr(f"{upper_arm_ik_aim_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")

        self.upperArmIkWM = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[1]}SecondaryUpperIkWM_MMX", ss=True)
        fourByfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.names[1]}SecondaryUpperIkLocal_F4X", ss=True)
        sin = cmds.createNode("sin", name=f"{self.side}_{self.names[1]}SecondaryUpperIkWM_SIN", ss=True)
        negate = cmds.createNode("negate", name=f"{self.side}_{self.names[1]}SecondaryUpperIkWM_NEGATE", ss=True)

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

        cosValueSquared = cmds.createNode("multiply", name=f"{self.side}_{self.names[2]}SecondaryLowerCosValueSquared_MUL", ss=True)
        cmds.connectAttr(f"{lower_divide}.output", f"{cosValueSquared}.input[0]")
        cmds.connectAttr(f"{lower_divide}.output", f"{cosValueSquared}.input[1]")

        lower_sin_value_squared = cmds.createNode("subtract", name=f"{self.side}_{self.names[2]}SecondaryLowerSinValueSquared_SUB", ss=True)
        cmds.connectAttr(f"{cosValueSquared}.output", f"{lower_sin_value_squared}.input2")
        cmds.setAttr(f"{lower_sin_value_squared}.input1", 1)

        lower_sin_value_squared_clamped = cmds.createNode("max", name=f"{self.side}_{self.names[2]}SecondaryLowerSinValueSquared_MAX", ss=True)
        cmds.connectAttr(f"{lower_sin_value_squared}.output", f"{lower_sin_value_squared_clamped}.input[1]")
        self.floatConstant_zero = cmds.createNode("floatConstant", name=f"{self.side}_zero{self.names[2]}_FLC", ss=True)
        cmds.setAttr(f"{self.floatConstant_zero}.inFloat", 0)
        cmds.connectAttr(f"{self.floatConstant_zero}.outFloat", f"{lower_sin_value_squared_clamped}.input[0]")

        lower_sin = cmds.createNode("power", name=f"{self.side}_{self.names[2]}SecondaryLowerSin_POW", ss=True)
        cmds.connectAttr(f"{lower_sin_value_squared_clamped}.output", f"{lower_sin}.input")
        cmds.setAttr(f"{lower_sin}.exponent", 0.5)

        negate = cmds.createNode("negate", name=f"{self.side}_{self.names[2]}SecondaryLowerSin_NEGATE", ss=True)
        cmds.connectAttr(f"{lower_sin}.output", f"{negate}.input")

        fourByfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.names[2]}SecondaryLowerIkLocal_F4X", ss=True)
    
        cmds.connectAttr(f"{negate_cos_value}.output", f"{fourByfour}.in11")
        cmds.connectAttr(f"{negate_cos_value}.output", f"{fourByfour}.in00")
        cmds.connectAttr(f"{lower_sin}.output", f"{fourByfour}.in10")
        cmds.connectAttr(f"{negate}.output", f"{fourByfour}.in01")

        if self.side == "R":
            translate_negate = cmds.createNode("negate", name=f"{self.side}_{self.names[2]}SecondaryUpperTranslate_NEGATE", ss=True)
            cmds.connectAttr(f"{self.distance_between_output[0]}", f"{translate_negate}.input")
            cmds.connectAttr(f"{translate_negate}.output", f"{fourByfour}.in30")
            cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryInputAxis", 0, -1, 0, type="double3") ########################## CAMBIO QUIZAS

        else:
            cmds.connectAttr(f"{self.distance_between_output[0]}", f"{fourByfour}.in30")
            cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryInputAxis", 0, 1, 0, type="double3") ########################## CAMBIO QUIZAS


        lower_wm_multmatrix_end = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[2]}WM_MMX", ss=True)
        cmds.connectAttr(f"{fourByfour}.output", f"{lower_wm_multmatrix_end}.matrixIn[0]")
        cmds.connectAttr(f"{self.upperArmIkWM}.matrixSum", f"{lower_wm_multmatrix_end}.matrixIn[1]")

        # Hand

        lower_inverse_matrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{self.names[3]}LowerIkInverse_MTX", ss=True)
        cmds.connectAttr(f"{lower_wm_multmatrix_end}.matrixSum", f"{lower_inverse_matrix}.inputMatrix")

        hand_local_matrix_multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[3]}EndBaseLocal_MMX", ss=True)
        cmds.connectAttr(f"{self.ikHandleManager}", f"{hand_local_matrix_multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{lower_inverse_matrix}.outputMatrix", f"{hand_local_matrix_multmatrix}.matrixIn[1]")

        hand_local_matrix = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.names[3]}EndLocal_F4X", ss=True)

        hand_wm_multmatrix_end = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[3]}WM_MMX", ss=True)
        cmds.connectAttr(f"{hand_local_matrix}.output", f"{hand_wm_multmatrix_end}.matrixIn[0]")
        cmds.connectAttr(f"{lower_wm_multmatrix_end}.matrixSum", f"{hand_wm_multmatrix_end}.matrixIn[1]")


        for i in range(0, 3):
            row_from_matrix = cmds.createNode("rowFromMatrix", name=f"{self.side}_{self.names[3]}EndLocalAxis{i}_RFM", ss=True)
            cmds.connectAttr(f"{hand_local_matrix_multmatrix}.matrixSum", f"{row_from_matrix}.matrix")
            cmds.setAttr(f"{row_from_matrix}.input", i)
            for z, attr in enumerate(["X", "Y", "Z", "W"]):
                cmds.connectAttr(f"{row_from_matrix}.output{attr}", f"{hand_local_matrix}.in{i}{z}")

        if self.side == "R":
            translate_negate = cmds.createNode("negate", name=f"{self.side}_{self.names[3]}LowerTranslate_NEGATE", ss=True)
            cmds.connectAttr(f"{self.distance_between_output[1]}", f"{translate_negate}.input")
            cmds.connectAttr(f"{translate_negate}.output", f"{hand_local_matrix}.in30")
        else:
            cmds.connectAttr(f"{self.distance_between_output[1]}", f"{hand_local_matrix}.in30")      

        name = [f"{self.side}_{self.names[0]}UpperInitialLength", f"{self.side}_{self.names[1]}LowerInitialLength", f"{self.side}_{self.names[0]}CurrentLength"]


        self.ikHandleManager = f"{lower_wm_multmatrix_end}.matrixSum"
        
        self.distance_between_output = []
        for i, (first, second) in enumerate(zip([f"{self.guides[0]}.worldMatrix[0]", f"{self.guides[1]}.worldMatrix[0]", f"{self.root_ik_ctl}.worldMatrix[0]"], [f"{self.guides[1]}.worldMatrix[0]", f"{self.guides[2]}.worldMatrix[0]", f"{self.ikHandleManager}"])):
            distance = cmds.createNode("distanceBetween", name=f"{name[i]}_DB", ss=True)
            cmds.connectAttr(f"{first}", f"{distance}.inMatrix1")
            cmds.connectAttr(f"{second}", f"{distance}.inMatrix2")

            if i == 2:
                global_scale_divide = cmds.createNode("divide", name=f"{self.side}_{self.names[0]}GlobalScaleFactor_DIV", ss=True)
                cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", f"{global_scale_divide}.input2")
                cmds.connectAttr(f"{distance}.distance", f"{global_scale_divide}.input1")
                self.distance_between_output.append(f"{global_scale_divide}.output")
            else:
                self.distance_between_output.append(f"{distance}.distance")
            

        # --- STRETCH --- #

        arm_length = cmds.createNode("sum", name=f"{self.side}_{self.names[0]}Length_SUM", ss=True)
        cmds.connectAttr(f"{self.distance_between_output[0]}", f"{arm_length}.input[0]")
        cmds.connectAttr(f"{self.distance_between_output[1]}", f"{arm_length}.input[1]")

        arm_length_min = cmds.createNode("min", name=f"{self.side}_{self.names[0]}ClampedLength_MIN", ss=True)
        cmds.connectAttr(f"{arm_length}.output", f"{arm_length_min}.input[0]")
        cmds.connectAttr(f"{self.distance_between_output[2]}", f"{arm_length_min}.input[1]")



        # --- CUSTOM SOLVER --- #

        upper_divide, upper_arm_acos, power_mults = core.law_of_cosine(sides = [f"{self.distance_between_output[0]}", f"{self.distance_between_output[1]}", f"{arm_length_min}.output"], name = f"{self.side}_{self.names[0]}Upper", acos=True)
        lower_divide, lower_power_mults, negate_cos_value = core.law_of_cosine(sides = [f"{self.distance_between_output[0]}", f"{arm_length_min}.output", f"{self.distance_between_output[1]}"],
                                                                             power = [power_mults[0], power_mults[2], power_mults[1]],
                                                                             name = f"{self.side}_{self.names[0]}Lower", 
                                                                             negate=True)

        # --- Aligns --- #
 
        upper_arm_ik_aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{self.names[0]}UpperIk_AIM", ss=True)
        cmds.connectAttr(f"{self.ikHandleManager}", f"{upper_arm_ik_aim_matrix}.primaryTargetMatrix")
        cmds.connectAttr(f"{self.pv_ik_ctl}.worldMatrix", f"{upper_arm_ik_aim_matrix}.secondaryTargetMatrix")
        cmds.connectAttr(f"{self.root_ik_ctl}.worldMatrix", f"{upper_arm_ik_aim_matrix}.inputMatrix")
        cmds.setAttr(f"{upper_arm_ik_aim_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")

        self.upperArmIkWM = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[0]}WM_MMX", ss=True)
        fourByfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.names[0]}UpperIkLocal_F4X", ss=True)
        sin = cmds.createNode("sin", name=f"{self.side}_{self.names[0]}UpperIkWM_SIN", ss=True)
        negate = cmds.createNode("negate", name=f"{self.side}_{self.names[0]}UpperIkWM_NEGATE", ss=True)

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

        cosValueSquared = cmds.createNode("multiply", name=f"{self.side}_{self.names[1]}LowerCosValueSquared_MUL", ss=True)
        cmds.connectAttr(f"{lower_divide}.output", f"{cosValueSquared}.input[0]")
        cmds.connectAttr(f"{lower_divide}.output", f"{cosValueSquared}.input[1]")

        lower_sin_value_squared = cmds.createNode("subtract", name=f"{self.side}_{self.names[1]}LowerSinValueSquared_SUB", ss=True)
        cmds.connectAttr(f"{cosValueSquared}.output", f"{lower_sin_value_squared}.input2")
        cmds.setAttr(f"{lower_sin_value_squared}.input1", 1)

        lower_sin_value_squared_clamped = cmds.createNode("max", name=f"{self.side}_{self.names[1]}LowerSinValueSquared_MAX", ss=True)
        cmds.connectAttr(f"{lower_sin_value_squared}.output", f"{lower_sin_value_squared_clamped}.input[1]")
        cmds.connectAttr(f"{self.floatConstant_zero}.outFloat", f"{lower_sin_value_squared_clamped}.input[0]")


        lower_sin = cmds.createNode("power", name=f"{self.side}_{self.names[1]}LowerSin_POW", ss=True)
        cmds.connectAttr(f"{lower_sin_value_squared_clamped}.output", f"{lower_sin}.input")
        cmds.setAttr(f"{lower_sin}.exponent", 0.5)

        negate = cmds.createNode("negate", name=f"{self.side}_{self.names[1]}LowerSin_NEGATE", ss=True)
        cmds.connectAttr(f"{lower_sin}.output", f"{negate}.input")

        fourByfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.names[1]}LowerIkLocal_F4X", ss=True)
      
        cmds.connectAttr(f"{negate_cos_value}.output", f"{fourByfour}.in11")
        cmds.connectAttr(f"{negate_cos_value}.output", f"{fourByfour}.in00")
        cmds.connectAttr(f"{lower_sin}.output", f"{fourByfour}.in10")
        cmds.connectAttr(f"{negate}.output", f"{fourByfour}.in01")

        if self.side == "R":
            translate_negate = cmds.createNode("negate", name=f"{self.side}_{self.names[1]}UpperTranslate_NEGATE", ss=True)
            cmds.connectAttr(f"{self.distance_between_output[0]}", f"{translate_negate}.input")
            cmds.connectAttr(f"{translate_negate}.output", f"{fourByfour}.in30")
            cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryInputAxis", 0, -1, 0, type="double3") ########################## CAMBIO QUIZAS

        else:
            cmds.connectAttr(f"{self.distance_between_output[0]}", f"{fourByfour}.in30")
            cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryInputAxis", 0, 1, 0, type="double3") ########################## CAMBIO QUIZAS


        lower_wm_multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[1]}WM_MMX", ss=True)
        cmds.connectAttr(f"{fourByfour}.output", f"{lower_wm_multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{self.upperArmIkWM}.matrixSum", f"{lower_wm_multmatrix}.matrixIn[1]")

        # Hand

       
        self.ik_wm = [f"{self.upperArmIkWM}.matrixSum", f"{lower_wm_multmatrix}.matrixSum", f"{lower_wm_multmatrix_end}.matrixSum", f"{hand_wm_multmatrix_end}.matrixSum"]
        
        self.attached_fk()

    def attached_fk(self):
        """
        Creates the attached FK controllers for the neck module, including sub-neck controllers and joints.

        Args:
            self: Instance of the SpineModule class.
        Returns:
            list: A list of sub-neck joint names created for the attached FK system.
        """
        
        ctls_sub_neck = []
        # sub_neck_ctl_trn = cmds.createNode("transform", n=f"{self.side}_sub{self.names[0]}Controllers_GRP", parent=self.individual_controllers_grp, ss=True)


        for i, joint in enumerate(self.ik_wm):
            name = joint.split(".")[0].split("_")[1]

            ctl, controller_grp = controller_creator(
                name=f"{self.side}_{name}AttachedFk",
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=ctls_sub_neck[-1] if ctls_sub_neck else self.individual_controllers_grp
            )

            if i == 0:
                cmds.setAttr(f"{controller_grp[0]}.inheritsTransform", 0)
                cmds.connectAttr(f"{self.hand_ik_ctl}.attachedFKVis", f"{controller_grp[0]}.visibility")
                cmds.connectAttr(f"{joint}", f"{controller_grp[0]}.offsetParentMatrix")

            else:
                mmt = cmds.createNode("multMatrix", n=f"{self.side}_{name}SubAttachedFk0{i+1}_MMT")

                inverse = cmds.createNode("inverseMatrix", n=f"{self.side}_{name}SubAttachedFk0{i+1}_IMX")
                cmds.connectAttr(f"{self.ik_wm[i-1]}", f"{inverse}.inputMatrix")
                cmds.connectAttr(f"{joint}", f"{mmt}.matrixIn[0]")
                cmds.connectAttr(f"{inverse}.outputMatrix", f"{mmt}.matrixIn[1]")
                cmds.connectAttr(f"{mmt}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix")

                for attr in ["translateX","translateY","translateZ", "rotateX", "rotateY", "rotateZ"]:
                    cmds.setAttr(f"{controller_grp[0]}.{attr}", 0)

            ctls_sub_neck.append(ctl)

        self.ik_wm = [f"{ctl}.worldMatrix[0]" for ctl in ctls_sub_neck]

        self.pairblends()

    def pairblends(self):

        cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{self.fk_grps[0][0]}.visibility", force=True)
        cmds.connectAttr(f"{self.ik_visibility_rev}.outputX", f"{self.ik_controllers}.visibility")


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

        self.shoulder_rotate_matrix = self.blend_wm[0]
        self.blend_wm[0] = f"{nonRollAim}.outputMatrix"

        self.bendys()

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
        self.bendy_controllers = cmds.createNode("transform", name=f"{self.side}_{self.names[1]}BendyControllers_GRP", parent=self.individual_controllers_grp, ss=True)
        cmds.connectAttr(f"{self.switch_ctl}.bendysVis", f"{self.bendy_controllers}.visibility")
        cmds.setAttr(f"{self.bendy_controllers}.inheritsTransform", 0)
        

        for i, bendy in enumerate(["UpperBendy", "MiddleBendy", "LowerBendy"]):
            ctl, ctl_grp = controller_creator(
                name=f"{self.side}_{self.names[i]}{bendy}",
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
            )

            cmds.parent(ctl_grp[0], self.bendy_controllers)

            initial_matrix = self.shoulder_rotate_matrix if i == 0 else self.blend_wm[i]

            blendMatrix = cmds.createNode("blendMatrix", name=f"{self.side}_{self.names[i]}{bendy}_BLM", ss=True)
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

 
            de_boors_002.de_boor_ribbon(aim_axis=self.primary_aim, up_axis=self.secondary_aim, cvs= cvMatrices, num_joints=self.twist_number, name = f"{self.side}_{self.names[i]}{bendy}", parent=self.skinnging_grp, custom_parm=t_values)

            if bendy == "LowerBendy":
                joint = cmds.createNode("joint", name= f"{self.side}_{self.names[i]}{bendy}0{self.twist_number+1}_JNT", ss=True, parent=self.skinnging_grp)
                cmds.connectAttr(f"{cvMatrices[-1]}", f"{joint}.offsetParentMatrix")



# cmds.file(new=True, force=True)

# core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/test_03.guides")
# core.DataManager.set_ctls_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/curves/AYCHEDRAL_curves_001.json")

# basic_structure.create_basic_structure(asset_name="dragon")
# a = falangeModule("L_firstMetacarpal_GUIDE").make()
