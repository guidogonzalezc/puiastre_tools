

# Tools / utils import
from puiastreTools.utils import basic_structure
from puiastreTools.utils import data_export
from puiastreTools.utils import core

# Rig modules import
from puiastreTools.autorig import limb_module_matrix as lbm
from puiastreTools.autorig import dragon_falanges as dfl
from puiastreTools.autorig import dragon_leg_matrix as dlm
from puiastreTools.autorig import neck_module_quad_matrix as nmm
from puiastreTools.autorig import spine_module_biped_matrix as spmm
from puiastreTools.autorig import tail_module_matrix as tmm
from puiastreTools.autorig import skeleton_hierarchy as skh

# Python libraries import
import maya.cmds as cmds
from importlib import reload
import json
import maya.api.OpenMaya as om

reload(basic_structure)
reload(core)
reload(data_export)
reload(lbm)
reload(dfl)
reload(dlm)
reload(nmm)
reload(spmm)
reload(tmm)
reload(skh)

def rename_ctl_shapes():
    """
    Rename all shapes in the scene to follow a specific naming convention.
    This function finds all nurbsCurve shapes in the scene, retrieves their parent transform, and renames the shape to match the parent's name with "Shape" appended.
    """
    
    obj = cmds.ls(type="nurbsCurve")

    for shapes in obj:
        parentName = cmds.listRelatives(shapes, parent=True)[0]
        cmds.rename(shapes, f"{parentName}Shape")

def setIsHistoricallyInteresting(value=0):
    cmds.select(r=True, allDependencyNodes=True)
    allNodes = cmds.ls(sl=True)
    allNodes.extend(cmds.ls(shapes=True))

    failed = []
    for node in allNodes:
        plug = '{}.ihi'.format(node)
        if cmds.objExists(plug):
            try:
                cmds.setAttr(plug, value)
            except:
                failed.append(node)
    if failed:
        print("Skipped the following nodes {}".format(failed))


def joint_label():
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

def make(asset_name="dragon"):
    """
    Build a complete dragon rig in Maya by creating basic structure, modules, and setting up space switching for controllers.
    This function initializes various modules, creates the basic structure, and sets up controllers and constraints for the rig.
    It also sets the radius for all joints and displays a completion message.
    """   
    cmds.file(new=True, force=True)
    #UNI
    # core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/test_03.guides")
    # core.DataManager.set_ctls_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/curves/template_curves_001.json")

    #CASA
    core.DataManager.set_guide_data("D:/git/maya/puiastre_tools/guides/test_03.guides")
    core.DataManager.set_ctls_data("D:/git/maya/puiastre_tools/curves/template_curves_001.json")

    data_exporter = data_export.DataExport()
    data_exporter.new_build()
    if not asset_name:
        asset_name = "asset"
    basic_structure.create_basic_structure(asset_name=asset_name)


    

    final_path = core.DataManager.get_guide_data()
    # core.DataManager.set_asset_name("Dragon")
    # core.DataManager.set_mesh_data("Puiastre")

    try:
        with open(final_path, "r") as infile:
            guides_data = json.load(infile)

    except Exception as e:
        om.MGlobal.displayError(f"Error loading guides data: {e}")

    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":
                if guide_info.get("moduleName") == "arm":
                    lbm.ArmModule(guide_name).make()

                if guide_info.get("moduleName") == "backLeg":
                    dlm.BackLegModule(guide_name).make()

                if guide_info.get("moduleName") == "hand":
                    dfl.FalangeModule().hand_distribution(guide_name=guide_name)

                if guide_info.get("moduleName") == "spine":
                    spmm.SpineModule().make(guide_name)

                if guide_info.get("moduleName") == "neck":
                    nmm.NeckModule().make(guide_name)

                if guide_info.get("moduleName") == "tail":
                    tmm.TailModule().make(guide_name)

    skeleton_hierarchy = skh.build_complete_hierarchy() 

    rename_ctl_shapes()
    joint_label()
    setIsHistoricallyInteresting(0)

    cmds.inViewMessage(
    amg=f'Completed <hl> {asset_name.capitalize()} RIG</hl> build.',
    pos='midCenter',
    fade=True,
    alpha=0.8)

    cmds.select(clear=True)


make()