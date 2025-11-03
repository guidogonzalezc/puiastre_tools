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

def get_closest_transform(main_transform, transform_list):
    """
    Returns the transform from transform_list that is closest to main_transform.
    
    Args:
        main_transform (str): Name of the main transform.
        transform_list (list): List of transform names to compare.

    Returns:
        str: Name of the closest transform.
    """
                    
    # Get main transform position
    main_pos = om.MVector(cmds.xform(main_transform, q=True, ws=True, t=True))
    
    closest_obj = None
    closest_dist = float('inf')
    
    for t in transform_list:
        if not cmds.objExists(t):
            continue
        
        pos = om.MVector(cmds.xform(t, q=True, ws=True, t=True))
        dist = (pos - main_pos).length()
        
        if dist < closest_dist:
            closest_dist = dist
            closest_obj = t

    return closest_obj

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
            joint_env = cmds.createNode("joint", n=joint.replace("_JNT", "_ENV"), ss=True)
            cmds.setAttr(joint_env + ".inheritsTransform", 0)


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
            
            cmds.connectAttr(complete_chain[index][i] + ".worldMatrix[0]", joint + ".offsetParentMatrix", force=True)
        
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
    leg_joints = []

    complete_arm_chain = []

    spine_joints = parented_chain(skinning_joints=skinning_joints[spine_index], parent=None, hand_value=False)

    for i, skinning_joint_list in enumerate(skinning_joints):
        if i != spine_index:
            if "backLeg" in skinning_joint_list[0] or "tail" in skinning_joint_list[0] or "leg" in skinning_joint_list[0]:
                joints = parented_chain(skinning_joints=skinning_joint_list, parent=spine_joints[-1], hand_value=False)
                leg_joints.append(joints[-1])
            elif "Finger" in skinning_joint_list[0] or "Membran" in skinning_joint_list[0] or "thumb01" in skinning_joint_list[0].split("_", 1)[1].lower():
                pass
            else:
                joints = parented_chain(skinning_joints=skinning_joint_list, parent=spine_joints[-2], hand_value=False)
                if "clavicle" in skinning_joint_list[0] or "scapula" in skinning_joint_list[0]:
                    arm_joints.append(joints[-1])
                    complete_arm_chain.extend(skinning_joint_list)


    hand_settings_value = None
    for i, skinning_joint_list in enumerate(skinning_joints):
        if "thumb01" in skinning_joint_list[0].split("_", 1)[1].lower():
            side = skinning_joint_list[0].split("_")[0]
            parent_joint = next((j for j in leg_joints if side in j), None)
            for i in range(0, 12, 3):
                joint_list = skinning_joint_list[i:i+3]
                parented_chain(skinning_joints=joint_list, parent=parent_joint, hand_value=False)

            continue

        
        if "Finger" in skinning_joint_list[0]:
            side = skinning_joint_list[0].split("_")[0]
            index = l_arm_index if side == "L" else r_arm_index
            parent_joint = next((j for j in arm_joints if side in j), None)
            parented_chain(skinning_joints=skinning_joint_list, parent=parent_joint, hand_value=False)

        if "Membran" in skinning_joint_list[0]:
            side = skinning_joint_list[0].split("_")[0]

            parent_joint = None

            for joint_arm in arm_joints:
                side_arm = joint_arm.split("_")[0]
                if side == side_arm:
                    parent_joint = joint_arm
                    break

            membrane_groups = []
            current_group = []

            for index, joint in enumerate(skinning_joint_list):
                if "Membrane01" in joint and not "PrimaryMembrane01" in joint:
                    current_group = [joint, skinning_joint_list[index + 1], skinning_joint_list[index + 2], skinning_joint_list[index + 3]]
                    membrane_groups.append(current_group)


                elif "PrimaryMembrane01" in joint:
                    current_group = [joint, skinning_joint_list[index + 1]]#, skinning_joint_list[index + 2]]
                    membrane_groups.append(current_group)                

            for joint_list in membrane_groups:
                if joint_list:
                    if "PrimaryMembrane01" in joint_list[0]:
                        closest01 = get_closest_transform(joint_list[0], complete_arm_chain)
                        parented_chain(skinning_joints=joint_list, parent=closest01, hand_value=False)
                    else:
                        parented_chain(skinning_joints=joint_list, parent=parent_joint, hand_value=True)

        # ===== SPACE SWITCHES ===== #
        if "backLeg" in skel_grps[i] or "leg" in skel_grps[i]:
            fk = data_exporter.get_data(modules_name[i], "fk_ctl")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")

            parents = [data_exporter.get_data("C_spineModule", "localHip"), data_exporter.get_data("C_spineModule", "body_ctl")]

            space_switch.fk_switch(target = fk, sources= parents, sources_names=["LocalHip", "Body"])
            space_switch.fk_switch(target = root, sources= parents, sources_names=["LocalHip", "Body"])
            space_switch.fk_switch(target = ik, sources= parents, default_rotate=0, default_translate=0, sources_names=["LocalHip", "Body"])
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= parents, sources_names=["AnkleIK", "LocalHip", "Body"])

        if "frontLeg" in skel_grps[i]:
            fk = data_exporter.get_data(modules_name[i], "fk_ctl")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")
            scapula = data_exporter.get_data(modules_name[i], "scapula_ctl")
            first_bendy = data_exporter.get_data(modules_name[i], "first_bendy_joints")

            parents = [data_exporter.get_data("C_spineModule", "localChest"), data_exporter.get_data("C_spineModule", "end_main_ctl")]

            space_switch.fk_switch(target = fk, sources= parents, sources_names=["LocalChest", "SpineEnd"])
            space_switch.fk_switch(target = root, sources= parents, sources_names=["LocalChest", "SpineEnd"])
            parents.insert(0, first_bendy)
            space_switch.fk_switch(target = scapula, sources= parents, sources_names=["Front Leg", "LocalChest", "SpineEnd"])
            parents.pop(0)
            space_switch.fk_switch(target = ik, sources= parents, default_rotate=0, default_translate=0, sources_names=["LocalChest", "SpineEnd"])
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= parents, sources_names=["AnkleIK", "LocalChest", "SpineEnd"])

        if "tail" in skel_grps[i]:
            main_ctl= data_exporter.get_data(modules_name[i], "main_ctl")
            parents = [data_exporter.get_data("C_spineModule", "localHip"), data_exporter.get_data("C_spineModule", "body_ctl")]
            space_switch.fk_switch(target = main_ctl, sources= parents, sources_names=["LocalHip", "Body"])

        if "neck" in skel_grps[i]:
            main_ctl= data_exporter.get_data(modules_name[i], "neck_ctl")
            parents = [data_exporter.get_data("C_spineModule", "localChest"), data_exporter.get_data("C_spineModule", "end_main_ctl")]
            space_switch.fk_switch(target = main_ctl, sources= parents, sources_names=["LocalChest", "SpineEnd"])

        if "arm" in skel_grps[i]:
            fk = data_exporter.get_data(modules_name[i], "fk_ctl")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")
            scapula = data_exporter.get_data(modules_name[i], "scapula_ctl")

            parents = [data_exporter.get_data("C_spineModule", "localChest"), data_exporter.get_data("C_spineModule", "end_main_ctl")]

            space_switch.fk_switch(target = scapula, sources= parents, sources_names=["LocalChest", "SpineEnd"])
            parents.insert(0, scapula)


            space_switch.fk_switch(target = fk, sources= parents, sources_names=["Scapula", "LocalChest", "SpineEnd"])
            space_switch.fk_switch(target = root, sources= parents, sources_names=["Scapula", "LocalChest", "SpineEnd"])
            space_switch.fk_switch(target = ik, sources= parents, default_rotate=0, default_translate=0, sources_names=["Scapula", "LocalChest", "SpineEnd"])
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= parents, sources_names=["WristIK", "Scapula", "LocalChest", "SpineEnd"])
        
        if "Metacarpal" in skel_grps[i]:

            fk = data_exporter.get_data(modules_name[i], "fk_ctls")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")
            
            side = skel_grps[i].split("_")[0]
            index = l_arm_index if side == "L" else r_arm_index
            parent_joint = next((j for j in arm_joints if side in j), None)
            hand_settings = data_exporter.get_data(modules_name[i], "settings_ctl")

            if hand_settings_value is None or hand_settings_value != modules_name[i].split("_")[0]:
                space_switch.fk_switch(target = hand_settings, sources=[parent_joint])
                hand_settings_value = modules_name[i].split("_")[0]
            parents = [parent_joint]

            space_switch.fk_switch(target = fk, sources= parents, sources_names=["Wrist"])
            space_switch.fk_switch(target = root, sources= parents, sources_names=["Wrist"])
            space_switch.fk_switch(target = ik, sources= parents, default_rotate=1, default_translate=1, sources_names=[ "Wrist"])
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= parents, sources_names=["MiddleFingerIK", "Wrist"])
