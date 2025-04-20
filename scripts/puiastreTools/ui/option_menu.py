import sys
import os
import maya.cmds as cmds
from functools import partial
from importlib import reload

def reload_ui(*args):
    from puiastreTools.ui import option_menu
    reload(option_menu)
    option_menu.puiastre_ui()

def export_guides(*args):   
    from puiastreTools.utils import guides_manager
    from importlib import reload
    reload(guides_manager)
    guides_manager.guides_export()

def import_guides(*args, value=None): 
    if value == True:   
        from puiastreTools.utils import guides_manager
        from importlib import reload
        reload(guides_manager)
        guides_manager.guide_import(joint_name = "all")

def leg_module(*args):
    from puiastreTools.autorig import leg_module
    from importlib import reload
    reload(leg_module)
    module = leg_module.LegModule()
    module.make(side = "L")

def export_curves(*args):   
    from puiastreTools.tools import curve_tool
    from importlib import reload
    reload(curve_tool)
    curve_tool.export_nurbs_curve()

def puiastre_ui():

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
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Rig", subMenu=True, tearOff=True, boldFont=True, image="rig.png")
    cmds.menuItem(label="   Build L leg (dev only)", command=leg_module)
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)

    cmds.menuItem(label="   Animation", subMenu=True, tearOff=True, boldFont=True)
    cmds.setParent("..", menu=True)
    cmds.menuItem(dividerLabel="\n ", divider=True)


    cmds.setParent("..", menu=True)
