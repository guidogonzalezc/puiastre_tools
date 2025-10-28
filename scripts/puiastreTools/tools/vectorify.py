## Created by Ehsan Bayat, 2025
# Repath your animation the way you want.

# VECTORIFY V2.8

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.mel as mel
import json
import math
import builtins

try:
    max = builtins.max 
    min = builtins.min
    sum = builtins.sum
    abs = builtins.abs
    len = builtins.len
    int = builtins.int
    str = builtins.str
    set = builtins.set
    range = builtins.range
    list = builtins.list
    dict = builtins.dict
except:
    pass


x12s_field = None
y34t_field = None
z56u_field = None


def h67j(obj):
    return get_shape_nodes(obj)

def k89l(curve_obj):
    return get_cv_count(curve_obj)

def m12n(base_curve, target_cv_count):
    try:
        cmds.rebuildCurve(
            base_curve,
            constructionHistory=False,
            replaceOriginal=True,
            rebuildType=0,
            endKnots=1,
            keepRange=1,
            keepControlPoints=0,
            keepEndPoints=0,
            keepTangents=0,
            spans=target_cv_count - 3, 
            degree=3,
            tolerance=0.01
        )
        return True
    except:
        return False

def o34p():
    sel = cmds.ls(sl=True, long=True)
    if len(sel) != 2:
        cmds.error("Please select exactly two objects: base mesh first, then target mesh.")
    
    base, target = sel[0], sel[1]
    
    base_shapes = h67j(base)
    target_shapes = h67j(target)
    
    if not base_shapes or not target_shapes:
        cmds.error("Both selected objects must have shape nodes.")
    
    if (cmds.objectType(base_shapes[0]) != "nurbsCurve" or 
        cmds.objectType(target_shapes[0]) != "nurbsCurve"):
        cmds.error("Both selected objects must be NURBS curves.")
    
    target_cv_count = k89l(target)
    base_cv_count = k89l(base)
    
    if target_cv_count is None or base_cv_count is None:
        cmds.error("Could not determine CV count for selected curves.")
    
    if base_cv_count != target_cv_count:
        if not m12n(base, target_cv_count):
            cmds.error("Failed to rebuild base curve to match target CV count.")
    
    mel_cmd = 'blendShape -origin world "{}" "{}";'.format(target, base)
    blendshape_result = mel.eval(mel_cmd)
    
    if isinstance(blendshape_result, list):
        blendshape = blendshape_result[0]
    else:
        blendshape = blendshape_result

    weight_attr = "{}.w[0]".format(blendshape)
    try:
        cmds.aliasAttr(target, weight_attr)
    except Exception:
        pass

    cmds.setAttr(weight_attr, 1.0)
    
    return blendshape


def get_vectorify_network_node():
    node = "vectorifyDataNode"
    if not cmds.objExists(node):
        current_selection = cmds.ls(selection=True)
        node = cmds.createNode("network", name=node)
        cmds.addAttr(node, longName="connectedObjects", dataType="string")
        cmds.addAttr(node, longName="pathCurve", dataType="string")
        if current_selection:
            cmds.select(current_selection, replace=True)
        else:
            cmds.select(clear=True)
    return node

def save_vectorify_data(objects_list, path_curve):
    node = get_vectorify_network_node()
    
    existing_objects, existing_path = load_vectorify_data()
    
    if existing_objects:
        combined_objects = list(set(existing_objects + objects_list))
    else:
        combined_objects = objects_list
    
    objects_json = json.dumps(combined_objects) if combined_objects else ""
    path_json = json.dumps(path_curve) if path_curve else ""
    
    cmds.setAttr(f"{node}.connectedObjects", objects_json, type="string")
    cmds.setAttr(f"{node}.pathCurve", path_json, type="string")

def load_vectorify_data():
    node = get_vectorify_network_node()
    objects_list = []
    path_curve = ""
    
    if cmds.objExists(f"{node}.connectedObjects"):
        try:
            raw_objects = cmds.getAttr(f"{node}.connectedObjects")
            if raw_objects and raw_objects.strip():
                objects_list = json.loads(raw_objects)
        except Exception:
            pass
    
    if cmds.objExists(f"{node}.pathCurve"):
        try:
            raw_path = cmds.getAttr(f"{node}.pathCurve")
            if raw_path and raw_path.strip():
                path_curve = json.loads(raw_path)
        except Exception:
            pass
    
    return objects_list, path_curve

def delete_vectorify_network():
    node = "vectorifyDataNode"
    if cmds.objExists(node):
        cmds.delete(node)

def w89e():
    node = "vectorifySelectionSets"
    if not cmds.objExists(node):
        current_selection = cmds.ls(selection=True)
        node = cmds.createNode("network", name=node)
        cmds.addAttr(node, longName="controlsList", dataType="string")
        cmds.addAttr(node, longName="pathName", dataType="string")
        if current_selection:
            cmds.select(current_selection, replace=True)
        else:
            cmds.select(clear=True)
    return node

def q45r(controls_list, path_name):
    node = w89e()
    controls_json = json.dumps(controls_list) if controls_list else ""
    path_json = json.dumps(path_name) if path_name else ""
    
    cmds.setAttr(f"{node}.controlsList", controls_json, type="string")
    cmds.setAttr(f"{node}.pathName", path_json, type="string")

def t67y():
    node = w89e()
    controls_list = []
    path_name = ""
    
    if cmds.objExists(f"{node}.controlsList"):
        try:
            raw_controls = cmds.getAttr(f"{node}.controlsList")
            if raw_controls and raw_controls.strip():  # Check for non-empty string
                controls_list = json.loads(raw_controls)
        except Exception:
            pass
    
    if cmds.objExists(f"{node}.pathName"):
        try:
            raw_path = cmds.getAttr(f"{node}.pathName")
            if raw_path and raw_path.strip():  # Check for non-empty string
                path_name = json.loads(raw_path)
        except Exception:
            pass
    
    return controls_list, path_name

def show_nurbs_curves_in_viewports():
    all_panels = cmds.getPanel(type='modelPanel')
    for panel in all_panels:
        if cmds.modelPanel(panel, query=True, exists=True):
            editor = cmds.modelPanel(panel, query=True, modelEditor=True)
            cmds.modelEditor(editor, edit=True, nurbsCurves=True)
            cmds.modelEditor(editor, edit=True, cv=True)


def a4d5f():
    playback_slider = mel.eval('global string $gPlayBackSlider; $temp=$gPlayBackSlider')
    selected_time = cmds.timeControl(playback_slider, query=True, rangeArray=True)
    curves = cmds.keyframe(query=True, name=True, selected=True)
    
    if (selected_time[1] - selected_time[0]) <= 1 and not curves:
        return None
    elif (selected_time[1] - selected_time[0]) <= 1 and curves:
        num_frames = cmds.keyframe(query=True, selected=True)
        num_frames = sorted(num_frames)
        if num_frames:
            return [num_frames[0], num_frames[-1] + 1]
    
    return selected_time


def b7f2c(obj, coords):
    cmds.currentTime(obj)
    pos = cmds.xform(coords, query=True, worldSpace=True, translation=True)
    return pos


def c9e8a(coords, threshold=0.001):
    if len(coords) < 2:
        return coords
    
    final_coords = []
    for i in range(len(coords) - 1):
        delta_x = coords[i][0] - coords[i+1][0]
        delta_y = coords[i][1] - coords[i+1][1]
        delta_z = coords[i][2] - coords[i+1][2]
        magnitude = (delta_x**2 + delta_y**2 + delta_z**2)**0.5
        
        if magnitude > threshold:
            final_coords.append(coords[i])
    
    final_coords.append(coords[-1])
    return final_coords


def d3h7k(coords):
    if not coords:
        return coords
    
    final_coords = []
    index_mask = [1] * len(coords)
    
    for i in range(len(coords) - 1):
        if index_mask[i] == 1 and index_mask[i+1] == 1:
            radius_x = coords[i][0] - coords[i+1][0]
            radius_y = coords[i][1] - coords[i+1][1]
            radius_z = coords[i][2] - coords[i+1][2]
            radius_mag = (radius_x**2 + radius_y**2 + radius_z**2)**0.5
            
            for k in range(i+2, len(coords)):
                test_x = coords[i][0] - coords[k][0]
                test_y = coords[i][1] - coords[k][1]
                test_z = coords[i][2] - coords[k][2]
                test_mag = (test_x**2 + test_y**2 + test_z**2)**0.5
                
                if radius_mag > test_mag:
                    index_mask[k] = 0
    
    for i in range(len(coords)):
        if index_mask[i] == 1:
            final_coords.append(coords[i])
    
    return final_coords


def e5m2n(coords):
    result = d3h7k(coords)
    result = list(reversed(result))
    result = d3h7k(result)
    result = list(reversed(result))
    return result


def get_namespace(name):
    short_name = name.split('|')[-1]
    if ':' in short_name:
        return ':'.join(short_name.split(':')[:-1])
    return ''    


def strip_namespace(name):
    if isinstance(name, (list, tuple)):
        name = name[0] if len(name) > 0 else ""
    name_str = str(name)
    if ':' in name_str:
        return name_str.split(':')[-1]
    return name_str

def get_short_name(full_path):
    if isinstance(full_path, (list, tuple)):
        full_path = full_path[0] if len(full_path) > 0 else ""
    path_str = str(full_path)
    return path_str.split('|')[-1]



def f8k4p(coords, degree):
    if len(coords) <= 1:
        return ""
    
    curve_name = cmds.curve(point=[(c[0], c[1], c[2]) for c in coords], degree=degree)
    return curve_name


def g2n9r(obj, frame_range):
    coords = []
    for frame in range(int(frame_range[0]), int(frame_range[1])):
        pos = b7f2c(frame, obj)
        coords.append(pos)
    return coords





def h6s1t(step_count=20, from_edge_only=False, zero_vertical=True):
    current_time = cmds.currentTime(query=True)
    selection = cmds.ls(selection=True)
    
    if not selection:
        cmds.warning("Nothing selected")
        return None
    
    frame_range = a4d5f()
    if not frame_range or (frame_range[1] - frame_range[0]) == 1:
        frame_range = [
            cmds.playbackOptions(query=True, min=True),
            cmds.playbackOptions(query=True, max=True) + 1
        ]
    
    maya_version = cmds.about(version=True)
    eval_mode = None
    
    cmds.waitCursor(state=True)
    cmds.refresh(suspend=True)
    
    created_curves = []
    
    try:
        if float(maya_version.split()[0]) >= 2016:
            eval_mode = cmds.evaluationManager(query=True, mode=True)
            if eval_mode[0] != "off":
                cmds.evaluationManager(mode="off")
        
        for obj in selection:
            if from_edge_only:
                cmds.currentTime(frame_range[1] - 1)
                pos_end = cmds.xform(obj, query=True, worldSpace=True, pivots=True)[:3]
                
                cmds.currentTime(frame_range[0])
                pos_start = cmds.xform(obj, query=True, worldSpace=True, pivots=True)[:3]
                
                coords = [pos_start, pos_end]
            else:
                coords = g2n9r(obj, frame_range)
            
            if zero_vertical:
                up_axis = cmds.upAxis(query=True, axis=True)
                first_pos = coords[0]
                fixed_height = first_pos[2] if up_axis == "z" else first_pos[1]
                
                new_coords = []
                for coord in coords:
                    if up_axis == "z":
                        new_coords.append([coord[0], coord[1], fixed_height])
                    else:
                        new_coords.append([coord[0], fixed_height, coord[2]])
                coords = new_coords
            
            coords = c9e8a(coords)
            coords = e5m2n(coords)
            
            if from_edge_only:
                curve_name = f8k4p(coords, 1)
            else:
                curve_name = f8k4p(coords, 3)
            
            if not curve_name:
                continue
            
            mel.eval('SmoothHairCurves 100')
            
            rebuild_step = int((frame_range[1] - frame_range[0]) / step_count)
            curve_name = cmds.rebuildCurve(
                curve_name,
                constructionHistory=False,
                replaceOriginal=True,
                rebuildType=0,
                endKnots=1,
                keepRange=1,
                keepControlPoints=0,
                keepEndPoints=0,
                keepTangents=0,
                spans=rebuild_step,
                degree=3,
                tolerance=0.01
            )[0]

            cmds.setAttr(curve_name + '.useOutlinerColor', True)
            cmds.setAttr(curve_name + ".outlinerColor", 1, 1, 0)            
            
            curve_name = cmds.rebuildCurve(
                curve_name,
                constructionHistory=False,
                replaceOriginal=True,
                rebuildType=0,
                endKnots=1,
                keepRange=1,
                keepControlPoints=0,
                keepEndPoints=0,
                keepTangents=0,
                spans=rebuild_step,
                degree=3,
                tolerance=0.01
            )[0]
            
            cmds.setAttr(curve_name + ".dispCV", 1)
            cmds.setAttr(curve_name + ".overrideEnabled", 1)
            cmds.setAttr(curve_name + ".overrideColor", 17)
            
            created_curves.append(curve_name)
        
        cmds.currentTime(current_time)
        
        if created_curves:
            cmds.select(created_curves, replace=True)
            
            n34o()
            l12m()
            
            show_nurbs_curves_in_viewports()
            
            if len(created_curves) == 1:
                cmds.textField(x12s_field, edit=True, text=created_curves[0])
                controls_list, _ = t67y()
                q45r(controls_list, created_curves[0])
            else:
                curve_names = ", ".join(created_curves)
                cmds.textField(x12s_field, edit=True, text=curve_names)
        
        return created_curves
        
    finally:
        cmds.refresh(suspend=False)
        cmds.waitCursor(state=False)
        
        if eval_mode:
            cmds.evaluationManager(mode=eval_mode[0])


def u12i():
    global x12s_field, y34t_field
    
    try:
        if x12s_field and y34t_field:
            # Check if fields still exist before trying to access them
            if not (cmds.textField(x12s_field, exists=True) and cmds.textField(y34t_field, exists=True)):
                return
                
            controls_list, path_name = t67y()
            
            # Update controls field
            if controls_list and isinstance(controls_list, list):
                # Filter out empty or None values
                valid_controls = [str(ctrl) for ctrl in controls_list if ctrl and str(ctrl).strip()]
                if valid_controls:
                    controls_str = ", ".join(valid_controls)
                    cmds.textField(y34t_field, edit=True, text=controls_str)
                else:
                    cmds.textField(y34t_field, edit=True, text="")
            else:
                cmds.textField(y34t_field, edit=True, text="")
            
            # Update path field
            if path_name and str(path_name).strip():
                cmds.textField(x12s_field, edit=True, text=str(path_name))
            else:
                cmds.textField(x12s_field, edit=True, text="")
                
    except Exception as e:
        # For debugging, let's print the error instead of hiding it
        print(f"Error in u12i(): {e}")

def refresh_ui_data(*args):
    """Manually reload the UI data from the network node"""
    u12i()
    print("UI data reloaded from network node.")

def on_selection_change(*args):
    
    try:
        
        global x12s_field, y34t_field
        if x12s_field and y34t_field:
            
            if cmds.textField(x12s_field, exists=True) and cmds.textField(y34t_field, exists=True):
                
                cmds.evalDeferred(u12i)
    except Exception as e:
        print(f"Error in selection callback: {e}")

def setup_selection_callback():
    remove_selection_callback()
    
    # Add new selection change callback
    try:
        import maya.api.OpenMaya as om
        callback_id = om.MEventMessage.addEventCallback("SelectionChanged", on_selection_change)
        
        cmds.optionVar(intValue=("vectorify_selection_callback", callback_id))
        return callback_id
    except Exception as e:
        cmds.warning(f"Failed to setup selection callback: {e}")
        return None

def remove_selection_callback():
    
    try:
        import maya.api.OpenMaya as om
        
        if cmds.optionVar(exists="vectorify_selection_callback"):
            callback_id = cmds.optionVar(query="vectorify_selection_callback")
            if callback_id and callback_id != 0:
                try:
                    om.MMessage.removeCallback(callback_id)
                except:
                    pass  
        
        cmds.optionVar(remove="vectorify_selection_callback")
    except Exception:
        pass

def smartPointConstraint(ctrl=None, object=None, maintainOffset=False):
    transAttr = cmds.listAttr(object, keyable=True, unlocked=True, string='translate*')
    
    if not transAttr:
        return None
    
    transSkip = []
    for axis in ['x','y','z']:
        if f'translate{axis.upper()}' not in transAttr:
            transSkip.append(axis)
    
    try:
        if len(transSkip) == 3:
            return None
        elif transSkip:
            return cmds.pointConstraint(ctrl, object, skip=transSkip, maintainOffset=maintainOffset)[0]
        else:
            return cmds.pointConstraint(ctrl, object, maintainOffset=maintainOffset)[0]
    except Exception:
        return None


def smartOrientConstraint(ctrl=None, object=None, maintainOffset=False):
    rotAttr = cmds.listAttr(object, keyable=True, unlocked=True, string='rotate*')
    
    if not rotAttr:
        return None
    
    rotSkip = []
    for axis in ['x','y','z']:
        if f'rotate{axis.upper()}' not in rotAttr:
            rotSkip.append(axis)
    
    try:
        if len(rotSkip) == 3:
            return None
        elif rotSkip:
            return cmds.orientConstraint(ctrl, object, skip=rotSkip, maintainOffset=maintainOffset)[0]
        else:
            return cmds.orientConstraint(ctrl, object, maintainOffset=maintainOffset)[0]
    except Exception:
        return None

def get_or_create_backup_network():
    node = "Vectorify_Backup_Network"
    if not cmds.objExists(node):
        current_selection = cmds.ls(selection=True)
        node = cmds.createNode("network", name=node)
        cmds.addAttr(node, longName="backupLocators", dataType="string")
        if current_selection:
            cmds.select(current_selection, replace=True)
        else:
            cmds.select(clear=True)
    return node


def get_or_create_backup_set():
    set_name = "Vectorify_Backup"
    if not cmds.objExists(set_name):
        cmds.sets(name=set_name, empty=True)
    return set_name
    

def save_backup_locators_to_network(locator_long_names):
    node = get_or_create_backup_network()
    
    existing_locators = []
    if cmds.objExists(f"{node}.backupLocators"):
        try:
            raw_data = cmds.getAttr(f"{node}.backupLocators")
            if raw_data and raw_data.strip():
                existing_locators = json.loads(raw_data)
        except Exception:
            pass
    
    combined_locators = list(set(existing_locators + locator_long_names))
    
    locators_json = json.dumps(combined_locators)
    cmds.setAttr(f"{node}.backupLocators", locators_json, type="string")

def create_backup_locator_for_object(failed_obj, source_obj=None):

    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    min_time = cmds.playbackOptions(q=True, animationStartTime=True)
    max_time = cmds.playbackOptions(q=True, animationEndTime=True)
    
    short_name = failed_obj.split('|')[-1]
    locator_name = short_name + "_backupLoc"
    
    if cmds.objExists(locator_name):
        cmds.delete(locator_name)
    
    backup_loc = cmds.spaceLocator(name=locator_name)[0]
    
    constraint = cmds.parentConstraint(failed_obj, backup_loc, mo=False)[0]
    
    cmds.bakeResults(backup_loc,
                   time=(min_time, max_time),
                   simulation=True,
                   sampleBy=1,
                   oversamplingRate=1,
                   disableImplicitControl=True,
                   preserveOutsideKeys=True,
                   sparseAnimCurveBake=False,
                   removeBakedAttributeFromLayer=False,
                   bakeOnOverrideLayer=False,
                   controlPoints=False,
                   shape=True)
    
    cmds.delete(constraint)
    
    group_name = "VECTORIFY_DO_NOT_TOUCH"
    if not cmds.objExists(group_name):
        group_name = cmds.group(empty=True, name=group_name)
        cmds.setAttr(f"{group_name}.visibility", 0)
        for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']:
            try:
                cmds.setAttr(f"{group_name}.{attr}", lock=True, keyable=False, channelBox=False)
            except:
                pass
    
    cmds.parent(backup_loc, group_name)
    backup_loc_long = cmds.ls(backup_loc, long=True)[0]
    
    for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']:
        try:
            cmds.setAttr(f"{backup_loc}.{attr}", lock=True, keyable=False, channelBox=False)
        except:
            pass
    
    set_name = get_or_create_backup_set()
    if not cmds.sets(backup_loc_long, isMember=set_name):
        cmds.sets(backup_loc_long, add=set_name)
    
    save_backup_locators_to_network([backup_loc_long])
    
    return backup_loc


def create_backup_locators_batch(failed_objects):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    
    min_time = cmds.playbackOptions(q=True, animationStartTime=True)
    max_time = cmds.playbackOptions(q=True, animationEndTime=True)
    
    backup_locators = []
    temp_constraints = []
    
    for failed_obj in failed_objects:
        short_name = failed_obj.split('|')[-1]
        locator_name = short_name + "_backupLoc"
        
        if cmds.objExists(locator_name):
            cmds.delete(locator_name)
        
        backup_loc = cmds.spaceLocator(name=locator_name)[0]
        
        constraint = cmds.parentConstraint(failed_obj, backup_loc, mo=False)[0]
        
        backup_locators.append(backup_loc)
        temp_constraints.append(constraint)
    
    if backup_locators:
        cmds.bakeResults(backup_locators,
                       time=(min_time, max_time))
        
        cmds.delete(temp_constraints)
        
        group_name = "VECTORIFY_DO_NOT_TOUCH"
        if not cmds.objExists(group_name):
            group_name = cmds.group(empty=True, name=group_name)
            cmds.setAttr(f"{group_name}.visibility", 0)
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']:
                try:
                    cmds.setAttr(f"{group_name}.{attr}", lock=True, keyable=False, channelBox=False)
                except:
                    pass
        
        set_name = get_or_create_backup_set()
        backup_locators_long = []
        
        for loc in backup_locators:
            if cmds.objExists(loc):
                cmds.parent(loc, group_name)
                loc_long = cmds.ls(loc, long=True)[0]
                backup_locators_long.append(loc_long)
                
                for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']:
                    try:
                        cmds.setAttr(f"{loc}.{attr}", lock=True, keyable=False, channelBox=False)
                    except:
                        pass
                
                if not cmds.sets(loc_long, isMember=set_name):
                    cmds.sets(loc_long, add=set_name)
        
        save_backup_locators_to_network(backup_locators_long)
    
    return backup_locators

def smartParentConstraint(ctrl=None, object=None, maintainOffset=True):
    transAttr = cmds.listAttr(object, keyable=True, unlocked=True, string='translate*')
    rotAttr = cmds.listAttr(object, keyable=True, unlocked=True, string='rotate*')
    
    if not transAttr and not rotAttr:
        return None
    
    transSkip = []
    rotSkip = []
    
    for axis in ['x','y','z']:
        if transAttr and f'translate{axis.upper()}' not in transAttr:
            transSkip.append(axis)
        if rotAttr and f'rotate{axis.upper()}' not in rotAttr:
            rotSkip.append(axis)
    
    try:
        if len(transSkip) == 3 and len(rotSkip) == 3:
            return None
        elif transSkip and rotSkip:
            return cmds.parentConstraint(ctrl, object, maintainOffset=maintainOffset, skipTranslate=transSkip, skipRotate=rotSkip)[0]
        elif transSkip:
            return cmds.parentConstraint(ctrl, object, maintainOffset=maintainOffset, skipTranslate=transSkip)[0]
        elif rotSkip:
            return cmds.parentConstraint(ctrl, object, maintainOffset=maintainOffset, skipRotate=rotSkip)[0]
        else:
            return cmds.parentConstraint(ctrl, object, maintainOffset=maintainOffset)[0]
    except Exception:
        create_backup_locator_for_object(object, ctrl)
        return None



def is_locator(node):
    if not cmds.objExists(node):
        return False
    shapes = cmds.listRelatives(node, shapes=True, fullPath=True)
    return shapes and cmds.nodeType(shapes[0]) == 'locator'


def is_constrained_to_object(node):
    connections = cmds.listConnections(node, type='constraint', source=False, destination=True)
    if connections:
        for conn in connections:
            if cmds.nodeType(conn) in ['parentConstraint', 'pointConstraint', 'orientConstraint']:
                return True
    return False



def find_matching_target(locator_full_path, identifier_pattern="vectorify_ctrl_"):
    locator_short = get_short_name(locator_full_path)
    locator_namespace = get_namespace(locator_short)
    locator_no_ns = strip_namespace(locator_short)
    
    if not locator_no_ns.startswith(identifier_pattern):
        return None
    
    target_name = locator_no_ns.replace(identifier_pattern, "", 1)
    
    if not target_name:
        return None
    
    if locator_namespace:
        expected_target = f"{locator_namespace}:{target_name}"
    else:
        expected_target = target_name
    
    all_transforms = cmds.ls(dag=True, long=True, type='transform')
    
    for obj in all_transforms:
        if obj == locator_full_path:
            continue
        
        if is_locator(obj):
            continue
        
        obj_short = get_short_name(obj)
        
        if obj_short == expected_target:
            return obj
    
    return None

def clear_animation(obj):
    transAttr = cmds.listAttr(obj, keyable=True, unlocked=True, string='translate*')
    rotAttr = cmds.listAttr(obj, keyable=True, unlocked=True, string='rotate*')
    
    if transAttr:
        for attr in ['tx', 'ty', 'tz']:
            try:
                cmds.cutKey(obj, attribute=attr, clear=True)
            except Exception:
                pass
    
    if rotAttr:
        for attr in ['rx', 'ry', 'rz']:
            try:
                cmds.cutKey(obj, attribute=attr, clear=True)
            except Exception:
                pass    

def is_locator_constrained_to_object(locator):
    connections = cmds.listConnections(locator, type='constraint', source=False, destination=True)
    if connections:
        for conn in connections:
            if cmds.nodeType(conn) in ['parentConstraint', 'pointConstraint', 'orientConstraint']:
                return True
    return False


def apply_force_parent_constraint_to_vectorify(vectorify_group):
    all_descendants = cmds.listRelatives(vectorify_group, allDescendents=True, fullPath=True, type='transform') or []
    
    constrained_count = 0
    
    for desc in all_descendants:
        if not is_locator(desc):
            continue
            
        locator_short = get_short_name(desc)
        locator_no_ns = strip_namespace(locator_short)
        
        if not locator_no_ns.startswith("vectorify_ctrl_"):
            continue
            
        if is_constrained_to_object(desc):
            continue
        
        matching_object = find_matching_target(desc, "vectorify_ctrl_")
        
        if not matching_object:
            continue
        
        clear_animation(matching_object)
        result = smartParentConstraint(desc, matching_object, maintainOffset=True)
        
        if result:
            constrained_count += 1
            
            if "_forced" not in desc:
                try:
                    cmds.rename(desc, desc.split("|")[-1] + "_forced")
                except:
                    pass
    
    return constrained_count

