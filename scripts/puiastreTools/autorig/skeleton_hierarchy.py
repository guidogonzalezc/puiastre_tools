#Python libraries import
from maya import cmds
from importlib import reload
import os
import json
import maya.api.OpenMaya as om

# Tools / utils import
from puiastreTools.utils import data_export
from puiastreTools.utils import core
from puiastreTools.utils import space_switch

reload(core)

def parented_chain(skinning_joints, parent, hand_value=False):

    data_exporter = data_export.DataExport()

    skelHierarchy_grp = data_exporter.get_data("basic_structure", "skeletonHierarchy_GRP")

    try:
        env_replace = parent.replace("_JNT", "_ENV")
        if cmds.objExists(env_replace):
            parent = env_replace
    except Exception as e:
        parent = parent

    complete_chain = []

    if hand_value:
        def get_finger_key(joint):
            name = joint.split("_", 1)[1]
            name = name.replace("metacarpal", "")
            name = ''.join([c for c in name if not c.isdigit()])
            name = name.replace("JNT", "")
            return name.lower()

        finger_chains = {}
        for joint in skinning_joints:
            key = get_finger_key(joint)
            if key not in finger_chains:
                finger_chains[key] = []
            finger_chains[key].append(joint)

        complete_chain = [finger_chains[key] for key in finger_chains]
    else:
        complete_chain = [skinning_joints]

    end_joints = []
    for index, chain in enumerate(complete_chain):
        joints = []
        for joint in chain:
            cmds.select(clear=True)
            joint_env = cmds.createNode("joint", n=joint.replace("_JNT", "_ENV"), ss=True)



            if "localHip" in joint_env:
                cmds.parent(joint_env, joints[0])
                joints.append(joint_env)
                end_joints.append(joint_env)

                continue

            if joints:

                cmds.parent(joint_env, joints[-1])

            elif parent:
                cmds.parent(joint_env, parent)

            elif parent is None:
                cmds.parent(joint_env, skelHierarchy_grp)
            
            joints.append(joint_env)
            end_joints.append(joint_env)

        for i, joint in enumerate(joints):
            
            if parent is None:
                cmds.connectAttr(complete_chain[index][i] + ".worldMatrix[0]", joint + ".offsetParentMatrix", force=True)
            
            elif parent:
                mult_matrix = cmds.createNode("multMatrix", n=joint.replace("_ENV", "_MMX"), ss=True)
                cmds.connectAttr(complete_chain[index][i] + ".worldMatrix[0]", mult_matrix + ".matrixIn[0]", force=True)
                cmds.connectAttr(parent + ".worldInverseMatrix[0]", mult_matrix + ".matrixIn[1]", force=True)
                cmds.connectAttr(mult_matrix + ".matrixSum", joint + ".offsetParentMatrix", force=True)

                for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
                    cmds.setAttr(joint + "." + attr, 0)
                
            

            if "localHip" in joint:
                mult_matrix = cmds.createNode("multMatrix", n=joint.replace("_ENV", "_MMX"), ss=True)
                cmds.connectAttr(complete_chain[index][i] + ".worldMatrix[0]", mult_matrix + ".matrixIn[0]", force=True)
                cmds.connectAttr(joints[0] + ".worldInverseMatrix[0]", mult_matrix + ".matrixIn[1]", force=True)
                cmds.connectAttr(mult_matrix + ".matrixSum", joint + ".offsetParentMatrix", force=True)

                for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
                    cmds.setAttr(joint + "." + attr, 0)

            elif i != 0:
                mult_matrix = cmds.createNode("multMatrix", n=joint.replace("_ENV", "_MMX"), ss=True)
                cmds.connectAttr(complete_chain[index][i] + ".worldMatrix[0]", mult_matrix + ".matrixIn[0]", force=True)
                cmds.connectAttr(joints[i-1] + ".worldInverseMatrix[0]", mult_matrix + ".matrixIn[1]", force=True)
                cmds.connectAttr(mult_matrix + ".matrixSum", joint + ".offsetParentMatrix", force=True)

                for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
                    cmds.setAttr(joint + "." + attr, 0)

            cmds.setAttr(joint + ".jointOrient", 0, 0, 0, type="double3")

    return end_joints


