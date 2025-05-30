import sys
import os
import maya.cmds as cmds
from functools import partial
from importlib import reload
from puiastreTools.utils import basic_structure


def reload_ui(*args):
    """
    Function to reload the Puiastre Productions UI.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    from puiastreTools.ui import option_menu
    reload(option_menu)
    option_menu.puiastre_ui()

def export_guides(*args): 
    """
    Function to export selected guides from the scene.

    Args:
        *args: Variable length argument list, not used in this function.
    """ 
    from puiastreTools.utils import guides_manager 
    reload(guides_manager)
    guides_manager.guides_export()

def import_guides(*args, value=None): 
    """
    Function to import guides into the scene. If value is True, imports all guides; if None, opens an option box.

    Args:
        *args: Variable length argument list, not used in this function.
        value (bool, optional): If True, imports all guides. If None, opens an option box. Defaults to None.
    """
    from puiastreTools.utils import guides_manager
    if value == True:   
        reload(guides_manager)
        guides_manager.guide_import(joint_name = "all")

def complete_rig(*args):
    """
    Function to build a complete rig using the rig builder module.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    from puiastreTools.autorig import rig_builder
    reload(rig_builder)
    rig_builder.make()

def export_curves(*args): 
    """
    Function to export all controller curves data.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    from puiastreTools.tools import curve_tool  
    reload(curve_tool)
    curve_tool.get_all_ctl_curves_data()

def mirror_ctl(*args): 
    """
    Function to mirror all left controller shapes to their right counterparts.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    from puiastreTools.tools import curve_tool  
    reload(curve_tool)
    curve_tool.mirror_all_L_CTL_shapes()

def puiastre_ui():
    """
    Create the Puiastre Productions menu in Maya.
    """

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
    cmds.menuItem(label="   Export all controllers", command=export_curves)
    cmds.menuItem(label="   Mirror all L_ to R_", command=mirror_ctl)
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Rig", subMenu=True, tearOff=True, boldFont=True, image="rig.png")
    cmds.menuItem(label="   Complete Rig (dev only)", command=complete_rig)
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