class r78v:
    def __init__(self):
        self.q91w = 1.0
        self.e23r = 18
    
    def d67f(self, node_name):
        if not node_name or not cmds.objExists(node_name):
            raise RuntimeError(f"Object '{node_name}' does not exist")
        selection_list = om.MSelectionList()
        selection_list.add(node_name)
        return selection_list.getDependNode(0)
    
    def g89h(self, start_frame, end_frame):
        time_unit = om.MTime.uiUnit()
        time_array = om.MTimeArray()
        for frame in range(start_frame, end_frame + 1):
            time_array.append(om.MTime(frame, time_unit))
        return time_array
    
    def j12k(self, obj_name):
        short_name = obj_name.split('|')[-1].split(':')[-1]
        try:
            keyable_attrs = cmds.listAttr(obj_name, keyable=True) or []
        except:
            keyable_attrs = []
        return {
            'name': obj_name,
            'short_name': short_name,
            'keyable_attrs': set(keyable_attrs)
        }
    
    def l34m(self, obj_name, frame=None):
        try:
            max = builtins.max 
            min = builtins.min
            sum = builtins.sum
            abs = builtins.abs
            len = builtins.len
            int = builtins.int
            str = builtins.str
            set = builtins.set
            range = builtins.range
            list = builtins.list
            dict = builtins.dict
        except:
            pass
        
        if frame is not None:
            current_frame = cmds.currentTime(query=True)
            cmds.currentTime(frame)
            try:
                pos = cmds.xform(obj_name, query=True, worldSpace=True, translation=True)
                return om.MPoint(pos[0], pos[1], pos[2])
            finally:
                cmds.currentTime(current_frame)
        else:
            pos = cmds.xform(obj_name, query=True, worldSpace=True, translation=True)
            return om.MPoint(pos[0], pos[1], pos[2])
    
    def n56o(self, base_name):
        if not cmds.objExists(base_name):
            return base_name
        counter = 1
        while True:
            new_name = f"{base_name}_{counter:02d}"
            if not cmds.objExists(new_name):
                return new_name
            counter += 1
    
    def p78q(self, name, size=None, color=None):
        if size is None:
            size = self.q91w
        if color is None:
            color = self.e23r
        
        unique_name = self.n56o(f"{name}_vectorify_loc")
        locator = cmds.spaceLocator(name=unique_name)[0]
        
        shape = cmds.listRelatives(locator, shapes=True)[0]
        cmds.setAttr(f"{shape}.overrideEnabled", True)
        cmds.setAttr(f"{shape}.overrideColor", color)
        cmds.setAttr(f"{locator}.displayHandle", True)
        
        current_unit = cmds.currentUnit(query=True, linear=True)
        scale_factor = size
        
        unit_multipliers = {
            'mm': 10.0, 'cm': 1.0, 'm': 0.1,
            'in': 2.54, 'ft': 0.3048, 'yd': 0.0914
        }
        
        if current_unit in unit_multipliers:
            scale_factor *= unit_multipliers[current_unit]
        
        cmds.setAttr(f"{shape}.localScaleX", scale_factor)
        cmds.setAttr(f"{shape}.localScaleY", scale_factor)
        cmds.setAttr(f"{shape}.localScaleZ", scale_factor)
        
        for attr in ['scaleX', 'scaleY', 'scaleZ']:
            cmds.setAttr(f"{locator}.{attr}", lock=True, keyable=False)
        
        return locator
    
    def r90s(self, objects, curve, start_frame, end_frame):
        if not cmds.objExists(curve):
            raise RuntimeError(f"Curve '{curve}' does not exist")
            
        curve_shapes = cmds.listRelatives(curve, children=True, shapes=True)
        if not curve_shapes:
            raise RuntimeError(f"No curve shape found for {curve}")
        
        curve_shape = curve_shapes[0]
        if not cmds.objExists(curve_shape):
            raise RuntimeError(f"Curve shape '{curve_shape}' does not exist")
            
        curve_mobj = self.d67f(curve_shape)
        curve_fn = om.MFnNurbsCurve(curve_mobj)
        
        object_parameters = {}
        num_frames = end_frame - start_frame + 1
        
        for obj in objects:
            if not cmds.objExists(obj):
                raise RuntimeError(f"Object '{obj}' does not exist")
            parameters = om.MDoubleArray()
            parameters.setLength(num_frames)
            object_parameters[obj] = parameters
        
        original_time = cmds.currentTime(query=True)
        eval_mode = cmds.evaluationManager(query=True, mode=True)[0]
        
        cmds.waitCursor(state=True)
        cmds.evaluationManager(mode="off")
        cmds.refresh(suspend=True)
        
        try:
            for i, frame in enumerate(range(start_frame, end_frame + 1)):
                cmds.currentTime(frame, edit=True)
                
                for obj in objects:
                    pos = cmds.xform(obj, query=True, worldSpace=True, translation=True)
                    world_pos = om.MPoint(pos[0], pos[1], pos[2])
                    closest_point, param = curve_fn.closestPoint(world_pos)
                    object_parameters[obj][i] = param
        finally:
            cmds.currentTime(original_time, edit=True)
            cmds.refresh(suspend=False)
            cmds.evaluationManager(mode=eval_mode)
            cmds.waitCursor(state=False)
        
        return object_parameters
    
    def t12u(self, objects, curve, object_parameters, start_frame, end_frame):
        master_group = cmds.group(empty=True, name=f"{curve}_VECTORIFY_01")
        v34w(master_group, color=(1.0, 0.4, 0.7))
        
        up_axis = cmds.upAxis(query=True, axis=True)
        up_vector = [0, 1, 0] if up_axis == "y" else [0, 0, 1]
        
        time_array = self.g89h(start_frame, end_frame)
        motion_path_groups = {}
        
        for obj in objects:
            obj_data = self.j12k(obj)
            
            mp_group = cmds.group(
                empty=True, 
                name=f"{obj_data['short_name']}_vectorify_grp",
                parent=master_group
            )
            motion_path_groups[obj] = mp_group
            
            motion_path_node = cmds.pathAnimation(
                mp_group,
                curve=curve,
                worldUpType="vector",
                worldUpVector=up_vector,
                follow=True
            )
            
            motion_path_mobj = self.d67f(motion_path_node)
            mp_dep_node = om.MFnDependencyNode(motion_path_mobj)
            u_value_plug = mp_dep_node.findPlug("uValue", False)
            
            if u_value_plug.isConnected:
                source_plug = u_value_plug.source()
                anim_curve_node = source_plug.node()
                anim_curve_fn = oma.MFnAnimCurve(anim_curve_node)
            else:
                anim_curve_fn = oma.MFnAnimCurve()
                anim_curve_fn.create(u_value_plug)
            
            parameter_values = object_parameters[obj]
            anim_curve_fn.addKeys(
                time_array,
                parameter_values,
                tangentInType=oma.MFnAnimCurve.kTangentGlobal,
                tangentOutType=oma.MFnAnimCurve.kTangentGlobal,
                keepExistingKeys=False
            )
        
        return master_group, motion_path_groups
    
    def x56y(self, objects, motion_path_groups, start_frame, end_frame):
        try:
            max = builtins.max 
            min = builtins.min
            sum = builtins.sum
            abs = builtins.abs
            len = builtins.len
            int = builtins.int
            str = builtins.str
            set = builtins.set
            range = builtins.range
            list = builtins.list
            dict = builtins.dict
        except:
            pass
        
        locators = {}
        temp_constraints = []
        
        use_simulation = len(objects) > 4
        
        for obj in objects:
            obj_data = self.j12k(obj)
            
            obj_bbox = cmds.exactWorldBoundingBox(obj)
            obj_size = max([
                obj_bbox[3] - obj_bbox[0],
                obj_bbox[4] - obj_bbox[1],
                obj_bbox[5] - obj_bbox[2]
            ]) * 0.5
            
            locator = self.p78q(obj_data['short_name'], size=obj_size)
            cmds.parent(locator, motion_path_groups[obj])
            
            constraint = cmds.parentConstraint(obj, locator, maintainOffset=False)[0]
            temp_constraints.append(constraint)
            locators[obj] = locator
        
        eval_mode = cmds.evaluationManager(query=True, mode=True)[0]
        
        cmds.evaluationManager(mode="off")
        cmds.refresh(suspend=True)
        
        try:
            locator_list = list(locators.values())
            
            cmds.bakeResults(
                locator_list,
                time=(start_frame, end_frame),
                simulation=use_simulation,
                sampleBy=1,
                oversamplingRate=1,
                disableImplicitControl=True,
                preserveOutsideKeys=False,
                sparseAnimCurveBake=False,
                removeBakedAttributeFromLayer=False,
                removeBakedAnimFromLayer=False,
                bakeOnOverrideLayer=False,
                minimizeRotation=True,
                controlPoints=False,
                shape=False
            )
        finally:
            cmds.refresh(suspend=False)
            cmds.evaluationManager(mode=eval_mode)
        
        for constraint in temp_constraints:
            if cmds.objExists(constraint):
                cmds.delete(constraint)
        
        return locators
    
    def z78a(self, objects, locators):
        for obj in objects:
            locator = locators[obj]
            obj_data = self.j12k(obj)
            keyable_attrs = obj_data['keyable_attrs']
            
            translate_attrs = ['translateX', 'translateY', 'translateZ']
            has_translate = any(attr in keyable_attrs for attr in translate_attrs)
            
            rotate_attrs = ['rotateX', 'rotateY', 'rotateZ']
            has_rotate = any(attr in keyable_attrs for attr in rotate_attrs)
            
            if has_translate or has_rotate:
                try:
                    smartParentConstraint(locator, obj)
                except Exception:
                    pass

    
    def b90c(self):
        all_panels = cmds.getPanel(type='modelPanel')
        for panel in all_panels:
            if cmds.modelPanel(panel, query=True, exists=True):
                editor = cmds.modelPanel(panel, query=True, modelEditor=True)
                cmds.modelEditor(editor, edit=True, locators=True)
    
    def d12e(self, objects):
        path_name = cmds.textField(x12s_field, query=True, text=True)
        save_vectorify_data(objects, path_name)
        return "vectorifyDataNode"
    
    def f34g(self, objects, curve, start_frame, end_frame):
        cmds.refresh(suspend=True)
        
        try:
            object_parameters = self.r90s(objects, curve, start_frame, end_frame)
            master_group, motion_path_groups = self.t12u(
                objects, curve, object_parameters, start_frame, end_frame
            )
            locators = self.x56y(objects, motion_path_groups, start_frame, end_frame)
            self.b90c()
            self.z78a(objects, locators)
            self.d12e(objects)
            
            if cmds.objExists(curve):
                current_parent = cmds.listRelatives(curve, parent=True)
                if not current_parent or current_parent[0] != master_group:
                    try:
                        cmds.parent(curve, master_group)
                    except Exception as e:
                        cmds.warning(f"Could not parent curve to VECTORIFY group: {e}")
            
            driving_locators = []
            for obj in objects:
                if obj in locators:
                    locator = locators[obj]
                    if cmds.objExists(locator):
                        long_name = cmds.ls(locator, long=True)[0]
                        driving_locators.append(long_name)
            
            if driving_locators:
                cmds.select(driving_locators, replace=True)
            else:
                cmds.select(clear=True)
            
            return master_group
            
        finally:
            cmds.refresh(suspend=False)
    
    def h56i(self, objects, curve, start_frame=None, end_frame=None):
        if start_frame is None:
            start_frame = int(cmds.playbackOptions(query=True, minTime=True))
        if end_frame is None:
            end_frame = int(cmds.playbackOptions(query=True, maxTime=True))
        
        return self.f34g(objects, curve, start_frame, end_frame)


def get_shape_nodes(transform_node):
    if cmds.nodeType(transform_node) == "transform":
        shapes = cmds.listRelatives(transform_node, fullPath=True, shapes=True)
        return shapes if shapes else []
    else:
        return [transform_node]

def get_cv_count(curve_obj):
    shape_nodes = get_shape_nodes(curve_obj)
    if not shape_nodes:
        return None
    
    if cmds.objectType(shape_nodes[0]) == "nurbsCurve":
        spans = cmds.getAttr(curve_obj + ".spans")
        degree = cmds.getAttr(curve_obj + ".degree")
        cv_count = spans + degree
        return cv_count
    return None

def get_curve_length(curve_obj):
    shape_nodes = get_shape_nodes(curve_obj)
    if not shape_nodes or cmds.objectType(shape_nodes[0]) != "nurbsCurve":
        return None
    
    curve_info = cmds.createNode('curveInfo')
    cmds.connectAttr(f"{shape_nodes[0]}.worldSpace[0]", f"{curve_info}.inputCurve")
    arc_length = cmds.getAttr(f"{curve_info}.arcLength")
    cmds.delete(curve_info)
    return arc_length

def sample_curve_at_parameter(curve_obj, parameter):
    shape_nodes = get_shape_nodes(curve_obj)
    if not shape_nodes:
        return None
    
    min_param = cmds.getAttr(f"{curve_obj}.minValue")
    max_param = cmds.getAttr(f"{curve_obj}.maxValue")
    curve_param = min_param + (max_param - min_param) * parameter
    
    point_on_curve = cmds.createNode('pointOnCurveInfo')
    cmds.connectAttr(f"{shape_nodes[0]}.worldSpace[0]", f"{point_on_curve}.inputCurve")
    cmds.setAttr(f"{point_on_curve}.parameter", curve_param)
    
    position = cmds.getAttr(f"{point_on_curve}.position")[0]
    cmds.delete(point_on_curve)
    
    return position

def find_joints_for_curve(base_curve):
    joints = []
    try:
        for i in range(20):
            joint_name = f"cv_{i}_joint"
            if cmds.objExists(joint_name):
                joints.append(joint_name)
            else:
                break
    except:
        pass
    return joints

def get_stored_slide_offset(base_curve):
    if not cmds.attributeQuery("slideOffset", node=base_curve, exists=True):
        cmds.addAttr(base_curve, longName="slideOffset", attributeType="double", defaultValue=0.0)
        return 0.0
    else:
        return cmds.getAttr(f"{base_curve}.slideOffset")

def set_stored_slide_offset(base_curve, offset):
    if not cmds.attributeQuery("slideOffset", node=base_curve, exists=True):
        cmds.addAttr(base_curve, longName="slideOffset", attributeType="double", defaultValue=offset)
    else:
        cmds.setAttr(f"{base_curve}.slideOffset", offset)

def get_stored_distances(base_curve):
    distances = []
    try:
        for i in range(20):
            attr_name = f"storedDist_{i}"
            if cmds.attributeQuery(attr_name, node=base_curve, exists=True):
                dist = cmds.getAttr(f"{base_curve}.{attr_name}")
                distances.append(dist)
            else:
                break
    except:
        pass
    return distances

def find_parameter_at_distance_on_curve(curve_obj, start_param, target_distance):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass


    low_param = start_param
    high_param = 1.0
    tolerance = 0.001
    
    for _ in range(50):
        mid_param = (low_param + high_param) / 2.0
        
        start_pos = sample_curve_at_parameter(curve_obj, start_param)
        mid_pos = sample_curve_at_parameter(curve_obj, mid_param)
        
        if start_pos and mid_pos:
            dx = mid_pos[0] - start_pos[0]
            dy = mid_pos[1] - start_pos[1]
            dz = mid_pos[2] - start_pos[2]
            current_distance = (dx*dx + dy*dy + dz*dz) ** 0.5
            
            if abs(current_distance - target_distance) < tolerance:
                return mid_param
            elif current_distance < target_distance:
                low_param = mid_param
            else:
                high_param = mid_param
        else:
            break
    
    return (low_param + high_param) / 2.0

