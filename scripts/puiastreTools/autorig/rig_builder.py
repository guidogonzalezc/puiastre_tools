

# Tools / utils import
from puiastreTools.utils import basic_structure
from puiastreTools.utils import data_export
from puiastreTools.utils import core

# Rig modules import
from puiastreTools.autorig import limb_module_matrix as lbm
from puiastreTools.autorig import dragon_falanges as dfl
from puiastreTools.autorig import dragon_leg_matrix as dlm
from puiastreTools.autorig import neck_quad as nkq
from puiastreTools.autorig import neck_biped as nkb
from puiastreTools.autorig import spine_quad as spq
from puiastreTools.autorig import spine_biped as spb
from puiastreTools.autorig import tail_module_matrix as tmm
from puiastreTools.autorig import skeleton_hierarchy as skh
from puiastreTools.autorig import membran_module as mm
from puiastreTools.autorig import finger_module as fm
from puiastreTools.autorig import eye_module as em


# Python libraries import
import maya.cmds as cmds
from importlib import reload
import json
import maya.api.OpenMaya as om
import os

reload(basic_structure)
reload(core)
reload(data_export)
reload(lbm)
reload(dfl)
reload(dlm)
reload(nkq)
reload(nkb)
reload(spq)
reload(tmm)
reload(skh)
reload(mm)
reload(fm)
reload(em)
reload(spb)

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

def make():
    """
    Build a complete dragon rig in Maya by creating basic structure, modules, and setting up space switching for controllers.
    This function initializes various modules, creates the basic structure, and sets up controllers and constraints for the rig.
    It also sets the radius for all joints and displays a completion message.
    """


    # DEV COMMANDS
    cmds.file(new=True, force=True)
    # cmds.scriptEditorInfo(ch=True)

    # REL PATH
    file_path = os.path.dirname(os.path.abspath(__file__)).split("\scripts")[0]

    # Append the paths to DataManager
    core.DataManager.set_guide_data(os.path.join(file_path, r"guides\moana_001.guides")) # MAIASAURA_003.guides
    core.DataManager.set_ctls_data(os.path.join(file_path, r"curves\AYCHEDRAL_curves_001.json")) # MAIASAURA_curves_001.json

    # Create a new data export instance and generate build data
    data_exporter = data_export.DataExport()
    data_exporter.new_build()

    final_path = core.DataManager.get_guide_data()

    # Load guides data from the specified file
    try:
        with open(final_path, "r") as infile:
            guides_data = json.load(infile)

    except Exception as e:
        om.MGlobal.displayError(f"Error loading guides data: {e}")

    # Set asset name and mesh data in DataManager
    core.DataManager.set_asset_name(list(guides_data.keys())[0])
    core.DataManager.set_mesh_data(guides_data["meshes"])
    basic_structure.create_basic_structure(asset_name=core.DataManager.get_asset_name())

    # Loop through guides data and create modules based on guide information
    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":

                if guide_info.get("moduleName") == "arm":

                    lbm.ArmModule(guide_name).make()
                
                if guide_info.get("moduleName") == "leg":

                    lbm.LegModule(guide_name).make()

                if guide_info.get("moduleName") == "backLeg":
 
                    dlm.BackLegModule(guide_name).make()

                if guide_info.get("moduleName") == "frontLeg":

                    dlm.FrontLegModule(guide_name).make()

                if guide_info.get("moduleName") == "handQuad":

                    dfl.FalangeModule().hand_distribution(guide_name=guide_name)

                if guide_info.get("moduleName") == "spineQuad":
                    
                    spq.SpineModule().make(guide_name)

                if guide_info.get("moduleName") == "spine":
                    
                    spb.SpineModule().make(guide_name)

                if guide_info.get("moduleName") == "neckQuad":

                    nkq.NeckModule().make(guide_name)
                
                if guide_info.get("moduleName") == "neck":

                    nkb.NeckModule().make(guide_name, num_joints=guide_info.get("jointTwist", 5))

                if guide_info.get("moduleName") == "tail":

                    tmm.TailModule().make(guide_name)
                
                # if guide_info.get("moduleName") == "eye":

                #     em.EyeModule().make(guide_name)

                
    # Additional modules who depends on others modules
    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":

                if guide_info.get("moduleName") == "membran":
                    mm.MembraneModule().make(guide_name)
        
                if guide_info.get("moduleName") == "backLegFoot":
                    fm.FingersModule().make(guide_name)

    # Create the skeleton hierarchy and spaces
    skeleton_hierarchy = skh.build_complete_hierarchy() 

    # End commands to clean the scene
    rename_ctl_shapes()
    joint_label()
    setIsHistoricallyInteresting(0)

    # End message
    cmds.inViewMessage(
    amg=f'Completed <hl> {core.DataManager.get_asset_name().capitalize()} RIG</hl> build.',
    pos='midCenter',
    fade=True,
    alpha=0.8)

    cmds.select(clear=True)

