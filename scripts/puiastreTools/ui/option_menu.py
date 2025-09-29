import maya.cmds as cmds
from functools import partial
import os
from importlib import reload

from puiastreTools.ui import option_menu
from puiastreTools.utils import guide_creation 
from puiastreTools.autorig import rig_builder
from puiastreTools.utils import curve_tool 
from puiastreTools.utils import basic_structure
from puiastreTools.utils import core

reload(option_menu)
reload(guide_creation)
reload(rig_builder)
reload(curve_tool)


def reload_ui(*args):
    """
    Function to reload the Puiastre Productions UI.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    reload(option_menu)
    option_menu.puiastre_ui()

def export_guides(*args): 
    """
    Function to export selected guides from the scene.

    Args:
        *args: Variable length argument list, not used in this function.
    """ 
    guide_creation.guides_export()

def import_guides(*args, value=None): 
    """
    Function to import guides into the scene. If value is True, imports all guides; if None, opens an option box.

    Args:
        *args: Variable length argument list, not used in this function.
        value (bool, optional): If True, imports all guides. If None, opens an option box. Defaults to None.
    """
    if value == True:   
        guide_creation.guide_import(joint_name = "all")

def complete_rig(*args):
    """
    Function to build a complete rig using the rig builder module.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    reload(rig_builder)
    rig_builder.make()

def build_eye(*args):
    """
    Function to build an eye rig using the rig builder module.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    from puiastreTools.autorig import eye_module_matrix
    reload(eye_module_matrix)

    cmds.file(new=True, force=True)

    #Uni
    # core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/AYCHEDRAL_007.guides")
    # core.DataManager.set_ctls_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/curves/AYCHEDRAL_curves_001.json")

    #Laia
    core.DataManager.set_guide_data("C:/3ero/TFG/puiastre_tools/guides/AYCHEDRAL_007.guides")
    core.DataManager.set_ctls_data("C:/3ero/TFG/puiastre_tools/curves/AYCHEDRAL_curves_001.json")


    basic_structure.create_basic_structure()
    eye_module_matrix.EyelidModule("L_eyeDown01_GUIDE").make()

def export_curves(*args, curves_path): 
    """
    Function to export all controller curves data.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    curve_tool.init_template_file(curves_path)
    curve_tool.get_all_ctl_curves_data()

def mirror_ctl(*args): 
    """
    Function to mirror all left controller shapes to their right counterparts.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    curve_tool.mirror_all_L_CTL_shapes()

def puiastre_ui():
    """
    Create the Puiastre Productions menu in Maya.
    """

    complete_path = os.path.realpath(__file__)
    relative_path = complete_path.split("\scripts")[0]
    curves_path = os.path.join(relative_path, "curves", "AYCHEDRAL_curves_001.json") 

    if cmds.menu("PuiastreMenu", exists=True):
        cmds.deleteUI("PuiastreMenu")
    cmds.menu("PuiastreMenu", label="Puiastre Productions", tearOff=True, parent="MayaWindow")

    cmds.menuItem(label="   Settings", subMenu=True, tearOff=True, boldFont=True, image="puiastreLogo.png")
    cmds.menuItem(label="   Reload UI", command=reload_ui)

    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)


    cmds.menuItem(label="   Guides", subMenu=True, tearOff=True, boldFont=True, image="puiastreJoint.png")
    cmds.menuItem(label="   Export selected Guides", command=export_guides)
    cmds.menuItem(label="   Import Guides", command=partial(import_guides, value = True))
    cmds.menuItem(label="   Import selected Guides", optionBox=True, command=partial(import_guides, value = None))
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Controls", subMenu=True, tearOff=True, boldFont=True, image="controllers.png")
    cmds.menuItem(label="   Export all controllers", command=partial(export_curves, curves_path=curves_path))
    cmds.menuItem(label="   Mirror all L_ to R_", command=mirror_ctl)
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Rig", subMenu=True, tearOff=True, boldFont=True, image="rig.png")
    cmds.menuItem(label="   Complete Rig (dev only)", command=complete_rig)
    cmds.menuItem(label="   Build eye", command=build_eye)
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Animation", subMenu=True, tearOff=True, boldFont=True)
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Skin Cluster", subMenu=True, tearOff=True, boldFont=True)
    cmds.menuItem(label="   Export Skin Data")
    cmds.menuItem(label="   Import Skin Data")
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.setParent("..", menu=True)