def slide_curve_forward():
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass


    sel = cmds.ls(sl=True, long=True)
    if len(sel) == 0:
        result = cmds.confirmDialog(
            title='Selection Required',
            message='No curves selected!\n\nHow to use this script:\n1. Select the base curve (the one that will slide)\n2. Then select the target curve (the path to slide along)\n3. Run this script to slide forward\n\nNote: You must run the main morphing script first to set up the joints.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return False
    elif len(sel) == 1:
        result = cmds.confirmDialog(
            title='Second Curve Needed',
            message='Only one curve selected!\n\nHow to use this script:\n1. Keep your current selection (base curve)\n2. Add the target curve to your selection\n3. Run this script to slide forward\n\nSelection order: Base curve first, then target curve.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return False
    elif len(sel) > 2:
        result = cmds.confirmDialog(
            title='Too Many Objects Selected',
            message='More than 2 objects selected!\n\nHow to use this script:\n1. Select only the base curve (the one that will slide)\n2. Then select only the target curve (the path to slide along)\n3. Run this script to slide forward\n\nPlease select exactly 2 curves.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return False
    
    base, target = sel[0], sel[1]
    
    base_shapes = get_shape_nodes(base)
    target_shapes = get_shape_nodes(target)
    
    if not base_shapes or not target_shapes:
        cmds.error("Both objects must have shape nodes.")
    
    if (cmds.objectType(base_shapes[0]) != "nurbsCurve" or 
        cmds.objectType(target_shapes[0]) != "nurbsCurve"):
        cmds.error("Both objects must be NURBS curves.")
    
    base_cv_count = get_cv_count(base)
    if not base_cv_count:
        cmds.error("Could not get CV count for base curve.")
    
    joints = find_joints_for_curve(base)
    if not joints:
        cmds.error("No joints found. Please run the main morphing script first.")
    
    original_length = get_curve_length(base)
    target_length = get_curve_length(target)
    
    if not original_length or not target_length:
        cmds.error("Could not get curve lengths.")
    
    length_ratio = original_length / target_length
    max_parameter = min(1.0, length_ratio)
    
    current_offset = get_stored_slide_offset(base)
    slide_increment = 0.05
    new_offset = current_offset + slide_increment
    
    stored_distances = get_stored_distances(base)
    if not stored_distances:
        cmds.error("No stored distances found. Please run the main morphing script first.")
    
    total_original_length = sum(stored_distances)
    required_curve_length_ratio = total_original_length / get_curve_length(target)
    
    if new_offset > 1.0:
        cmds.warning("Cannot slide forward - already at the end of the curve.")
        cmds.select([base, target])
        return False
    
    if new_offset + required_curve_length_ratio > 1.0:
        cmds.warning("Cannot slide forward - not enough curve length remaining.")
        cmds.select([base, target])
        return False
    
    cmds.undoInfo(openChunk=True)
    
    try:
        first_joint_param = new_offset
        first_joint_pos = sample_curve_at_parameter(target, first_joint_param)
        if first_joint_pos:
            cmds.move(first_joint_pos[0], first_joint_pos[1], first_joint_pos[2], joints[0], absolute=True, worldSpace=True)
        
        current_param = first_joint_param
        
        for i in range(1, len(joints)):
            if i-1 < len(stored_distances):
                target_distance = stored_distances[i-1]
                next_param = find_parameter_at_distance_on_curve(target, current_param, target_distance)
                
                if next_param > 1.0:
                    cmds.undoInfo(closeChunk=True)
                    cmds.undo()
                    cmds.warning("Cannot slide forward - curve would extend beyond target curve end.")
                    cmds.select([base, target])
                    return False
                
                next_param = max(0.0, min(1.0, next_param))
                
                next_pos = sample_curve_at_parameter(target, next_param)
                if next_pos:
                    cmds.move(next_pos[0], next_pos[1], next_pos[2], joints[i], absolute=True, worldSpace=True)
                    current_param = next_param
        
        set_stored_slide_offset(base, new_offset)
        
    finally:
        cmds.undoInfo(closeChunk=True)
    
    cmds.select([base, target])
    return True


def get_shape_nodes(transform_node):
    if cmds.nodeType(transform_node) == "transform":
        shapes = cmds.listRelatives(transform_node, fullPath=True, shapes=True)
        return shapes if shapes else []
    else:
        return [transform_node]

def get_cv_count(curve_obj):
    shape_nodes = get_shape_nodes(curve_obj)
    if not shape_nodes:
        return None
    
    if cmds.objectType(shape_nodes[0]) == "nurbsCurve":
        spans = cmds.getAttr(curve_obj + ".spans")
        degree = cmds.getAttr(curve_obj + ".degree")
        cv_count = spans + degree
        return cv_count
    return None

def get_curve_length(curve_obj):
    shape_nodes = get_shape_nodes(curve_obj)
    if not shape_nodes or cmds.objectType(shape_nodes[0]) != "nurbsCurve":
        return None
    
    curve_info = cmds.createNode('curveInfo')
    cmds.connectAttr(f"{shape_nodes[0]}.worldSpace[0]", f"{curve_info}.inputCurve")
    arc_length = cmds.getAttr(f"{curve_info}.arcLength")
    cmds.delete(curve_info)
    return arc_length

def sample_curve_at_parameter(curve_obj, parameter):
    shape_nodes = get_shape_nodes(curve_obj)
    if not shape_nodes:
        return None
    
    min_param = cmds.getAttr(f"{curve_obj}.minValue")
    max_param = cmds.getAttr(f"{curve_obj}.maxValue")
    curve_param = min_param + (max_param - min_param) * parameter
    
    point_on_curve = cmds.createNode('pointOnCurveInfo')
    cmds.connectAttr(f"{shape_nodes[0]}.worldSpace[0]", f"{point_on_curve}.inputCurve")
    cmds.setAttr(f"{point_on_curve}.parameter", curve_param)
    
    position = cmds.getAttr(f"{point_on_curve}.position")[0]
    cmds.delete(point_on_curve)
    
    return position

def find_joints_for_curve(base_curve):
    joints = []
    try:
        for i in range(20):
            joint_name = f"cv_{i}_joint"
            if cmds.objExists(joint_name):
                joints.append(joint_name)
            else:
                break
    except:
        pass
    return joints

def get_stored_slide_offset(base_curve):
    if not cmds.attributeQuery("slideOffset", node=base_curve, exists=True):
        cmds.addAttr(base_curve, longName="slideOffset", attributeType="double", defaultValue=0.0)
        return 0.0
    else:
        return cmds.getAttr(f"{base_curve}.slideOffset")

def set_stored_slide_offset(base_curve, offset):
    if not cmds.attributeQuery("slideOffset", node=base_curve, exists=True):
        cmds.addAttr(base_curve, longName="slideOffset", attributeType="double", defaultValue=offset)
    else:
        cmds.setAttr(f"{base_curve}.slideOffset", offset)

def get_stored_distances(base_curve):
    distances = []
    try:
        for i in range(20):
            attr_name = f"storedDist_{i}"
            if cmds.attributeQuery(attr_name, node=base_curve, exists=True):
                dist = cmds.getAttr(f"{base_curve}.{attr_name}")
                distances.append(dist)
            else:
                break
    except:
        pass
    return distances

def find_parameter_at_distance_on_curve(curve_obj, start_param, target_distance):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass


    low_param = start_param
    high_param = 1.0
    tolerance = 0.001
    
    for _ in range(50):
        mid_param = (low_param + high_param) / 2.0
        
        start_pos = sample_curve_at_parameter(curve_obj, start_param)
        mid_pos = sample_curve_at_parameter(curve_obj, mid_param)
        
        if start_pos and mid_pos:
            dx = mid_pos[0] - start_pos[0]
            dy = mid_pos[1] - start_pos[1]
            dz = mid_pos[2] - start_pos[2]
            current_distance = (dx*dx + dy*dy + dz*dz) ** 0.5
            
            if abs(current_distance - target_distance) < tolerance:
                return mid_param
            elif current_distance < target_distance:
                low_param = mid_param
            else:
                high_param = mid_param
        else:
            break
    
    return (low_param + high_param) / 2.0


def get_shape_nodes(transform_node):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    if cmds.nodeType(transform_node) == "transform":
        shapes = cmds.listRelatives(transform_node, fullPath=True, shapes=True)
        return shapes if shapes else []
    else:
        return [transform_node]

def get_cv_count(curve_obj):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    shape_nodes = get_shape_nodes(curve_obj)
    if not shape_nodes:
        return None
    
    if cmds.objectType(shape_nodes[0]) == "nurbsCurve":
        spans = cmds.getAttr(curve_obj + ".spans")
        degree = cmds.getAttr(curve_obj + ".degree")
        cv_count = spans + degree
        return cv_count
    return None

def get_curve_length(curve_obj):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass    
    shape_nodes = get_shape_nodes(curve_obj)
    if not shape_nodes or cmds.objectType(shape_nodes[0]) != "nurbsCurve":
        return None
    
    curve_info = cmds.createNode('curveInfo')
    cmds.connectAttr(f"{shape_nodes[0]}.worldSpace[0]", f"{curve_info}.inputCurve")
    arc_length = cmds.getAttr(f"{curve_info}.arcLength")
    cmds.delete(curve_info)
    return arc_length

def sample_curve_at_parameter(curve_obj, parameter):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass    
    shape_nodes = get_shape_nodes(curve_obj)
    if not shape_nodes:
        return None
    
    min_param = cmds.getAttr(f"{curve_obj}.minValue")
    max_param = cmds.getAttr(f"{curve_obj}.maxValue")
    curve_param = min_param + (max_param - min_param) * parameter
    
    point_on_curve = cmds.createNode('pointOnCurveInfo')
    cmds.connectAttr(f"{shape_nodes[0]}.worldSpace[0]", f"{point_on_curve}.inputCurve")
    cmds.setAttr(f"{point_on_curve}.parameter", curve_param)
    
    position = cmds.getAttr(f"{point_on_curve}.position")[0]
    cmds.delete(point_on_curve)
    
    return position

def calculate_original_distances(joints):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    distances = []
    for i in range(len(joints) - 1):
        pos1 = cmds.xform(joints[i], query=True, worldSpace=True, translation=True)
        pos2 = cmds.xform(joints[i+1], query=True, worldSpace=True, translation=True)
        
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        dz = pos2[2] - pos1[2]
        distance = (dx*dx + dy*dy + dz*dz) ** 0.5
        distances.append(distance)
    
    return distances

def store_distances(base_curve, distances):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    for i, dist in enumerate(distances):
        attr_name = f"storedDist_{i}"
        if not cmds.attributeQuery(attr_name, node=base_curve, exists=True):
            cmds.addAttr(base_curve, longName=attr_name, attributeType="double", defaultValue=dist)
        else:
            cmds.setAttr(f"{base_curve}.{attr_name}", dist)

def set_stored_slide_offset(base_curve, offset):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass


    if not cmds.attributeQuery("slideOffset", node=base_curve, exists=True):
        cmds.addAttr(base_curve, longName="slideOffset", attributeType="double", defaultValue=offset)
    else:
        cmds.setAttr(f"{base_curve}.slideOffset", offset)

def find_parameter_at_distance_on_curve(curve_obj, start_param, target_distance):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    low_param = start_param
    high_param = 1.0
    tolerance = 0.001
    
    for _ in range(50):
        mid_param = (low_param + high_param) / 2.0
        
        start_pos = sample_curve_at_parameter(curve_obj, start_param)
        mid_pos = sample_curve_at_parameter(curve_obj, mid_param)
        
        if start_pos and mid_pos:
            dx = mid_pos[0] - start_pos[0]
            dy = mid_pos[1] - start_pos[1]
            dz = mid_pos[2] - start_pos[2]
            current_distance = (dx*dx + dy*dy + dz*dz) ** 0.5
            
            if abs(current_distance - target_distance) < tolerance:
                return mid_param
            elif current_distance < target_distance:
                low_param = mid_param
            else:
                high_param = mid_param
        else:
            break
    
    return (low_param + high_param) / 2.0

def set_curve_color_pink(curve_obj):
    cmds.setAttr(f"{curve_obj}.overrideEnabled", 1)
    cmds.setAttr(f"{curve_obj}.overrideColor", 9)

def find_vectorify_group():
    all_transforms = cmds.ls(type='transform')
    for obj in all_transforms:
        if "VECTORIFY_01" in obj:
            return obj
    return None

def create_morph_group():
    if cmds.objExists("Morph_GRP"):
        cmds.delete("Morph_GRP")
    
    morph_grp = cmds.group(empty=True, name="Morph_GRP")
    
    vectorify_grp = find_vectorify_group()
    if vectorify_grp:
        morph_grp = cmds.parent(morph_grp, vectorify_grp)[0]
        print(f"Morph_GRP parented to {vectorify_grp}")
    
    return morph_grp

def show_usage_dialog():
    cmds.confirmDialog(
        title="Curve Morphing - Usage Instructions",
        message=(
            "CURVE MORPHING SCRIPT USAGE:\n\n"
            "1. Select exactly TWO NURBS curves\n"
            "2. Select the BASE curve first (the one to be morphed)\n"
            "3. Select the TARGET curve second (the shape to morph to)\n"
            "4. Run this script"
        ),
        button=['Got it!'],
        defaultButton='Got it!',
        backgroundColor=[0.15, 0.15, 0.15]
    )

def morph_curve():
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    sel = cmds.ls(sl=True, long=True)
    
    if len(sel) != 2:
        show_usage_dialog()
        return False
    
    base, target = sel[0], sel[1]
    
    
    cmds.select(clear=True)
    
    base_shapes = get_shape_nodes(base)
    target_shapes = get_shape_nodes(target)
    
    if not base_shapes or not target_shapes:
        cmds.error("Both objects must have shape nodes.")
    
    if (cmds.objectType(base_shapes[0]) != "nurbsCurve" or 
        cmds.objectType(target_shapes[0]) != "nurbsCurve"):
        cmds.error("Both objects must be NURBS curves.")
    
    base_cv_count = get_cv_count(base)
    if not base_cv_count:
        cmds.error("Could not get CV count for base curve.")
    
    
    cursor_started = False
    try:
        cmds.waitCursor(state=True)
        cursor_started = True
    except:
        pass
    
    try:
        morph_grp = create_morph_group()
        
        clusters = []
        joints = []
        
        original_length = get_curve_length(base)
        target_length = get_curve_length(target)
        
        if not original_length or not target_length:
            cmds.error("Could not get curve lengths.")
        
        length_ratio = original_length / target_length
        
        for i in range(base_cv_count):
            cmds.select(f"{base}.cv[{i}]")
            cluster_result = cmds.cluster(name=f"cv_{i}_cluster")
            cluster_name = cluster_result[1]
            clusters.append(cluster_name)
            
            cv_pos = cmds.pointPosition(f"{base}.cv[{i}]", world=True)
            
            cmds.select(clear=True)
            joint_name = cmds.joint(position=cv_pos, name=f"cv_{i}_joint")
            joints.append(joint_name)
            
            cmds.parentConstraint(joint_name, cluster_name, maintainOffset=False)
            
            cmds.setAttr(f"{joint_name}.visibility", 0)
            cmds.setAttr(f"{cluster_name}.visibility", 0)
            
            if cmds.objExists(morph_grp):
                cmds.parent(cluster_name, morph_grp)
                cmds.parent(joint_name, morph_grp)
        
        original_distances = calculate_original_distances(joints)
        
        current_param = 0.0
        for i in range(base_cv_count):
            if i == 0:
                target_pos = sample_curve_at_parameter(target, current_param)
                if target_pos:
                    cmds.xform(joints[i], worldSpace=True, translation=target_pos)
            else:
                if i-1 < len(original_distances):
                    target_distance = original_distances[i-1]
                    next_param = find_parameter_at_distance_on_curve(target, current_param, target_distance)
                    
                    if next_param <= 1.0:
                        next_pos = sample_curve_at_parameter(target, next_param)
                        if next_pos:
                            cmds.xform(joints[i], worldSpace=True, translation=next_pos)
                            current_param = next_param
                    else:
                        prev_pos = cmds.xform(joints[i-1], query=True, worldSpace=True, translation=True)
                        
                        if i >= 2:
                            prev_prev_pos = cmds.xform(joints[i-2], query=True, worldSpace=True, translation=True)
                            direction = [prev_pos[0] - prev_prev_pos[0], prev_pos[1] - prev_prev_pos[1], prev_pos[2] - prev_prev_pos[2]]
                            direction_length = (direction[0]**2 + direction[1]**2 + direction[2]**2) ** 0.5
                            if direction_length > 0:
                                direction = [direction[0]/direction_length, direction[1]/direction_length, direction[2]/direction_length]
                            else:
                                direction = [1, 0, 0]
                        else:
                            direction = [1, 0, 0]
                        
                        target_distance = original_distances[i-1]
                        new_pos = [
                            prev_pos[0] + direction[0] * target_distance,
                            prev_pos[1] + direction[1] * target_distance,
                            prev_pos[2] + direction[2] * target_distance
                        ]
                        
                        cmds.xform(joints[i], worldSpace=True, translation=new_pos)
        
        store_distances(base, original_distances)
        set_stored_slide_offset(base, 0.0)
        
        set_curve_color_pink(target)
        
        cmds.select(base)
        print(f"Curve morphing completed successfully. All elements grouped under {morph_grp}. Target curve '{target}' is now colored pink.")
        
        return True
        
    except Exception as e:
        cmds.warning(f"Morph curve operation failed: {str(e)}")
        return False
        
    finally:
        
        if cursor_started:
            try:
                cmds.waitCursor(state=False)
            except:
                pass



def slide_curve_backward():
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass    
    sel = cmds.ls(sl=True, long=True)
    if len(sel) == 0:
        result = cmds.confirmDialog(
            title='Selection Required',
            message='No curves selected!\n\nHow to use this script:\n1. Select the base curve (the one that will slide)\n2. Then select the target curve (the path to slide along)\n3. Run this script to slide backward\n\nNote: You must run the main morphing script first to set up the joints.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return False
    elif len(sel) == 1:
        result = cmds.confirmDialog(
            title='Second Curve Needed',
            message='Only one curve selected!\n\nHow to use this script:\n1. Keep your current selection (base curve)\n2. Add the target curve to your selection\n3. Run this script to slide backward\n\nSelection order: Base curve first, then target curve.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return False
    elif len(sel) > 2:
        result = cmds.confirmDialog(
            title='Too Many Objects Selected',
            message='More than 2 objects selected!\n\nHow to use this script:\n1. Select only the base curve (the one that will slide)\n2. Then select only the target curve (the path to slide along)\n3. Run this script to slide backward\n\nPlease select exactly 2 curves.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return False
    
    base, target = sel[0], sel[1]
    
    base_shapes = get_shape_nodes(base)
    target_shapes = get_shape_nodes(target)
    
    if not base_shapes or not target_shapes:
        cmds.error("Both objects must have shape nodes.")
    
    if (cmds.objectType(base_shapes[0]) != "nurbsCurve" or 
        cmds.objectType(target_shapes[0]) != "nurbsCurve"):
        cmds.error("Both objects must be NURBS curves.")
    
    base_cv_count = get_cv_count(base)
    if not base_cv_count:
        cmds.error("Could not get CV count for base curve.")
    
    joints = find_joints_for_curve(base)
    if not joints:
        cmds.error("No joints found. Please run the main morphing script first.")
    
    original_length = get_curve_length(base)
    target_length = get_curve_length(target)
    
    if not original_length or not target_length:
        cmds.error("Could not get curve lengths.")
    
    length_ratio = original_length / target_length
    max_parameter = min(1.0, length_ratio)
    
    current_offset = get_stored_slide_offset(base)
    slide_increment = 0.05
    new_offset = current_offset - slide_increment
    
    stored_distances = get_stored_distances(base)
    if not stored_distances:
        cmds.error("No stored distances found. Please run the forward slide script first.")
    
    total_original_length = sum(stored_distances)
    required_curve_length_ratio = total_original_length / get_curve_length(target)
    
    if new_offset < 0.0:
        cmds.warning("Cannot slide backward - already at the beginning of the curve.")
        cmds.select([base, target])
        return False
    
    if new_offset + required_curve_length_ratio > 1.0:
        cmds.warning("Cannot slide backward - not enough curve length remaining.")
        cmds.select([base, target])
        return False
    
    cmds.undoInfo(openChunk=True)
    
    try:
        first_joint_param = new_offset
        first_joint_pos = sample_curve_at_parameter(target, first_joint_param)
        if first_joint_pos:
            cmds.move(first_joint_pos[0], first_joint_pos[1], first_joint_pos[2], joints[0], absolute=True, worldSpace=True)
        
        current_param = first_joint_param
        
        for i in range(1, len(joints)):
            if i-1 < len(stored_distances):
                target_distance = stored_distances[i-1]
                next_param = find_parameter_at_distance_on_curve(target, current_param, target_distance)
                
                if next_param > 1.0:
                    cmds.undoInfo(closeChunk=True)
                    cmds.undo()
                    cmds.warning("Cannot slide backward - curve would extend beyond target curve end.")
                    cmds.select([base, target])
                    return False
                
                next_param = max(0.0, min(1.0, next_param))
                
                next_pos = sample_curve_at_parameter(target, next_param)
                if next_pos:
                    cmds.move(next_pos[0], next_pos[1], next_pos[2], joints[i], absolute=True, worldSpace=True)
                    current_param = next_param
        
        set_stored_slide_offset(base, new_offset)
        
    finally:
        cmds.undoInfo(closeChunk=True)
    
    cmds.select([base, target])
    return True





def v34w(obj, color=(0.5, 0.8, 1.0)):
    if not cmds.objExists(obj):
        cmds.warning(f"Object {obj} does not exist.")
        return
    
    try:
        cmds.setAttr(f"{obj}.useOutlinerColor", 1)
        cmds.setAttr(f"{obj}.outlinerColor", color[0], color[1], color[2], type="double3")
    except Exception as e:
        cmds.warning(f"Failed to set outliner color: {e}")

def l12m():
    selection = cmds.ls(selection=True)
    if selection:
        for obj in selection:
            cmds.xform(obj, centerPivots=True)

def n34o():
    selection = cmds.ls(sl=True)
    if not selection:
        cmds.warning("Please select one or more NURBS curves.")
        return

    for obj in selection:
        shape = obj
        if cmds.nodeType(shape) != "nurbsCurve":
            shapes = cmds.listRelatives(obj, shapes=True, type="nurbsCurve") or []
            if shapes:
                shape = shapes[0]
            else:
                cmds.warning(f"Skipping: {obj} (no NURBS curve found)")
                continue
        
        cmds.setAttr(f"{shape}.dispCV", 1)

def r78s(spans_num):
    selected = cmds.ls(selection=True)
    
    if not selected:
        return
    
    for obj in selected:
        shape_nodes = t90u(obj)
        
        if not shape_nodes:
            continue
        
        if cmds.objectType(shape_nodes[0]) == "nurbsCurve":
            # Delete existing history before rebuilding to avoid warning
            try:
                cmds.delete(obj, constructionHistory=True)
            except:
                pass
            
            degree = cmds.getAttr(obj + ".degree")
            
            try:
                cmds.rebuildCurve(
                    obj,
                    constructionHistory=False,
                    replaceOriginal=True,
                    rebuildType=0,
                    endKnots=1,
                    keepRange=1,
                    keepControlPoints=False,
                    keepEndPoints=False,
                    keepTangents=False,
                    spans=int(spans_num),
                    degree=degree,
                    tolerance=0.01
                )
            except Exception as e:
                continue


def r78s_v2(spans_num):
    selected = cmds.ls(selection=True)
    
    if not selected:
        return
    
    for obj in selected:
        shape_nodes = t90u(obj)
        
        if not shape_nodes:
            continue
        
        if cmds.objectType(shape_nodes[0]) == "nurbsCurve":
            degree = cmds.getAttr(obj + ".degree")
            
            try:
                cmds.rebuildCurve(
                    obj,
                    constructionHistory=False,
                    replaceOriginal=True,
                    rebuildType=0,
                    endKnots=1,
                    keepRange=1,
                    keepControlPoints=False,
                    keepEndPoints=False,
                    keepTangents=False,
                    spans=int(spans_num),
                    degree=degree,
                    tolerance=0.01
                )
            except Exception as e:
                continue



def t90u(transform_node):
    if cmds.nodeType(transform_node) == "transform":
        shapes = cmds.listRelatives(transform_node, fullPath=True, shapes=True)
        return shapes if shapes else []
    else:
        return [transform_node]

def v12w():
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    selection = cmds.ls(selection=True)
    
    if not selection:
        cmds.warning("Please select a NURBS curve.")
        return
    
    curve_name = selection[0]
    
    if not cmds.objectType(curve_name) == 'nurbsCurve' and not cmds.listRelatives(curve_name, shapes=True, type='nurbsCurve'):
        curve_shapes = cmds.listRelatives(curve_name, shapes=True, type='nurbsCurve')
        if not curve_shapes:
            cmds.warning("Selected object is not a NURBS curve.")
            return
        curve_shape = curve_shapes[0]
    else:
        curve_shape = curve_name
    
    original_length = cmds.arclen(curve_shape, constructionHistory=False)
    
    curve_degree = cmds.getAttr(f"{curve_shape}.degree")
    curve_spans = cmds.getAttr(f"{curve_shape}.spans")
    num_cvs = curve_spans + curve_degree
    
    cv_positions = []
    for i in range(num_cvs):
        pos = cmds.pointPosition(f"{curve_shape}.cv[{i}]", world=True)
        cv_positions.append(pos)
    
    start_pos = cv_positions[0]
    end_pos = cv_positions[-1]
    
    direction = [
        end_pos[0] - start_pos[0],
        end_pos[1] - start_pos[1],
        end_pos[2] - start_pos[2]
    ]
    
    straight_distance = math.sqrt(direction[0]**2 + direction[1]**2 + direction[2]**2)
    
    if straight_distance > 0:
        direction = [d/straight_distance for d in direction]
    else:
        cmds.warning("Start and end CVs are at the same position.")
        return
    
    new_end_pos = [
        start_pos[0] + direction[0] * original_length,
        start_pos[1] + direction[1] * original_length,
        start_pos[2] + direction[2] * original_length
    ]
    
    cmds.undoInfo(openChunk=True)
    try:
        for i in range(num_cvs):
            if num_cvs == 1:
                t = 0
            else:
                t = i / (num_cvs - 1)
            
            new_pos = [
                start_pos[0] + t * (new_end_pos[0] - start_pos[0]),
                start_pos[1] + t * (new_end_pos[1] - start_pos[1]),
                start_pos[2] + t * (new_end_pos[2] - start_pos[2])
            ]
            
            cmds.move(new_pos[0], new_pos[1], new_pos[2], 
                     f"{curve_shape}.cv[{i}]", absolute=True, worldSpace=True)
        
        cmds.select(curve_name)
        
    except Exception as e:
        cmds.warning(f"Error positioning CVs: {str(e)}")
    finally:
        cmds.undoInfo(closeChunk=True)

def x34y():
    sel = cmds.ls(sl=True)
    
    for s in sel:
        cmds.select(s)
        v12w()
        
    cmds.select(sel)

def b78c():
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass
    
    cmds.waitCursor(state=True)
    
    try:
        selection = cmds.ls(selection=True)
        
        if not selection:
            cmds.warning("Please select a curve.")
            return
        
        all_locators = []
        
        for obj in selection:
            if not cmds.objectType(obj, isType='nurbsCurve'):
                shapes = cmds.listRelatives(obj, shapes=True, type='nurbsCurve')
                if shapes:
                    obj = cmds.listRelatives(shapes[0], parent=True)[0]
                else:
                    cmds.warning(f"{obj} is not a NURBS curve.")
                    continue
            
            shape_node = cmds.listRelatives(obj, shapes=True, type='nurbsCurve')[0]
            
            try:
                cmds.setAttr(f"{shape_node}.lockLength", 0)
            except:
                pass
            
            cmds.setAttr(f"{obj}.dispCV", 1)
            cmds.setAttr(f"{obj}.visibility", 1)
            
            num_cvs = cmds.getAttr(f"{shape_node}.spans") + cmds.getAttr(f"{shape_node}.degree")
            
            cluster_handles = []
            
            for i in range(num_cvs):
                cluster_base_name = "cluster_esn_piv_anim"
                cluster_result = cmds.cluster(f"{shape_node}.cv[{i}]", name=cluster_base_name)
                cluster_handle = cluster_result[1]
                cmds.hide(cluster_handle)
                cmds.setAttr(f"{cluster_handle}.hiddenInOutliner", True)
                cluster_handles.append(cluster_handle)
            
            curve_locators = []
            
            for cluster_handle in cluster_handles:
                loc_base_name = "repath_esn_piv_anim"
                loc_result = cmds.spaceLocator(name=loc_base_name)
                loc = loc_result[0]
                
                cmds.matchTransform(loc, cluster_handle, pos=True, rot=True)
                
                curve_locators.append(loc)
            
            for i, loc in enumerate(curve_locators):
                if i < len(cluster_handles):
                    try:
                        cmds.parent(cluster_handles[i], loc)
                    except:
                        pass
            
            for cluster in cluster_handles:
                cmds.setAttr(f"{cluster}.translateX", lock=True)
                cmds.setAttr(f"{cluster}.translateY", lock=True)
                cmds.setAttr(f"{cluster}.translateZ", lock=True)
            
            for loc in curve_locators:
                cmds.setAttr(f"{loc}.displayHandle", 1)
                cmds.setAttr(f"{loc}.overrideEnabled", 1)
                cmds.setAttr(f"{loc}.overrideColor", 13)
                
                cmds.setAttr(f"{loc}.scaleX", lock=True)
                cmds.setAttr(f"{loc}.scaleY", lock=True)
                cmds.setAttr(f"{loc}.scaleZ", lock=True)
                
                try:
                    v34w(loc, color=(0.5, 0.8, 1.0))
                except:
                    pass
            
            curve_length = cmds.arclen(obj)
            scale_factor = curve_length / 20.0
            
            for loc in curve_locators:
                cmds.setAttr(f"{loc}.localScale", scale_factor, scale_factor, scale_factor)
            
            cmds.select(curve_locators, replace=True)
            
            current_selection = curve_locators[:]
            for i in range(len(current_selection) - 1):
                try:
                    cmds.parent(current_selection[i+1], current_selection[i])
                except:
                    pass
            
            node = cmds.createNode("blindDataTemplate", name="anim_movement_on_curve_tool_sequent_control")
            
            attr_name = f"curve"
            cmds.addAttr(node, longName=attr_name, niceName=attr_name, attributeType='long', defaultValue=0)
            cmds.setAttr(f"{node}.{attr_name}", edit=True, channelBox=True)
            cmds.connectAttr(f"{obj}.visibility", f"{node}.{attr_name}", force=True)
            
            for i, loc in enumerate(curve_locators):
                if i == 0:
                    attr_name = f"base_sequent_loc"
                else:
                    attr_name = f"loc{i}"
                
                cmds.addAttr(node, longName=attr_name, niceName=attr_name, attributeType='long', defaultValue=0)
                cmds.setAttr(f"{node}.{attr_name}", edit=True, channelBox=True)
                cmds.connectAttr(f"{loc}.visibility", f"{node}.{attr_name}", force=True)
            
            if curve_locators:
                root_locator = curve_locators[0]
                
                curve_parents = cmds.listRelatives(obj, parent=True, fullPath=True)
                vectorify_group = None
                
                if curve_parents:
                    for parent in curve_parents:
                        if "VECTORIFY" in parent:
                            vectorify_group = parent
                            break
                
                if vectorify_group:
                    try:
                        current_parent = cmds.listRelatives(root_locator, parent=True)
                        if not current_parent or current_parent[0] != vectorify_group:
                            cmds.parent(root_locator, vectorify_group)
                    except Exception as e:
                        pass
                
                all_locators.extend(curve_locators)
                
                for attr in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]:
                    if cmds.objExists(f"{obj}.{attr}"):
                        cmds.setAttr(f"{obj}.{attr}", lock=True)
        
        if all_locators:
            cmds.select(clear=True)
            for loc in all_locators:
                if cmds.objExists(loc):
                    cmds.select(loc, add=True)
    
    finally:
        cmds.waitCursor(state=False)

def d90e():
    objects_to_bake = []
    
    set_name = "Vectorify_Set"
    if cmds.objExists(set_name):
        set_members = cmds.sets(set_name, query=True) or []
        objects_to_bake = [obj for obj in set_members if cmds.objExists(obj)]
    else:
        stored_objects, _ = load_vectorify_data()
        if stored_objects:
            all_dag_objects = cmds.ls(dag=True, long=True)
            for stored_name in stored_objects:
                for dag_obj in all_dag_objects:
                    if dag_obj.split('|')[-1] == stored_name:
                        objects_to_bake.append(dag_obj)
                        break
    
    if not objects_to_bake:
        cmds.warning("No objects found to bake.")


        curve_to_surface_node = cmds.ls("*Curve_To_Surface*")
        for obj in curve_to_surface_node:
            if cmds.objExists(obj):
                try:
                    cmds.delete(obj)
                except:
                    pass

        vec_env = cmds.ls("*VECTORIFY_TEMP_ENV*")
        for env in vec_env:
            if cmds.objExists(env):
                try:
                    cmds.delete(env)
                except:
                    pass

        vec_backup = cmds.ls("*Vectorify_Backup*")
        for env in vec_backup:
            if cmds.objExists(env):
                try:
                    cmds.delete(env)
                except:
                    pass

        
        return
    
    try:
        cmds.evaluationManager(mode="off")
        cmds.refresh(suspend=True)
        
        start_frame = int(cmds.playbackOptions(query=True, minTime=True))
        end_frame = int(cmds.playbackOptions(query=True, maxTime=True))
        
        cmds.bakeResults(
            objects_to_bake,
            time=(start_frame, end_frame),
            simulation=True,
            sampleBy=1,
            oversamplingRate=1,
            disableImplicitControl=True,
            preserveOutsideKeys=True,
            sparseAnimCurveBake=False,
            removeBakedAttributeFromLayer=False,
            removeBakedAnimFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            controlPoints=False
        )
        
        if cmds.objExists(set_name):
            cmds.delete(set_name)
        
        all_vectorify_groups = cmds.ls("*_VECTORIFY_*", type="transform")
        for group in all_vectorify_groups:
            if cmds.objExists(group):
                try:
                    cmds.delete(group)
                except:
                    pass
        
        all_motionpath_groups = cmds.ls("*vectorify_motionpath*", type="transform")
        for mp_group in all_motionpath_groups:
            if cmds.objExists(mp_group):
                try:
                    cmds.delete(mp_group)
                except:
                    pass
        
        all_repath_objects = cmds.ls("*repath_esn*", type="transform")
        for repath_obj in all_repath_objects:
            if cmds.objExists(repath_obj):
                try:
                    cmds.delete(repath_obj)
                except:
                    pass
        
        all_cluster_handles = cmds.ls("*cluster_esn_piv_anim*", type="transform")
        for cluster in all_cluster_handles:
            if cmds.objExists(cluster):
                try:
                    cmds.delete(cluster)
                except:
                    pass


        vec_backup = cmds.ls("*Vectorify_Backup*")
        for env in vec_backup:
            if cmds.objExists(env):
                try:
                    cmds.delete(env)
                except:
                    pass                     


        
        path_name = cmds.textField(x12s_field, query=True, text=True)
        if path_name and cmds.objExists(path_name):
            curve_shapes = cmds.listRelatives(path_name, shapes=True, type='nurbsCurve')
            if curve_shapes or cmds.objectType(path_name) == 'nurbsCurve':
                try:
                    cmds.delete(path_name)
                except:
                    pass
        
        delete_vectorify_network()
        
        u12i()
        
        cmds.evaluationManager(mode="parallel")
        cmds.refresh(suspend=False)
        
    except Exception as e:
        cmds.evaluationManager(mode="parallel")
        cmds.refresh(suspend=False)
        cmds.warning(f"Bake and delete operation failed: {e}")


def create_path_from_selection(*args):
    selected_objects = cmds.ls(selection=True)
    ct = cmds.currentTime(q=True)
    
    if not selected_objects:
        cmds.warning("Please select one or more animated objects to track their paths.")
        return
    
    start_frame = cmds.playbackOptions(q=True, min=True)
    end_frame = cmds.playbackOptions(q=True, max=True)
    
    try:
        cmds.waitCursor(state=True)
        cmds.evaluationManager(mode="off")
        cmds.refresh(suspend=True)
        
        created_curves = []
        
        for object_name in selected_objects:
            if not cmds.objExists(object_name):
                cmds.warning("Selected object '{0}' does not exist.".format(object_name))
                continue
            
            has_anim, message = hma(object_name, start_frame, end_frame)
            if not has_anim:
                cmds.warning("Object '{0}': {1}".format(object_name, message))
                continue
            
            positions = []
            for frame in range(int(start_frame), int(end_frame) + 1):
                cmds.currentTime(frame, edit=True)
                pos = cmds.xform(object_name, query=True, worldSpace=True, translation=True)
                positions.append(pos)
            
            if not positions:
                cmds.warning("No positions captured for '{0}'. Check the timeline range.".format(object_name))
                continue
            
            curve = cmds.curve(d=3, p=positions)
            
            cmds.setAttr("{0}.overrideEnabled".format(curve), 1)
            cmds.setAttr("{0}.overrideColor".format(curve), 17)
            
            cmds.setAttr(curve + '.useOutlinerColor', True)
            cmds.setAttr(curve + ".outlinerColor", 1, 1, 0)
            
            created_curves.append(curve)
        
        if created_curves:
            cmds.currentTime(ct)
            
            cmds.select(created_curves, replace=True)
            
            n34o()
            l12m()
            
            show_nurbs_curves_in_viewports()
            
            if len(created_curves) == 1:
                cmds.textField(x12s_field, edit=True, text=created_curves[0])
                controls_list, _ = t67y()
                q45r(controls_list, created_curves[0])
            else:
                curve_names = ", ".join(created_curves)
                cmds.textField(x12s_field, edit=True, text=curve_names)
        else:
            cmds.warning("No valid paths could be created from the selected objects.")

    except Exception as e:
        cmds.warning("Failed to create path: {0}".format(str(e)))
    finally:
        cmds.waitCursor(state=False)
        cmds.evaluationManager(mode="parallel")
        cmds.refresh(suspend=False)



def is_straight(curve_name=None):
    if curve_name:
        if not cmds.objExists(curve_name):
            return False
        selected = cmds.ls(curve_name, type='nurbsCurve')
        if not selected:
            selected = cmds.ls(curve_name, dag=True, type='nurbsCurve')
    else:
        selected = cmds.ls(selection=True, type='nurbsCurve')
        if not selected:
            selected = cmds.ls(selection=True, dag=True, type='nurbsCurve')
    
    if not selected:
        return False
    
    curve = selected[0]
    cvs = cmds.ls(curve + '.cv[*]', flatten=True)
    num_cvs = len(cvs)
    
    if num_cvs < 2:
        return False
    
    cv_positions = []
    for cv in cvs:
        pos = cmds.xform(cv, query=True, worldSpace=True, translation=True)
        cv_positions.append(pos)
    
    tolerance = 0.001
    for i in range(num_cvs):
        for j in range(i + 1, num_cvs):
            dist = distance(cv_positions[i], cv_positions[j])
            if dist < tolerance:
                print("NOT straight")
                return False
    
    segments = []
    for i in range(num_cvs - 1):
        segments.append((cv_positions[i], cv_positions[i + 1]))
    
    is_closed = cmds.getAttr(curve + '.form') != 0
    if is_closed and num_cvs > 2:
        segments.append((cv_positions[-1], cv_positions[0]))
    
    for i in range(len(segments)):
        for j in range(i + 2, len(segments)):
            if abs(i - j) <= 1 or (is_closed and (i == 0 and j == len(segments) - 1)):
                continue
            
            if segments_intersect(segments[i], segments[j]):
                print("NOT straight")
                return False
    
    print("is_straight")
    return True


def distance(p1, p2):
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2)**0.5

def segments_intersect(seg1, seg2):
    p1, p2 = seg1
    p3, p4 = seg2
    tolerance = 0.01
    
    d1 = [p2[i] - p1[i] for i in range(3)]
    d2 = [p4[i] - p3[i] for i in range(3)]
    w0 = [p1[i] - p3[i] for i in range(3)]
    
    a = dot(d1, d1)
    b = dot(d1, d2)
    c = dot(d2, d2)
    d = dot(d1, w0)
    e = dot(d2, w0)
    
    denom = a * c - b * b
    
    if abs(denom) < 1e-10:
        return False
    
    s = (b * e - c * d) / denom
    t = (a * e - b * d) / denom
    
    if 0 <= s <= 1 and 0 <= t <= 1:
        closest1 = [p1[i] + s * d1[i] for i in range(3)]
        closest2 = [p3[i] + t * d2[i] for i in range(3)]
        dist = distance(closest1, closest2)
        if dist < tolerance:
            return True
    
    return False

def dot(v1, v2):
    return sum(v1[i] * v2[i] for i in range(len(v1)))



def hma(object_name, start_frame, end_frame):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    positions = []
    frame_range = int(end_frame - start_frame + 1)
    
    if frame_range < 2:
        return False, "Timeline range is too short."
    
    sample_frames = list(range(int(start_frame), int(end_frame) + 1))
    
    current_time = cmds.currentTime(q=True)
    try:
        for frame in sample_frames:
            cmds.currentTime(frame, edit=True)
            pos = cmds.xform(object_name, query=True, worldSpace=True, translation=True)
            positions.append(pos)
    finally:
        cmds.currentTime(current_time, edit=True)
    
    if len(positions) < 2:
        return False, "Could not sample enough positions."
    
    tolerance = 0.001
    first_pos = positions[0]
    has_movement = False
    max_distance = 0.0
    
    for pos in positions[1:]:
        dx = pos[0] - first_pos[0]
        dy = pos[1] - first_pos[1]
        dz = pos[2] - first_pos[2]
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        if distance > max_distance:
            max_distance = distance
        if distance > tolerance:
            has_movement = True
    
    if not has_movement:
        return False, "The object shows no position changes (max distance: {0:.6f} units). Please ensure the object moves in world space.".format(max_distance)
    
    return True, "Animation detected (movement range: {0:.3f} units).".format(max_distance)


def reverse_selected_curves():
    selection = cmds.ls(selection=True, long=True)
    
    if not selection:
        cmds.warning("No objects selected. Please select one or more NURBS curves.")
        return
    
    cmds.waitCursor(state=True)
    
    try:
        curves_to_reverse = []
        
        for obj in selection:
            if cmds.nodeType(obj) == 'nurbsCurve':
                if obj not in curves_to_reverse:
                    curves_to_reverse.append(obj)
            else:
                shapes = cmds.listRelatives(obj, shapes=True, type='nurbsCurve')
                if shapes:
                    if obj not in curves_to_reverse:
                        curves_to_reverse.append(obj)
                else:
                    all_curves = cmds.ls(type='nurbsCurve')
                    
                    for curve_shape in all_curves:
                        curve_transform = cmds.listRelatives(curve_shape, parent=True, fullPath=True)
                        if not curve_transform:
                            continue
                        
                        curve = curve_transform[0]
                        history = cmds.listHistory(curve) or []
                        
                        for node in history:
                            if cmds.nodeType(node) == 'cluster':
                                matrix_conn = cmds.listConnections(f"{node}.matrix", source=True, destination=False)
                                if not matrix_conn:
                                    continue
                                
                                cluster_handle = matrix_conn[0]
                                
                                current = cluster_handle
                                found = False
                                while current:
                                    if current == obj:
                                        found = True
                                        break
                                    parent_result = cmds.listRelatives(current, parent=True, fullPath=True)
                                    if not parent_result:
                                        break
                                    current = parent_result[0]
                                
                                if found:
                                    if curve not in curves_to_reverse:
                                        curves_to_reverse.append(curve)
                                    break
        
        if not curves_to_reverse:
            cmds.warning("No NURBS curves found in selection.")
            return
        
        reversed_curves = []
        
        cmds.undoInfo(openChunk=True)
        
        for curve in curves_to_reverse:
            try:
                history = cmds.listHistory(curve) or []
                has_repath_clusters = False
                
                for node in history:
                    if cmds.nodeType(node) == 'cluster':
                        matrix_conn = cmds.listConnections(f"{node}.matrix", source=True, destination=False)
                        if matrix_conn:
                            cluster_handle = matrix_conn[0]
                            parent = cmds.listRelatives(cluster_handle, parent=True, fullPath=True)
                            if parent and 'repath_esn_piv_anim' in parent[0]:
                                has_repath_clusters = True
                                break
                
                if not has_repath_clusters:
                    cmds.delete(curve, constructionHistory=True)
                    result = cmds.reverseCurve(curve, 
                                             constructionHistory=False,
                                             replaceOriginal=True)
                else:
                    mel.eval(f'catchQuiet(`reverseCurve -ch 0 -rpo 1 "{curve}"`);')
                
                reversed_curves.append(curve)
                
            except Exception as curve_error:
                try:
                    mel.eval(f'catchQuiet(`reverseCurve -ch 0 -rpo 1 "{curve}"`);')
                    reversed_curves.append(curve)
                except Exception as mel_error:
                    pass
        
        cmds.undoInfo(closeChunk=True)
        
        if reversed_curves:
            cmds.select(reversed_curves)
        else:
            cmds.warning("No curves were successfully reversed.")
            
    except Exception as e:
        cmds.error(f"Error reversing curves: {str(e)}")
    finally:
        cmds.waitCursor(state=False)


def assign_path_name(*args):
    selection = cmds.ls(selection=True)
    if selection:
        curve_found = False
        for obj in selection:
            if cmds.objectType(obj, isType='nurbsCurve') or cmds.listRelatives(obj, shapes=True, type='nurbsCurve'):
                cmds.textField(x12s_field, edit=True, text=obj)
                
                controls_list, _ = t67y()
                q45r(controls_list, obj)
                
                curve_found = True
                break
        
        if not curve_found:
            cmds.warning("Please select a NURBS curve!")
    else:
        cmds.warning("No objects selected!")

def assign_ctrls(*args):
    selection = cmds.ls(selection=True)
    if selection:
        ctrl_names = ", ".join(selection)
        cmds.textField(y34t_field, edit=True, text=ctrl_names)
        
        _, path_name = t67y()
        q45r(selection, path_name)
        
        path_name = cmds.textField(x12s_field, query=True, text=True)
        if path_name and cmds.objExists(path_name):
            save_vectorify_data(selection, path_name)
    else:
        cmds.warning("No objects selected!")

j90k_tool = r78v()


def reverse_parent_hierarchy():
    sel = cmds.ls(selection=True, long=True)
    
    if not sel:
        cmds.warning("Please select a locator or transform node.")
        return
    
    if len(sel) > 1:
        cmds.warning("Please select only one object.")
        return
    
    obj = sel[0]
    original_uuid = cmds.ls(obj, uuid=True)[0]
    
    shape = cmds.listRelatives(obj, shapes=True, fullPath=True)
    if not shape or cmds.nodeType(shape[0]) != 'locator':
        cmds.warning("Please select a locator. Selected object is not a locator.")
        return
    
    children = cmds.listRelatives(obj, children=True, fullPath=True, type='transform')
    child_locator = None
    
    if children:
        for child in children:
            child_shape = cmds.listRelatives(child, shapes=True, fullPath=True)
            if child_shape and cmds.nodeType(child_shape[0]) == 'locator':
                child_locator = child
                break
    
    if child_locator:
        start_node = child_locator
    else:
        start_node = obj
    
    hierarchy_uuids = []
    hierarchy_names = []
    current = start_node
    
    while True:
        uuid = cmds.ls(current, uuid=True)[0]
        short_name = current.split('|')[-1]
        
        hierarchy_uuids.append(uuid)
        hierarchy_names.append(short_name)
        
        parent = cmds.listRelatives(current, parent=True, fullPath=True)
        if not parent:
            break
        
        parent_shape = cmds.listRelatives(parent[0], shapes=True, fullPath=True)
        if not parent_shape or cmds.nodeType(parent_shape[0]) != 'locator':
            break
        
        current = parent[0]
    
    if len(hierarchy_uuids) < 2:
        cmds.warning("Selected object has no parents to reverse.")
        return
    
    transforms_data = {}
    for uuid in hierarchy_uuids:
        node = cmds.ls(uuid, long=True)[0]
        transforms_data[uuid] = {
            'translate': cmds.xform(node, query=True, translation=True, worldSpace=True),
            'rotate': cmds.xform(node, query=True, rotation=True, worldSpace=True),
            'scale': cmds.xform(node, query=True, scale=True, worldSpace=True)
        }
    
    try:
        top_uuid = hierarchy_uuids[-1]
        top_node = cmds.ls(top_uuid, long=True)[0]
        external_parent = cmds.listRelatives(top_node, parent=True, fullPath=True)
        
        for uuid in hierarchy_uuids:
            node = cmds.ls(uuid, long=True)[0]
            current_parent = cmds.listRelatives(node, parent=True)
            if current_parent:
                cmds.parent(node, world=True)
        
        for i in range(1, len(hierarchy_uuids)):
            child_uuid = hierarchy_uuids[i]
            parent_uuid = hierarchy_uuids[i - 1]
            
            child_node = cmds.ls(child_uuid, long=True)[0]
            parent_node = cmds.ls(parent_uuid, long=True)[0]
            
            cmds.parent(child_node, parent_node)
        
        if external_parent:
            new_root_uuid = hierarchy_uuids[0]
            new_root_node = cmds.ls(new_root_uuid, long=True)[0]
            cmds.parent(new_root_node, external_parent[0])
        
        for uuid in hierarchy_uuids:
            node = cmds.ls(uuid, long=True)[0]
            cmds.xform(node, translation=transforms_data[uuid]['translate'], worldSpace=True)
            cmds.xform(node, rotation=transforms_data[uuid]['rotate'], worldSpace=True)
            cmds.xform(node, scale=transforms_data[uuid]['scale'], worldSpace=True)
        
        original_node_result = cmds.ls(original_uuid, long=True)
        if original_node_result:
            cmds.select(original_node_result[0], replace=True)
        
    except Exception as e:
        cmds.error(f"Error during hierarchy reversal: {str(e)}")
        import traceback
        traceback.print_exc()
 


def attach_to_straight_curve(*args):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    def execute_connect_logic(objects, curve, frame_range):
        time = cmds.currentTime(query=True)
        items_to_parent = []
        
        if not cmds.objExists(curve):
            return
        
        maya_unit = cmds.currentUnit(query=True, linear=True)
        if maya_unit != "cm":
            cmds.currentUnit(linear="cm")
        
        cmds.select(curve)
        lock_curve_length()
        
        cmds.optionVar(intValue=('animBlendingOpt', 1))
        cmds.optionVar(intValue=('animBlendBrokenInputOpt', 1))
        
        cmds.select(objects)
        maya_version = mel.eval('getApplicationVersionAsFloat')
        
        if maya_version >= 2019:
            try:
                mel.eval('python("from maya.plugin.evaluator.cache_preferences import CachePreferenceEnabled")')
                mel.eval('python("CachePreferenceEnabled().set_value( False )")')
            except:
                pass
        
        set_name = "Vectorify_Set"
        if not cmds.objExists(set_name):
            cmds.sets(name=set_name, empty=True)
        
        locator_objects = create_parent_locators(objects)
        
        for obj in locator_objects:
            mp = create_motion_path(obj, curve, frame_range)
            tmp_sel = cmds.ls(selection=True)
            items_to_parent.append(tmp_sel[0])
        
        parent_objects_to_locators(items_to_parent, locator_objects)
        
        for i in range(len(items_to_parent)):
            gr = cmds.group(locator_objects[i], name="maintain_anim_offset")
            cmds.xform(objectSpace=True, pivots=[0, 0, 0])
            
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']:
                cmds.setAttr(f"{gr}.{attr}", lock=True, keyable=False, channelBox=False)
            
            node = cmds.createNode("blindDataTemplate", name="vectorify_movement_curve_tool")
            
            attr = add_custom_attr("obj_on_curve", node)
            cmds.connectAttr(f"{items_to_parent[i]}.visibility", attr, force=True)
            
            attr = add_custom_attr("parent_object", node)
            cmds.connectAttr(f"{locator_objects[i]}.visibility", attr, force=True)
            
            attr = add_custom_attr("parent_group", node)
            cmds.connectAttr(f"{gr}.visibility", attr, force=True)
        
        curve_short_name = curve.split('|')[-1].split(':')[-1]
        master_group = cmds.group(items_to_parent + [curve], name=f"{curve_short_name}_VECTORIFY_01")
        v34w(master_group, color=(1.0, 0.4, 0.7))
        cmds.xform(pivots=[0, 0, 0])
        
        try:
            cmds.sets(objects, edit=True, addElement=set_name)
        except Exception as e:
            pass
        
        constrained_count = apply_force_parent_constraint_to_vectorify(master_group)
        
        try:
            valid_locs = [loc for loc in locator_objects if cmds.objExists(loc)]
            if valid_locs:
                cmds.select(valid_locs)
            else:
                cmds.select(clear=True)
        except:
            cmds.select(clear=True)
        
        cmds.currentTime(time)
        cmds.currentUnit(linear=maya_unit)
        
        backup_set = get_or_create_backup_set()
        backup_network = get_or_create_backup_network()
        
        if cmds.objExists("VECTORIFY_DO_NOT_TOUCH"):
            backup_locs = cmds.listRelatives("VECTORIFY_DO_NOT_TOUCH", children=True, fullPath=True, type='transform') or []
            
            if backup_locs:
                backup_locs_long = []
                for loc in backup_locs:
                    if cmds.objExists(loc) and '_backupLoc' in loc:
                        loc_long = cmds.ls(loc, long=True)[0]
                        
                        # Add to set if not already a member
                        if not cmds.sets(loc_long, isMember=backup_set):
                            cmds.sets(loc_long, add=backup_set)
                        
                        backup_locs_long.append(loc_long)
                
                # Update network node with all backup locators
                if backup_locs_long:
                    save_backup_locators_to_network(backup_locs_long)
        
        return master_group

    path_name = cmds.textField(x12s_field, query=True, text=True)
    ctrl_names = cmds.textField(y34t_field, query=True, text=True)
    j90k_tool.b90c()
    
    if not path_name or not ctrl_names:
        cmds.warning("Please specify both path and controls!")
        return
    
    if not cmds.objExists(path_name):
        cmds.warning(f"Path '{path_name}' does not exist!")
        return
    
    ctrl_list = [name.strip() for name in ctrl_names.split(',')]
    existing_ctrls = [ctrl for ctrl in ctrl_list if cmds.objExists(ctrl)]
    
    if not existing_ctrls:
        cmds.warning("No valid controls found!")
        return

    undo_state = cmds.undoInfo(query=True, state=True)
    cmds.undoInfo(state=False)        

    
    cmds.waitCursor(state=True)
    cmds.refresh(suspend=True)
    
    maya_version = cmds.about(version=True)
    eval_mode = None
 
    try:
        if float(maya_version.split()[0]) >= 2016:
            eval_mode = cmds.evaluationManager(query=True, mode=True)
            if eval_mode[0] != "off":
                cmds.evaluationManager(mode="off")
        
        frame_range = [
            cmds.playbackOptions(query=True, min=True),
            cmds.playbackOptions(query=True, max=True) + 1
        ]
        
        master_group = execute_connect_logic(existing_ctrls, path_name, frame_range)
        
        cmds.select(path_name, replace=True)
        b78c()
        cmds.waitCursor(state=False)
        
        msg = "                       Successful!\n\nDelete the Vectorify group to undo.\nUse REVERT SETUP to remove the whole setup."
        cmds.confirmDialog(
            title='Connected to Curve',
            message=msg,
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.12, 0.12, 0.12]
        )
        
        return master_group
        
    finally:
        cmds.refresh(suspend=False)
        cmds.undoInfo(state=undo_state)        
        
        if eval_mode:
            cmds.evaluationManager(mode=eval_mode[0])


def attach_to_not_straight_curve(*args):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    path_name = cmds.textField(x12s_field, query=True, text=True)
    ctrl_names = cmds.textField(y34t_field, query=True, text=True)
    j90k_tool.b90c()
    
    if not path_name or not ctrl_names:
        cmds.warning("Please specify both path and controls!")
        return
    
    if not cmds.objExists(path_name):
        cmds.warning(f"Path '{path_name}' does not exist!")
        return
    
    ctrl_list = [name.strip() for name in ctrl_names.split(',')]
    existing_ctrls = [ctrl for ctrl in ctrl_list if cmds.objExists(ctrl)]
    
    if not existing_ctrls:
        cmds.warning("No valid controls found!")
        return

    undo_state = cmds.undoInfo(query=True, state=True)
    cmds.undoInfo(state=False)
    
    cmds.waitCursor(state=True)
    cmds.refresh(suspend=True)
    
    maya_version = cmds.about(version=True)
    eval_mode = None
 
    try:
        if float(maya_version.split()[0]) >= 2016:
            eval_mode = cmds.evaluationManager(query=True, mode=True)
            if eval_mode[0] != "off":
                cmds.evaluationManager(mode="off")
        
        frame_range = [
            cmds.playbackOptions(query=True, min=True),
            cmds.playbackOptions(query=True, max=True) + 1
        ]
        
        time = cmds.currentTime(query=True)
        motion_path_groups = []
        motion_path_nodes = []
        
        maya_unit = cmds.currentUnit(query=True, linear=True)
        if maya_unit != "cm":
            cmds.currentUnit(linear="cm")
        
        cmds.select(path_name)
        lock_curve_length()
        
        cmds.optionVar(intValue=('animBlendingOpt', 1))
        cmds.optionVar(intValue=('animBlendBrokenInputOpt', 1))
        
        maya_version_float = mel.eval('getApplicationVersionAsFloat')
        
        if maya_version_float >= 2019:
            try:
                mel.eval('python("from maya.plugin.evaluator.cache_preferences import CachePreferenceEnabled")')
                mel.eval('python("CachePreferenceEnabled().set_value( False )")')
            except:
                pass
        
        set_name = "Vectorify_Set"
        if not cmds.objExists(set_name):
            cmds.sets(name=set_name, empty=True)
        
        for obj in existing_ctrls:
            mp = create_motion_path(obj, path_name, frame_range)
            motion_path_nodes.append(mp)
            tmp_sel = cmds.ls(selection=True)
            motion_path_groups.append(tmp_sel[0])
        
        for mp in motion_path_nodes:
            selected_curves = [f"{mp}.uValue"]
            
            for curve in selected_curves:
                smoothness = 0.4
                iterations = 2
                
                for iteration in range(iterations):
                    times = cmds.keyframe(curve, query=True, timeChange=True)
                    values = cmds.keyframe(curve, query=True, valueChange=True)
                    
                    if not times or len(times) < 3:
                        continue
                    
                    keys_to_remove = []
                    
                    for i in range(1, len(times) - 1):
                        prev_val = values[i-1]
                        curr_val = values[i]
                        next_val = values[i+1]
                        
                        expected_val = (prev_val + next_val) / 2.0
                        deviation = abs(curr_val - expected_val)
                        neighbor_range = abs(next_val - prev_val)
                        
                        if neighbor_range > 0:
                            deviation_ratio = deviation / (neighbor_range + 0.001)
                            if deviation_ratio > smoothness:
                                keys_to_remove.append(times[i])
                        else:
                            if deviation > 0.001:
                                keys_to_remove.append(times[i])
                    
                    if keys_to_remove:
                        for key_time in keys_to_remove:
                            cmds.cutKey(curve, time=(key_time, key_time))

                    cmds.keyTangent(curve, inTangentType='auto', outTangentType='auto')
        
        cmds.currentTime(time)
        cmds.currentUnit(linear=maya_unit)
        
        objects = existing_ctrls
        
        current_time = cmds.currentTime(query=True)
        
        cmds.select(objects)
        add_initial_keyframes(objects)
        create_locators_at_selection()
        rename_locators("vectorify_ctrl_", objects)
        hide_scale_attrs()
        
        locator_objects = cmds.ls(selection=True)
        
        for i, loc in enumerate(locator_objects):
            if i < len(objects):
                obj = objects[i]
                obj_bbox = cmds.exactWorldBoundingBox(obj)
                obj_size = max([
                    obj_bbox[3] - obj_bbox[0],
                    obj_bbox[4] - obj_bbox[1],
                    obj_bbox[5] - obj_bbox[2]
                ]) * 0.5
                
                current_unit = cmds.currentUnit(query=True, linear=True)
                scale_factor = obj_size
                
                unit_multipliers = {
                    'mm': 10.0, 'cm': 1.0, 'm': 0.1,
                    'in': 2.54, 'ft': 0.3048, 'yd': 0.0914
                }
                
                if current_unit in unit_multipliers:
                    scale_factor *= unit_multipliers[current_unit]
                
                loc_shape = cmds.listRelatives(loc, shapes=True)
                if loc_shape:
                    cmds.setAttr(f"{loc_shape[0]}.localScaleX", scale_factor)
                    cmds.setAttr(f"{loc_shape[0]}.localScaleY", scale_factor)
                    cmds.setAttr(f"{loc_shape[0]}.localScaleZ", scale_factor)
                
                cmds.setAttr(f"{loc}.displayHandle", True)
        
        set_override_color(18)
        
        temp_constraints = parent_constrain(objects, locator_objects)
        bake_animation()
        if temp_constraints:
            cmds.delete(temp_constraints)
        
        locator_world_data = {}
        for loc in locator_objects:
            locator_world_data[loc] = {}
            for frame in range(int(frame_range[0]), int(frame_range[1]) + 1):
                cmds.currentTime(frame)
                locator_world_data[loc][frame] = {
                    'translate': cmds.xform(loc, query=True, worldSpace=True, translation=True),
                    'rotate': cmds.xform(loc, query=True, worldSpace=True, rotation=True),
                    'scale': cmds.xform(loc, query=True, worldSpace=True, scale=True)
                }
        
        items_to_parent = []
        for i, loc in enumerate(locator_objects):
            if i < len(motion_path_groups):
                mp_group = motion_path_groups[i]
                if cmds.objExists(mp_group):
                    cmds.parent(loc, mp_group)
                    items_to_parent.append(mp_group)
        
        for loc in locator_objects:
            for frame in range(int(frame_range[0]), int(frame_range[1]) + 1):
                cmds.currentTime(frame)
                data = locator_world_data[loc][frame]
                cmds.xform(loc, worldSpace=True, translation=data['translate'])
                cmds.xform(loc, worldSpace=True, rotation=data['rotate'])
                cmds.xform(loc, worldSpace=True, scale=data['scale'])
                
                cmds.setKeyframe(loc, attribute='translate')
                cmds.setKeyframe(loc, attribute='rotate')
        
        cmds.currentTime(current_time)
        
        for j, loc in enumerate(locator_objects):
            if j < len(objects):
                obj = objects[j]
                
                cmds.addAttr(loc, longName="movement", niceName="movement", attributeType='double', defaultValue=0)
                cmds.setAttr(f"{loc}.movement", edit=True, channelBox=True)
                cmds.setAttr(f"{loc}.movement", 1)
                
                cmds.addAttr(loc, longName="rotates", niceName="rotates", attributeType='double', defaultValue=0)
                cmds.setAttr(f"{loc}.rotates", edit=True, channelBox=True)
                cmds.setAttr(f"{loc}.rotates", 1)
                
                pt_constr = point_constrain([loc], [obj])
                or_constr = orient_constrain_maintain_offset([loc], [obj])
                
                if j < len(pt_constr):
                    try:
                        conn = cmds.listConnections(pt_constr[j], type='pairBlend') or []
                        if conn:
                            cmds.connectAttr(f"{loc}.movement", f"{conn[0]}.weight", force=True)
                            cmds.setAttr(f"{conn[0]}.rotInterpolation", 1)
                    except Exception:
                        pass
                
                if j < len(or_constr):
                    try:
                        conn = cmds.listConnections(or_constr[j], type='pairBlend') or []
                        if conn:
                            cmds.connectAttr(f"{loc}.rotates", f"{conn[0]}.weight", force=True)
                            cmds.setAttr(f"{conn[0]}.rotInterpolation", 1)
                    except Exception:
                        pass
        
        for i in range(len(items_to_parent)):
            gr = cmds.group(locator_objects[i], name="maintain_anim_offset")
            cmds.xform(objectSpace=True, pivots=[0, 0, 0])
            
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']:
                cmds.setAttr(f"{gr}.{attr}", lock=True, keyable=False, channelBox=False)
            
            node = cmds.createNode("blindDataTemplate", name="vectorify_movement_curve_tool")
            
            attr = add_custom_attr("obj_on_curve", node)
            cmds.connectAttr(f"{items_to_parent[i]}.visibility", attr, force=True)
            
            attr = add_custom_attr("parent_object", node)
            cmds.connectAttr(f"{locator_objects[i]}.visibility", attr, force=True)
            
            attr = add_custom_attr("parent_group", node)
            cmds.connectAttr(f"{gr}.visibility", attr, force=True)
        
        curve_short_name = path_name.split('|')[-1].split(':')[-1]
        master_group = cmds.group(items_to_parent + [path_name], name=f"{curve_short_name}_VECTORIFY_01")
        v34w(master_group, color=(1.0, 0.4, 0.7))
        cmds.xform(pivots=[0, 0, 0])
        
        set_name = "Vectorify_Set"
        try:
            cmds.sets(objects, edit=True, addElement=set_name)
        except Exception:
            pass
        
        constrained_count = apply_force_parent_constraint_to_vectorify(master_group)
        
        backup_set = get_or_create_backup_set()
        
        if cmds.objExists("VECTORIFY_DO_NOT_TOUCH"):
            backup_locs = cmds.listRelatives("VECTORIFY_DO_NOT_TOUCH", children=True, fullPath=True, type='transform') or []
            
            if backup_locs:
                backup_locs_long = []
                for loc in backup_locs:
                    if cmds.objExists(loc) and '_backupLoc' in loc:
                        loc_long = cmds.ls(loc, long=True)[0]
                        
                        if not cmds.sets(loc_long, isMember=backup_set):
                            cmds.sets(loc_long, add=backup_set)
                        
                        backup_locs_long.append(loc_long)
                
                if backup_locs_long:
                    save_backup_locators_to_network(backup_locs_long)
        
        cmds.select(path_name, replace=True)
        b78c()
        
        cmds.waitCursor(state=False)
        
    finally:
        cmds.refresh(suspend=False)
        cmds.undoInfo(state=undo_state)
        
        if eval_mode:
            cmds.evaluationManager(mode=eval_mode[0])

            
        msg = "                       Successful!\n\nDelete the Vectorify group to undo.\nUse REVERT SETUP to remove the whole setup."
        cmds.confirmDialog(
            title='Connected to Curve',
            message=msg,
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.12, 0.12, 0.12]
        )
        


def is_curve_straight_from_field(curve_name, tolerance=0.0001):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass
    
    if not cmds.objExists(curve_name):
        return False
    
    curve_shapes = cmds.listRelatives(curve_name, shapes=True, type='nurbsCurve')
    if not curve_shapes:
        return False
    
    curve = curve_shapes[0]
    
    degree = cmds.getAttr(curve + '.degree')
    spans = cmds.getAttr(curve + '.spans')
    form = cmds.getAttr(curve + '.form')
    
    if form == 2:
        num_cvs = spans
    else:
        num_cvs = spans + degree
    
    cv_positions = []
    for i in range(num_cvs):
        pos = cmds.xform(curve + '.cv[' + str(i) + ']', query=True, worldSpace=True, translation=True)
        cv_positions.append([pos[0], pos[1], pos[2]])
    
    if len(cv_positions) < 3:
        return True
    
    v1_x = cv_positions[1][0] - cv_positions[0][0]
    v1_y = cv_positions[1][1] - cv_positions[0][1]
    v1_z = cv_positions[1][2] - cv_positions[0][2]
    v1_length = (v1_x**2 + v1_y**2 + v1_z**2)**0.5
    
    if v1_length > 0:
        v1_x /= v1_length
        v1_y /= v1_length
        v1_z /= v1_length
    
    is_straight = True
    for i in range(2, len(cv_positions)):
        v2_x = cv_positions[i][0] - cv_positions[0][0]
        v2_y = cv_positions[i][1] - cv_positions[0][1]
        v2_z = cv_positions[i][2] - cv_positions[0][2]
        v2_length = (v2_x**2 + v2_y**2 + v2_z**2)**0.5
        
        if v2_length < tolerance:
            continue
        
        v2_x /= v2_length
        v2_y /= v2_length
        v2_z /= v2_length
        
        cross_x = v1_y * v2_z - v1_z * v2_y
        cross_y = v1_z * v2_x - v1_x * v2_z
        cross_z = v1_x * v2_y - v1_y * v2_x
        cross_length = (cross_x**2 + cross_y**2 + cross_z**2)**0.5
        
        if cross_length > tolerance:
            is_straight = False
            break
    
    return is_straight


def attach_to_curve(*args):
    path_name = cmds.textField(x12s_field, query=True, text=True)
    ctrl_names = cmds.textField(y34t_field, query=True, text=True)
    
    if not path_name or not ctrl_names:
        cmds.warning("Please specify both path and controls!")
        return
    
    if not cmds.objExists(path_name):
        cmds.warning(f"Path '{path_name}' does not exist!")
        return
    
    ctrl_list = [name.strip() for name in ctrl_names.split(',')]
    existing_ctrls = [ctrl for ctrl in ctrl_list if cmds.objExists(ctrl)]
    
    if not existing_ctrls:
        cmds.warning("No valid controls found!")
        return
      
    curve_is_straight = is_straight(path_name)
    
    if curve_is_straight:
        attach_to_straight_curve()
    else:
        attach_to_not_straight_curve()    
        
            
def create_motion_path(obj, curve, frame_range):

    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    if (frame_range[1] - frame_range[0]) == 1:
        frame_range[0] = cmds.playbackOptions(query=True, min=True)
        frame_range[1] = cmds.playbackOptions(query=True, max=True) + 1
    
    grp = cmds.group(empty=True, name="vectorify_motionpath_grp")
    grp = rename_with_unique_name("vectorify_motionpath_grp", [grp])
    
    mp = cmds.pathAnimation(
        grp[0],
        curve=curve,
        fractionMode=False,
        follow=True,
        followAxis='x',
        upAxis='z',
        worldUpType='scene',
        inverseUp=False,
        inverseFront=False,
        bank=False,
        startTimeU=frame_range[0],
        endTimeU=frame_range[1] - 1
    )
    
    near_node = cmds.createNode("nearestPointOnCurve")
    decomp_node = cmds.createNode("decomposeMatrix")
    
    cmds.connectAttr(f"{obj}.worldMatrix[0]", f"{decomp_node}.inputMatrix", force=True)
    cmds.connectAttr(f"{decomp_node}.outputTranslate", f"{near_node}.inPosition", force=True)
    
    curve_shape = get_shape_nodes(curve)
    cmds.connectAttr(f"{curve_shape[0]}.worldSpace[0]", f"{near_node}.inputCurve", force=True)
    
    cmds.select(mp)
    
    for i in range(int(frame_range[0]), int(frame_range[1])):
        cmds.currentTime(i)
        param = cmds.getAttr(f"{near_node}.parameter")
        cmds.setKeyframe(mp, attribute="uValue", value=param, time=i)
        cmds.keyframe(f"{mp}_uValue", edit=True, valueChange=param, time=(i, i))
    
    for mark in get_position_markers(mp):
        cmds.setAttr(f"{mark}.lodVisibility", 0)
        cmds.setAttr(f"{mark}.visibility", 0)
        cmds.setAttr(f"{mark}.hideOnPlayback", 1)
        cmds.setAttr(f"{mark}.hiddenInOutliner", 1)
        
        mark_shape = get_shape_nodes(mark)
        cmds.setAttr(f"{mark_shape[0]}.lodVisibility", 0)
        cmds.setAttr(f"{mark_shape[0]}.visibility", 0)
        cmds.setAttr(f"{mark_shape[0]}.hideOnPlayback", 1)
        cmds.setAttr(f"{mark_shape[0]}.hiddenInOutliner", 1)
    
    cmds.keyTangent(mp, inTangentType='linear', outTangentType='linear')
    cmds.delete([near_node, decomp_node])
    
    for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']:
        cmds.setAttr(f"{grp[0]}.{attr}", lock=True, keyable=False, channelBox=False)
    
    cmds.select(grp)
    
    return mp


def get_position_markers(mp):

    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    connected = cmds.listConnections(mp, destination=True) or []
    markers = [item for item in connected if "positionMarker" in item]
    markers_all = []
    for obj in markers:
        parts = obj.split("->")
        if len(parts) > 1:
            markers_all.append(parts[1])
    return markers_all


def lock_curve_length():
    sel_curve = get_selected_objects()
    shape = get_shape_nodes(sel_curve[0])
    if len(shape) > 1:
        cmds.delete(shape[1])
    mel.eval('LockCurveLength')


def get_shape_nodes(transform):
    shapes = [transform]
    if cmds.nodeType(transform) == "transform":
        shapes = cmds.listRelatives(transform, fullPath=True, shapes=True) or []
    return shapes


def get_selected_objects():
    faces = cmds.ls(long=True, selection=True, objectsOnly=True) or []
    str1 = " ".join(faces)
    sel = cmds.ls(long=True, selection=True) or []
    str2 = " ".join(sel)
    
    if str1 != str2:
        obj_sel = cmds.listRelatives(faces, fullPath=True, parent=True) or []
    else:
        obj_sel = sel
    
    if len(obj_sel) == 0:
        obj_sel = faces
    
    return obj_sel


def rename_with_unique_name(prefix, objs):
    j = 0
    for i in range(len(objs)):
        while cmds.objExists(f"{prefix}{j}"):
            j += 1
        cmds.rename(objs[i], f"{prefix}{j}")
        objs = cmds.ls(selection=True)
    return objs


def add_custom_attr(attr_name, obj):
    cmds.addAttr(obj, longName=attr_name, niceName=attr_name, attributeType='long', defaultValue=0)
    cmds.setAttr(f"{obj}.{attr_name}", edit=True, channelBox=True)
    return f"{obj}.{attr_name}"


def parent_objects_to_locators(targets, objects):

    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    cmds.select(objects)
    unlock_scale_attrs()
    clear_scale_keys()
    hide_scale_attrs()
    
    tmp_locs = create_temp_locators(objects)
    parent_to_targets(targets, objects)
    
    cmds.select(objects)
    bake_animation()
    cmds.delete(tmp_locs)


def create_temp_locators(objects):

    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    sel = cmds.ls(selection=True, flatten=True)
    if not sel:
        cmds.warning("select something")
        return []
    
    locs = create_locators_at_selection()
    locs = rename_locators("vectorify_ctrl_", sel)
    hide_scale_attrs()
    
    for i, loc in enumerate(locs):
        if i < len(sel):
            obj = sel[i]
            obj_bbox = cmds.exactWorldBoundingBox(obj)
            obj_size = max([
                obj_bbox[3] - obj_bbox[0],
                obj_bbox[4] - obj_bbox[1],
                obj_bbox[5] - obj_bbox[2]
            ]) * 0.5
            
            current_unit = cmds.currentUnit(query=True, linear=True)
            scale_factor = obj_size
            
            unit_multipliers = {
                'mm': 10.0, 'cm': 1.0, 'm': 0.1,
                'in': 2.54, 'ft': 0.3048, 'yd': 0.0914
            }
            
            if current_unit in unit_multipliers:
                scale_factor *= unit_multipliers[current_unit]
            
            loc_shape = cmds.listRelatives(loc, shapes=True)
            if loc_shape:
                cmds.setAttr(f"{loc_shape[0]}.localScaleX", scale_factor)
                cmds.setAttr(f"{loc_shape[0]}.localScaleY", scale_factor)
                cmds.setAttr(f"{loc_shape[0]}.localScaleZ", scale_factor)
            
            cmds.setAttr(f"{loc}.displayHandle", True)
    
    set_override_color(18)
    
    constr = orient_constrain(sel, locs)
    cmds.delete(constr)
    
    try:
        constr_names = parent_constrain(sel, locs)
    except:
        constr_names = []
    
    bake_animation()
    if constr_names:
        cmds.delete(constr_names)
    
    try:
        parent_constrain(locs, sel)
    except:
        pass
    
    return locs


def create_parent_locators(objects):

    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass
    
    sel = cmds.ls(selection=True, flatten=True)
    add_initial_keyframes(sel)
    create_locators_at_selection()
    rename_locators("vectorify_ctrl_", sel)
    hide_scale_attrs()
    
    locs = cmds.ls(selection=True)
    
    for i, loc in enumerate(locs):
        if i < len(sel):
            obj = sel[i]
            obj_bbox = cmds.exactWorldBoundingBox(obj)
            obj_size = max([
                obj_bbox[3] - obj_bbox[0],
                obj_bbox[4] - obj_bbox[1],
                obj_bbox[5] - obj_bbox[2]
            ]) * 0.5
            
            current_unit = cmds.currentUnit(query=True, linear=True)
            scale_factor = obj_size
            
            unit_multipliers = {
                'mm': 10.0, 'cm': 1.0, 'm': 0.1,
                'in': 2.54, 'ft': 0.3048, 'yd': 0.0914
            }
            
            if current_unit in unit_multipliers:
                scale_factor *= unit_multipliers[current_unit]
            
            loc_shape = cmds.listRelatives(loc, shapes=True)
            if loc_shape:
                cmds.setAttr(f"{loc_shape[0]}.localScaleX", scale_factor)
                cmds.setAttr(f"{loc_shape[0]}.localScaleY", scale_factor)
                cmds.setAttr(f"{loc_shape[0]}.localScaleZ", scale_factor)
            
            cmds.setAttr(f"{loc}.displayHandle", True)
    
    set_override_color(18)
    
    parent_constrain(sel, locs)
    bake_animation()
    mel.eval('DeleteConstraints')
    
    pt_constr = point_constrain(locs, sel)
    or_constr = orient_constrain_maintain_offset(locs, sel)
    
    for j, obj in enumerate(locs):
        cmds.addAttr(obj, longName="movement", niceName="movement", attributeType='double', defaultValue=0)
        cmds.setAttr(f"{obj}.movement", edit=True, channelBox=True)
        cmds.setAttr(f"{obj}.movement", 1)
        
        cmds.addAttr(obj, longName="rotates", niceName="rotates", attributeType='double', defaultValue=0)
        cmds.setAttr(f"{obj}.rotates", edit=True, channelBox=True)
        cmds.setAttr(f"{obj}.rotates", 1)
        
        if j < len(pt_constr):
            try:
                conn = cmds.listConnections(pt_constr[j], type='pairBlend') or []
                if conn:
                    cmds.connectAttr(f"{obj}.movement", f"{conn[0]}.weight", force=True)
                    cmds.setAttr(f"{conn[0]}.rotInterpolation", 1)
            except Exception:
                pass
        
        if j < len(or_constr):
            try:
                conn = cmds.listConnections(or_constr[j], type='pairBlend') or []
                if conn:
                    cmds.connectAttr(f"{obj}.rotates", f"{conn[0]}.weight", force=True)
                    cmds.setAttr(f"{conn[0]}.rotInterpolation", 1)
            except Exception:
                pass
    
    return locs



def create_locators_at_selection():
    sel_true = cmds.ls(selection=True, flatten=True)
    sel = cmds.ls(selection=True, flatten=True, objectsOnly=True)
    locs = []
    
    if len(sel) > 0:
        for obj in sel:
            pv_pos = get_position_and_rotation(obj)
            b = cmds.spaceLocator(position=[0, 0, 0])
            locs.append(b[0])
            cmds.xform(b[0], worldSpace=True, translation=[pv_pos[0], pv_pos[1], pv_pos[2]])
            cmds.rotate(pv_pos[3], pv_pos[4], pv_pos[5], b[0], worldSpace=True)
        
        cmds.select(clear=True)
        for obj in locs:
            cmds.select(obj, add=True)
    else:
        locs = cmds.spaceLocator(position=[0, 0, 0])
    
    return locs


def get_position_and_rotation(sel):
    obj_pos = []
    
    is_mesh = cmds.objectType(sel, isType='mesh')
    is_surf = cmds.objectType(sel, isType='nurbsSurface')
    is_curve = cmds.objectType(sel, isType='nurbsCurve')
    is_lattice = cmds.objectType(sel, isType='lattice')
    
    if is_mesh or is_surf or is_curve or is_lattice:
        if is_mesh:
            parts = sel.split('.')
            obj_name = parts[0]
            
            if len(parts) > 1:
                comp_parts = parts[1].split('[')
                comp_name = comp_parts[0]
                
                if comp_name == "vtx":
                    pv_pos = cmds.pointPosition(sel, world=True)
                    obj_pos = [pv_pos[0], pv_pos[1], pv_pos[2], 0, 0, 0]
                
                elif comp_name == "e":
                    ef_result = cmds.polyInfo(sel, edgeToVertex=True)
                    tokens = ef_result[0].split()
                    coords = []
                    for i in range(2, len(tokens) - 1):
                        vtx_pos = cmds.pointPosition(f"{obj_name}.vtx[{tokens[i]}]", world=True)
                        coords.append(vtx_pos)
                    coo = calculate_average_position(coords)
                    obj_pos = [coo[0], coo[1], coo[2], 0, 0, 0]
                
                elif comp_name == "f":
                    ef_result = cmds.polyInfo(sel, faceToVertex=True)
                    tokens = ef_result[0].split()
                    coords = []
                    for i in range(2, len(tokens) - 1):
                        vtx_pos = cmds.pointPosition(f"{obj_name}.vtx[{tokens[i]}]", world=True)
                        coords.append(vtx_pos)
                    coo = calculate_average_position(coords)
                    obj_pos = [coo[0], coo[1], coo[2], 0, 0, 0]
        else:
            pv_pos = cmds.pointPosition(sel, world=True)
            obj_pos = [pv_pos[0], pv_pos[1], pv_pos[2], 0, 0, 0]
    else:
        pv_pos = cmds.xform(sel, query=True, worldSpace=True, pivots=True)
        rot = cmds.xform(sel, query=True, rotation=True, worldSpace=True)
        obj_pos = [pv_pos[0], pv_pos[1], pv_pos[2], rot[0], rot[1], rot[2]]
    
    return obj_pos


def calculate_average_position(coords):
    num = len(coords)
    avg = [0, 0, 0]
    for coord in coords:
        avg[0] += coord[0]
        avg[1] += coord[1]
        avg[2] += coord[2]
    avg[0] /= num
    avg[1] /= num
    avg[2] /= num
    return avg


def rename_locators(prefix, name_massive):
    objs = cmds.ls(selection=True)
    new_names = []
    
    for i in range(len(objs)):
        namespace = ""
        if ":" in name_massive[i]:
            namespace = name_massive[i].rsplit(":", 1)[0] + ":"
        short_name = name_massive[i].split("|")[-1].split(":")[-1]
        fin_name = find_unique_name(namespace + prefix + short_name)
        new_name = cmds.rename(objs[i], fin_name)
        new_names.append(new_name)
    
    return new_names


def find_unique_name(name):
    i = 0
    orig_name = name
    while cmds.objExists(name):
        name = orig_name + str(i)
        i += 1
    return name


def hide_scale_attrs():
    objs = cmds.ls(selection=True)
    if not objs:
        return
    for obj in objs:
        cmds.setAttr(f"{obj}.sx", keyable=False, channelBox=False)
        cmds.setAttr(f"{obj}.sy", keyable=False, channelBox=False)
        cmds.setAttr(f"{obj}.sz", keyable=False, channelBox=False)
        cmds.setAttr(f"{obj}.v", keyable=False, channelBox=False)


def set_local_scale(local_scale):
    objs = cmds.ls(selection=True)
    local_scale = convert_units(local_scale) * convert_units(1)
    if not objs:
        return
    for obj in objs:
        try:
            cmds.setAttr(f"{obj}.localScaleX", local_scale)
            cmds.setAttr(f"{obj}.localScaleY", local_scale)
            cmds.setAttr(f"{obj}.localScaleZ", local_scale)
        except:
            pass


def convert_units(val):
    un = cmds.currentUnit(query=True, linear=True)
    coeff_map = {
        "mm": 0.1, "cm": 1, "m": 100, "km": 100000,
        "in": 2.54, "ft": 30.48, "yd": 91.44, "mi": 160934.4
    }
    coeff = coeff_map.get(un, 1)
    return val / coeff


def set_override_color(color):
    objs = cmds.ls(selection=True)
    if not objs:
        return
    for obj in objs:
        try:
            cmds.setAttr(f"{obj}.overrideEnabled", 1)
            cmds.setAttr(f"{obj}.overrideColor", color, lock=False)
        except:
            pass


def orient_constrain(target_arr, obj_arr):
    constrs = []
    failed_objects = []
    
    for i in range(len(target_arr)):
        rx_lock = cmds.getAttr(f"{obj_arr[i]}.rx", lock=True)
        ry_lock = cmds.getAttr(f"{obj_arr[i]}.ry", lock=True)
        rz_lock = cmds.getAttr(f"{obj_arr[i]}.rz", lock=True)
        h = rx_lock + ry_lock + rz_lock
        
        if h < 3:
            skip = []
            if rx_lock: skip.append('x')
            if ry_lock: skip.append('y')
            if rz_lock: skip.append('z')
            try:
                tmp = cmds.orientConstraint(target_arr[i], obj_arr[i], skip=skip)
                constrs.append(tmp[0])
            except Exception:
                failed_objects.append(obj_arr[i])
    
    if failed_objects:
        create_backup_locators_batch(failed_objects)
    
    return constrs


def parent_constrain(target_arr, obj_arr):
    constrs = []
    failed_objects = []
    
    for i in range(len(target_arr)):
        rx_lock = cmds.getAttr(f"{obj_arr[i]}.rx", lock=True)
        ry_lock = cmds.getAttr(f"{obj_arr[i]}.ry", lock=True)
        rz_lock = cmds.getAttr(f"{obj_arr[i]}.rz", lock=True)
        tx_lock = cmds.getAttr(f"{obj_arr[i]}.tx", lock=True)
        ty_lock = cmds.getAttr(f"{obj_arr[i]}.ty", lock=True)
        tz_lock = cmds.getAttr(f"{obj_arr[i]}.tz", lock=True)
        h = rx_lock + ry_lock + rz_lock + tx_lock + ty_lock + tz_lock
        
        if h < 6:
            skip_t = []
            skip_r = []
            if tx_lock: skip_t.append('x')
            if ty_lock: skip_t.append('y')
            if tz_lock: skip_t.append('z')
            if rx_lock: skip_r.append('x')
            if ry_lock: skip_r.append('y')
            if rz_lock: skip_r.append('z')
            
            if target_arr[i] != "":
                try:
                    tmp = cmds.parentConstraint(target_arr[i], obj_arr[i], maintainOffset=True, skipTranslate=skip_t, skipRotate=skip_r)
                    constrs.append(tmp[0])
                except Exception:
                    failed_objects.append(obj_arr[i])
    
    if failed_objects:
        create_backup_locators_batch(failed_objects)
    
    return constrs

def create_backup_locators_batch(failed_objects):
    first_key = cmds.playbackOptions(q=True, animationStartTime=True)
    last_key = cmds.playbackOptions(q=True, animationEndTime=True)
    
    backup_locators = []
    temp_constraints = []
    
    for failed_obj in failed_objects:
        short_name = failed_obj.split('|')[-1]
        locator_name = short_name + "_backupLoc"
        
        if cmds.objExists(locator_name):
            cmds.delete(locator_name)
        
        backup_loc = cmds.spaceLocator(name=locator_name)[0]
        
        constraint = cmds.parentConstraint(failed_obj, backup_loc, mo=False)[0]
        
        backup_locators.append(backup_loc)
        temp_constraints.append(constraint)
    
    if backup_locators:
        cmds.bakeResults(backup_locators,
                       time=(first_key, last_key),
                       simulation=True,
                       sampleBy=1,
                       oversamplingRate=1,
                       disableImplicitControl=True,
                       preserveOutsideKeys=True,
                       sparseAnimCurveBake=False,
                       removeBakedAttributeFromLayer=False,
                       bakeOnOverrideLayer=False,
                       controlPoints=False,
                       shape=True)
        
        cmds.delete(temp_constraints)
        
        group_name = "VECTORIFY_DO_NOT_TOUCH"
        if not cmds.objExists(group_name):
            group_name = cmds.group(empty=True, name=group_name)
            cmds.setAttr(f"{group_name}.visibility", 0)
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']:
                try:
                    cmds.setAttr(f"{group_name}.{attr}", lock=True, keyable=False, channelBox=False)
                except:
                    pass
        
        set_name = get_or_create_backup_set()
        backup_locators_long = []
        
        for loc in backup_locators:
            if cmds.objExists(loc):
                cmds.parent(loc, group_name)
                loc_long = cmds.ls(loc, long=True)[0]
                backup_locators_long.append(loc_long)
                
                for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']:
                    try:
                        cmds.setAttr(f"{loc}.{attr}", lock=True, keyable=False, channelBox=False)
                    except:
                        pass
                
                if not cmds.sets(loc_long, isMember=set_name):
                    cmds.sets(loc_long, add=set_name)
        
        save_backup_locators_to_network(backup_locators_long)
    
    return backup_locators


def remove_curve_controls(*args):
    selection = cmds.ls(selection=True, long=True)
    
    if not selection:
        cmds.confirmDialog(
            title='Selection Required',
            message='Please select a curve or locator to remove its controls.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return
    
    curves_to_process = []
    
    for obj in selection:
        if cmds.objectType(obj, isType='nurbsCurve') or cmds.listRelatives(obj, shapes=True, type='nurbsCurve'):
            curves_to_process.append(obj)
        else:
            all_curves = cmds.ls(type='nurbsCurve')
            
            for curve_shape in all_curves:
                curve_transform = cmds.listRelatives(curve_shape, parent=True, fullPath=True)
                if not curve_transform:
                    continue
                
                curve = curve_transform[0]
                history = cmds.listHistory(curve) or []
                
                for node in history:
                    if cmds.nodeType(node) == 'cluster':
                        matrix_conn = cmds.listConnections(f"{node}.matrix", source=True, destination=False)
                        if not matrix_conn:
                            continue
                        
                        cluster_handle = matrix_conn[0]
                        
                        current = cluster_handle
                        found = False
                        while current:
                            if current == obj:
                                found = True
                                break
                            parent_result = cmds.listRelatives(current, parent=True, fullPath=True)
                            if not parent_result:
                                break
                            current = parent_result[0]
                        
                        if found:
                            if curve not in curves_to_process:
                                curves_to_process.append(curve)
                            break
    
    if not curves_to_process:
        cmds.confirmDialog(
            title='No Curves Found',
            message='No curves with controls found in selection.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return
    
    for curve in curves_to_process:
        history = cmds.listHistory(curve) or []
        
        locators_to_delete = []
        clusters_to_delete = []
        
        for node in history:
            if cmds.nodeType(node) == 'cluster':
                connections = cmds.listConnections(f"{node}.matrix", source=True, destination=False)
                if connections:
                    cluster_handle = connections[0]
                    
                    if 'repath_esn' in cluster_handle or 'cluster_esn' in cluster_handle:
                        clusters_to_delete.append(cluster_handle)
                        
                        parent = cmds.listRelatives(cluster_handle, parent=True, fullPath=True)
                        if parent and 'repath_esn_piv_anim' in parent[0]:
                            current = parent[0]
                            while True:
                                up = cmds.listRelatives(current, parent=True, fullPath=True)
                                if not up or 'repath_esn_piv_anim' not in up[0]:
                                    if current not in locators_to_delete:
                                        locators_to_delete.append(current)
                                    break
                                current = up[0]
        
        for loc_root in locators_to_delete:
            if cmds.objExists(loc_root):
                cmds.delete(loc_root)
        
        for cluster in clusters_to_delete:
            if cmds.objExists(cluster):
                cmds.delete(cluster)
        
        locked_attrs = {}
        for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
            try:
                is_locked = cmds.getAttr(f"{curve}.{attr}", lock=True)
                if is_locked:
                    locked_attrs[attr] = True
                    cmds.setAttr(f"{curve}.{attr}", lock=False)
            except:
                pass
        
        cmds.delete(curve, constructionHistory=True)
        
        for attr, was_locked in locked_attrs.items():
            try:
                cmds.setAttr(f"{curve}.{attr}", lock=True)
            except:
                pass
    
    if curves_to_process:
        cmds.select(curves_to_process, replace=True)


def bake_animation():
    sel = cmds.ls(selection=True)
    maya_version = mel.eval('getApplicationVersionAsFloat')
    
    eval_mode = []
    if maya_version >= 2016:
        eval_mode = cmds.evaluationManager(query=True, mode=True)
        if eval_mode[0] != "off":
            cmds.evaluationManager(mode="off")
    
    min_time = cmds.playbackOptions(query=True, min=True)
    max_time = cmds.playbackOptions(query=True, max=True)
    
    try:
        cmds.bakeResults(sel, simulation=True, sampleBy=1, time=(min_time, max_time))
        baked = False
    except:
        baked = True
    
    if maya_version >= 2016:
        if eval_mode[0] != "off":
            cmds.evaluationManager(mode=eval_mode[0])
    
    if baked:
        cmds.warning("select something")


def parent_to_targets(target, obj):
    cmds.select(obj)
    set_result = cmds.sets(name="vectorify_object_set")
    for i in range(len(target)):
        childs = cmds.listConnections(set_result, type='node')
        try:
            cmds.parent(childs[i], target[i])
        except:
            pass
    childs = cmds.listConnections(set_result, type='node')
    cmds.select(childs)
    cmds.delete(set_result)


def point_constrain(target_arr, obj_arr):
    constrs = []
    failed_objects = []
    
    for i in range(len(target_arr)):
        tx_lock = cmds.getAttr(f"{obj_arr[i]}.tx", lock=True)
        ty_lock = cmds.getAttr(f"{obj_arr[i]}.ty", lock=True)
        tz_lock = cmds.getAttr(f"{obj_arr[i]}.tz", lock=True)
        h = tx_lock + ty_lock + tz_lock
        
        if h < 3:
            skip = []
            if tx_lock: skip.append('x')
            if ty_lock: skip.append('y')
            if tz_lock: skip.append('z')
            try:
                tmp = cmds.pointConstraint(target_arr[i], obj_arr[i], skip=skip)
                constrs.append(tmp[0])
            except Exception:
                failed_objects.append(obj_arr[i])
    
    if failed_objects:
        create_backup_locators_batch(failed_objects)
    
    return constrs


def orient_constrain_maintain_offset(target_arr, obj_arr):
    constrs = []
    failed_objects = []
    
    for i in range(len(target_arr)):
        rx_lock = cmds.getAttr(f"{obj_arr[i]}.rx", lock=True)
        ry_lock = cmds.getAttr(f"{obj_arr[i]}.ry", lock=True)
        rz_lock = cmds.getAttr(f"{obj_arr[i]}.rz", lock=True)
        h = rx_lock + ry_lock + rz_lock
        
        if h < 3:
            skip = []
            if rx_lock: skip.append('x')
            if ry_lock: skip.append('y')
            if rz_lock: skip.append('z')
            try:
                tmp = cmds.orientConstraint(target_arr[i], obj_arr[i], maintainOffset=True, skip=skip)
                constrs.append(tmp[0])
            except Exception:
                failed_objects.append(obj_arr[i])
    
    if failed_objects:
        create_backup_locators_batch(failed_objects)
    
    return constrs

def unlock_scale_attrs():
    objs = cmds.ls(selection=True)
    if not objs:
        return
    for obj in objs:
        cmds.setAttr(f"{obj}.scale", lock=False)
        cmds.setAttr(f"{obj}.scaleX", lock=False)
        cmds.setAttr(f"{obj}.scaleY", lock=False)
        cmds.setAttr(f"{obj}.scaleZ", lock=False)


def clear_scale_keys():
    objs = cmds.ls(selection=True)
    if not objs:
        return
    for obj in objs:
        cmds.cutKey(obj, clear=True, time=(':',), float=(':',), attribute=['sx', 'sy', 'sz'])


def add_initial_keyframes(objects):
    channels = [".tx", ".ty", ".tz", ".rx", ".ry", ".rz"]
    for obj in objects:
        for ch in channels:
            result = cmds.listConnections(f"{obj}{ch}", destination=False, source=True)
            if not result or result[0] == "":
                try:
                    cmds.setKeyframe(f"{obj}{ch}", breakdown=False, hierarchy='none', controlPoints=False, shape=False)
                except:
                    pass

            

def apply_cvs(*args):
    try:
        cv_count = cmds.intField(z56u_field, query=True, value=True)
    except:
        pass
    
    selected = cmds.ls(selection=True, long=True)
    curves_to_process = []
    
    if selected:
        for obj in selected:
            if cmds.objectType(obj, isType='nurbsCurve') or cmds.listRelatives(obj, shapes=True, type='nurbsCurve'):
                curves_to_process.append(obj)
            else:
                all_curves = cmds.ls(type='nurbsCurve')
                
                for curve_shape in all_curves:
                    curve_transform = cmds.listRelatives(curve_shape, parent=True, fullPath=True)
                    if not curve_transform:
                        continue
                    
                    curve = curve_transform[0]
                    history = cmds.listHistory(curve) or []
                    
                    for node in history:
                        if cmds.nodeType(node) == 'cluster':
                            matrix_conn = cmds.listConnections(f"{node}.matrix", source=True, destination=False)
                            if not matrix_conn:
                                continue
                            
                            cluster_handle = matrix_conn[0]
                            
                            current = cluster_handle
                            found = False
                            while current:
                                if current == obj:
                                    found = True
                                    break
                                parent_result = cmds.listRelatives(current, parent=True, fullPath=True)
                                if not parent_result:
                                    break
                                current = parent_result[0]
                            
                            if found:
                                if curve not in curves_to_process:
                                    curves_to_process.append(curve)
                                break
                    
                    if curves_to_process:
                        break
    
    if not curves_to_process:
        path_name = cmds.textField(x12s_field, query=True, text=True)
        if not path_name or not cmds.objExists(path_name):
            cmds.warning("Please select a curve or specify a valid path name!")
            return
        curves_to_process = [path_name]
    
    all_created_locators = []
    
    for curve in curves_to_process:
        history = cmds.listHistory(curve) or []
        clusters_on_curve = [h for h in history if cmds.nodeType(h) == 'cluster']
        
        roots_to_delete = []
        for cluster in clusters_on_curve:
            connections = cmds.listConnections(f"{cluster}.matrix")
            if not connections:
                continue
            cluster_handle = connections[0]
            
            parent = cmds.listRelatives(cluster_handle, parent=True, fullPath=True)
            if parent and 'repath_esn_piv_anim' in parent[0]:
                current = parent[0]
                while True:
                    up = cmds.listRelatives(current, parent=True, fullPath=True)
                    if not up or 'repath_esn_piv_anim' not in up[0]:
                        if current not in roots_to_delete:
                            roots_to_delete.append(current)
                        break
                    current = up[0]
        
        cmds.select(curve, replace=True)
        r78s(cv_count)
        
        for root in roots_to_delete:
            if cmds.objExists(root):
                cmds.delete(root)
        
        cmds.select(curve, replace=True)
        b78c()
        
        current_selection = cmds.ls(selection=True, long=True) or []
        all_created_locators.extend(current_selection)
    
    show_nurbs_curves_in_viewports()
    j90k_tool.b90c()
    
    if all_created_locators:
        cmds.select(all_created_locators, replace=True)
    elif curves_to_process:
        cmds.select(curves_to_process, replace=True)
    else:
        cmds.select(clear=True)


def apply_cvs2(*args):
    cv_count = cmds.intField(a78b_field, query=True, value=True) 
    selected = cmds.ls(selection=True)
    
    if selected:
        r78s_v2(cv_count)
        cmds.select(selected)
    else:
        path_name = cmds.textField(x12s_field, query=True, text=True)
        
        if not path_name:
            cmds.warning("Please select a curve or specify a path name!")
            return
        
        if not cmds.objExists(path_name):
            cmds.warning(f"Path '{path_name}' does not exist!")
            return
        
        curve_shapes = cmds.listRelatives(path_name, shapes=True, type='nurbsCurve')
        if not curve_shapes and not cmds.objectType(path_name) == 'nurbsCurve':
            cmds.warning(f"'{path_name}' is not a NURBS curve!")
            return
        
        cmds.select(path_name)
        r78s_v2(cv_count)
        cmds.select(clear=True)


def show_nurbs_curves_in_all_viewports():
    all_panels = cmds.getPanel(type='modelPanel')
    for panel in all_panels:
        if cmds.modelPanel(panel, query=True, exists=True):
            editor = cmds.modelPanel(panel, query=True, modelEditor=True)
            cmds.modelEditor(editor, edit=True, nurbsCurves=True)
            cmds.modelEditor(panel, edit=True, controllers=True)


def turn_off_selection_highlighting():
    all_panels = cmds.getPanel(type='modelPanel')
    for panel in all_panels:
        if cmds.modelPanel(panel, query=True, exists=True):
            cmds.modelEditor(panel, edit=True, selectionHiliteDisplay=False)


def turn_on_selection_highlighting():
    all_panels = cmds.getPanel(type='modelPanel')
    for panel in all_panels:
        if cmds.modelPanel(panel, query=True, exists=True):
            cmds.modelEditor(panel, edit=True, selectionHiliteDisplay=True)


def change_selected_color():
    colors = [13, 17, 18, 31, 28, 6, 9, 14, 20, 25]
    selection = cmds.ls(selection=True, type='transform')
    
    if not selection:
        return

    valid_objects = []

    for obj in selection:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
        has_valid_shape = any(cmds.nodeType(shape) in ["nurbsCurve", "locator"] for shape in shapes)
        if has_valid_shape:
            valid_objects.append(obj)

    if not valid_objects:
        return

    show_nurbs_curves_in_all_viewports()
    turn_off_selection_highlighting()

    for obj in valid_objects:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
        
        for shape in shapes:
            try:
                use_object_color = cmds.getAttr(shape + ".useObjectColor")
                if use_object_color == 2:
                    cmds.setAttr(shape + ".useObjectColor", 0)
                    cmds.setAttr(shape + ".wireColorRGB", 0, 0, 0, type="double3")
            except:
                pass

        current_color = 0
        try:
            if cmds.getAttr(obj + ".overrideEnabled"):
                current_color = cmds.getAttr(obj + ".overrideColor")
        except:
            pass

        if current_color in colors:
            next_index = (colors.index(current_color) + 1) % len(colors)
        else:
            next_index = 0

        next_color = colors[next_index]

        try:
            cmds.setAttr(obj + ".overrideEnabled", 1)
            cmds.setAttr(obj + ".overrideColor", next_color)
        except:
            pass

    cmds.scriptJob(runOnce=True, killWithScene=True, event=["SelectionChanged", "turn_on_selection_highlighting()"])



def add_ctrls_to_curve(*args):
    selected = cmds.ls(selection=True)
    j90k_tool.b90c()
    
    if selected:
        curves_to_process = []
        for obj in selected:
            if cmds.objectType(obj, isType='nurbsCurve') or cmds.listRelatives(obj, shapes=True, type='nurbsCurve'):
                curves_to_process.append(obj)
        
        if curves_to_process:
            all_created_locators = []
            
            for curve in curves_to_process:
                cmds.select(curve)
                b78c()
                
                current_selection = cmds.ls(selection=True, long=True) or []
                all_created_locators.extend(current_selection)
            
            if all_created_locators:
                cmds.select(all_created_locators, replace=True)
            else:
                cmds.select(clear=True)
            return
        else:
            cmds.warning("No NURBS curves found in selection!")
            return
    
    path_name = cmds.textField(x12s_field, query=True, text=True)
    
    if not path_name:
        cmds.warning("Please select a curve or specify a path name!")
        return
    
    if not cmds.objExists(path_name):
        cmds.warning(f"Path '{path_name}' does not exist!")
        return
    
    curve_shapes = cmds.listRelatives(path_name, shapes=True, type='nurbsCurve')
    if not curve_shapes and not cmds.objectType(path_name) == 'nurbsCurve':
        cmds.warning(f"'{path_name}' is not a NURBS curve!")
        return
    
    cmds.select(path_name)
    b78c()
        

def select_all_ctrls(*args):
    selection = cmds.ls(selection=True, long=True) or []
    hierarchies_to_select = []

    if selection:
        roots = []
        for obj in selection:
            current = obj
            found_parents = []
            while current:
                if "repath_esn_piv_anim" in current:
                    found_parents.append(current)
                parent = cmds.listRelatives(current, parent=True, fullPath=True)
                current = parent[0] if parent else None
            
            if found_parents:
                root = found_parents[-1]
                if root not in roots:
                    roots.append(root)
        
        if roots:
            all_matching = cmds.ls("*{}*".format("repath_esn_piv_anim"), long=True) or []
            for match in all_matching:
                for root in roots:
                    if match.startswith(root + "|") or match == root:
                        if match not in hierarchies_to_select:
                            hierarchies_to_select.append(match)
                        break
    else:
        hierarchies_to_select = cmds.ls("*{}*".format("repath_esn_piv_anim"), long=True) or []

    if not hierarchies_to_select:
        cmds.warning("No matching objects found with '{}' in the name.".format("repath_esn_piv_anim"))
        return

    cmds.select(clear=True)
    for obj in hierarchies_to_select:
        cmds.select(obj, hierarchy=True, add=True)
    
    all_selected = cmds.ls(selection=True, long=True)
    transform_nodes = []
    for obj in all_selected:
        if cmds.nodeType(obj) == "transform":
            transform_nodes.append(obj)
    
    if transform_nodes:
        cmds.select(transform_nodes, replace=True)
        

def project_curves(*args):
    selection = cmds.ls(sl=True, long=True)
    
    if not selection or len(selection) != 2:
        instructions = (
            "Morphing Curves Instructions:\n\n"
            "1. Select exactly TWO NURBS curves.\n"
            "2. Select the BASE curve first.\n"
            "3. Select the TARGET curve second. (this will be morphed)\n"
            "4. Run the script."
        )
        
        cmds.confirmDialog(
            title="Morph Curves - Selection Error",
            message=instructions,
            button=["Got it"],
            defaultButton="OK",
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return
    
    for i, obj in enumerate(selection):
        shapes = h67j(obj)
        if not shapes or cmds.objectType(shapes[0]) != "nurbsCurve":
            curve_type = "base" if i == 0 else "target"
            
            error_message = (
                f"Selection Error:\n\n"
                f"The {curve_type} object '{obj}' is not a NURBS curve.\n\n"
                f"Please select two NURBS curves:\n"
                f"1. Base curve (first selection)\n"
                f"2. Target curve (second selection)"
            )
            
            cmds.confirmDialog(
                title="Project Curves - Object Type Error",
                message=error_message,
                button=["OK"],
                defaultButton="OK",
                backgroundColor=[0.15, 0.15, 0.15]
            )
            return
    
    try:
        base_curve = selection[0]
        target_curve = selection[1]
        o34p()
        mel.eval("setCurveLengthLock 0;")
        
        set_name = "Vectorify_Set"
        if not cmds.objExists(set_name):
            cmds.sets(name=set_name, empty=True)
        
        try:
            cmds.sets(base_curve, edit=True, addElement=set_name)
        except Exception as e:
            cmds.warning(f"Failed to add '{base_curve}' to {set_name}: {e}")
        
        vectorify_groups = cmds.ls("*_VECTORIFY_*", type="transform")
        if vectorify_groups:
            latest_vectorify_group = vectorify_groups[-1]
            
            try:
                current_parent = cmds.listRelatives(target_curve, parent=True)
                if not current_parent or not any("VECTORIFY" in str(parent) for parent in current_parent):
                    cmds.parent(target_curve, latest_vectorify_group)
            except Exception as e:
                cmds.warning(f"Could not parent target curve to VECTORIFY group: {e}")
        else:
            cmds.warning("No VECTORIFY group found. Please use 'Connect to Curve' first to create a VECTORIFY group.")
            
    except Exception as e:
        cmds.warning(f"Project curves failed: {str(e)}")


import json
def bake_vectorify_objects_in_layers():
    objects_to_check = []
    
    set_name = "Vectorify_Set"
    if cmds.objExists(set_name):
        set_members = cmds.sets(set_name, query=True) or []
        objects_to_check = [obj for obj in set_members if cmds.objExists(obj)]
    else:
        node = "vectorifyDataNode"
        if cmds.objExists(node) and cmds.objExists(f"{node}.connectedObjects"):
            try:
                raw_objects = cmds.getAttr(f"{node}.connectedObjects")
                if raw_objects and raw_objects.strip():
                    stored_names = json.loads(raw_objects)
                    all_dag_objects = cmds.ls(dag=True, long=True)
                    for stored_name in stored_names:
                        for dag_obj in all_dag_objects:
                            dag_short = dag_obj.split('|')[-1]
                            if dag_short == stored_name:
                                objects_to_check.append(dag_obj)
                                break
            except:
                pass
    
    if not objects_to_check:
        return
    
    animLayers = cmds.ls(type='animLayer')
    root_layer = cmds.animLayer(q=True, root=True)
    if root_layer and root_layer in animLayers:
        animLayers.remove(root_layer)
    
    if not animLayers:
        return
    
    objects_in_layers = []
    all_affected_layers = set()
    
    for animLyr in animLayers:
        attrs = cmds.animLayer(animLyr, q=True, attribute=True)
        if attrs:
            for attr in attrs:
                obj_from_attr = attr.split('.')[0]
                
                for checked_obj in objects_to_check:
                    checked_short = checked_obj.split('|')[-1]
                    attr_short = obj_from_attr.split('|')[-1]
                    
                    if checked_short == attr_short:
                        if checked_obj not in objects_in_layers:
                            objects_in_layers.append(checked_obj)
                        all_affected_layers.add(animLyr)
                        break
    
    if not objects_in_layers:
        return
    
    bake_all_objects_from_layers(objects_in_layers, list(all_affected_layers))

def bake_all_objects_from_layers(objects_to_bake, affected_layers):
    playBackSlider = mel.eval('$animBot_playBackSliderPython=$gPlayBackSlider')
    timeRange = cmds.timeControl(playBackSlider, query=True, rangeArray=True)
    StartRange = int(timeRange[0])
    EndRange = int(timeRange[1] - 1)
    
    allAnimLayers = cmds.ls(type="animLayer")
    root_layer = cmds.animLayer(q=True, root=True)
    if root_layer and root_layer in allAnimLayers:
        allAnimLayers.remove(root_layer)
    
    original_mute_states = {}
    for layer in allAnimLayers:
        original_mute_states[layer] = cmds.animLayer(layer, q=True, mute=True)
    
    for layer in allAnimLayers:
        if layer not in affected_layers:
            cmds.animLayer(layer, edit=True, mute=True)
    
    for layer in affected_layers:
        cmds.animLayer(layer, edit=True, mute=False)
    
    cmds.refresh(suspend=True)
    cmds.evaluationManager(mode="off")
    
    try:
        min_time = cmds.playbackOptions(q=True, animationStartTime=True)
        max_time = cmds.playbackOptions(q=True, animationEndTime=True)

        cmds.bakeResults(objects_to_bake, sm=True, pok=True, t=(min_time, max_time), removeBakedAttributeFromLayer=True)
       
        for layer in allAnimLayers:
            if layer not in affected_layers and cmds.objExists(layer):
                cmds.animLayer(layer, edit=True, mute=original_mute_states[layer])
        
        layers_to_delete = []
        for layer in allAnimLayers:
            if cmds.objExists(layer):
                attrs = cmds.animLayer(layer, q=True, attribute=True)
                if not attrs:
                    layers_to_delete.append(layer)
        
        if layers_to_delete:
            cmds.delete(layers_to_delete)
        
    except Exception:
        pass
    finally:
        cmds.refresh(suspend=False)
        cmds.evaluationManager(mode="parallel")



def bake_and_delete(*args):
    bake_vectorify_objects_in_layers()
    d90e()

def f12g():
    sel = cmds.ls(sl=True)
    
    for s in sel:
        cmds.select(s)
        v12w()
        
    cmds.select(sel)


## Curve to Surface



def set_outliner_color(obj, color=(0.5, 0.8, 1.0)):
    if not cmds.objExists(obj):
        return
    
    try:
        cmds.setAttr(f"{obj}.useOutlinerColor", 1)
        cmds.setAttr(f"{obj}.outlinerColor", color[0], color[1], color[2], type="double3")
    except Exception as e:
        pass

def select_all_curve_ctrls(sources):
    hierarchies_to_select = []

    if sources:
        roots = []
        for obj in sources:
            current = obj
            found_parents = []
            while current:
                if "repath_esn_piv_anim" in current:
                    found_parents.append(current)
                parent = cmds.listRelatives(current, parent=True, fullPath=True)
                current = parent[0] if parent else None
            
            if found_parents:
                root = found_parents[-1]
                if root not in roots:
                    roots.append(root)
        
        if roots:
            all_matching = cmds.ls("*{}*".format("repath_esn_piv_anim"), long=True) or []
            for match in all_matching:
                for root in roots:
                    if match.startswith(root + "|") or match == root:
                        if match not in hierarchies_to_select:
                            hierarchies_to_select.append(match)
                        break
    else:
        hierarchies_to_select = cmds.ls("*{}*".format("repath_esn_piv_anim"), long=True) or []

    if not hierarchies_to_select:
        return []

    all_selected = []
    for obj in hierarchies_to_select:
        descendants = cmds.listRelatives(obj, allDescendents=True, fullPath=True, type='transform') or []
        all_selected.append(obj)
        all_selected.extend(descendants)
    
    transform_nodes = []
    for obj in all_selected:
        if cmds.nodeType(obj) == "transform":
            transform_nodes.append(obj)
    
    return transform_nodes

def curve_to_surface():
    temp_name = "VECTORIFY_TEMP_ENV"
    
    sel = cmds.ls(orderedSelection=True, long=True)
    
    if len(sel) < 2:
        cmds.confirmDialog(
            title='Selection Error',
            message='Please select at least 2 objects. The last object will be the target.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return
    
    original_target = sel[-1]
    sources = sel[:-1]
    
    all_locators = []
    
    for src in sources:
        shapes = cmds.listRelatives(src, shapes=True, noIntermediate=True, fullPath=True) or []
        
        if shapes and cmds.objectType(shapes[0]) == 'locator':
            locators_from_hierarchy = select_all_curve_ctrls([src])
            all_locators.extend(locators_from_hierarchy)
    
    if all_locators:
        objects_to_constrain = all_locators
    else:
        objects_to_constrain = sources
    
    duplicated = cmds.duplicate(original_target, returnRootsOnly=True)[0]
    target = cmds.rename(duplicated, temp_name)
    cmds.makeIdentity(target, apply=True, translate=True, rotate=True, scale=True)
    cmds.delete(target, constructionHistory=True)
    cmds.setAttr(f"{target}.visibility", 0)
    
    constraints_created = []
    
    for obj in objects_to_constrain:
        try:
            constraint = cmds.geometryConstraint(target, obj)
            constraints_created.extend(constraint)
        except Exception as e:
            cmds.warning(f"Could not constrain {obj} to {target}: {str(e)}")
    
    if constraints_created:
        cmds.delete(constraints_created)
    
    cmds.select(clear=True)

def cleanup_temp_env():
    try:
        cmds.delete("*VECTORIFY_TEMP_ENV*")
    except:
        pass

def esn_curve_to_surface():        
    curve_to_surface()
    cmds.scriptJob(event=['SelectionChanged', cleanup_temp_env], runOnce=True, killWithScene=True)


import json
def bake_backup_locators():
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass
    
    original_selection = cmds.ls(selection=True, long=True)
    
    node_name = "Vectorify_Backup_Network"
    
    if not cmds.objExists(node_name):
        #cmds.warning("Vectorify_Backup_Network does not exist. No backup locators to bake.")
        return
    
    if not cmds.objExists(f"{node_name}.backupLocators"):
        cmds.warning("No backupLocators attribute found.")
        return
    
    raw_data = cmds.getAttr(f"{node_name}.backupLocators")
    
    if not raw_data or not raw_data.strip():
        cmds.warning("No backup locators stored in network node.")
        return
    
    backup_locators = json.loads(raw_data)
    
    if not backup_locators:
        cmds.warning("Backup locators list is empty.")
        return
    
    existing_locators = []
    for loc in backup_locators:
        if cmds.objExists(loc):
            existing_locators.append(loc)
    
    if not existing_locators:
        cmds.warning("None of the stored backup locators exist in the scene.")
        return
    
    for loc in existing_locators:
        attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']
        for attr in attrs:
            try:
                cmds.setAttr(f"{loc}.{attr}", lock=False, keyable=True)
            except:
                pass
    
    objects_to_bake = []
    for loc_long in existing_locators:
        loc_short = loc_long.split('|')[-1]
        
        if '_backupLoc' in loc_short:
            obj_name = loc_short.replace('_backupLoc', '')
            objects_to_bake.append(obj_name)
    
    if not objects_to_bake:
        cmds.warning("No objects derived from backup locators.")
        return
    
    actual_objects = []
    all_dag_objects = cmds.ls(dag=True, long=True)
    
    for obj_name in objects_to_bake:
        for dag_obj in all_dag_objects:
            if dag_obj.split('|')[-1] == obj_name:
                actual_objects.append(dag_obj)
                break
    
    if not actual_objects:
        cmds.warning("No matching objects found in the scene.")
        return
    
    first_key = None
    last_key = None
    max_range = -1
    
    for loc in existing_locators:
        keyframes = cmds.keyframe(loc, query=True, timeChange=True)
        
        if keyframes:
            loc_first = min(keyframes)
            loc_last = max(keyframes)
            frame_range = loc_last - loc_first
            
            if frame_range > max_range:
                max_range = frame_range
                first_key = loc_first
                last_key = loc_last
    
    if first_key is None or last_key is None:
        first_key = cmds.playbackOptions(q=True, min=True)
        last_key = cmds.playbackOptions(q=True, max=True)
    
    cmds.refresh(suspend=True)
    cmds.evaluationManager(mode="off")
    
    try:
        constraints_to_delete = []
        
        for i, obj in enumerate(actual_objects):
            obj_short = obj.split('|')[-1]
            
            matching_locator = None
            for loc in existing_locators:
                if loc.split('|')[-1].replace('_backupLoc', '') == obj_short:
                    matching_locator = loc
                    break
            
            if not matching_locator:
                continue
            
            cmds.cutKey(obj, clear=True, at=("tx", "ty", "tz", "rx", "ry", "rz"))
            
            temp_constraint = cmds.parentConstraint(
                matching_locator,
                obj,
                maintainOffset=False
            )
            
            if temp_constraint:
                constraints_to_delete.append(temp_constraint[0])
        
        if actual_objects:
            cmds.bakeResults(
                actual_objects,
                time=(first_key, last_key),
                simulation=True,
                sampleBy=1,
                oversamplingRate=1,
                disableImplicitControl=True,
                preserveOutsideKeys=True,
                sparseAnimCurveBake=False,
                removeBakedAttributeFromLayer=False,
                removeBakedAnimFromLayer=False,
                bakeOnOverrideLayer=False,
                minimizeRotation=True,
                controlPoints=False,
                shape=True
            )
        
        if constraints_to_delete:
            cmds.delete(constraints_to_delete)
        
        if cmds.objExists("VECTORIFY_DO_NOT_TOUCH"):
            cmds.delete("VECTORIFY_DO_NOT_TOUCH")
        
        backup_set = "Vectorify_Backup"
        if cmds.objExists(backup_set):
            cmds.delete(backup_set)
        
        if cmds.objExists(node_name):
            cmds.delete(node_name)
        
        cmds.select(actual_objects, replace=True)
        
    finally:
        cmds.refresh(suspend=False)
        cmds.evaluationManager(mode="parallel")
    
    cmds.select(clear=True)




def delete_vectorify_nodes():
    all_nodes = cmds.ls()
    
    vectorify_nodes = []
    for node in all_nodes:
        node_lower = node.lower()
        
        if node == "Vectorify_Backup_Network" or node == "Vectorify_Backup":
            continue
        
        if node == "vectorifyDataNode" or node == "vectorifySelectionSets":
            continue
        
        if node == "VECTORIFY_DO_NOT_TOUCH":
            continue
        
        if 'vectorify' in node_lower or 'repath_esn' in node_lower or 'cluster_esn' in node_lower:
            vectorify_nodes.append(node)
    
    if not vectorify_nodes:
        bake_backup_locators()
        return
    
    result = cmds.confirmDialog(
        title='Delete Vectorify Setup',
        message='This will delete all the Vectorify setup.\n\nAre you sure you want to continue?',
        button=['Yes', 'No'],
        defaultButton='No',
        cancelButton='No',
        dismissString='No',
        backgroundColor=[0.15, 0.15, 0.15]
    )
    
    if result == 'No':
        return
    
    deleted_count = 0
    for node in vectorify_nodes:
        if cmds.objExists(node):
            try:
                cmds.delete(node)
                deleted_count += 1
            except:
                pass


    curve_to_surface_node = cmds.ls("*Curve_To_Surface*")
    for obj in curve_to_surface_node:
        if cmds.objExists(obj):
            try:
                cmds.delete(obj)
            except:
                pass

    vec_env = cmds.ls("*VECTORIFY_TEMP_ENV*")
    for env in vec_env:
        if cmds.objExists(env):
            try:
                cmds.delete(env)
            except:
                pass

    vec_backup = cmds.ls("*Vectorify_Backup*")
    for env in vec_backup:
        if cmds.objExists(env):
            try:
                cmds.delete(env)
            except:
                pass 


    bake_backup_locators()

def make_curve_straight(*args):
    try:
        max = builtins.max 
        min = builtins.min
        sum = builtins.sum
        abs = builtins.abs
        len = builtins.len
        int = builtins.int
        str = builtins.str
        set = builtins.set
        range = builtins.range
        list = builtins.list
        dict = builtins.dict
    except:
        pass

    selection = cmds.ls(selection=True, long=True)
    
    if not selection:
        path_name = cmds.textField(x12s_field, query=True, text=True)
        
        if not path_name:
            cmds.warning("Please select a curve or specify a path name!")
            return
        
        if not cmds.objExists(path_name):
            cmds.warning(f"Path '{path_name}' does not exist!")
            return
        
        selection = cmds.ls(path_name, long=True)
    
    cmds.waitCursor(state=True)
    
    try:
        for selected_curve in selection:
            curves = cmds.listRelatives(selected_curve, shapes=True, fullPath=True, type="nurbsCurve")
            if not curves:
                continue
            
            history = cmds.listHistory(selected_curve) or []
            locators_to_delete = []
            
            for node in history:
                if cmds.nodeType(node) == 'cluster':
                    connections = cmds.listConnections(f"{node}.matrix", source=True, destination=False)
                    if connections:
                        cluster_handle = connections[0]
                        parent = cmds.listRelatives(cluster_handle, parent=True, fullPath=True)
                        if parent and 'repath_esn_piv_anim' in parent[0]:
                            current = parent[0]
                            while True:
                                up = cmds.listRelatives(current, parent=True, fullPath=True)
                                if not up or 'repath_esn_piv_anim' not in up[0]:
                                    if current not in locators_to_delete:
                                        locators_to_delete.append(current)
                                    break
                                current = up[0]
            
            for loc_root in locators_to_delete:
                if cmds.objExists(loc_root):
                    cmds.delete(loc_root)
            
            cmds.select(selected_curve)
            mel.eval("setCurveLengthLock 0;")
            
            locked_attrs = {}
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
                try:
                    is_locked = cmds.getAttr(f"{selected_curve}.{attr}", lock=True)
                    if is_locked:
                        locked_attrs[attr] = True
                        cmds.setAttr(f"{selected_curve}.{attr}", lock=False)
                except:
                    pass
            
            curve_shape = curves[0]
            degree = cmds.getAttr(f"{curve_shape}.degree")
            spans = cmds.getAttr(f"{curve_shape}.spans")
            num_cvs = spans + degree
            
            first_cv_pos = cmds.pointPosition(f"{curve_shape}.cv[0]", world=True)
            last_cv_pos = cmds.pointPosition(f"{curve_shape}.cv[{num_cvs-1}]", world=True)
            
            total_curve_length = 0.0
            for i in range(num_cvs - 1):
                cv_pos = cmds.pointPosition(f"{curve_shape}.cv[{i}]", world=True)
                next_cv_pos = cmds.pointPosition(f"{curve_shape}.cv[{i+1}]", world=True)
                
                dx = next_cv_pos[0] - cv_pos[0]
                dy = next_cv_pos[1] - cv_pos[1]
                dz = next_cv_pos[2] - cv_pos[2]
                
                segment_length = (dx**2 + dy**2 + dz**2)**0.5
                total_curve_length += segment_length
            
            direction_x = last_cv_pos[0] - first_cv_pos[0]
            direction_y = last_cv_pos[1] - first_cv_pos[1]
            direction_z = last_cv_pos[2] - first_cv_pos[2]
            
            straight_distance = (direction_x**2 + direction_y**2 + direction_z**2)**0.5
            
            if straight_distance > 0.0001:
                direction_x /= straight_distance
                direction_y /= straight_distance
                direction_z /= straight_distance
            else:
                continue
            
            for i in range(num_cvs):
                if num_cvs > 1:
                    t = i / float(num_cvs - 1)
                else:
                    t = 0.0
                
                new_x = first_cv_pos[0] + direction_x * total_curve_length * t
                new_y = first_cv_pos[1] + direction_y * total_curve_length * t
                new_z = first_cv_pos[2] + direction_z * total_curve_length * t
                
                cmds.move(new_x, new_y, new_z, f"{curve_shape}.cv[{i}]", absolute=True, worldSpace=True)
            
            for attr, was_locked in locked_attrs.items():
                try:
                    cmds.setAttr(f"{selected_curve}.{attr}", lock=True)
                except:
                    pass
        
        if selection:
            cmds.select(selection, replace=True)
            
    finally:
        cmds.waitCursor(state=False)


def vectorify_ui():
    global x12s_field, y34t_field, z56u_field, a78b_field
    
    window_name = "VectorifyWin"
    dock_name = "VectorifyDock"
    
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    if cmds.dockControl(dock_name, exists=True):
        cmds.deleteUI(dock_name)
    
    window = cmds.window(
        window_name,
        title="Vectorify",
        backgroundColor=[0.12, 0.12, 0.12]
    )
    
    main_layout = cmds.columnLayout(
        adjustableColumn=True,
        columnAttach=('both', 8),
        rowSpacing=4,
        backgroundColor=[0.135, 0.135, 0.135]
    )
    
    cmds.text(
        label="VECTORIFY v2.8",
        align='center',
        font='smallBoldLabelFont',
        height=20,
        backgroundColor=[0.13, 0.13, 0.13]
    )
    
    cmds.separator(height=5, style='none')
    
    cmds.button(
        label="C R E A T E   P A T H",
        command=lambda x: h6s1t(step_count=20, from_edge_only=False, zero_vertical=True),
        height=25,
        backgroundColor=[0.5, 0.8, 1],
        annotation="Create path from selected object's animation"
    )

    cmds.button(
        label="C R E A T E    E X A C T    P A T H",
        command=create_path_from_selection,
        height=25,
        backgroundColor=[0.3, 0.6, 0.8],
        annotation="Create path from selected object's animation"
    )

    
    cmds.button(
        label="Reload Data",
        command=refresh_ui_data,
        height=22,
        backgroundColor=[0.3, 0.35, 0.4],
        annotation="Load stored path and controls data from scene"
    )
    
    cmds.separator(height=3, style='none')
    
    path_row = cmds.rowLayout(
        numberOfColumns=2,
        columnAttach=[(1, 'both', 0), (2, 'left', 5)],
        columnWidth2=(160, 120),
        parent=main_layout
    )
    
    x12s_field = cmds.textField(
        placeholderText="Path ...",
        backgroundColor=[0.15, 0.15, 0.15],
        height=20,
        annotation="Current path curve"
    )
    
    cmds.button(
        label="Assign Path",
        command=assign_path_name,
        height=20,
        backgroundColor=[0.22, 0.25, 0.32],
        annotation="Assign selected curve as path"
    )
    
    cmds.setParent(main_layout)
    
    cmds.separator(height=3, style='none')
    
    controls_row = cmds.rowLayout(
        numberOfColumns=2,
        columnAttach=[(1, 'both', 0), (2, 'left', 5)],
        columnWidth2=(160, 120),
        parent=main_layout
    )
    
    y34t_field = cmds.textField(
        placeholderText="Controls ...",
        backgroundColor=[0.15, 0.15, 0.15],
        height=20,
        annotation="Controls to attach to path"
    )
    
    cmds.button(
        label="Assign Ctrls",
        command=assign_ctrls,
        height=20,
        backgroundColor=[0.22, 0.25, 0.32],
        annotation="Assign selected objects as controls"
    )
    
    cmds.setParent(main_layout)
    
    cmds.separator(height=5, style='none')
    
    cmds.button(
        label="C O N N E C T   T O   C U R V E",
        command=attach_to_curve,
        height=30,
        backgroundColor=[0.2, 0.5, 1],
        annotation="Connect controls to curve"
    )
    
    cmds.separator(height=5, style='none')
    
    cv_frame = cmds.frameLayout(
        label="Add CVs and Ctrls",
        collapsable=True,
        collapse=False,
        backgroundColor=[0.15, 0.15, 0.15],
        labelAlign='center',
        marginWidth=3,
        marginHeight=3
    )
    
    cv_layout = cmds.columnLayout(
        adjustableColumn=True,
        columnAttach=('both', 2),
        rowSpacing=2
    )

    cvs_display_row = cmds.rowLayout(
        numberOfColumns=3,
        columnAttach=[(1, 'both', 0), (2, 'left', 5), (3, 'left', 3)],
        columnWidth3=(75, 65, 82),
        backgroundColor=[0.15, 0.15, 0.15]
    )

    cmds.text(
        label="Number of CV:",
        align='left'
    )

    a78b_field = cmds.intField(
        value=10,
        minValue=2,
        maxValue=1000,
        backgroundColor=[0.15, 0.15, 0.15],
        height=18,
        annotation="Number of CVs from path curve"
    )

    cmds.button(
        label=" Add ",
        command=apply_cvs2,
        height=25,
        width=82,
        backgroundColor=[0.25, 0.25, 0.25],
        annotation="Apply displayed CV count"
    )

    cmds.setParent('..')

    cvs_row = cmds.rowLayout(
        numberOfColumns=4,
        columnAttach=[(1, 'both', 0), (2, 'left', 5), (3, 'left', 3), (4, 'left', 3)],
        columnWidth4=(75, 65, 38, 38),
        backgroundColor=[0.15, 0.15, 0.15]
    )

    cmds.text(
        label="Number of Ctrls:",
        align='left'
    )

    z56u_field = cmds.intField(
        value=10,
        minValue=2,
        maxValue=1000,
        backgroundColor=[0.15, 0.15, 0.15],
        height=18,
        annotation="Number of CVs for curve rebuild"
    )

    cmds.button(
        label="Add",
        command=apply_cvs,
        height=25,
        width=38,
        backgroundColor=[0.25, 0.25, 0.25],
        annotation="Apply CV count to curve"
    )

    cmds.button(
        label="Del",
        command=lambda x: remove_curve_controls(),
        height=25,
        width=38,
        backgroundColor=[0.25, 0.25, 0.25],
        annotation="Remove curve controls"
    )

    cmds.setParent('..')
    cmds.setParent('..')
    cmds.setParent('..')
    
    cmds.setParent(main_layout)
    
    cmds.separator(height=3, style='none')
    
    curve_tools_frame = cmds.frameLayout(
        label="Curve Tools",
        collapsable=True,
        collapse=False,
        backgroundColor=[0.15, 0.15, 0.15],
        labelAlign='center',
        marginWidth=3,
        marginHeight=3,
        parent=main_layout
    )
    
    curve_tools_layout = cmds.columnLayout(
        adjustableColumn=True,
        columnAttach=('both', 2),
        rowSpacing=2
    )
    
    cmds.button(
        label="Select All Curve Ctrls",
        command=select_all_ctrls,
        height=27,
        backgroundColor=[0.25, 0.25, 0.25],
        annotation="Select all curve controls"
    )
    
    cmds.button(
        label="Reverse Selected Locator Hierarchy",
        command=lambda x: reverse_parent_hierarchy(),
        height=35,
        backgroundColor=[0.2, 0.2, 0.2]
    )

    cmds.separator(height=10, style='in')
    
    cmds.button(
        label="Make Selected Curves Straight",
        command=make_curve_straight,
        height=27,
        backgroundColor=[0.25, 0.25, 0.25],
        annotation="Make curve straight"
    )
    
    cmds.button(
        label="Reverse Selected Curves Animation",
        command=lambda x: reverse_selected_curves(),
        height=35,
        backgroundColor=[0.2, 0.2, 0.2],
        annotation="Reverse curve direction"
    )
    
    cmds.setParent(main_layout)
    
    cmds.separator(height=3, style='none')
    
    additional_tools_frame = cmds.frameLayout(
        label="Additional Curve Tools",
        collapsable=True,
        collapse=False,
        backgroundColor=[0.15, 0.15, 0.15],
        labelAlign='center',
        marginWidth=3,
        marginHeight=3,
        parent=main_layout
    )
    
    additional_tools_layout = cmds.columnLayout(
        adjustableColumn=True,
        columnAttach=('both', 2),
        rowSpacing=2
    )

    cmds.button(
        label="Curve to Surface",
        command=lambda x: esn_curve_to_surface(),
        height=35,
        backgroundColor=[0.15, 0.15, 0.15],
        annotation="Curve to a ground surface."
    )

    cmds.button(
        label="Morph A --> B",
        command=lambda x: project_curves(),
        height=35,
        backgroundColor=[0.16, 0.16, 0.16],
        annotation="Morph curve A to curve B"
    )
    
    cmds.button(
        label="Morph A --> B (Preserve Length)",
        command=lambda x: morph_curve(),
        height=35,
        backgroundColor=[0.15, 0.15, 0.15],
        annotation="Morph with length preservation"
    )
    
    cmds.separator(height=10, style='in')
    
    cmds.button(
        label="Slide Forward A Along B",
        command=lambda x: slide_curve_forward(),
        height=35,
        backgroundColor=[0.16, 0.16, 0.16],
        annotation="Slide curve forward"
    )
    
    cmds.button(
        label="Slide Backward A Along B",
        command=lambda x: slide_curve_backward(),
        height=35,
        backgroundColor=[0.15, 0.15, 0.15],
        annotation="Slide curve backward"
    )
    
    cmds.setParent(main_layout)
    
    cmds.separator(height=5, style='none')
    
    cmds.button(
        label="B A K E   A N D   D E L E T E",
        command=bake_and_delete,
        height=35,
        backgroundColor=[0.8, 0.3, 0.35],
        annotation="Bake animation and clean up"
    )

    cmds.button(
        label="R E V E R T   S E T U P",
        command=lambda x: delete_vectorify_nodes(),
        height=29,
        backgroundColor=[0.17, 0.15, 0.15],
        annotation="Delete any Vectorify setup in the scene."
    )

    
    cmds.separator(height=5, style='in')
    cmds.separator(height=5, style='out')
    
    cmds.button(
        label="=    M A S T E R   F O L L O W   S E T U P    =",
        command=lambda x: esn_master_follow_ui(),
        height=45,
        backgroundColor=[0.12, 0.13, 0.15],
        annotation="Master follow setup"
    )

    cmds.separator(height=5, style='out')



    curve_tools_frame = cmds.frameLayout(
        label="Locator Tools",
        collapsable=True,
        collapse=True,
        backgroundColor=[0.15, 0.15, 0.15],
        labelAlign='center',
        marginWidth=3,
        marginHeight=3,
        parent=main_layout
    )

    locator_tools_layout = cmds.columnLayout(
        adjustableColumn=True,
        columnAttach=('both', 2),
        rowSpacing=2
    )

    locator_row = cmds.rowLayout(
        numberOfColumns=3,
        columnAttach=[(1, 'both', 0), (2, 'both', 0), (3, 'both', 0)],
        columnWidth3=(80, 80, 80),
        parent=locator_tools_layout
    )

    cmds.button(
        label="Bigger",
        command=lambda x: esn_loc_bigger(),
        height=28,
        backgroundColor=[0.15, 0.15, 0.15],
        annotation="Make selected locators bigger.",
        parent=locator_row
    )

    cmds.button(
        label="Smaller",
        command=lambda x: esn_loc_smaller(),
        height=28,
        backgroundColor=[0.16, 0.16, 0.16],
        annotation="Make selected locators smaller.",
        parent=locator_row
    )

    cmds.button(
        label="Color",
        command=lambda x: change_selected_color(),
        height=28,
        backgroundColor=[0.17, 0.17, 0.17],
        annotation="Cycle through locator colors.",
        parent=locator_row
    )

    cmds.setParent('..')
    cmds.setParent('..')

    
    cmds.dockControl(
        dock_name,
        label="Vectorify",
        area="left",
        content=window,
        allowedArea=["left", "right"],
        sizeable=False,
        width=260
    )
    
    u12i()

### MASTER FOLLOW

import json
master_ctrl_field = None
world_ctrls_field = None

def create_network_node():
    node = "masterFollowDataNode"
    if not cmds.objExists(node):
        current_selection = cmds.ls(selection=True)
        node = cmds.createNode("network", name=node)
        cmds.addAttr(node, longName="masterCtrlName", dataType="string")
        cmds.addAttr(node, longName="worldCtrlsList", dataType="string")
        if current_selection:
            cmds.select(current_selection, replace=True)
        else:
            cmds.select(clear=True)
    return node

def save_data_to_scene(master_ctrl, world_ctrls):
    node = create_network_node()
    master_json = json.dumps(master_ctrl) if master_ctrl else ""
    world_json = json.dumps(world_ctrls) if world_ctrls else ""
    
    cmds.setAttr(f"{node}.masterCtrlName", master_json, type="string")
    cmds.setAttr(f"{node}.worldCtrlsList", world_json, type="string")

def load_data_from_scene():
    node = create_network_node()
    master_ctrl = ""
    world_ctrls = []
    
    if cmds.objExists(f"{node}.masterCtrlName"):
        try:
            raw_master = cmds.getAttr(f"{node}.masterCtrlName")
            if raw_master and raw_master.strip():
                master_ctrl = json.loads(raw_master)
        except Exception:
            pass
    
    if cmds.objExists(f"{node}.worldCtrlsList"):
        try:
            raw_world = cmds.getAttr(f"{node}.worldCtrlsList")
            if raw_world and raw_world.strip():
                world_ctrls = json.loads(raw_world)
        except Exception:
            pass
    
    return master_ctrl, world_ctrls

def update_ui_fields():
    global master_ctrl_field, world_ctrls_field
    
    try:
        if master_ctrl_field and world_ctrls_field:
            if not (cmds.textField(master_ctrl_field, exists=True) and 
                    cmds.textField(world_ctrls_field, exists=True)):
                return
                
            master_ctrl, world_ctrls = load_data_from_scene()
            
            if master_ctrl and str(master_ctrl).strip():
                cmds.textField(master_ctrl_field, edit=True, text=str(master_ctrl))
            else:
                cmds.textField(master_ctrl_field, edit=True, text="")
            
            if world_ctrls and isinstance(world_ctrls, list):
                valid_ctrls = [str(ctrl) for ctrl in world_ctrls if ctrl and str(ctrl).strip()]
                if valid_ctrls:
                    ctrls_str = ", ".join(valid_ctrls)
                    cmds.textField(world_ctrls_field, edit=True, text=ctrls_str)
                else:
                    cmds.textField(world_ctrls_field, edit=True, text="")
            else:
                cmds.textField(world_ctrls_field, edit=True, text="")
                
    except Exception:
        pass

def reload_data(*args):
    update_ui_fields()


def bake_master_lyrs():
    objects_to_check = []
    
    set_name = "Vec_Master_Ctrl"
    if cmds.objExists(set_name):
        set_members = cmds.sets(set_name, query=True) or []
        objects_to_check = [obj for obj in set_members if cmds.objExists(obj)]
    else:
        node = "vectorifyDataNode"
        if cmds.objExists(node) and cmds.objExists(f"{node}.connectedObjects"):
            try:
                raw_objects = cmds.getAttr(f"{node}.connectedObjects")
                if raw_objects and raw_objects.strip():
                    stored_names = json.loads(raw_objects)
                    all_dag_objects = cmds.ls(dag=True, long=True)
                    for stored_name in stored_names:
                        for dag_obj in all_dag_objects:
                            dag_short = dag_obj.split('|')[-1]
                            if dag_short == stored_name:
                                objects_to_check.append(dag_obj)
                                break
            except:
                pass
    
    if not objects_to_check:
        return
    
    animLayers = cmds.ls(type='animLayer')
    root_layer = cmds.animLayer(q=True, root=True)
    if root_layer and root_layer in animLayers:
        animLayers.remove(root_layer)
    
    if not animLayers:
        return
    
    objects_in_layers = []
    all_affected_layers = set()
    
    for animLyr in animLayers:
        attrs = cmds.animLayer(animLyr, q=True, attribute=True)
        if attrs:
            for attr in attrs:
                obj_from_attr = attr.split('.')[0]
                
                for checked_obj in objects_to_check:
                    checked_short = checked_obj.split('|')[-1]
                    attr_short = obj_from_attr.split('|')[-1]
                    
                    if checked_short == attr_short:
                        if checked_obj not in objects_in_layers:
                            objects_in_layers.append(checked_obj)
                        all_affected_layers.add(animLyr)
                        break
    
    if not objects_in_layers:
        return
    
    bake_all_objects_from_layers(objects_in_layers, list(all_affected_layers))
    try:
        cmds.delete("Vec_Master_Ctrl")
    except:
        pass

def bake_all_objects_from_layers(objects_to_bake, affected_layers):
    playBackSlider = mel.eval('$animBot_playBackSliderPython=$gPlayBackSlider')
    timeRange = cmds.timeControl(playBackSlider, query=True, rangeArray=True)
    StartRange = int(timeRange[0])
    EndRange = int(timeRange[1] - 1)
    
    allAnimLayers = cmds.ls(type="animLayer")
    root_layer = cmds.animLayer(q=True, root=True)
    if root_layer and root_layer in allAnimLayers:
        allAnimLayers.remove(root_layer)
    
    original_mute_states = {}
    for layer in allAnimLayers:
        original_mute_states[layer] = cmds.animLayer(layer, q=True, mute=True)
    
    for layer in allAnimLayers:
        if layer not in affected_layers:
            cmds.animLayer(layer, edit=True, mute=True)
    
    for layer in affected_layers:
        cmds.animLayer(layer, edit=True, mute=False)
    
    cmds.refresh(suspend=True)
    cmds.evaluationManager(mode="off")
    
    try:
        min_time = cmds.playbackOptions(q=True, animationStartTime=True)
        max_time = cmds.playbackOptions(q=True, animationEndTime=True)
        
        
        cmds.bakeResults(objects_to_bake, sm=True, pok=True, t=(min_time, max_time), removeBakedAttributeFromLayer=True)

        
        for layer in allAnimLayers:
            if layer not in affected_layers and cmds.objExists(layer):
                cmds.animLayer(layer, edit=True, mute=original_mute_states[layer])
        
        layers_to_delete = []
        for layer in allAnimLayers:
            if cmds.objExists(layer):
                attrs = cmds.animLayer(layer, q=True, attribute=True)
                if not attrs:
                    layers_to_delete.append(layer)
        
        if layers_to_delete:
            cmds.delete(layers_to_delete)
        
    except Exception:
        pass
    finally:
        cmds.refresh(suspend=False)
        cmds.evaluationManager(mode="parallel")



def bake_command_handler(master_ctrl_field, world_ctrls_field, master_follow_cb, x_cb, y_cb, z_cb, rx_cb, ry_cb, rz_cb):
    result = cmds.confirmDialog(
        title='Select World Controls',
        message='Have you selected all the world controls?',
        button=['Yes', 'No'],
        defaultButton='Yes',
        cancelButton='No',
        dismissString='No',
        backgroundColor=[0.15, 0.15, 0.15]
    )
    
    if result == 'No':
        return
    
    selection = cmds.ls(selection=True, long=True)
    
    
    master_text = cmds.textField(master_ctrl_field, query=True, text=True)
    if master_text:
        all_objects = cmds.ls(dag=True, long=True)
        for obj in all_objects:
            if obj.split('|')[-1] == master_text.strip():
                master_set_name = "Vec_Master_Ctrl"
                if not cmds.objExists(master_set_name):
                    cmds.sets(name=master_set_name, empty=True)
                if not cmds.sets(obj, isMember=master_set_name):
                    cmds.sets(obj, add=master_set_name)
                break
    
    if len(selection) == 0:
        cmds.confirmDialog(
            title='No Selection',
            message='Please select all the world controls first.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return
    
    master_text = cmds.textField(master_ctrl_field, query=True, text=True)
    master_short_name = master_text.strip() if master_text else ""
    
    if master_short_name:
        master_in_selection = False
        for obj in selection:
            if obj.split('|')[-1] == master_short_name:
                master_in_selection = True
                break
        
        if master_in_selection:
            if len(selection) == 1:
                cmds.confirmDialog(
                    title='Invalid Selection',
                    message="You can't add the master control to the World Ctrls.",
                    button=['OK'],
                    defaultButton='OK',
                    backgroundColor=[0.15, 0.15, 0.15]
                )
                return
            else:
                filtered_selection = []
                for obj in selection:
                    if obj.split('|')[-1] != master_short_name:
                        filtered_selection.append(obj)
                selection = filtered_selection
    
    try:
        try:            
            min_time = cmds.playbackOptions(q=True, min=True)
            max_time = cmds.playbackOptions(q=True, max=True)
            bake_master_lyrs()
            cmds.refresh(suspend=True)
            cmds.evaluationManager(mode="off")
            cmds.bakeResults(sm=True, t=(min_time, max_time), pok=True)
            
        finally:
            cmds.refresh(suspend=False)
            cmds.evaluationManager(mode="parallel")

        bake_world_controls(world_ctrls_field, master_ctrl_field, selection)
        show_reposition_window(master_ctrl_field, world_ctrls_field, master_follow_cb, x_cb, y_cb, z_cb, rx_cb, ry_cb, rz_cb)
   
    except Exception as e:
        pass


def auto_select_world_ctrls(*args):
    global world_ctrls_field
    
    world_text = cmds.textField(world_ctrls_field, query=True, text=True)
    
    if not world_text or not world_text.strip():
        cmds.confirmDialog(
            title='No World Controls',
            message='Please add the world ctrls to the script first.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return
    
    ctrl_names = [c.strip() for c in world_text.split(',') if c.strip()]
    
    if not ctrl_names:
        cmds.confirmDialog(
            title='No World Controls',
            message='Please add the world ctrls to the script first.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return
    
    found_objects = []
    all_objects = cmds.ls(dag=True, long=True)
    
    for ctrl_name in ctrl_names:
        for obj in all_objects:
            if obj.split('|')[-1] == ctrl_name:
                found_objects.append(obj)
                break
    
    if found_objects:
        cmds.select(found_objects, replace=True)
    else:
        cmds.confirmDialog(
            title='Controls Not Found',
            message='Could not find any of the world controls in the scene.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )

def esn_master_follow_ui():
    global master_ctrl_field, world_ctrls_field
    
    window_name = "MasterFollowUI"
    
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name, window=True)
    
    window = cmds.window(
        window_name,
        title="Master Follow",
        widthHeight=(400, 340),
        sizeable=False,
        minimizeButton=False,
        maximizeButton=False,
        retain=True,
        backgroundColor=[0.12, 0.12, 0.12]
    )
    
    main_layout = cmds.columnLayout(
        adjustableColumn=True,
        columnAttach=('both', 10),
        rowSpacing=8,
        backgroundColor=[0.15, 0.15, 0.15],
        parent=window
    )
    
    cmds.separator(height=5, style='none', parent=main_layout)
    
    cmds.text(
        label="Master Follow Setup",
        align='center',
        font='obliqueLabelFont',
        height=20,
        backgroundColor=[0.15, 0.15, 0.15],
        parent=main_layout
    )
    
    cmds.separator(height=5, style='none', parent=main_layout)
    
    def assign_master_ctrl(*args):
            selection = cmds.ls(selection=True, long=True)
            
            if len(selection) == 0:
                result = cmds.confirmDialog(
                    title='No Selection',
                    message='Please select the master control first.',
                    button=['OK'],
                    defaultButton='OK',
                    backgroundColor=[0.15, 0.15, 0.15]
                )
                return
            
            if len(selection) > 1:
                cmds.confirmDialog(
                    title='Multiple Selection',
                    message='Please select only one master control.',
                    button=['OK'],
                    defaultButton='OK',
                    backgroundColor=[0.15, 0.15, 0.15]
                )
                return
            
            master_ctrl = selection[0]
            short_name = master_ctrl.split('|')[-1]
            cmds.textField(master_ctrl_field, edit=True, text=short_name)
            
            # Add master control to Vec_Master_Ctrl set
            master_set_name = "Vec_Master_Ctrl"
            if not cmds.objExists(master_set_name):
                cmds.sets(name=master_set_name, empty=True)
            if not cmds.sets(master_ctrl, isMember=master_set_name):
                cmds.sets(master_ctrl, add=master_set_name)
            
            world_text = cmds.textField(world_ctrls_field, query=True, text=True)
            world_list = [c.strip() for c in world_text.split(',')] if world_text else []
            save_data_to_scene(short_name, world_list)
    
    master_row = cmds.rowLayout(
        numberOfColumns=4,
        columnAttach=[(1, 'both', 0), (2, 'both', 0), (3, 'left', 5), (4, 'both', 0)],
        columnWidth4=(50, 110, 160, 50),
        parent=main_layout
    )
    
    cmds.text(label="", parent=master_row)
    
    cmds.button(
        label="Assign Master Ctrl",
        height=20,
        backgroundColor=[0.22, 0.25, 0.32],
        command=assign_master_ctrl,
        parent=master_row
    )
    
    master_ctrl_field = cmds.textField(
        placeholderText="Master Ctrl...",
        backgroundColor=[0.10, 0.10, 0.10],
        height=20,
        parent=master_row
    )
    
    cmds.text(label="", parent=master_row)
    
    cmds.setParent('..')
    
    cmds.separator(height=8, style='in', parent=main_layout)
    
    controls_row = cmds.rowLayout(
        numberOfColumns=12,
        columnAttach=[(1, 'both', 0)],
        columnWidth=[(1, 25), (2, 90), (3, 20), (4, 20), (5, 60), (6, 10), (7, 20), (8, 10), (9, 20), (10, 10), (11, 20), (12, 10)],
        parent=main_layout
    )
    
    cmds.text(label="", parent=controls_row)
    
    cmds.text(
        label="Master Follow",
        align='left',
        parent=controls_row
    )
    
    master_follow_cb = cmds.checkBox(
        label="",
        value=True,
        parent=controls_row
    )
    
    cmds.text(label="", parent=controls_row)
    
    cmds.text(label="Translate", align='left', parent=controls_row)
    
    cmds.text(label="X", align='right', parent=controls_row)
    x_cb = cmds.checkBox(label="", value=True, enable=True, parent=controls_row)
    
    cmds.text(label="Y", align='right', parent=controls_row)
    y_cb = cmds.checkBox(label="", value=False, enable=True, parent=controls_row)
    
    cmds.text(label="Z", align='right', parent=controls_row)
    z_cb = cmds.checkBox(label="", value=True, enable=True, parent=controls_row)
    
    cmds.text(label="", parent=controls_row)
    
    cmds.setParent('..')
    
    rotation_row = cmds.rowLayout(
        numberOfColumns=8,
        columnAttach=[(1, 'both', 0)],
        columnWidth=[(1, 162), (2, 60), (3, 10), (4, 20), (5, 10), (6, 20), (7, 10), (8, 20)],
        parent=main_layout
    )
    
    cmds.text(label="", parent=rotation_row)
    
    cmds.text(label="Rotate", align='left', parent=rotation_row)
    
    cmds.text(label="X", align='right', parent=rotation_row)
    rx_cb = cmds.checkBox(label="", value=False, enable=True, parent=rotation_row)
    
    cmds.text(label="Y", align='right', parent=rotation_row)
    ry_cb = cmds.checkBox(label="", value=False, enable=True, parent=rotation_row)
    
    cmds.text(label="Z", align='right', parent=rotation_row)
    rz_cb = cmds.checkBox(label="", value=False, enable=True, parent=rotation_row)
    
    cmds.setParent('..')
    
    def toggle_xyz_checkboxes(*args):
        is_checked = cmds.checkBox(master_follow_cb, query=True, value=True)
        cmds.checkBox(x_cb, edit=True, enable=is_checked)
        cmds.checkBox(y_cb, edit=True, enable=is_checked)
        cmds.checkBox(z_cb, edit=True, enable=is_checked)
        cmds.checkBox(rx_cb, edit=True, enable=is_checked)
        cmds.checkBox(ry_cb, edit=True, enable=is_checked)
        cmds.checkBox(rz_cb, edit=True, enable=is_checked)
    
    cmds.checkBox(master_follow_cb, edit=True, changeCommand=toggle_xyz_checkboxes)
    
    cmds.separator(height=3, style='none', parent=main_layout)
    
    cmds.button(
        label="Auto Select World Ctrls",
        height=30,
        backgroundColor=[0.3, 0.35, 0.4],
        command=auto_select_world_ctrls,
        parent=main_layout
    )
    
    world_row = cmds.rowLayout(
        numberOfColumns=2,
        columnAttach=[(1, 'both', 0), (2, 'left', 5)],
        columnWidth2=(130, 240),
        parent=main_layout
    )
    
    def add_world_ctrls(*args):
        selection = cmds.ls(selection=True, long=True)
        
        if len(selection) == 0:
            cmds.confirmDialog(
                title='No Selection',
                message='Please select all the world controls first.',
                button=['OK'],
                defaultButton='OK',
                backgroundColor=[0.15, 0.15, 0.15]
            )
            return
        
        master_text = cmds.textField(master_ctrl_field, query=True, text=True)
        master_short_name = master_text.strip() if master_text else ""
        
        if master_short_name:
            master_in_selection = False
            for obj in selection:
                if obj.split('|')[-1] == master_short_name:
                    master_in_selection = True
                    break
            
            if master_in_selection:
                if len(selection) == 1:
                    cmds.confirmDialog(
                        title='Invalid Selection',
                        message="You can't add the master control to the World Ctrls.",
                        button=['OK'],
                        defaultButton='OK',
                        backgroundColor=[0.15, 0.15, 0.15]
                    )
                    return
                else:
                    filtered_selection = []
                    for obj in selection:
                        if obj.split('|')[-1] != master_short_name:
                            filtered_selection.append(obj)
                    selection = filtered_selection
        
        original_names = [obj.split('|')[-1] for obj in selection]
        world_names = ', '.join(original_names)
        cmds.textField(world_ctrls_field, edit=True, text=world_names)
        
        save_data_to_scene(master_text, original_names)
        
        cmds.inViewMessage(amg=f'Added {len(original_names)} world control(s)', pos='midCenter', fade=True)
    
    cmds.button(
        label="Add World Ctrls",
        height=20,
        backgroundColor=[0.22, 0.25, 0.32],
        command=add_world_ctrls,
        parent=world_row
    )
    
    world_ctrls_field = cmds.textField(
        placeholderText="World Ctrls...",
        backgroundColor=[0.10, 0.10, 0.10],
        height=20,
        parent=world_row
    )
    
    cmds.setParent('..')
    
    cmds.separator(height=8, style='none', parent=main_layout)
    
    cmds.button(
        label="R U N   ( B A K E )",
        height=35,
        backgroundColor=[0.8, 0.3, 0.35],
        command=lambda *args: bake_command_handler(master_ctrl_field, world_ctrls_field, master_follow_cb, x_cb, y_cb, z_cb, rx_cb, ry_cb, rz_cb),
        parent=main_layout
    )
    
    cmds.button(
        label="Reload Data",
        height=22,
        backgroundColor=[0.3, 0.35, 0.4],
        command=reload_data,
        parent=main_layout
    )
    
    cmds.separator(height=7, style='none', parent=main_layout)
    
    cmds.showWindow(window)
    
    update_ui_fields()


def show_reposition_window(master_ctrl_field, world_ctrls_field, master_follow_cb, x_cb, y_cb, z_cb, rx_cb, ry_cb, rz_cb):
    master_text = cmds.textField(master_ctrl_field, query=True, text=True)
    
    if master_text:
        all_objects = cmds.ls(dag=True, long=True)
        for obj in all_objects:
            if obj.split('|')[-1] == master_text:
                cmds.select(obj, replace=True)
                break
    
    reposition_window_name = "RepositionMasterUI"
    
    if cmds.window(reposition_window_name, exists=True):
        cmds.deleteUI(reposition_window_name, window=True)
    
    reposition_window = cmds.window(
        reposition_window_name,
        title="Reposition Master Control",
        widthHeight=(340, 150),
        sizeable=False,
        minimizeButton=False,
        maximizeButton=False,
        backgroundColor=[0.12, 0.12, 0.12]
    )
    
    reposition_layout = cmds.columnLayout(
        adjustableColumn=True,
        columnAttach=('both', 10),
        rowSpacing=15,
        backgroundColor=[0.15, 0.15, 0.15],
        parent=reposition_window
    )
    
    cmds.separator(height=10, style='none', parent=reposition_layout)
    
    cmds.text(
        label="Please reposition the master control now.",
        align='center',
        font='boldLabelFont',
        height=30,
        backgroundColor=[0.15, 0.15, 0.15],
        parent=reposition_layout
    )
    
    cmds.separator(height=5, style='none', parent=reposition_layout)
    
    def go_command(*args):
        cmds.deleteUI(reposition_window_name, window=True)
        
        try:
            master_text = cmds.textField(master_ctrl_field, query=True, text=True)
            
            if master_text:
                all_objects = cmds.ls(dag=True, long=True)
                for obj in all_objects:
                    if obj.split('|')[-1] == master_text:
                        cmds.cutKey(obj, clear=True)
                        break
            
            master_follow_enabled = cmds.checkBox(master_follow_cb, query=True, value=True)
            
            if master_follow_enabled:
                world_text = cmds.textField(world_ctrls_field, query=True, text=True)
                
                if not master_text or not world_text:
                    cmds.confirmDialog(
                        title='Missing Data',
                        message='Please assign both World Controls and Master Control.',
                        button=['OK'],
                        defaultButton='OK',
                        backgroundColor=[0.15, 0.15, 0.15]
                    )
                    return
                
                x_enabled = cmds.checkBox(x_cb, query=True, value=True)
                y_enabled = cmds.checkBox(y_cb, query=True, value=True)
                z_enabled = cmds.checkBox(z_cb, query=True, value=True)
                
                rx_enabled = cmds.checkBox(rx_cb, query=True, value=True)
                ry_enabled = cmds.checkBox(ry_cb, query=True, value=True)
                rz_enabled = cmds.checkBox(rz_cb, query=True, value=True)
                
                skip_translate = []
                if not x_enabled:
                    skip_translate.append('x')
                if not y_enabled:
                    skip_translate.append('y')
                if not z_enabled:
                    skip_translate.append('z')
                
                skip_rotate = []
                if not rx_enabled:
                    skip_rotate.append('x')
                if not ry_enabled:
                    skip_rotate.append('y')
                if not rz_enabled:
                    skip_rotate.append('z')
                
                success, active_axes = apply_master_follow(master_ctrl_field, world_ctrls_field, skip_translate, skip_rotate)
                if success:
                    bake_and_cleanup_master_controls(master_ctrl_field, include_master=True, active_axes=active_axes)
                else:
                    return
            else:
                bake_and_cleanup_master_controls(master_ctrl_field, include_master=False)
            
        except Exception as e:
            cmds.confirmDialog(
                title='Error',
                message=f'An error occurred during final baking.\n\nError: {str(e)}',
                button=['OK'],
                defaultButton='OK',
                backgroundColor=[0.15, 0.15, 0.15]
            )
    
    cmds.button(
        label="G O !",
        height=40,
        backgroundColor=[0.8, 0.3, 0.35],
        command=go_command,
        parent=reposition_layout
    )
    
    cmds.separator(height=10, style='none', parent=reposition_layout)
    
    cmds.showWindow(reposition_window)


def cleanup_master_world_setup():
    group_name = "ESN_MASTER_WORLD"
    if cmds.objExists(group_name):
        cmds.delete(group_name)
    
    locators_set_name = "Vec_Master_Locators"
    if cmds.objExists(locators_set_name):
        locators = cmds.sets(locators_set_name, query=True)
        if locators:
            for loc in locators:
                if cmds.objExists(loc):
                    cmds.delete(loc)
        cmds.delete(locators_set_name)


def bake_world_controls(world_field, master_field, selection):
    master_text = cmds.textField(master_field, query=True, text=True)
    master_short_name = master_text.strip() if master_text else ""
    
    if master_short_name:
        filtered_selection = []
        for obj in selection:
            if obj.split('|')[-1] != master_short_name:
                filtered_selection.append(obj)
        selection = filtered_selection
        
        if len(selection) == 0:
            cmds.confirmDialog(
                title='Invalid Selection',
                message="All selected objects were filtered out. Please select world controls only.",
                button=['OK'],
                defaultButton='OK',
                backgroundColor=[0.15, 0.15, 0.15]
            )
            return
    
    playBackSlider = mel.eval('$animBot_playBackSliderPython=$gPlayBackSlider')
    timeRange = cmds.timeControl(playBackSlider, query=True, rangeArray=True)
    StartRange = int(timeRange[0])
    EndRange = int(timeRange[1] - 1)
    
    minimum = cmds.playbackOptions(query=True, minTime=True)
    maximum = cmds.playbackOptions(query=True, maxTime=True)
    
    try:
        cmds.refresh(suspend=True)
        cmds.evaluationManager(mode="off")
        cmds.bakeResults(
            selection,
            simulation=True,
            time=(StartRange, EndRange),
            sampleBy=1,
            oversamplingRate=1,
            disableImplicitControl=True,
            preserveOutsideKeys=True,
            sparseAnimCurveBake=False,
            removeBakedAttributeFromLayer=False,
            removeBakedAnimFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            controlPoints=False,
            shape=True
        )
        cmds.evaluationManager(mode="parallel")
        cmds.refresh(suspend=False)
    except Exception as e:
        cmds.refresh(suspend=False)
        cmds.evaluationManager(mode='parallel')
        cmds.confirmDialog(
            title='Baking Error',
            message='Failed to bake animation on selected controls.',
            button=['OK'],
            defaultButton='OK',
            backgroundColor=[0.15, 0.15, 0.15]
        )
        return

    
    group_name = "ESN_MASTER_WORLD"
    if cmds.objExists(group_name):
        cmds.delete(group_name)
    
    locators_set_name = "Vec_Master_Locators"
    if cmds.objExists(locators_set_name):
        locators = cmds.sets(locators_set_name, query=True)
        if locators:
            for loc in locators:
                if cmds.objExists(loc):
                    cmds.delete(loc)
        cmds.delete(locators_set_name)
    
    objects_set_name = "Vec_Master_Objects"
    if not cmds.objExists(objects_set_name):
        cmds.sets(name=objects_set_name, empty=True)
    
    for obj in selection:
        if not cmds.sets(obj, isMember=objects_set_name):
            cmds.sets(obj, add=objects_set_name)
    
    create_world_locators(selection, StartRange, EndRange, minimum, maximum)
    
    original_names = [obj.split('|')[-1] for obj in selection]
    world_names = ', '.join(original_names)
    cmds.textField(world_field, edit=True, text=world_names)
    
    save_data_to_scene(master_text, original_names)
    
    cmds.select(selection, replace=True)
    
    cmds.inViewMessage(amg='World controls baked successfully. Now reposition the master control.', pos='midCenter', fade=True)


def create_world_locators(selection, start_range, end_range, minimum, maximum):
    def add_to_vec_master_locators_set(locators):
        set_name = "Vec_Master_Locators"
        if not cmds.objExists(set_name):
            cmds.sets(name=set_name, empty=True)
        for loc in locators:
            if not cmds.sets(loc, isMember=set_name):
                cmds.sets(loc, add=set_name)
    
    def smartConstraint(ctrl=None, object=None):
        transAttr = cmds.listAttr(object, keyable=True, unlocked=True, string='translate*')
        rotAttr = cmds.listAttr(object, keyable=True, unlocked=True, string='rotate*')
        
        rotSkip = []
        transSkip = []
        
        for axis in ['x', 'y', 'z']:
            if transAttr and not 'translate' + axis.upper() in transAttr:
                transSkip.append(axis)
            if rotAttr and not 'rotate' + axis.upper() in rotAttr:
                rotSkip.append(axis)
        
        if not transSkip:
            transSkip = 'none'
        if not rotSkip:
            rotSkip = 'none'
        
        constraints = []
        try:
            if rotAttr and transAttr and rotSkip == 'none' and transSkip == 'none':
                constraints.append(cmds.parentConstraint(ctrl, object, maintainOffset=True))
            else:
                if transAttr:
                    constraints.append(cmds.pointConstraint(ctrl, object, skip=transSkip, maintainOffset=True))
                if rotAttr:
                    constraints.append(cmds.orientConstraint(ctrl, object, skip=rotSkip, maintainOffset=True))
            return constraints
        except Exception:
            create_backup_locator_for_object(object, ctrl)
            return []
    
    try:
        cmds.evaluationManager(mode='off')
        cmds.refresh(suspend=True)
        
        controlList = []
        constraintList = []
        controlToObjectMap = {}
        
        for s in selection:
            shortName = s.split('|')[-1]
            ctrl = cmds.spaceLocator(name=shortName + "_esn_MasterCtrl")[0]
            ctrlLong = cmds.ls(ctrl, long=True)[0]
            
            cmds.xform(ctrlLong, rotateOrder=("xzy"))
            cmds.setAttr(ctrlLong + ".scaleX", keyable=False, channelBox=False)
            cmds.setAttr(ctrlLong + ".scaleY", keyable=False, channelBox=False)
            cmds.setAttr(ctrlLong + ".scaleZ", keyable=False, channelBox=False)
            cmds.setAttr(ctrlLong + ".visibility", 0)
            cmds.setAttr(ctrlLong + ".visibility", keyable=False, channelBox=False)
            cmds.setAttr(ctrlLong + ".overrideEnabled", 1)
            cmds.setAttr(ctrlLong + ".overrideColor", 18)
            cmds.setAttr(ctrlLong + '.useOutlinerColor', True)
            cmds.setAttr(ctrlLong + ".outlinerColor", 1, .5, .5)
            
            controlList.append(ctrlLong)
            controlToObjectMap[ctrlLong] = s
            cmds.matchTransform(ctrlLong, s)
            
            con = cmds.parentConstraint(s, ctrlLong, maintainOffset=True)
            constraintList.append(con[0])
        
        bake_time = (start_range, end_range) if (end_range - start_range) > 0 else (minimum, maximum)
        cmds.bakeResults(
            controlList,
            simulation=True,
            preserveOutsideKeys=True,
            attribute=("translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ"),
            time=bake_time,
            sampleBy=1,
            oversamplingRate=1,
            disableImplicitControl=True,
            sparseAnimCurveBake=False,
            removeBakedAttributeFromLayer=False,
            removeBakedAnimFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            controlPoints=False,
            shape=True
        )
        
        add_to_vec_master_locators_set(controlList)
        
        cmds.delete(constraintList)
        constraintList = []
        
        for ctrl in controlList:
            targetObject = controlToObjectMap[ctrl]
            cons = smartConstraint(ctrl, targetObject)
            if cons:
                constraintList.extend(cons)
        
        if controlList:
            group_name = "ESN_MASTER_WORLD"
            if cmds.objExists(group_name):
                cmds.delete(group_name)
            master_group = cmds.group(controlList, name=group_name)
            cmds.setAttr(master_group + '.useOutlinerColor', True)
            cmds.setAttr(master_group + '.outlinerColor', 1, 1, 0)
            cmds.setAttr(master_group + '.visibility', 0)
        
        cmds.select(clear=True)
        cmds.evaluationManager(mode='parallel')
        
    except Exception as e:
        cleanup_master_world_setup()
        cmds.refresh(suspend=False)
        cmds.evaluationManager(mode='parallel')
        
        group_name = "ESN_MASTER_WORLD"
        if cmds.objExists(group_name):
            cmds.confirmDialog(
                title='Error',
                message='An error occurred while creating world controls.\n\nPlease try again.',
                button=['OK'],
                defaultButton='OK'
            )
        return
    finally:
        cmds.refresh(suspend=False)


def apply_master_follow(master_field, world_field, skip_translate, skip_rotate):
    master_text = cmds.textField(master_field, query=True, text=True)
    
    if not master_text:
        cmds.confirmDialog(
            title='Missing Master Control',
            message='No master control assigned.',
            button=['OK'],
            defaultButton='OK'
        )
        return (False, [])
    
    locators_set_name = "Vec_Master_Locators"
    if not cmds.objExists(locators_set_name):
        cmds.confirmDialog(
            title='Missing World Controls',
            message='World controls not found. Please run the bake first.',
            button=['OK'],
            defaultButton='OK'
        )
        return (False, [])
    
    world_locators = cmds.sets(locators_set_name, query=True)
    
    if not world_locators:
        cmds.confirmDialog(
            title='Missing World Controls',
            message='No world controls found in the scene.',
            button=['OK'],
            defaultButton='OK'
        )
        return (False, [])
    
    master_ctrl = None
    all_objects = cmds.ls(dag=True, long=True)
    for obj in all_objects:
        if obj.split('|')[-1] == master_text:
            master_ctrl = obj
            break
    
    if not master_ctrl:
        cmds.confirmDialog(
            title='Master Control Not Found',
            message=f"Master control '{master_text}' not found in scene.",
            button=['OK'],
            defaultButton='OK'
        )
        return (False, [])
    
    active_axes = []
    if 'x' not in skip_translate:
        active_axes.append('translateX')
    if 'y' not in skip_translate:
        active_axes.append('translateY')
    if 'z' not in skip_translate:
        active_axes.append('translateZ')
    
    if 'x' not in skip_rotate:
        active_axes.append('rotateX')
    if 'y' not in skip_rotate:
        active_axes.append('rotateY')
    if 'z' not in skip_rotate:
        active_axes.append('rotateZ')
    
    try:
        has_translate = any(axis in ['x', 'y', 'z'] for axis in ['x', 'y', 'z'] if axis not in skip_translate)
        if has_translate:
            if skip_translate:
                cmds.pointConstraint(
                    world_locators,
                    master_ctrl,
                    maintainOffset=True,
                    skip=skip_translate
                )
            else:
                cmds.pointConstraint(
                    world_locators,
                    master_ctrl,
                    maintainOffset=True
                )
        
        has_rotate = any(axis in ['x', 'y', 'z'] for axis in ['x', 'y', 'z'] if axis not in skip_rotate)
        if has_rotate:
            if skip_rotate:
                cmds.orientConstraint(
                    world_locators,
                    master_ctrl,
                    maintainOffset=True,
                    skip=skip_rotate
                )
            else:
                cmds.orientConstraint(
                    world_locators,
                    master_ctrl,
                    maintainOffset=True
                )
        
        return (True, active_axes)
    except Exception as e:
        cmds.confirmDialog(
            title='Constraint Failed',
            message=f'Failed to apply constraint to master control.\n\nError: {str(e)}',
            button=['OK'],
            defaultButton='OK'
        )
        return (False, [])



def esn_loc_bigger():
    selected = cmds.ls(selection=True, type='transform')
    
    locators = []
    for obj in selected:
        shapes = cmds.listRelatives(obj, shapes=True, type='locator')
        if shapes:
            locators.append(obj)
    
    if not locators:
        return
    
    for loc in locators:
        current_scale = cmds.getAttr(loc + '.localScaleX')
        new_scale = current_scale * 1.1
        cmds.setAttr(loc + '.localScaleX', new_scale)
        cmds.setAttr(loc + '.localScaleY', new_scale)
        cmds.setAttr(loc + '.localScaleZ', new_scale)
        

def esn_loc_smaller():
    selected = cmds.ls(selection=True, type='transform')
    
    locators = []
    for obj in selected:
        shapes = cmds.listRelatives(obj, shapes=True, type='locator')
        if shapes:
            locators.append(obj)
    
    if not locators:
        return
    
    for loc in locators:
        current_scale = cmds.getAttr(loc + '.localScaleX')
        new_scale = current_scale / 1.1
        cmds.setAttr(loc + '.localScaleX', new_scale)
        cmds.setAttr(loc + '.localScaleY', new_scale)
        cmds.setAttr(loc + '.localScaleZ', new_scale)

   



def bake_and_cleanup_master_controls(master_field, include_master=False, active_axes=None):
    objects_set_name = "Vec_Master_Objects"
    if not cmds.objExists(objects_set_name):
        return
    
    objects_to_bake = cmds.sets(objects_set_name, query=True)
    
    if not objects_to_bake:
        return
    
    master_text = cmds.textField(master_field, query=True, text=True)
    master_ctrl = None
    
    if master_text and include_master:
        all_objects = cmds.ls(dag=True, long=True)
        for obj in all_objects:
            if obj.split('|')[-1] == master_text:
                master_ctrl = obj
                break
    
    playBackSlider = mel.eval('$animBot_playBackSliderPython=$gPlayBackSlider')
    timeRange = cmds.timeControl(playBackSlider, query=True, rangeArray=True)
    StartRange = int(timeRange[0])
    EndRange = int(timeRange[1] - 1)
    
    minimum = cmds.playbackOptions(query=True, minTime=True)
    maximum = cmds.playbackOptions(query=True, maxTime=True)
    
    if EndRange - StartRange == 0:
        bake_start = minimum
        bake_end = maximum
    else:
        bake_start = StartRange
        bake_end = EndRange
    
    cmds.refresh(suspend=True)
    cmds.evaluationManager(mode="off")
    
    try:
        cmds.bakeResults(
            objects_to_bake,
            simulation=True,
            time=(bake_start, bake_end),
            sampleBy=1,
            oversamplingRate=1,
            disableImplicitControl=True,
            preserveOutsideKeys=True,
            sparseAnimCurveBake=False,
            removeBakedAttributeFromLayer=False,
            removeBakedAnimFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            controlPoints=False,
            shape=True
        )
        
        if master_ctrl and active_axes:
            cmds.bakeResults(
                master_ctrl,
                simulation=True,
                time=(bake_start, bake_end),
                sampleBy=1,
                oversamplingRate=1,
                disableImplicitControl=True,
                preserveOutsideKeys=True,
                sparseAnimCurveBake=False,
                removeBakedAttributeFromLayer=False,
                removeBakedAnimFromLayer=False,
                bakeOnOverrideLayer=False,
                minimizeRotation=True,
                controlPoints=False,
                shape=True,
                attribute=active_axes
            )
            
            all_transform_attrs = ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']
            for attr in all_transform_attrs:
                if attr not in active_axes:
                    try:
                        cmds.cutKey(master_ctrl, attribute=attr, clear=True)
                    except Exception:
                        pass
        
        group_name = "ESN_MASTER_WORLD"
        if cmds.objExists(group_name):
            cmds.delete(group_name)
        
        locators_set_name = "Vec_Master_Locators"
        if cmds.objExists(locators_set_name):
            cmds.delete(locators_set_name)
        
        if cmds.objExists(objects_set_name):
            cmds.delete(objects_set_name)
        
        cmds.inViewMessage(amg='Bake complete!', pos='midCenter', fade=True)
        
    finally:
        cmds.refresh(suspend=False)
        cmds.evaluationManager(mode="parallel")
    
    cmds.select(clear=True)