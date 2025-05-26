from puiastreTools.autorig import finger_module
from puiastreTools.autorig import leg_module
from puiastreTools.autorig import neck_module
from puiastreTools.autorig import wing_arm_module
from puiastreTools.autorig import spine_module
from puiastreTools.autorig import tail_module
from puiastreTools.autorig import clavicle_module
from puiastreTools.utils import basic_structure
import maya.cmds as cmds
from importlib import reload

reload(leg_module)
reload(wing_arm_module)
reload(neck_module)
reload(finger_module)
reload(spine_module)
reload(tail_module)
reload(clavicle_module)

def make():   
    basic_structure.create_basic_structure(asset_name = "Varyndor")
    
    fingermodule = finger_module.FingerModule()
    wingmodule = wing_arm_module.WingArmModule()
    spinemodule = spine_module.SpineModule()
    neck = neck_module.NeckModule()
    tail = tail_module.TailModule()
    leg_Module = leg_module.LegModule()
    clavicle = clavicle_module.ClavicleModule()



    for side in ["L", "R"]:
        # leg_Module.make(side = side)
        wingmodule.make(side = side)


    spinemodule.make()
    

    for side in ["L", "R"]:
        clavicle.make(side = side)
        # fingermodule.make(side = side)

    neck.make()
    tail.make()


    
    for joint in cmds.ls(type="joint"):
        cmds.setAttr(f"{joint}.radius", 10)

    cmds.inViewMessage(
    amg='Completed <hl>DRAGON RIG</hl> build.',
    pos='midCenter',
    fade=True,
    alpha=0.8)

    disable_inherits()
    rename_ctl_shapes()
    joint_lable()

def disable_inherits():
    sel = cmds.ls()

    for obj in sel:
        if "CRV" in obj:
            if not "Shape" in obj:
                cmds.setAttr(obj + ".inheritsTransform", 0)    

def rename_ctl_shapes():
    
    obj = cmds.ls(type="nurbsCurve")

    for shapes in obj:
        parentName = cmds.listRelatives(shapes, parent=True)[0]
        cmds.rename(shapes, f"{parentName}Shape")

def joint_lable():
    for jnt in cmds.ls(type="joint"):
        if "L_" in jnt:
            cmds.setAttr(jnt + ".side", 1)
        if "R_" in jnt:
            cmds.setAttr(jnt + ".side", 2)
        if "C_" in jnt:
            cmds.setAttr(jnt + ".side", 0)
        cmds.setAttr(jnt + ".type", 18)
        cmds.setAttr(jnt + ".otherType", jnt.split("_")[1], type= "string")


