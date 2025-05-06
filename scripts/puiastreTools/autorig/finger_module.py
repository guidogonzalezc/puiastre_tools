"""
Leg module for dragon rigging system
"""
import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import basic_structure
import maya.mel as mel
import math
import os
import re
from importlib import reload
reload(guides_manager)
reload(basic_structure)
reload(curve_tool)    

class FingerModule():
    def __init__(self):
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "dragon_guides_template_01.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "template_curves_001.json") 

    def make(self, side):

        self.side = side    

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_fingerModule_GRP", ss=True)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_fingerControllers_GRP", ss=True)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_fingerSkinning_GRP", ss=True)

        basic_structure.create_basic_structure(asset_name = "Varyndor")

        self.settings_curve_ctl, self.settings_curve_grp = curve_tool.controller_creator(f"{self.side}_fingerAttr", suffixes = ["GRP"])
        position, rotation = guides_manager.guide_import(joint_name=f"{self.side}_fingerAttr", filePath=self.guides_path)
        cmds.xform(self.settings_curve_grp[0], ws=True, translation=position)
        cmds.xform(self.settings_curve_grp[0], ws=True, rotation=rotation)
        cmds.parent(self.settings_curve_grp[0], self.controllers_trn)
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


        self.controllers_fk = []

        for name in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
            self.individual_module_trn = cmds.createNode("transform", name=f"{self.side}_{name.lower()}Module_GRP", ss=True, p=self.module_trn)
            self.bendy_module = cmds.createNode("transform", name=f"{self.side}_{name.lower()}BendyModule_GRP", ss=True, p=self.individual_module_trn)

            self.create_chain(name=name)  
            self.set_controllers()
            self.call_bendys()

    def lock_attr(self, ctl, attrs = ["scaleX", "scaleY", "scaleZ", "visibility"]):
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", keyable=False, channelBox=False, lock=True)

    def create_chain(self, name):
        
        self.blend_chain = guides_manager.guide_import(
            joint_name=f"{self.side}_finger{name}01_JNT",
            all_descendents=True,
            filePath=self.guides_path
        )
        cmds.parent(self.blend_chain[0], self.individual_module_trn)


    def attr_curl_setup(self, sdk_grp, jointName, i):
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

        # -- FK CONTROLLER -- #

        self.fk_ctl_list = []
        self.fk_grp_list = []

        self.joint_name = self.blend_chain[0].split("_")[1]

        for i, joint in enumerate(self.blend_chain):
            fk_ctl, fk_grp = curve_tool.controller_creator(joint.replace('_JNT', ''), suffixes = ["GRP", "SDK", "OFF"])
            self.fk_ctl_list.append(fk_ctl)
            self.fk_grp_list.append(fk_grp)
            cmds.matchTransform(fk_grp[0], joint)
            cmds.parentConstraint(fk_ctl, joint, mo=True)

            self.attr_curl_setup(fk_grp[1], self.joint_name, i)

            if i > 0:
                cmds.parent(fk_grp[0], self.fk_ctl_list[i - 1])
            else:
                cmds.addAttr(fk_ctl, shortName="waveSep", niceName="Wave_____", enumName="_____",attributeType="enum", keyable=True)
                cmds.setAttr(fk_ctl+".waveSep", channelBox=True, lock=True)
                cmds.addAttr(fk_ctl, shortName="amplitude", niceName="Amplitude", defaultValue=0, keyable=True)
                cmds.addAttr(fk_ctl, shortName="wavelength", niceName="Wavelength", defaultValue=0, keyable=True)
                cmds.addAttr(fk_ctl, shortName="offset", niceName="Offset", defaultValue=0, keyable=True)
                cmds.addAttr(fk_ctl, shortName="dropoff", niceName="Dropoff", defaultValue=0, keyable=True)
                cmds.parent(fk_grp[0], self.settings_curve_ctl)
            
            self.lock_attr(fk_ctl)


    def call_bendys(self):
        normals = (0, 0, 1)
        bendy = Bendys(self.side, self.blend_chain[0], self.blend_chain[1], self.bendy_module, self.skinning_trn, normals, self.controllers_trn, self.joint_name + "Upper")
        end_bezier01 = bendy.lower_twists_setup()
        bendy = Bendys(self.side, self.blend_chain[1], self.blend_chain[2], self.bendy_module, self.skinning_trn, normals, self.controllers_trn, self.joint_name + "Middle")
        end_bezier02 = bendy.lower_twists_setup()
        bendy = Bendys(self.side, self.blend_chain[2], self.blend_chain[3], self.bendy_module, self.skinning_trn, normals, self.controllers_trn, self.joint_name + "Lower")
        end_bezier03 = bendy.lower_twists_setup()

        self.wave_handle(beziers=[end_bezier01, end_bezier02, end_bezier03])

    def wave_handle(self, beziers = []):
        
        dupe_beziers = []
        for bezier in beziers:
            dupe = cmds.duplicate(bezier, name=bezier.replace("_CRV", "Dupe_CRV"))
            cmds.delete(dupe[0], ch=True)
            dupe_beziers.append(dupe[0])
        
        dupe_parent = cmds.listRelatives(dupe_beziers[0], parent=True, fullPath=True)
        wave_name = dupe_beziers[0].split("_")[1].split("01")[0]
        wave = cmds.nonLinear(dupe_beziers, type="wave", name=f"{self.side}_{wave_name}Wave_HDL")
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

        for i, blendshape in enumerate([blendshape01, blendshape02, blendshape03]):
            cmds.connectAttr(f"{self.settings_curve_ctl}.waveEnvelop", f"{blendshape}.{dupe_beziers[i]}", f=True)

        for attr in ["amplitude", "wavelength", "offset", "dropoff"]:
            pma = cmds.createNode("plusMinusAverage", name=f"{self.side}_{wave_name}{attr}_PMA", ss=True)
            cmds.connectAttr(f"{self.settings_curve_ctl}.global{attr.capitalize()}", f"{pma}.input1D[0]", f=True)
            cmds.connectAttr(f"{self.fk_ctl_list[0]}.{attr}", f"{pma}.input1D[1]", f=True)
            cmds.connectAttr(f"{pma}.output1D", f"{wave[0]}.{attr}", f=True)


