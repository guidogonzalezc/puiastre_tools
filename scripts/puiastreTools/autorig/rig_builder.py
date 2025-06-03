from puiastreTools.autorig import finger_module
from puiastreTools.autorig import leg_module
from puiastreTools.autorig import neck_module
from puiastreTools.autorig import wing_arm_module
from puiastreTools.autorig import spine_module
from puiastreTools.autorig import tail_module
from puiastreTools.autorig import clavicle_module
from puiastreTools.autorig import spikes_module
from puiastreTools.utils import basic_structure
from puiastreTools.utils import data_export
from puiastreTools.autorig import matrix_spaceSwitch
import maya.cmds as cmds
from importlib import reload

reload(leg_module)
reload(wing_arm_module)
reload(neck_module)
reload(finger_module)
reload(spine_module)
reload(tail_module)
reload(clavicle_module)
reload(spikes_module)
reload(data_export)
reload(matrix_spaceSwitch)

def disable_inherits():
    """
    Disable the inheritsTransform attribute for all controllers in the scene.
    This function iterates through all selected objects and sets the inheritsTransform attribute to 0 for those that contain "CRV" in their name but do not contain "Shape".
    """
    sel = cmds.ls()

    for obj in sel:
        if "CRV" in obj:
            if not "Shape" in obj:
                cmds.setAttr(obj + ".inheritsTransform", 0)    

def rename_ctl_shapes():
    """
    Rename all shapes in the scene to follow a specific naming convention.
    This function finds all nurbsCurve shapes in the scene, retrieves their parent transform, and renames the shape to match the parent's name with "Shape" appended.
    """
    
    obj = cmds.ls(type="nurbsCurve")

    for shapes in obj:
        parentName = cmds.listRelatives(shapes, parent=True)[0]
        cmds.rename(shapes, f"{parentName}Shape")

def joint_lable():
    """
    Set attributes for all joints in the scene to label them according to their side and type.
    This function iterates through all joints, checks their names for side indicators (L_, R_, C_), and sets the 'side' and 'type' attributes accordingly.
    """

    for jnt in cmds.ls(type="joint"):
        if "L_" in jnt:
            cmds.setAttr(jnt + ".side", 1)
        if "R_" in jnt:
            cmds.setAttr(jnt + ".side", 2)
        if "C_" in jnt:
            cmds.setAttr(jnt + ".side", 0)
        cmds.setAttr(jnt + ".type", 18)
        cmds.setAttr(jnt + ".otherType", jnt.split("_")[1], type= "string")



def make():
    """
    Build a complete dragon rig in Maya by creating basic structure, modules, and setting up space switching for controllers.
    This function initializes various modules, creates the basic structure, and sets up controllers and constraints for the rig.
    It also sets the radius for all joints and displays a completion message.
    """   
    
    basic_structure.create_basic_structure(asset_name = "Varyndor")
    
    fingermodule = finger_module.FingerModule()
    wingmodule = wing_arm_module.WingArmModule()
    spinemodule = spine_module.SpineModule()
    neck = neck_module.NeckModule()
    tail = tail_module.TailModule()
    leg_Module = leg_module.LegModule()
    clavicle = clavicle_module.ClavicleModule()
    spikes = spikes_module.SpikesModule()



    for side in ["L", "R"]:
        leg_Module.make(side = side)
        wingmodule.make(side = side)


    spinemodule.make()
    

    for side in ["L", "R"]:
        clavicle.make(side = side)
        fingermodule.make(side = side)

    neck.make()
    tail.make()
    spikes.make()


    
    for joint in cmds.ls(type="joint"):
        cmds.setAttr(f"{joint}.radius", 10)

    cmds.inViewMessage(
    amg='Completed <hl>DRAGON RIG</hl> build.',
    pos='midCenter',
    fade=True,
    alpha=0.8)

    data_exporter = data_export.DataExport()
    localHip = data_exporter.get_data("C_spineModule", "localHip")    
    localChest = data_exporter.get_data("C_spineModule", "localChest")

    for side in ["L", "R"]:
        armIk = data_exporter.get_data(f"{side}_armModule", "armIk")
        clavicle_ctl = data_exporter.get_data(f"{side}_clavicleModule", "clavicle_ctl")
        armFk = data_exporter.get_data(f"{side}_armModule", "shoulderFK")
        armPV = data_exporter.get_data(f"{side}_armModule", "armPV")
        armRoot = data_exporter.get_data(f"{side}_armModule", "armRoot")

        legIk = data_exporter.get_data(f"{side}_legModule", "ik_ctl")
        legPV = data_exporter.get_data(f"{side}_legModule", "pv_ctl")
        legFk = data_exporter.get_data(f"{side}_legModule", "fk_ctl")
        legRoot = data_exporter.get_data(f"{side}_legModule", "root_ctl")

        for name in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:   
            fingerPv = data_exporter.get_data(f"{side}_finger{name}", "ikPv")
            fingerIk = data_exporter.get_data(f"{side}_finger{name}", "ikFinger")
            fingerAttr = data_exporter.get_data(f"{side}_finger{name}", "settingsAttr")

            spaceSwitches = {
                    fingerPv: [[fingerIk, fingerAttr], 1],
                    fingerIk: [[fingerAttr],1],
                }
            
            for child, (parents, default_value) in spaceSwitches.items():
                print(f"Creating space switch for {child} with parents {parents} and default value {default_value}")
                matrix_spaceSwitch.switch_matrix_space(child, parents, default_value)

    

        spaceSwitches = {
                    legIk: [[localHip], 0],
                    legFk: [[localHip], 1],
                    clavicle_ctl: [[localChest], 1],
                    armFk: [[clavicle_ctl, localChest], 1],
                    armIk: [[localChest], 0],
                    armPV: [[armIk], 1],
                    legRoot: [[localHip],1],
                    armRoot: [[clavicle_ctl],1],
                }

        for child, (parents, default_value) in spaceSwitches.items():
            matrix_spaceSwitch.switch_matrix_space(child, parents, default_value)

    tail00 = data_exporter.get_data("C_tailModule", "tail00_ctl")
    print(f"Creating space switch for tail00: {tail00}")
    spaceSwitches = {
                tail00: [[localHip], 1],
            }
    for child, (parents, default_value) in spaceSwitches.items():
        matrix_spaceSwitch.switch_matrix_space(child, parents, default_value)


    disable_inherits()
    rename_ctl_shapes()
    joint_lable()


