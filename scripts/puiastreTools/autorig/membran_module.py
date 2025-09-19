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

class MembraneModule(object):

    def __init__(self):
        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")
        self.muscle_locators = self.data_exporter.get_data("basic_structure", "muscleLocators_GRP")
    
    def number_to_ordinal_word(n):
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
        
        self.primary_aim_vector = om.MVector(AXIS_VECTOR[self.primary_aim])
        self.secondary_aim_vector = om.MVector(AXIS_VECTOR[self.secondary_aim])

        self.guides = guide_import(guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]

        cmds.addAttr(self.skinnging_grp, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)


        self.main_membrane_guide = [[self.guides[0], self.guides[1]], [self.guides[2], self.guides[3]]]
        self.secondary_membrane_guides = [self.guides[4 + i:4 + i + 3] for i in range(0, len(self.guides[4:]), 3)]

        for i, list in enumerate(self.secondary_membrane_guides):

            self.secondary_membranes(list, i)



    def secondary_membranes(self, guides_list, input):

        print("Creating secondary membrane")
        print(guides_list)
        print(input)
        print(self.number_to_ordinal_word(input + 1))
        self.muscle_locators = self.data_exporter.get_data("basic_structure", "muscleLocators_GRP")








# cmds.file(new=True, force=True)

# core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/AYCHEDRAL_002.guides")
# core.DataManager.set_ctls_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/curves/AYCHEDRAL_curves_001.json")

# basic_structure.create_basic_structure(asset_name="dragon")
# a = MembraneModule().make("L_primaryMembran01_GUIDE")