class Bendys(object):
    def __init__(self, side, upper_joint, lower_joint, bendy_module, skinning_trn, normals, controls_trn, name):
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

        duplicated_twist_joints = cmds.duplicate(self.upper_joint, renameChildren=True)
        cmds.delete(duplicated_twist_joints[2])
        self.twist_joints = cmds.rename(duplicated_twist_joints[0], f"{self.side}_{self.name}{self.part}Roll_JNT")
        twist_end_joints = cmds.rename(duplicated_twist_joints[1], f"{self.side}_{self.part}LowerRollEnd_JNT")

        roll_offset_trn = cmds.createNode("transform", name=f"{self.side}_{self.part}LowerRollOffset_TRN", parent=self.bendy_module, ss=True)
        cmds.delete(cmds.parentConstraint(self.upper_joint, roll_offset_trn, maintainOffset=False))
        cmds.parent(self.twist_joints, roll_offset_trn)
        cmds.parentConstraint(self.upper_joint, roll_offset_trn, maintainOffset=False)

        ik_handle = cmds.ikHandle(sj=self.twist_joints, ee=twist_end_joints, solver="ikSCsolver", name=f"{self.side}_{self.part}LowerRoll_HDL")[0]
        cmds.parent(ik_handle, self.bendy_module)
        
        cmds.parentConstraint(f"{self.lower_joint}", ik_handle, maintainOffset=True)

        end_bezier = self.hooks()
        return end_bezier

    def hooks(self):
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

        end_bezier = self.bendy_setup()
        return end_bezier

    def bendy_setup(self):
        bendyCurve = cmds.curve(p=(cmds.xform(self.upper_joint, query=True, worldSpace=True, translation=True),cmds.xform(self.lower_joint, query=True, worldSpace=True, translation=True)) , d=1, n=f"{self.side}_{self.part}Bendy_CRV")
        cmds.rebuildCurve(bendyCurve, ch=False, rpo=True, rt=0, end=True, kr=False, kcp=False, kep=True, kt=False, fr=False, s=2, d=1, tol=0.01)
        cmds.select(bendyCurve)

        bezier = cmds.nurbsCurveToBezier()[0]

        cmds.select(f"{bendyCurve}.cv[6]", f"{bendyCurve}.cv[0]")
        cmds.bezierAnchorPreset(p=2)

        cmds.select(f"{bendyCurve}.cv[3]")
        cmds.bezierAnchorPreset(p=1)

        bendyDupe = cmds.duplicate(bendyCurve, name=f"{self.side}_{self.part}BendyDupe_CRV", )

        off_curve = cmds.offsetCurve(bendyDupe, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=1.5, tol=0.01, sd=0, ugn=False, name=f"{self.side}_{self.part}BendyOffset_CRV", normal=self.normals)
        
        off_curve[1] = cmds.rename(off_curve[1], f"{self.side}_{self.part}Bendy_OFC")
        cmds.setAttr(f"{off_curve[1]}.useGivenNormal", 1)
        cmds.setAttr(f"{off_curve[1]}.normal", 0,0,1)
        
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

        for i, value in enumerate([0, 0.25, 0.5, 0.75, 0.95]):
            bendy_joint.append(cmds.joint(name=f"{self.side}_{self.part}Bendy0{i}_JNT", rad=20))
            mpa = cmds.createNode("motionPath", name=f"{self.side}_{self.part}Bendy0{i}_MPA", ss=True)
            cmds.setAttr(f"{mpa}.fractionMode", True)
            cmds.setAttr(f"{mpa}.uValue", value)
            cmds.connectAttr(f"{bendyCurve}.worldSpace[0]", f"{mpa}.geometryPath")
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{bendy_joint[i]}.translate")
            if i == 3:
                cmds.connectAttr(f"{mpa}.allCoordinates", f"{bendy_helper_transform}.translate")
            cmds.parent(bendy_joint[i], self.skinning_trn)
        
        bendy_up_module = cmds.createNode("transform", name=f"{self.side}_{self.part}BendyUpModule_GRP", p=self.bendy_module, ss=True) 
        for i, value in enumerate([0, 0.25, 0.5, 0.75, 0.95]):
            blendy_up_trn.append(cmds.createNode("transform", name=f"{self.side}_{self.part}BendyUp0{i}_TRN"))
            cmds.setAttr(f"{blendy_up_trn[i]}.inheritsTransform", 0)
            mpa = cmds.createNode("motionPath", name=f"{self.side}_{self.part}BendyUp0{i}_MPA", ss=True)
            cmds.setAttr(f"{mpa}.fractionMode", True)
            cmds.setAttr(f"{mpa}.uValue", value)
            cmds.connectAttr(f"{off_curve[0]}.worldSpace[0]", f"{mpa}.geometryPath")
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{blendy_up_trn[i]}.translate")
            cmds.parent(blendy_up_trn[i], bendy_up_module)
        
        if self.side == "L":
            upvector = (0, 1, 0)
            aimVector = (1,0,0)
            reverseAim = (-1,0,0)

        elif self.side == "R":
            upvector = (0, 1, 0)
            aimVector = (-1,0,0)
            reverseAim = (1,0,0)

        for i, joint in enumerate(bendy_joint):
            if i != 4:
                aim = cmds.aimConstraint(bendy_joint[i+1], joint, aimVector=aimVector, upVector=upvector, worldUpType="object", worldUpObject=blendy_up_trn[i], maintainOffset=False)
                cmds.delete(aim)
                cmds.makeIdentity(joint, apply=True, r=1)
                cmds.aimConstraint(bendy_joint[i+1], joint, aimVector=aimVector, upVector=upvector, worldUpType="object", worldUpObject=blendy_up_trn[i], maintainOffset=False)
            else:
                aim = cmds.aimConstraint(bendy_helper_transform, joint, aimVector=reverseAim, upVector=upvector, worldUpType="object", worldUpObject=blendy_up_trn[i], maintainOffset=False)
                cmds.delete(aim)
                cmds.makeIdentity(joint, apply=True, r=1)
                cmds.aimConstraint(bendy_helper_transform, joint, aimVector=reverseAim, upVector=upvector, worldUpType="object", worldUpObject=blendy_up_trn[i], maintainOffset=False)

        cmds.parent(bendyCurve, self.bendy_module)
        cmds.parent(off_curve[0], self.bendy_module)
        cmds.parent(bendy_helper_transform, self.bendy_module)

        bezier_parent = cmds.listRelatives(bezier, parent=True, fullPath=True)
        end_bezier = cmds.rename(bezier_parent[0], f"{self.side}_{self.part}BendyBezier_CRV")

        return end_bezier

                            
