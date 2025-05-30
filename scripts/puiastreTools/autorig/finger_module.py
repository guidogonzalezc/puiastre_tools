"""
Finger module for dragon rigging system
"""
import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import basic_structure
from puiastreTools.utils import data_export
import maya.mel as mel
import math
import os
import re
from importlib import reload
reload(guides_manager)
reload(basic_structure)
reload(curve_tool)    
reload(data_export)    

class FingerModule():
    """
    Class to create a finger module in a Maya rigging setup.
    This module handles the creation of finger joints, controllers, and constraints.
    """
    def __init__(self):
        """
        Initializes the FingerModule class, setting up paths and data exporters.
        Args:
            self: Instance of the FingerModule class.
        """
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "dragon_guides_template_01.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "template_curves_001.json") 

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")

    def make(self, side):
        """
        Creates the finger module for the specified side (left or right).

        Args:
            side (str): The side for which to create the finger module. Should be either "L" or "R".
        """

        self.side = side    

        self.arm_skinning_joints = self.data_exporter.get_data(f"{self.side}_armModule", "skinning_joints")


        self.module_trn = cmds.createNode("transform", name=f"{self.side}_fingerModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_fingerControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_fingerSkinning_GRP", ss=True, p=self.skel_grp)


        self.settings_curve_ctl, self.settings_curve_grp = curve_tool.controller_creator(f"{self.side}_fingerAttr", suffixes = ["GRP"])
        position, rotation = guides_manager.guide_import(joint_name=f"{self.side}_fingerAttr", filePath=self.guides_path)
        cmds.xform(self.settings_curve_grp[0], ws=True, translation=position)
        cmds.xform(self.settings_curve_grp[0], ws=True, rotation=rotation)
        cmds.parent(self.settings_curve_grp[0], self.controllers_trn)
        cmds.parentConstraint(self.arm_skinning_joints[-1], self.settings_curve_grp[0], mo=True)
        self.lock_attr(self.settings_curve_ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])

        cmds.addAttr(self.settings_curve_ctl, shortName="handSep", niceName="Hand_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.settings_curve_ctl+".handSep", channelBox=True, lock=True)
        cmds.addAttr(self.settings_curve_ctl, shortName="curl", niceName="Curl", maxValue=10, minValue=-10,defaultValue=0, keyable=True)
        cmds.addAttr(self.settings_curve_ctl, shortName="spread", niceName="Spread", maxValue=10, minValue=-10,defaultValue=0, keyable=True)

        cmds.addAttr(self.settings_curve_ctl, shortName="globalWaveSep", niceName="GlobalWave_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.settings_curve_ctl+".globalWaveSep", channelBox=True, lock=True)
        cmds.addAttr(self.settings_curve_ctl, shortName="waveEnvelop", niceName="Wave Envelop", maxValue=1, minValue=0, defaultValue=0, keyable=True)
        cmds.addAttr(self.settings_curve_ctl, shortName="globalAmplitude", niceName="Global Amplitude", defaultValue=0, keyable=True)
        cmds.addAttr(self.settings_curve_ctl, shortName="globalWavelength", niceName="Global Wavelength", defaultValue=1, keyable=True)
        cmds.addAttr(self.settings_curve_ctl, shortName="globalOffset", niceName="Global Offset", defaultValue=0, keyable=True)
        cmds.addAttr(self.settings_curve_ctl, shortName="globalDropoff", niceName="Global Dropoff", defaultValue=0, minValue = 0, maxValue = 1, keyable=True)

        self.data_exporter.append_data(f"{self.side}_finger", {"attr_ctl": self.settings_curve_ctl})

        self.controllers_fk = []

        for name in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
            self.individual_module_trn = cmds.createNode("transform", name=f"{self.side}_{name.lower()}Module_GRP", ss=True, p=self.module_trn)
            self.bendy_module = cmds.createNode("transform", name=f"{self.side}_{name.lower()}BendyModule_GRP", ss=True, p=self.individual_module_trn)

            self.create_chain(name=name)  
            self.set_controllers()  
            self.call_bendys()

            data_exporter = data_export.DataExport()
            data_exporter.append_data(
                f"{self.side}_finger{name}",    
                {
                    "ikFinger": self.pv_ctl,
                    "ikPv": self.ik_ctl,
                    "settingsAttr": self.settings_curve_ctl,
                }
            )

    def lock_attr(self, ctl, attrs = ["scaleX", "scaleY", "scaleZ", "visibility"], ro=True):
        """
        Lock specified attributes of a controller, added rotate order attribute if ro is True.
        
        Args:
            ctl (str): The name of the controller to lock attributes on.
            attrs (list): List of attributes to lock. Default is ["scaleX", "scaleY", "scaleZ", "visibility"].
            ro (bool): If True, adds a rotate order attribute. Default is True.
        """

        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", keyable=False, channelBox=False, lock=True)
        
        if ro:
            cmds.addAttr(ctl, longName="rotate_order", nn="Rotate Order", attributeType="enum", enumName="xyz:yzx:zxy:xzy:yxz:zyx", keyable=True)
            cmds.connectAttr(f"{ctl}.rotate_order", f"{ctl}.rotateOrder")

    def create_chain(self, name):
        """
        Create a finger joint chain and import the guide for the specified finger name.

        Args:
            name (str): The name of the finger to create the joint chain for (e.g., "Thumb", "Index", etc.).
        """
        
        self.blend_chain = guides_manager.guide_import(
            joint_name=f"{self.side}_finger{name}01_JNT",
            all_descendents=True,
            filePath=self.guides_path
        )
        cmds.parent(self.blend_chain[0], self.individual_module_trn)


    def attr_curl_setup(self, sdk_grp, jointName, i):
        """
        Set up driven keys for finger curl and spread attributes.

        Args:
            sdk_grp (str): The name of the SDK group to apply driven keys to.
            jointName (str): The name of the joint to determine the finger type.
            i (int): The index of the joint in the blend chain.
        """
        values_attr_curl = {
            "fingerThumb": 40,
            "fingerIndex": 40,
            "fingerMiddle": 40,
            "fingerRing": 40,
            "fingerPinky": 40

        }

        
        values_attr_spread = {
            "fingerThumb": [-60, None, None, None],
            "fingerIndex": [-30, None,None, None],
            "fingerMiddle": [-5,  None,None, None],
            "fingerRing": [10, None,None, None],
            "fingerPinky": [15,None,None, None]
        }


        # ---- SET DRIVEN KEY ---- #

        if values_attr_spread.get(re.sub(r'\d', '', jointName))[i]:
            cmds.setDrivenKeyframe(f"{sdk_grp}.rotateY", currentDriver=f"{self.settings_curve_ctl}.spread", driverValue=10, value=-(values_attr_spread.get(re.sub(r'\d', '', jointName))[i])/2)
            cmds.setDrivenKeyframe(f"{sdk_grp}.rotateY", currentDriver=f"{self.settings_curve_ctl}.spread", driverValue=0, value=0)
            cmds.setDrivenKeyframe(f"{sdk_grp}.rotateY", currentDriver=f"{self.settings_curve_ctl}.spread", driverValue=-10, value=values_attr_spread.get(re.sub(r'\d', '', jointName))[i])
        
        cmds.setDrivenKeyframe(f"{sdk_grp}.rotateZ", currentDriver=f"{self.settings_curve_ctl}.curl", driverValue=10, value=-values_attr_curl.get(re.sub(r'\d', '', jointName)))
        cmds.setDrivenKeyframe(f"{sdk_grp}.rotateZ", currentDriver=f"{self.settings_curve_ctl}.curl", driverValue=0, value=0)
        cmds.setDrivenKeyframe(f"{sdk_grp}.rotateZ", currentDriver=f"{self.settings_curve_ctl}.curl", driverValue=-10, value=10)
        
    def set_controllers(self):
        """
        Set up the controllers for the finger module, including IK handles, pole vectors, and FK controllers.

        Args:
            self: Instance of the FingerModule class.
        """

        # -- FK CONTROLLER -- #



        self.joint_name = self.blend_chain[0].split("_")[1]

        if not cmds.pluginInfo("ikSpringSolver", query=True, loaded=True):
            cmds.loadPlugin("ikSpringSolver")
        
        mel.eval("ikSpringSolver")

        self.springIkHandle = cmds.ikHandle(
            name=f"{self.side}_{self.joint_name}SpringIk_HDL",
            startJoint=self.blend_chain[0],
            endEffector=self.blend_chain[-1],
            solver="ikSpringSolver",
        )[0]

        cmds.parent(self.springIkHandle, self.individual_module_trn)

        self.pv_ctl, pv_grp = curve_tool.controller_creator(f"{self.side}_{self.joint_name}PoleVector", suffixes=["GRP", "SDK"])
        cmds.parent(pv_grp[0], self.controllers_trn) 
        self.lock_attr(self.pv_ctl)
        cmds.matchTransform(pv_grp[0], self.blend_chain[1])
        if self.side == "L":
            cmds.move(0, 250, 0, pv_grp[0], relative=True, objectSpace=True, worldSpaceDistance=True)
        else:
            cmds.move(0, -250, 0, pv_grp[0], relative=True, objectSpace=True, worldSpaceDistance=True)
        cmds.xform(pv_grp[0], ws=True, rotation=(0, 0, 0))
        cmds.poleVectorConstraint(self.pv_ctl, self.springIkHandle)

        self.ik_ctl, ik_grp = curve_tool.controller_creator(f"{self.side}_{self.joint_name}Ik", suffixes=["GRP", "SDK"])
        cmds.parent(ik_grp[0], self.controllers_trn)
        self.lock_attr(self.ik_ctl)
        cmds.matchTransform(ik_grp[0], self.blend_chain[-1])
        cmds.parentConstraint(self.ik_ctl, self.springIkHandle, maintainOffset=True)

        ik_root_ctl, ik_root_grp = curve_tool.controller_creator(f"{self.side}_{self.joint_name}IkRoot", suffixes=["GRP", "SDK"])
        cmds.parent(ik_root_grp[0], self.settings_curve_ctl)
        self.lock_attr(ik_root_ctl)
        cmds.matchTransform(ik_root_grp[0], self.blend_chain[0])
        cmds.parentConstraint(ik_root_ctl, self.blend_chain[0], maintainOffset=True)

        sub_spine_ctl_trn = cmds.createNode("transform", n=f"{self.side}_{self.joint_name}Controllers_GRP", parent=self.masterWalk_ctl, ss=True)
        cmds.setAttr(f"{sub_spine_ctl_trn}.inheritsTransform", 0)
        
        self.fk_ctl_list = []
        self.fk_grp_list = []

        

        for i, joint in enumerate(self.blend_chain):
            
            ctl, controller_grp = curve_tool.controller_creator(joint.replace('_JNT', ''), suffixes = ["GRP", "SDK"])
            self.lock_attr(ctl)
                
            self.attr_curl_setup(controller_grp[1], self.joint_name, i)

            cmds.parent(controller_grp[0], sub_spine_ctl_trn)
            
                
            if i == 0:
                cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{controller_grp[0]}.offsetParentMatrix")

                cmds.addAttr(ctl, shortName="waveSep", niceName="Wave_____", enumName="_____",attributeType="enum", keyable=True)
                cmds.setAttr(ctl+".waveSep", channelBox=True, lock=True)
                cmds.addAttr(ctl, shortName="amplitude", niceName="Amplitude", defaultValue=0, keyable=True)
                cmds.addAttr(ctl, shortName="wavelength", niceName="Wavelength", defaultValue=0, keyable=True)
                cmds.addAttr(ctl, shortName="offset", niceName="Offset", defaultValue=0, keyable=True)
                cmds.addAttr(ctl, shortName="dropoff", niceName="Dropoff", defaultValue=0, keyable=True)
            else:
                mmt = cmds.createNode("multMatrix", n=f"{self.side}_{self.joint_name}Fk0{i+1}_MMT")
                cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{mmt}.matrixIn[0]")
                cmds.connectAttr(f"{self.blend_chain[i-1]}.worldInverseMatrix[0]", f"{mmt}.matrixIn[1]")
                cmds.connectAttr(f"{self.fk_ctl_list[i-1]}.worldMatrix[0]", f"{mmt}.matrixIn[2]")
                cmds.connectAttr(f"{mmt}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix")
            self.fk_ctl_list.append(ctl)
            self.fk_grp_list.append(controller_grp)  

        self.attached_fk_joints = []
        for i, joint in enumerate(self.blend_chain):
            cmds.select(clear=True)
            new_joint = cmds.joint(joint, name=f"{self.side}_{self.joint_name}Fk0{i+1}_JNT")
            cmds.setAttr(f"{new_joint}.inheritsTransform", 0)

            cmds.parent(new_joint, self.individual_module_trn)

            cmds.connectAttr(f"{self.fk_ctl_list[i]}.worldMatrix[0]", f"{new_joint}.offsetParentMatrix")
            self.attached_fk_joints.append(new_joint)


    def call_bendys(self):
        """
        Set up bendy joints for the finger module, creating lower twists and wave handles.

        Args:
            self: Instance of the FingerModule class.
        """

        normals = (0, 1, 0)
        bendy = Bendys(self.side, self.attached_fk_joints[0], self.attached_fk_joints[1], self.bendy_module, self.skinning_trn, normals, self.controllers_trn, self.joint_name + "Upper")
        end_bezier01, bendy_skin_cluster01, bendy_joint01, off_curve01, bendy_offset_skin_cluster01 = bendy.lower_twists_setup()
        bendy = Bendys(self.side, self.attached_fk_joints[1], self.attached_fk_joints[2], self.bendy_module, self.skinning_trn, normals, self.controllers_trn, self.joint_name + "Middle")
        end_bezier02, bendy_skin_cluster02, bendy_joint02, off_curve02, bendy_offset_skin_cluster02 = bendy.lower_twists_setup()
        bendy = Bendys(self.side, self.attached_fk_joints[2], self.attached_fk_joints[3], self.bendy_module, self.skinning_trn, normals, self.controllers_trn, self.joint_name + "Lower")
        end_bezier03, bendy_skin_cluster03, bendy_joint03, off_curve03, bendy_offset_skin_cluster03 = bendy.lower_twists_setup()

        self.wave_handle(beziers=[end_bezier01, end_bezier02, end_bezier03], 
                         skc = [bendy_skin_cluster01, bendy_skin_cluster02, bendy_skin_cluster03], 
                         bezier_off = [off_curve01, off_curve02, off_curve03],
                         offset_skc = [bendy_offset_skin_cluster01, bendy_offset_skin_cluster02, bendy_offset_skin_cluster03])
        
        bendy_joint = bendy_joint01 + bendy_joint02 + bendy_joint03
        name = re.sub(r'\d', '', self.joint_name)

        self.data_exporter.append_data(f"{self.side}_{name}", {"bendy_joints": bendy_joint})

    def wave_handle(self, beziers = [], skc = [], bezier_off=[], offset_skc= []):
        """
        Create a wave handle for the finger module using the provided bezier curves and skin clusters.

        Args:
            beziers (list): List of bezier curves to use for the wave handle.
            skc (list): List of skin clusters corresponding to the bezier curves.
            bezier_off (list): List of offset bezier curves.
            offset_skc (list): List of offset skin clusters corresponding to the offset bezier curves.
        """
        
        dupe_beziers = []
        dupe_beziers_offset = []
        bezier_shapes = []
        for i, bezier in enumerate(beziers):
            dupe = cmds.duplicate(bezier, name=bezier.replace("_CRV", "Dupe_CRV"))
            dupe_off = cmds.duplicate(bezier_off[i], name=bezier_off[i].replace("_CRV", "Dupe_CRV"))
            bezier_shapes.append(cmds.listRelatives(bezier, shapes=True, fullPath=True)[0])
            cmds.delete(dupe[0], ch=True)
            cmds.delete(dupe_off[0], ch=True)
            dupe_beziers.append(dupe[0])
            dupe_beziers_offset.append(dupe_off[0])
        
        dupe_parent = cmds.listRelatives(dupe_beziers[0], parent=True, fullPath=True)
        wave_name = dupe_beziers[0].split("_")[1].split("01")[0]
        wave = cmds.nonLinear(dupe_beziers, dupe_beziers_offset, type="wave", name=f"{self.side}_{wave_name}Wave_HDL")
        cmds.parent(wave[1], dupe_parent)
        cmds.matchTransform(wave[1], self.blend_chain[1])


        positions = [cmds.xform(jnt, q=True, ws=True, t=True) for jnt in self.blend_chain]

        mid_pos = [sum(coords) / len(coords) for coords in zip(*positions)]

        cmds.xform(wave[1], ws=True, t=mid_pos)


        relative_x_positions = [cmds.getAttr(jnt + ".tx") for jnt in self.blend_chain[1:]]
        if len(relative_x_positions) == 3:
            a, b, c = relative_x_positions
            radius = abs((a + b + c) / 2)
        else:
            radius = 0
        
        cmds.setAttr(f"{wave[1]}.scaleX", radius)
        cmds.setAttr(f"{wave[1]}.scaleY", radius)
        cmds.setAttr(f"{wave[1]}.scaleZ", radius)

        blendshape01 = cmds.blendShape(dupe_beziers[0], beziers[0], name=f"{self.side}_{wave_name}01_BS")[0]
        blendshape02 = cmds.blendShape(dupe_beziers[1], beziers[1], name=f"{self.side}_{wave_name}02_BS")[0]
        blendshape03 = cmds.blendShape(dupe_beziers[2], beziers[2], name=f"{self.side}_{wave_name}03_BS")[0]

        blendshape01_off = cmds.blendShape(dupe_beziers_offset[0], bezier_off[0], name=f"{self.side}_{wave_name}Offset01_BS")[0]
        blendshape02_off = cmds.blendShape(dupe_beziers_offset[1], bezier_off[1], name=f"{self.side}_{wave_name}Offset02_BS")[0]
        blendshape03_off = cmds.blendShape(dupe_beziers_offset[2], bezier_off[2], name=f"{self.side}_{wave_name}Offset03_BS")[0]

        offset_beziers = [blendshape01_off, blendshape02_off, blendshape03_off]

        for i, blendshape in enumerate([blendshape01, blendshape02, blendshape03]):
            cmds.connectAttr(f"{self.settings_curve_ctl}.waveEnvelop", f"{blendshape}.{dupe_beziers[i]}", f=True)
            cmds.connectAttr(f"{self.settings_curve_ctl}.waveEnvelop", f"{offset_beziers[i]}.{dupe_beziers_offset[i]}", f=True)

        for attr in ["amplitude", "wavelength", "offset", "dropoff"]:
            pma = cmds.createNode("plusMinusAverage", name=f"{self.side}_{wave_name}{attr}_PMA", ss=True)
            cmds.connectAttr(f"{self.settings_curve_ctl}.global{attr.capitalize()}", f"{pma}.input1D[0]", f=True)
            cmds.connectAttr(f"{self.fk_ctl_list[0]}.{attr}", f"{pma}.input1D[1]", f=True)
            
            cmds.connectAttr(f"{pma}.output1D", f"{wave[0]}.{attr}", f=True)

        for i, bls in enumerate([blendshape01, blendshape02, blendshape03]):
            cmds.reorderDeformers(skc[i][0], bls, beziers[i])
            cmds.reorderDeformers(offset_skc[i][0], offset_beziers[i], bezier_off[i])


class Bendys(object):
    """
    Class to create bendy modules for finger rigging in Maya.
    """

    def __init__(self, side, upper_joint, lower_joint, bendy_module, skinning_trn, normals, controls_trn, name):
        """
        Initializes the Bendys class with the necessary parameters.

        Args:
            side (str): The side of the finger (e.g., "L" or "R").
            upper_joint (str): The name of the upper joint in the finger chain.
            lower_joint (str): The name of the lower joint in the finger chain.
            bendy_module (str): The name of the bendy module transform.
            skinning_trn (str): The name of the skinning transform.
            normals (tuple): The normals for the bendy module.
            controls_trn (str): The name of the controls transform.
            name (str): The name of the finger part (e.g., "Thumb", "Index", etc.).
        """
        self.name = name
        self.normals = normals
        self.skinning_trn = skinning_trn
        self.side = side
        self.upper_joint = upper_joint
        self.lower_joint = lower_joint
        self.part = self.upper_joint.split("_")[1]
        self.bendy_module = cmds.createNode("transform", name=f"{self.side}_{self.name}BendyModule_GRP", p=bendy_module, ss=True)
        self.controls_trn = controls_trn
   
    def lower_twists_setup(self):
        """
        Set up the lower twists for the finger module, creating twist joints and IK handles.

        Returns:
            tuple: Contains the end bezier curve, bendy skin cluster, bendy joint, offset curve, and bendy offset skin cluster.
            
        """

        duplicated_twist_joints = cmds.duplicate(self.upper_joint, renameChildren=True)
        duplicated_twist_joints.append(cmds.duplicate(self.lower_joint, renameChildren=True)[0])
        self.twist_joints = cmds.rename(duplicated_twist_joints[0], f"{self.side}_{self.name}{self.part}Roll_JNT")
        twist_end_joints = cmds.rename(duplicated_twist_joints[1], f"{self.side}_{self.part}LowerRollEnd_JNT")
        cmds.parent(twist_end_joints, self.twist_joints)


        roll_offset_trn = cmds.createNode("transform", name=f"{self.side}_{self.part}LowerRollOffset_TRN", parent=self.bendy_module, ss=True)
        cmds.delete(cmds.parentConstraint(self.upper_joint, roll_offset_trn, maintainOffset=False))
        cmds.parent(self.twist_joints, roll_offset_trn)
        cmds.parentConstraint(self.upper_joint, roll_offset_trn, maintainOffset=False)

        ik_handle = cmds.ikHandle(sj=self.twist_joints, ee=twist_end_joints, solver="ikSCsolver", name=f"{self.side}_{self.part}LowerRoll_HDL")[0]
        cmds.parent(ik_handle, self.bendy_module)
        
        cmds.parentConstraint(f"{self.lower_joint}", ik_handle, maintainOffset=True)

        end_bezier, bendy_skin_cluster, bendy_joint, off_curve, bendy_offset_skin_cluster = self.hooks()
        return end_bezier, bendy_skin_cluster, bendy_joint, off_curve, bendy_offset_skin_cluster

    def hooks(self):
        """
        Create hook joints and motion paths for the bendy module.
        
        Returns:
            tuple: Contains the end bezier curve, bendy skin cluster, bendy joint, offset curve, and bendy offset skin cluster.
        """
        self.hook_joints = []
        parametric_lenght = [0.001, 0.5, 0.999]

        cmds.select(clear=True)
        curve = cmds.curve(degree=1, point=[
            cmds.xform(self.upper_joint, query=True, worldSpace=True, translation=True),
            cmds.xform(self.lower_joint, query=True, worldSpace=True, translation=True)
        ])
        curve = cmds.rename(curve, f"{self.side}_{self.part}Bendy_CRV")
        cmds.parent(curve, self.bendy_module)
        cmds.delete(curve, ch=True)
        dcpm = cmds.createNode("decomposeMatrix", name=f"{self.side}_{self.part}Bendy01_DPM", ss=True)
        dcpm02 = cmds.createNode("decomposeMatrix", name=f"{self.side}_{self.part}Bendy02_DPM", ss=True)
        cmds.connectAttr(f"{self.upper_joint}.worldMatrix[0]", f"{dcpm}.inputMatrix")
        cmds.connectAttr(f"{dcpm}.outputTranslate", f"{curve}.controlPoints[0]")
        cmds.connectAttr(f"{self.lower_joint}.worldMatrix[0]", f"{dcpm02}.inputMatrix")
        cmds.connectAttr(f"{dcpm02}.outputTranslate", f"{curve}.controlPoints[1]")
        for i, joint in enumerate(["Root", "Mid", "Tip"]):
            self.hook_joints.append(cmds.joint(name=f"{self.side}_{self.part}LowerBendy{joint}Hook_JNT"))
            cmds.setAttr(self.hook_joints[i] + ".inheritsTransform", 0)
            mpa = cmds.createNode("motionPath", name=f"{self.side}_{self.part}LowerBendy{joint}Hook_MPA", ss=True)
            flm = cmds.createNode("floatMath", name=f"{self.side}_{self.part}LowerBendy{joint}Hook_FLM", ss=True)
            flc = cmds.createNode("floatConstant", name=f"{self.side}_{self.part}LowerBendy{joint}Hook_FLC", ss=True)
            cmds.connectAttr(f"{curve}.worldSpace[0]", f"{mpa}.geometryPath")
            cmds.setAttr(f"{flc}.inFloat", parametric_lenght[i])
            cmds.connectAttr(f"{flm}.outFloat", f"{mpa}.frontTwist")
            cmds.connectAttr(f"{flc}.outFloat", f"{mpa}.uValue")
            cmds.connectAttr(f"{flc}.outFloat", f"{flm}.floatA")
            cmds.connectAttr(f"{self.twist_joints}.rotateX", f"{flm}.floatB")
            cmds.setAttr(f"{flm}.operation", 2)
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{self.hook_joints[i]}.translate")
            cmds.connectAttr(f"{mpa}.rotate", f"{self.hook_joints[i]}.rotate")
            cmds.setAttr(f"{mpa}.frontAxis", 0)
            cmds.setAttr(f"{mpa}.upAxis", 1)
            cmds.setAttr(f"{mpa}.worldUpType", 2)
            cmds.connectAttr(f"{self.upper_joint}.worldMatrix[0]", f"{mpa}.worldUpMatrix")
            cmds.setAttr(f"{mpa}.fractionMode", True)
            if self.side == "R_":
                cmds.setAttr(f"{mpa}.inverseFront", True)


        for joint in self.hook_joints:
            cmds.parent(joint, self.bendy_module)

        end_bezier, bendy_skin_cluster, bendy_joint, off_curve, bendy_offset_skin_cluster= self.bendy_setup()
        return end_bezier, bendy_skin_cluster, bendy_joint, off_curve, bendy_offset_skin_cluster

    def bendy_setup(self):
        """
        Create the bendy curve and its associated controllers, skin clusters, and offset curves.

        Returns:
            tuple: Contains the end bezier curve, bendy skin cluster, bendy joint, offset curve, and bendy offset skin cluster.
        """
        
        bendyCurve = cmds.curve(p=(cmds.xform(self.upper_joint, query=True, worldSpace=True, translation=True),cmds.xform(self.lower_joint, query=True, worldSpace=True, translation=True)) , d=1, n=f"{self.side}_{self.part}Bendy_CRV")
        cmds.rebuildCurve(bendyCurve, ch=False, rpo=True, rt=0, end=True, kr=False, kcp=False, kep=True, kt=False, fr=False, s=2, d=1, tol=0.01)
        cmds.select(bendyCurve)

        bezier = cmds.nurbsCurveToBezier()[0]
        cmds.delete(bezier, ch=True)


        cmds.select(f"{bendyCurve}.cv[6]", f"{bendyCurve}.cv[0]")
        cmds.bezierAnchorPreset(p=2)

        cmds.select(f"{bendyCurve}.cv[3]")
        cmds.bezierAnchorPreset(p=1)

        bendyDupe = cmds.duplicate(bendyCurve, name=f"{self.side}_{self.part}BendyDupe_CRV", )

        off_curve = cmds.offsetCurve(bendyDupe, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=1.5, tol=0.01, sd=0, ugn=False, name=f"{self.side}_{self.part}BendyOffset_CRV", normal=self.normals)

        cmds.select(f"{off_curve[0]}.cv[6]", f"{off_curve[0]}.cv[0]")
        cmds.bezierAnchorPreset(p=2)

        cmds.select(f"{off_curve[0]}.cv[3]")
        cmds.bezierAnchorPreset(p=1)
        
        rotation = cmds.xform(self.upper_joint, query=True, worldSpace=True, rotation=True)

        off_curve[1] = cmds.rename(off_curve[1], f"{self.side}_{self.part}Bendy_OFC")
        cmds.setAttr(f"{off_curve[1]}.useGivenNormal", 1)
        cmds.setAttr(f"{off_curve[1]}.subdivisionDensity", 0)
        cmds.setAttr(f"{off_curve[1]}.distance", 20)
        
        cmds.connectAttr(f"{bezier}.worldSpace[0]", f"{off_curve[1]}.inputCurve", f=True)
        cmds.delete(bendyDupe)
        bendyCtl, bendyCtlGRP = curve_tool.controller_creator(f"{self.side}_{self.part}Bendy", suffixes=["GRP"])  
        cmds.parent(bendyCtlGRP[0], self.controls_trn)
        cmds.delete(cmds.parentConstraint(self.hook_joints[1], bendyCtlGRP[0], maintainOffset=False))
        upper_bendy_joint = cmds.duplicate(self.hook_joints[1], renameChildren=True, parentOnly=True, name = f"{self.side}_{self.part}Bendy_JNT")
        cmds.parentConstraint(bendyCtl, upper_bendy_joint, maintainOffset=False)
        cmds.scaleConstraint(bendyCtl, upper_bendy_joint, maintainOffset=False)
        cmds.parentConstraint(self.hook_joints[1], bendyCtlGRP[0], maintainOffset=False)

        for attr in ["scaleY", "scaleZ", "visibility"]:
            cmds.setAttr(f"{bendyCtl}.{attr}", lock=True, keyable=False, channelBox=False)

        bendy_skin_cluster = cmds.skinCluster(upper_bendy_joint, self.hook_joints[0], self.hook_joints[2], bendyCurve, tsb=True, omi=False, rui=False, name=f"{self.side}_{self.part}Bendy_SKN") 

        cmds.skinPercent(bendy_skin_cluster[0], f"{bendyCurve}.cv[2]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_skin_cluster[0], f"{bendyCurve}.cv[3]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_skin_cluster[0], f"{bendyCurve}.cv[4]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_skin_cluster[0], f"{bendyCurve}.cv[0]", transformValue=(self.hook_joints[0], 1))
        cmds.skinPercent(bendy_skin_cluster[0], f"{bendyCurve}.cv[6]", transformValue=(self.hook_joints[2], 1))

        origin_shape = cmds.listRelatives(bendyCurve, allDescendents=True)
        origin_shape.remove(bezier)

        cmds.connectAttr(f"{origin_shape[0]}.worldSpace[0]", f"{off_curve[1]}.inputCurve", f=True)

        bendy_offset_skin_cluster = cmds.skinCluster(upper_bendy_joint, self.hook_joints[0], self.hook_joints[2], off_curve[0], tsb=True, omi=False, rui=False, name=f"{self.side}_{self.part}BendyOffset_SKN") 

        cmds.skinPercent(bendy_offset_skin_cluster[0], f"{off_curve[0]}.cv[2]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_offset_skin_cluster[0], f"{off_curve[0]}.cv[3]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_offset_skin_cluster[0], f"{off_curve[0]}.cv[4]", transformValue=(upper_bendy_joint[0], 1))
        cmds.skinPercent(bendy_offset_skin_cluster[0], f"{off_curve[0]}.cv[0]", transformValue=(self.hook_joints[0], 1))
        cmds.skinPercent(bendy_offset_skin_cluster[0], f"{off_curve[0]}.cv[6]", transformValue=(self.hook_joints[2], 1))

        bendy_helper_transform = cmds.createNode("transform", name=f"{self.side}_{self.part}BendyHelperAim04_TRN", ss=True)
        cmds.setAttr(f"{bendy_helper_transform}.inheritsTransform", 0)
        cmds.select(clear=True)

        bendy_joint = []
        blendy_up_trn = []

        if not "01" in self.part:
            values = [0, 0.25, 0.5, 0.75, 0.95]
            number = 3
        else:
            values = [0.1, 0.25, 0.5, 0.75, 0.95]
            number = 3

        mps = []

        for i, value in enumerate(values):
            part_splited = self.part.split("Blend")[0]
            if i == 0:
                name = f"{self.side}_{part_splited}Skinning_JNT"
            else:
                name = f"{self.side}_{part_splited}Bendy0{i}_JNT"
            bendy_joint.append(cmds.joint(name=name, rad=20))
            mpa = cmds.createNode("motionPath", name=f"{self.side}_{self.part}Bendy0{i}_MPA", ss=True)
            cmds.setAttr(f"{mpa}.fractionMode", True)
            cmds.setAttr(f"{mpa}.uValue", value)
            cmds.connectAttr(f"{bendyCurve}.worldSpace[0]", f"{mpa}.geometryPath")
            if i == number:
                cmds.connectAttr(f"{mpa}.allCoordinates", f"{bendy_helper_transform}.translate")
            cmds.parent(bendy_joint[i], self.skinning_trn)

            mps.append(mpa)

        
        bendy_up_module = cmds.createNode("transform", name=f"{self.side}_{self.part}BendyUpModule_GRP", p=self.bendy_module, ss=True) 
        for i, value in enumerate(values):
            blendy_up_trn.append(cmds.createNode("transform", name=f"{self.side}_{self.part}BendyUp0{i}_TRN"))
            cmds.setAttr(f"{blendy_up_trn[i]}.inheritsTransform", 0)
            mpa = cmds.createNode("motionPath", name=f"{self.side}_{self.part}BendyUp0{i}_MPA", ss=True)
            cmds.setAttr(f"{mpa}.fractionMode", True)
            cmds.setAttr(f"{mpa}.uValue", value)
            cmds.connectAttr(f"{off_curve[0]}.worldSpace[0]", f"{mpa}.geometryPath")
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{blendy_up_trn[i]}.translate")
            cmds.parent(blendy_up_trn[i], bendy_up_module)
        
        if self.side == "L":
            primary_upvectorX = 1
            secondary_upvectorZ =-1
            reverse_upvectorX = -1

        elif self.side == "R":
            primary_upvectorX = -1
            secondary_upvectorZ = 1
            reverse_upvectorX = 1

        for i, joint in enumerate(bendy_joint):

            compose_matrix = cmds.createNode("composeMatrix", name=f"{self.side}_{self.part}Bendy0{i}_CMP", ss=True)
            aimMatrix = cmds.createNode("aimMatrix", name=f"{self.side}_{self.part}Bendy0{i}_AMT", ss=True)
            cmds.connectAttr(f"{mps[i]}.allCoordinates", f"{compose_matrix}.inputTranslate")   
            cmds.connectAttr(f"{compose_matrix}.outputMatrix", f"{aimMatrix}.inputMatrix")
            cmds.connectAttr(f"{aimMatrix}.outputMatrix", f"{joint}.offsetParentMatrix")
            cmds.connectAttr(f"{blendy_up_trn[i]}.worldMatrix[0]", f"{aimMatrix}.secondaryTargetMatrix")
            cmds.setAttr(f"{aimMatrix}.primaryInputAxisY", 0)
            cmds.setAttr(f"{aimMatrix}.primaryInputAxisZ", 0)
            cmds.setAttr(f"{aimMatrix}.secondaryInputAxisX", 0)
            cmds.setAttr(f"{aimMatrix}.secondaryInputAxisY", 0)
            cmds.setAttr(f"{aimMatrix}.secondaryInputAxisZ", secondary_upvectorZ)
            cmds.setAttr(f"{aimMatrix}.primaryMode", 1)
            cmds.setAttr(f"{aimMatrix}.secondaryMode", 1) 

            if i != 4:
                cmds.connectAttr(f"{bendy_joint[i+1]}.worldMatrix[0]", f"{aimMatrix}.primaryTargetMatrix")
                cmds.setAttr(f"{aimMatrix}.primaryInputAxisX", primary_upvectorX)

            else:
                cmds.connectAttr(f"{bendy_helper_transform}.worldMatrix[0]", f"{aimMatrix}.primaryTargetMatrix")
                cmds.setAttr(f"{aimMatrix}.primaryInputAxisX", reverse_upvectorX)


        cmds.parent(bendyCurve, self.bendy_module)
        cmds.parent(off_curve[0], self.bendy_module)
        cmds.parent(bendy_helper_transform, self.bendy_module)

        bezier_parent = cmds.listRelatives(bezier, parent=True, fullPath=True)
        bezier_shape = cmds.rename(bezier, f"{self.side}_{self.part}BendyBezierShape_CRV")
        end_bezier = cmds.rename(bezier_parent[0], f"{self.side}_{self.part}BendyBezier_CRV")



        return end_bezier, bendy_skin_cluster, bendy_joint, off_curve[0], bendy_offset_skin_cluster

                            