def build_complete_hierarchy():
    """
    Reads the build and guide files, interprets the desired hierarchy, and
    constructs it in Maya by parenting the corresponding skinning groups.
    Uses file locations relative to the current script.
    """
    data_exporter = data_export.DataExport()
    try:
        complete_path = os.path.realpath(__file__)
        relative_path = complete_path.split("scripts")[0]
        build_path = os.path.join(relative_path, "build", "build_cache.cache")
        
        with open(build_path, "r") as f:
            build_data = json.load(f)

        guides_path = core.init_template_file(ext=".guides", export=False)
        
        with open(guides_path, "r") as f:
            guides_data = json.load(f)

    except IOError as e:
        om.MGlobal.displayError(f"File error: Could not find or read a data file. {e}")
        return
    except json.JSONDecodeError as e:
        om.MGlobal.displayError(f"JSON error: The file is malformed. {e}")
        return
    except Exception as e:
        om.MGlobal.displayError(f"Unexpected error while loading files: {e}")
        return

    skel_grps = []
    skinning_joints = []
    modules_name = []
    for module, data in build_data.items():
        for value in data.items():
            if "skinning_transform" in value:
                    joints = cmds.listRelatives(value[1], allDescendents=True, type="joint")
                    skel_grps.append((value[1]))
                    skinning_joints.append(joints)
                    modules_name.append(module)

    spine_index = next((i for i, grp in enumerate(skel_grps) if "spine" in grp.lower()), None)
    l_arm_index = next((i for i, grp in enumerate(skel_grps) if "L_arm" in grp), None)
    r_arm_index = next((i for i, grp in enumerate(skel_grps) if "R_arm" in grp), None)

    arm_joints = []

    spine_joints = parented_chain(skinning_joints=skinning_joints[spine_index], parent=None, hand_value=False)

    for i, skinning_joint_list in enumerate(skinning_joints):
        if i != spine_index:
            if "Leg" in skinning_joint_list[0] or "tail" in skinning_joint_list[0]:
                parented_chain(skinning_joints=skinning_joint_list, parent=spine_joints[-1], hand_value=False)
            elif "Metacarpal" in skinning_joint_list[0]:
                pass
            else:
                joints = parented_chain(skinning_joints=skinning_joint_list, parent=spine_joints[-2], hand_value=False)
                print(joints)
                if "clavicle" in skinning_joint_list[0]:
                    arm_joints.append(joints[-1])

    hand_settings_value = None

    for i, skinning_joint_list in enumerate(skinning_joints):

        if "Metacarpal" in skinning_joint_list[0]:
            side = skinning_joint_list[0].split("_")[0]
            index = l_arm_index if side == "L" else r_arm_index
            parent_joint = next((j for j in arm_joints if side in j), None)
            parented_chain(skinning_joints=skinning_joint_list, parent=parent_joint, hand_value=False)

        # ===== SPACE SWITCHES ===== #
        if "Leg" in skel_grps[i]:
            fk = data_exporter.get_data(modules_name[i], "fk_ctl")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")

            parents = [data_exporter.get_data("C_spineModule", "localHip"), data_exporter.get_data("C_spineModule", "body_ctl")]

            space_switch.fk_switch(target = fk, sources= parents)
            space_switch.fk_switch(target = root, sources= parents)
            space_switch.fk_switch(target = ik, sources= parents, default_rotate=0, default_translate=0)
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= parents)

        if "tail" in skel_grps[i]:
            main_ctl= data_exporter.get_data(modules_name[i], "main_ctl")
            parents = [data_exporter.get_data("C_spineModule", "localHip"), data_exporter.get_data("C_spineModule", "body_ctl")]
            space_switch.fk_switch(target = main_ctl, sources= parents)

        if "neck" in skel_grps[i]:
            main_ctl= data_exporter.get_data(modules_name[i], "neck_ctl")
            parents = [data_exporter.get_data("C_spineModule", "localChest"), data_exporter.get_data("C_spineModule", "end_main_ctl")]
            space_switch.fk_switch(target = main_ctl, sources= parents)

        if "arm" in skel_grps[i]:
            fk = data_exporter.get_data(modules_name[i], "fk_ctl")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")
            scapula = data_exporter.get_data(modules_name[i], "scapula_ctl")

            parents = [data_exporter.get_data("C_spineModule", "localChest"), data_exporter.get_data("C_spineModule", "end_main_ctl")]

            space_switch.fk_switch(target = scapula, sources= parents)
            parents.insert(0, scapula)


            space_switch.fk_switch(target = fk, sources= parents)
            space_switch.fk_switch(target = root, sources= parents)
            space_switch.fk_switch(target = ik, sources= parents, default_rotate=0, default_translate=0)
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= parents)
        
        if "Metacarpal" in skel_grps[i]:
            fk = data_exporter.get_data(modules_name[i], "fk_ctls")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")
            
            side = skel_grps[i].split("_")[0]
            index = l_arm_index if side == "L" else r_arm_index
            parent_joint = next((j for j in arm_joints if side in j), None)
            print(modules_name[i])
            hand_settings = data_exporter.get_data(modules_name[i], "settings_ctl")

            if hand_settings_value is None or hand_settings_value != modules_name[i].split("_")[0]:
                space_switch.fk_switch(target = hand_settings, sources=[parent_joint])
                hand_settings_value = modules_name[i].split("_")[0]
            parents = [hand_settings, parent_joint]

            space_switch.fk_switch(target = fk, sources= parents)
            space_switch.fk_switch(target = root, sources= parents)
            space_switch.fk_switch(target = ik, sources= parents, default_rotate=0, default_translate=0)
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= parents)

