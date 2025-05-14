from puiastreTools.autorig import finger_module
from puiastreTools.autorig import leg_module
from puiastreTools.autorig import neck_module
from puiastreTools.autorig import wing_arm_module
from puiastreTools.autorig import spine_module
from puiastreTools.utils import basic_structure
import maya.cmds as cmds
from importlib import reload

reload(leg_module)
reload(wing_arm_module)
reload(neck_module)
reload(finger_module)
reload(spine_module)

def make():   
    basic_structure.create_basic_structure(asset_name = "Varyndor")
    
    fingermodule = finger_module.FingerModule()

    wingmodule = wing_arm_module.WingArmModule()

    module = neck_module.NeckModule()
    leg_Module = leg_module.LegModule()
    for side in ["L", "R"]:
        leg_Module.make(side = side)
        wingmodule.make(side = side)
        fingermodule.make(side = side)

    spinemodule = spine_module.SpineModule()
    spinemodule.make()
        
    module.make()

    
    for joint in cmds.ls(type="joint"):
        cmds.setAttr(f"{joint}.radius", 100)

    cmds.inViewMessage(
    amg='Completed <hl>DRAGON RIG</hl> build.',
    pos='midCenter',
    fade=True,
    alpha=0.8)

    

