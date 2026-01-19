import maya.cmds as cmds
import maya.api.OpenMaya as om2
from functools import partial
import os
from importlib import reload
import traceback

from puiastreTools.ui import option_menu
from puiastreTools.utils import guide_creation 
from puiastreTools.autorig import rig_builder
from puiastreTools.utils import curve_tool 
from puiastreTools.utils import basic_structure
from puiastreTools.utils import core
from puiastreTools.ui import project_manager
from puiastreTools.tools import skincluster_manager
from puiastreTools.tools import copy_skinweights

reload(option_menu)
reload(guide_creation)
reload(rig_builder)
reload(curve_tool)
reload(project_manager)
reload(skincluster_manager)

FILE_PATH = os.path.dirname(os.path.abspath(__file__)).split("\scripts")[0]

def copy_skinweights_ui_call(*args):
    """
    Function to launch the Copy Skin Weights UI.

    This function imports the copy_skinweights module, reloads it to ensure the latest version is used,
    and then calls the copy_skinweights_ui function to display the UI.
    """
    reload(copy_skinweights)
    copy_skinweights.transfer_multi_skin_clusters()

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



def build_rig(*args):

    """
    Function to build a complete rig using the rig builder module.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    try:
        reload(rig_builder)
        rig_builder.make()
    except Exception:
        traceback.print_exc()

def asset_manager(*args):
    """
    Function to open the Asset Manager UI.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    reload(project_manager)
    project_manager.show()


def export_curves(*args): 
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

def usdAnimTool(*args):
    """
    Function to launch the USD Animation Tool UI.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    from puiastreTools.tools import usdAnimation
    reload(usdAnimation)
    usdAnimation.showUSDAnimationUI()

def replace_shapes(*args):

    """
    Funtion to replace the selected shapes with the first selection.
    Args:
        *args: Variable length argument list, not used in this function.
    """

    curve_tool.replace_shape_colored()

def import_guides(*args): 
    """
    Function to import guides into the scene. If value is True, imports all guides; if None, opens an option box.

    Args:
        *args: Variable length argument list, not used in this function.
        value (bool, optional): If True, imports all guides. If None, opens an option box. Defaults to None.
    """
    reload(guide_creation)
    guide_creation.load_guides()

def export_guides(*args, mirror = False): 
    """
    Function to export selected guides from the scene.

    Args:
        *args: Variable length argument list, not used in this function.
    """ 
    reload(guide_creation)
    core.load_data()
    om2.MGlobal.displayInfo(f"Exporting guides with mirror set to {mirror}")
    guide_creation.guides_export(mirror=mirror)


def export_skincluster(*args): 
    """
    Function to export skin cluster data from the scene.

    Args:
        *args: Variable length argument list, not used in this function.
    """ 
    core.load_data()
    path = core.DataManager.get_skinning_data()
    skincluster_manager.SkinIO().export_skins(file_path = path)

def adonis_ui_call(*args):
    """
    Function to launch the Adonis Tool UI.

    Args:
        *args: Variable length argument list, not used in this function.
    """
    from puiastreTools.tools import adonis_tool
    reload(adonis_tool)
    adonis_tool.show_adonis_ui()


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

    cmds.menuItem(label="   Asset Manager", boldFont=True, image="rig.png", command=asset_manager)
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)     

    cmds.menuItem(label="   Guides", subMenu=True, tearOff=True, boldFont=True, image="puiastreJoint.png")
    cmds.menuItem(label="Export Guides", command=export_guides)
    cmds.menuItem(optionBox=True, command=partial(export_guides, mirror=True), label="Export Mirrored Guides")

    cmds.menuItem(label="   Import Guides", command=partial(import_guides))
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Controls", subMenu=True, tearOff=True, boldFont=True, image="controllers.png")
    cmds.menuItem(label="   Export all controllers", command=partial(export_curves))
    cmds.menuItem(label="   Mirror all L_ to R_", command=mirror_ctl)
    cmds.menuItem(label="   Replace Shapes", command=replace_shapes)
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Build Rig", boldFont=True, image="rig.png", command=build_rig)
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)
    
    cmds.menuItem(label="   Skinning Tools", subMenu=True, tearOff=True, boldFont=True)
    cmds.menuItem(label="   Export Skin Cluster", command=export_skincluster)
    cmds.menuItem(label="   Copy Skin Cluster", command=copy_skinweights_ui_call)
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Animation", subMenu=True, tearOff=True, boldFont=True)
    cmds.menuItem(label="   USD Exporter", command=usdAnimTool)
    cmds.menuItem(label="   Vectorify", command=vectorify_ui_call)
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Adonis Tool", boldFont=True, image="rig.png", command=adonis_ui_call)
    cmds.setParent("PuiastreMenu", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)



    cmds.setParent("..", menu=True)
