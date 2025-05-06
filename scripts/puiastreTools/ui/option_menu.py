import sys
import os
import maya.cmds as cmds
from functools import partial
from importlib import reload
from puiastreTools.ui import option_menu
from puiastreTools.utils import guides_manager
from puiastreTools.autorig import leg_module
from puiastreTools.autorig import finger_module
from puiastreTools.autorig import wing_arm_module
from puiastreTools.tools import curve_tool
from puiastreTools.utils import data_export

def reload_ui(*args):
    reload(option_menu)
    option_menu.puiastre_ui()

def export_guides(*args):   
    reload(guides_manager)
    guides_manager.guides_export()

def import_guides(*args, value=None): 
    if value == True:   
        reload(guides_manager)
        guides_manager.guide_import(joint_name = "all")

def leg_module(*args):
    reload(leg_module)
    module = leg_module.LegModule()
    module.make(side = "L")

def finger_module(*args):
    reload(finger_module)
    data_export_func()
    module = finger_module.FingerModule()
    module.make(side = "L")

def arm_module(*args):
    reload(wing_arm_module)
    module = wing_arm_module.WingArmModule()
    module.make(side = "L")

def export_curves(*args):   
    reload(curve_tool)
    curve_tool.get_all_ctl_curves_data()

def data_export_func(*args):   
    reload(data_export)
    exporter = data_export.DataExport()
    exporter.new_build()  # Clears the cache


def puiastre_ui():

    if cmds.menu("PuiastreMenu", exists=True):
        cmds.deleteUI("PuiastreMenu")
    cmds.menu("PuiastreMenu", label="Puiastre Productions", tearOff=True, parent="MayaWindow")

    cmds.menuItem(label="   Settings", subMenu=True, tearOff=True, boldFont=True, image="puiastreLogo.png")
    cmds.menuItem(label="   Reload UI", command=reload_ui)
    cmds.menuItem(label="   New Build Test", command=data_export_func)

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
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Rig", subMenu=True, tearOff=True, boldFont=True, image="rig.png")
    cmds.menuItem(label="   Build L leg (dev only)", command=leg_module)
    cmds.menuItem(label="   Build L arm (dev only)", command=arm_module)
    cmds.menuItem(label="   Build L finger (dev only)", command=finger_module)
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Animation", subMenu=True, tearOff=True, boldFont=True)
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)


    cmds.setParent("..", menu=True)
