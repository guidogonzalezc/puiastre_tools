

# Tools / utils import
from puiastreTools.utils import basic_structure
from puiastreTools.utils import data_export
from puiastreTools.utils import core
from puiastreTools.ui import project_manager

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
from puiastreTools.autorig import fkFingers as fkf
from puiastreTools.autorig import jaw_module_matrix as jmm
from puiastreTools.autorig import eyebrow_module as ebm
from puiastreTools.autorig import eyelid_module as elm
from puiastreTools.autorig import nose_module as nm
from puiastreTools.autorig import cheek_module as cm
from puiastreTools.autorig import spikes_module_matrix as spm


import puiastreTools.utils.skinning_transfer as skt


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
reload(fkf)
reload(jmm)
reload(ebm)
reload(elm)
reload(nm)
reload(cm)
reload(spm)

reload(skt)
reload(project_manager)

def rename_ctl_shapes():
    """
    Rename all shapes in the scene to follow a specific naming convention.
    This function finds all nurbsCurve shapes in the scene, retrieves their parent transform, and renames the shape to match the parent's name with "Shape" appended.
    """
    
    obj = cmds.ls(type="nurbsCurve")

    for shapes in obj:
        parentName = cmds.listRelatives(shapes, parent=True)[0]
        cmds.rename(shapes, f"{parentName}Shape")

def setIsHistoricallyInteresting(value=2):
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

def make(asset_name = "", latest = False):
    """
    Build a complete dragon rig in Maya by creating basic structure, modules, and setting up space switching for controllers.
    This function initializes various modules, creates the basic structure, and sets up controllers and constraints for the rig.
    It also sets the radius for all joints and displays a completion message.
    Args:
        model_path (str): The file path to the model to be imported. (full path)
        guides_path (str): The file path to the guides data. (full path)
        ctls_path (str): The file path to the controllers data. (full path)
    """
    if latest:
        core.load_data()
    else:
        try:
            project_manager.load_asset_configuration(asset_name)
        except Exception as e:
            om.MGlobal.displayError(f"Error loading asset configuration: {e}")
            return
    # DEV COMMANDS
    # cmds.file(new=True, force=True)
    # cmds.scriptEditorInfo(ch=True)

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



    if core.DataManager.get_asset_name() != "oto":
        basic_structure.create_basic_structure(asset_name=core.DataManager.get_asset_name())

    else:
        data_exporter.append_data("basic_structure", {"modules_GRP": "setup",
                                    "skel_GRP": "jnt_org",
                                    "masterWalk_CTL": "masterWalk",
                                    "guides_GRP": "guide",
                                    "skeletonHierarchy_GRP": "out_skel_facial",
                                    "muscleLocators_GRP": "muscleSystems_GRP",
                                    "adonis_GRP" : "adonis",
                                    })
        data_exporter.append_data("C_neckModule", {"skinning_transform": "C_neck4_JNT",
                                    "neck_ctl": "C_neck01_CTL",
                                    "head_ctl": "C_head_CTL"
                            })
    guide_amount = 0
    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":
                guide_amount += 1

    progress_window = cmds.progressWindow(title='Rig builder',
                                            progress=0,
                                            status=f"Building {core.DataManager.get_asset_name()} rig!",
                                            isInterruptable=True )


    step = 80/guide_amount
    current_val = 0

    def update_ui(module_name):
        nonlocal current_val # Allows us to modify the variable from the outer scope
        current_val += step
        
        cmds.progressWindow(
            progress_window, 
            edit=True, 
            progress=current_val, 
            status=f"Building {module_name} module"
        )
        cmds.refresh()

    # Loop through guides data and create modules based on guide information
    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":

                if guide_info.get("moduleName") == "arm":
                    update_ui("arm")
                    lbm.ArmModule(guide_name).make()
                
                elif guide_info.get("moduleName") == "leg":
                    update_ui("leg")
                    lbm.LegModule(guide_name).make()

                elif guide_info.get("moduleName") == "backLeg":
                    update_ui("backLeg")
                    dlm.BackLegModule(guide_name).make()

                elif guide_info.get("moduleName") == "frontLeg":
                    update_ui("frontLeg")
                    dlm.FrontLegModule(guide_name).make()

                elif guide_info.get("moduleName") == "handQuad":
                    update_ui("handQuad")
                    dfl.FalangeModule().hand_distribution(guide_name=guide_name)

                elif guide_info.get("moduleName") == "spineQuad":
                    update_ui("spineQuad")
                    spq.SpineModule().make(guide_name)

                elif guide_info.get("moduleName") == "spine":
                    update_ui("spine")
                    spb.SpineModule().make(guide_name)

                elif guide_info.get("moduleName") == "neckQuad":
                    update_ui("neckQuad")
                    nkq.NeckModule().make(guide_name)
                
                elif guide_info.get("moduleName") == "neck":
                    update_ui("neck")
                    nkb.NeckModule().make(guide_name, num_joints=guide_info.get("jointTwist", 5))

                elif guide_info.get("moduleName") == "tail":
                    update_ui("tail")
                    tmm.TailModule().make(guide_name)
                


                
    # Additional modules who depends on others modules
    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":

                if guide_info.get("moduleName") == "spikes":
                    update_ui("spikes")
                    spm.SpikesModule().make(guide_name)

                if guide_info.get("moduleName") == "membran":
                    update_ui("membran")
                    mm.MembraneModule().make(guide_name)


                if guide_info.get("moduleName") == "backLegFoot" or guide_info.get("moduleName") == "footFront" or guide_info.get("moduleName") == "footBack" :
                    update_ui("foot")
                    fm.FingersModule().make(guide_name)

                     
                if guide_info.get("moduleName") == "mouth":
                    update_ui("jaw")
                    jmm.JawModule().make(guide_name)

                # if guide_info.get("moduleName") == "eyebrow":

                #     ebm.EyebrowModule().make(guide_name)

                # if guide_info.get("moduleName") == "eye":

                #     elm.EyelidModule().make(guide_name)

                # if guide_info.get("moduleName") == "nose":

                #     nm.NoseModule().make(guide_name)
                
                # if guide_info.get("moduleName") == "cheek":
                #     cm.CheekModule().make(guide_name)
    
    # Additional modules who depends on others modules
    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":

                if guide_info.get("moduleName") == "fkFinger":
                    update_ui("fkFinger")

                    fkf.FingersModule().make(guide_name)

    # Create the skeleton hierarchy and spaces
    cmds.progressWindow(edit=True, progress=90, status=(f"Creating the skeleton hierarchy and spaces") )

    # skeleton_hierarchy = skh.build_complete_hierarchy() 

    # # skt.load_skincluster()

    # End commands to clean the scene
    cmds.progressWindow(edit=True, progress=95, status=(f"Finalizing") )
    rename_ctl_shapes()
    joint_label()
    setIsHistoricallyInteresting(0)

    # End message
    cmds.inViewMessage(
    amg=f'Completed <hl> {core.DataManager.get_asset_name().capitalize()} RIG</hl> build.',
    pos='midCenter',
    fade=True,
    alpha=0.8)
    cmds.progressWindow(endProgress=True)
    cmds.select(clear=True)

