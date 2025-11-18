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
from puiastreTools.ui import project_manager

reload(option_menu)
reload(guide_creation)
reload(rig_builder)
reload(curve_tool)
reload(project_manager)

FILE_PATH = os.path.dirname(os.path.abspath(__file__)).split("\scripts")[0]


def vectorify_ui_call(*args):
    """
    Function to launch the Vectorify UI.

    This function imports the vectorify module, reloads it to ensure the latest version is used,
    and then calls the vectorify_ui function to display the UI.
    """
    from puiastreTools.tools import vectorify
    reload(vectorify)
    vectorify.vectorify_ui()

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

def build_rig(*args, asset_name = None):

    """
    Function to build a complete rig using the rig builder module.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    reload(rig_builder)
    if asset_name:
        rig_builder.make(asset_name)
    else:
        rig_builder.make(latest=True)


def export_curves(*args, curves_path): 
    """
    Function to export all controller curves data.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    core.load_data()
    curve_tool.get_all_ctl_curves_data()

def mirror_ctl(*args): 
    """
    Function to mirror all left controller shapes to their right counterparts.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    curve_tool.mirror_shapes()

def import_guides(*args, asset_name=None): 
    """
    Function to import guides into the scene. If value is True, imports all guides; if None, opens an option box.

    Args:
        *args: Variable length argument list, not used in this function.
        value (bool, optional): If True, imports all guides. If None, opens an option box. Defaults to None.
    """
    project_manager.load_asset_configuration(asset_name)
    guide_creation.load_guides()

def export_guides(*args): 
    """
    Function to export selected guides from the scene.

    Args:
        *args: Variable length argument list, not used in this function.
    """ 
    guide_creation.guides_export()

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

    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)


    cmds.menuItem(label="   Guides", subMenu=True, tearOff=True, boldFont=True, image="puiastreJoint.png")
    cmds.menuItem(label="   Export selected Guides", command=export_guides)
    cmds.menuItem(label="   Import Guides", subMenu=True, tearOff=True)
    cmds.menuItem(label="   Aychedral Guides", command=partial(import_guides, asset_name="aychedral"))
    cmds.menuItem(label="   Varyndor Guides", command=partial(import_guides, asset_name="varyndor"))
    cmds.menuItem(label="   Maiasaura Guides", command=partial(import_guides, asset_name="maiasaura"))
    cmds.menuItem(label="   Cheetah Guides", command=partial(import_guides, asset_name="cheetah"))
    cmds.menuItem(label="   Moana Guides", command=partial(import_guides, asset_name="moana"))
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Controls", subMenu=True, tearOff=True, boldFont=True, image="controllers.png")
    cmds.menuItem(label="   Export all controllers", command=partial(export_curves, curves_path=curves_path))
    cmds.menuItem(label="   Mirror all L_ to R_", command=mirror_ctl)
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Rig", subMenu=True, tearOff=True, boldFont=True, image="rig.png")
    cmds.menuItem(label="   Aychedral Rig", command=partial(build_rig, asset_name="aychedral"))
    cmds.menuItem(label="   Varyndor Rig", command=partial(build_rig, asset_name="varyndor"))
    cmds.menuItem(label="   Maiasaura Rig", command=partial(build_rig, asset_name="maiasaura"))
    cmds.menuItem(label="   Cheetah Rig", command=partial(build_rig, asset_name="cheetah"))
    cmds.menuItem(label="   Moana Rig", command=partial(build_rig, asset_name="moana"))
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Animation", subMenu=True, tearOff=True, boldFont=True)
    cmds.menuItem(label="   Vectorify", command=vectorify_ui_call)
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Skin Cluster", subMenu=True, tearOff=True, boldFont=True)
    cmds.menuItem(label="   Export Skin Data")
    cmds.menuItem(label="   Import Skin Data")
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.setParent("..", menu=True)
