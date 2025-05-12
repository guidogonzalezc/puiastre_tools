import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import basic_structure
from puiastreTools.utils import data_export
import os
import re
from importlib import reload

# Reload dependencies
reload(guides_manager)
reload(basic_structure)
reload(curve_tool)
reload(data_export)

class Fingers:
    def __init__(self):
        base_path = os.path.realpath(__file__).split("\\scripts")[0]
        self.guides_path = os.path.join(base_path, "guides", "dragon_guides_template_01.guides")
        self.curves_path = os.path.join(base_path, "curves", "template_curves_001.json")
        basic_structure.create_basic_structure(asset_name="Varyndor")

        self.data_exporter = data_export.DataExport()
        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")

    def make(self, side):
        self.side = side
        self.module_trn = cmds.createNode("transform", name=f"{side}_fingerModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{side}_fingerControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{side}_fingerSkinning_GRP", ss=True, parent=self.skel_grp)

        self.settings_curve_ctl, settings_curve_grp = curve_tool.controller_creator(f"{side}_fingerAttr", suffixes=["GRP"])
        pos, rot = guides_manager.guide_import(joint_name=f"{side}_fingerAttr", filePath=self.guides_path)
        cmds.xform(settings_curve_grp[0], ws=True, translation=pos)
        cmds.xform(settings_curve_grp[0], ws=True, rotation=rot)
        cmds.parent(settings_curve_grp[0], self.controllers_trn)
        self._lock_attr(self.settings_curve_ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])

        self._add_finger_attrs(self.settings_curve_ctl)
        self.data_exporter.append_data(f"{side}_finger", {"attr_ctl": self.settings_curve_ctl})

        for finger in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
            self._build_finger(finger)

    def _lock_attr(self, ctl, attrs):
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", keyable=False, channelBox=False, lock=True)

    def _add_finger_attrs(self, ctl):
        attrs = [
            ("handSep", "Hand_____", "enum", "_____"),
            ("curl", "Curl", "float", (-10, 10, 0)),
            ("spread", "Spread", "float", (-10, 10, 0)),
            ("globalWaveSep", "GlobalWave_____", "enum", "_____"),
            ("waveEnvelop", "Wave Envelop", "float", (0, 1, 0)),
            ("globalAmplitude", "Global Amplitude", "float", (None, None, 0)),
            ("globalWavelength", "Global Wavelength", "float", (None, None, 1)),
            ("globalOffset", "Global Offset", "float", (None, None, 0)),
            ("globalDropoff", "Global Dropoff", "float", (0, 1, 0))
        ]
        for short, nice, attr_type, val in attrs:
            if attr_type == "enum":
                cmds.addAttr(ctl, shortName=short, niceName=nice, enumName=val, attributeType="enum", keyable=True)
                cmds.setAttr(f"{ctl}.{short}", lock=True)
            else:
                min_val, max_val, def_val = val
                cmds.addAttr(ctl, shortName=short, niceName=nice, attributeType="float",
                             minValue=min_val if min_val is not None else -1e9,
                             maxValue=max_val if max_val is not None else 1e9,
                             defaultValue=def_val, keyable=True)

    def _build_finger(self, name):
        ind_mod = cmds.createNode("transform", name=f"{self.side}_{name.lower()}Module_GRP", ss=True, parent=self.module_trn)
        bendy_mod = cmds.createNode("transform", name=f"{self.side}_{name.lower()}BendyModule_GRP", ss=True, parent=ind_mod)
        chain = guides_manager.guide_import(joint_name=f"{self.side}_finger{name}01_JNT", all_descendents=True, filePath=self.guides_path)
        cmds.parent(chain[0], ind_mod)

        self.blend_chain = chain  # <— for wave centering
        self.fk_ctl_list, fk_grps = self._create_fk_controls(chain, name)
        
        # 🔻 Create bendy segments and gather all needed data
        bendy_data = self._create_bendy_segment(chain, bendy_mod, self.fk_ctl_list, name)

        # 🔻 Optionally, append finger-specific data
        self.data_exporter.append_data(f"{self.side}_{name.lower()}", {
            "bendy_joints": bendy_data["bendy_joints"]
        })

        # 🔻 🔥 CALL wave_handle() here
        self.wave_handle(
            beziers=bendy_data["beziers"],
            skc=bendy_data["skc"],
            bezier_off=bendy_data["offset_curves"],
            offset_skc=bendy_data["offset_skc"]
        )
    def _create_fk_controls(self, chain, finger_name):
        fk_ctls, fk_grps = [], []
        short_name = chain[0].split("_")[1]

        for i, joint in enumerate(chain):
            ctl, grp = curve_tool.controller_creator(joint.replace('_JNT', ''), suffixes=["GRP", "SDK", "OFF"])
            cmds.matchTransform(grp[0], joint)
            cmds.parentConstraint(ctl, joint, mo=True)

            fk_ctls.append(ctl)
            fk_grps.append(grp)

            self._setup_attr_driven_keys(grp[1], short_name, i)
            if i == 0:
                cmds.parent(grp[0], self.settings_curve_ctl)
                self._add_wave_attrs(ctl)
            else:
                cmds.parent(grp[0], fk_ctls[i - 1])

            self._lock_attr(ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])

        return fk_ctls, fk_grps

    def _add_wave_attrs(self, ctl):
        cmds.addAttr(ctl, shortName="waveSep", niceName="Wave_____", enumName="_____", attributeType="enum", keyable=True)
        cmds.setAttr(f"{ctl}.waveSep", channelBox=True, lock=True)
        for attr in ["amplitude", "wavelength", "offset", "dropoff"]:
            cmds.addAttr(ctl, shortName=attr, niceName=attr.capitalize(), defaultValue=0, keyable=True)

    def _setup_attr_driven_keys(self, sdk_grp, joint_name, index):
        curl_value = 40
        spread_values = {
            "Thumb": -60,
            "Index": -30,
            "Middle": -5,
            "Ring": 10,
            "Pinky": 15
        }

        clean_name = re.sub(r'\d', '', joint_name)
        if index == 0 and clean_name in spread_values:
            spread = spread_values[clean_name]
            cmds.setDrivenKeyframe(f"{sdk_grp}.rotateY", currentDriver=f"{self.settings_curve_ctl}.spread", driverValue=10, value=-spread / 2)
            cmds.setDrivenKeyframe(f"{sdk_grp}.rotateY", currentDriver=f"{self.settings_curve_ctl}.spread", driverValue=0, value=0)
            cmds.setDrivenKeyframe(f"{sdk_grp}.rotateY", currentDriver=f"{self.settings_curve_ctl}.spread", driverValue=-10, value=spread)

        cmds.setDrivenKeyframe(f"{sdk_grp}.rotateZ", currentDriver=f"{self.settings_curve_ctl}.curl", driverValue=10, value=-curl_value)
        cmds.setDrivenKeyframe(f"{sdk_grp}.rotateZ", currentDriver=f"{self.settings_curve_ctl}.curl", driverValue=0, value=0)
        cmds.setDrivenKeyframe(f"{sdk_grp}.rotateZ", currentDriver=f"{self.settings_curve_ctl}.curl", driverValue=-10, value=10)

    def _create_bendy_segment(self, joint_chain, bendy_module, fk_ctls, joint_name):
        normals = (0, 0, 1)
        bendy_joints = []

        # For each segment (e.g., Thumb01 -> Thumb02, Thumb02 -> Thumb03, etc.)
        for i in range(3):
            upper = joint_chain[i]
            lower = joint_chain[i + 1]
            part = upper.split("_")[1]
            name = f"{joint_name}{['Upper', 'Middle', 'Lower'][i]}"
            bendy_seg_grp = cmds.createNode("transform", name=f"{self.side}_{name}BendyModule_GRP", p=bendy_module, ss=True)

            # Twist Joint Duplication
            twist_joints = cmds.duplicate(upper, renameChildren=True)
            cmds.delete(twist_joints[2])
            twist_start = cmds.rename(twist_joints[0], f"{self.side}_{name}{part}Roll_JNT")
            twist_end = cmds.rename(twist_joints[1], f"{self.side}_{part}LowerRollEnd_JNT")

            offset_grp = cmds.createNode("transform", name=f"{self.side}_{part}LowerRollOffset_TRN", parent=bendy_seg_grp, ss=True)
            cmds.delete(cmds.parentConstraint(upper, offset_grp, mo=False))
            cmds.parent(twist_start, offset_grp)
            cmds.parentConstraint(upper, offset_grp, mo=False)

            ik_handle = cmds.ikHandle(sj=twist_start, ee=twist_end, solver="ikSCsolver", name=f"{self.side}_{part}LowerRoll_HDL")[0]
            cmds.parent(ik_handle, bendy_seg_grp)
            cmds.parentConstraint(lower, ik_handle, mo=True)

            # Motion Path Joint Hooks
            curve = cmds.curve(d=1, point=[
                cmds.xform(upper, q=True, ws=True, t=True),
                cmds.xform(lower, q=True, ws=True, t=True)
            ], name=f"{self.side}_{part}Bendy_CRV")
            cmds.parent(curve, bendy_seg_grp)
            cmds.delete(curve, ch=True)

            dcp1 = cmds.createNode("decomposeMatrix", name=f"{self.side}_{part}Bendy01_DPM", ss=True)
            dcp2 = cmds.createNode("decomposeMatrix", name=f"{self.side}_{part}Bendy02_DPM", ss=True)
            cmds.connectAttr(f"{upper}.worldMatrix[0]", f"{dcp1}.inputMatrix")
            cmds.connectAttr(f"{dcp1}.outputTranslate", f"{curve}.controlPoints[0]")
            cmds.connectAttr(f"{lower}.worldMatrix[0]", f"{dcp2}.inputMatrix")
            cmds.connectAttr(f"{dcp2}.outputTranslate", f"{curve}.controlPoints[1]")

            hooks = []
            for idx, label in enumerate(["Root", "Mid", "Tip"]):
                jnt = cmds.joint(name=f"{self.side}_{part}LowerBendy{label}Hook_JNT")
                cmds.setAttr(jnt + ".inheritsTransform", 0)
                u_value = [0.001, 0.5, 0.999][idx]

                mpath = cmds.createNode("motionPath", name=f"{self.side}_{part}LowerBendy{label}Hook_MPA", ss=True)
                flm = cmds.createNode("floatMath", name=f"{self.side}_{part}LowerBendy{label}Hook_FLM", ss=True)
                flc = cmds.createNode("floatConstant", name=f"{self.side}_{part}LowerBendy{label}Hook_FLC", ss=True)

                cmds.setAttr(f"{flc}.inFloat", u_value)
                cmds.connectAttr(f"{flc}.outFloat", f"{flm}.floatA")
                cmds.connectAttr(f"{twist_start}.rotateX", f"{flm}.floatB")
                cmds.setAttr(f"{flm}.operation", 2)

                cmds.connectAttr(f"{curve}.worldSpace[0]", f"{mpath}.geometryPath")
                cmds.connectAttr(f"{flm}.outFloat", f"{mpath}.frontTwist")
                cmds.connectAttr(f"{flc}.outFloat", f"{mpath}.uValue")
                cmds.connectAttr(f"{mpath}.allCoordinates", f"{jnt}.translate")
                cmds.connectAttr(f"{mpath}.rotate", f"{jnt}.rotate")
                cmds.connectAttr(f"{upper}.worldMatrix[0]", f"{mpath}.worldUpMatrix")
                cmds.setAttr(f"{mpath}.fractionMode", True)
                cmds.setAttr(f"{mpath}.frontAxis", 0)
                cmds.setAttr(f"{mpath}.upAxis", 1)
                cmds.setAttr(f"{mpath}.worldUpType", 2)

                if self.side == "R_":
                    cmds.setAttr(f"{mpath}.inverseFront", True)

                cmds.parent(jnt, bendy_seg_grp)
                hooks.append(jnt)

            # NURBS & Offset Curve
            bendy_result = self._build_bendy_curve(upper, lower, part, name, bendy_seg_grp, hooks, fk_ctls[0])
            bendy_joints.extend(bendy_result["bendy_joints"])

        return {"bendy_joints": bendy_joints}


    def _build_bendy_curve(self, upper_joint, lower_joint, part, name, parent_grp, hook_joints, root_ctl):
        side = self.side
        skin_joints = []

        p1 = cmds.xform(upper_joint, q=True, ws=True, t=True)
        p2 = cmds.xform(lower_joint, q=True, ws=True, t=True)
        curve = cmds.curve(p=(p1, p2), d=1, n=f"{side}_{part}Bendy_CRV")
        cmds.rebuildCurve(curve, ch=False, rpo=True, s=2, d=1)

        bezier = cmds.nurbsCurveToBezier()[0]
        cmds.delete(bezier, ch=True)
        cmds.select(f"{curve}.cv[6]", f"{curve}.cv[0]"); cmds.bezierAnchorPreset(p=2)
        cmds.select(f"{curve}.cv[3]"); cmds.bezierAnchorPreset(p=1)

        curve_dup = cmds.duplicate(curve, name=f"{side}_{part}BendyDupe_CRV")[0]
        offset_curve, offset_node = cmds.offsetCurve(
            curve_dup, ch=True, rn=False, cb=2, st=True, cl=True, d=1.5, tol=0.01, sd=0,
            ugn=False, name=f"{side}_{part}BendyOffset_CRV", normal=(0,0,1)
        )
        offset_node = cmds.rename(offset_node, f"{side}_{part}Bendy_OFC")
        cmds.setAttr(f"{offset_node}.useGivenNormal", 1)
        cmds.setAttr(f"{offset_node}.subdivisionDensity", 0)
        cmds.setAttr(f"{offset_node}.distance", 20)
        cmds.connectAttr(f"{bezier}.worldSpace[0]", f"{offset_node}.inputCurve", f=True)
        cmds.delete(curve_dup)

        ctl, ctl_grp = curve_tool.controller_creator(f"{side}_{part}Bendy", suffixes=["GRP"])
        cmds.parent(ctl_grp[0], self.controllers_trn)
        cmds.delete(cmds.parentConstraint(hook_joints[1], ctl_grp[0], mo=False))
        bendy_jnt = cmds.duplicate(hook_joints[1], renameChildren=True, parentOnly=True, name=f"{side}_{part}Bendy_JNT")[0]
        cmds.parentConstraint(ctl, bendy_jnt, mo=False)
        cmds.scaleConstraint(ctl, bendy_jnt, mo=False)
        cmds.parentConstraint(hook_joints[1], ctl_grp[0], mo=False)
        self._lock_attr(ctl, ["scaleY", "scaleZ", "visibility"])

        skc = cmds.skinCluster(bendy_jnt, hook_joints[0], hook_joints[2], curve, tsb=True, omi=False, rui=False,
                               name=f"{side}_{part}Bendy_SKN")[0]
        cmds.skinPercent(skc, f"{curve}.cv[2]", transformValue=(bendy_jnt, 1))
        cmds.skinPercent(skc, f"{curve}.cv[3]", transformValue=(bendy_jnt, 1))
        cmds.skinPercent(skc, f"{curve}.cv[4]", transformValue=(bendy_jnt, 1))
        cmds.skinPercent(skc, f"{curve}.cv[0]", transformValue=(hook_joints[0], 1))
        cmds.skinPercent(skc, f"{curve}.cv[6]", transformValue=(hook_joints[2], 1))

        offset_skc = cmds.skinCluster(bendy_jnt, hook_joints[0], hook_joints[2], offset_curve, tsb=True, omi=False, rui=False,
                                      name=f"{side}_{part}BendyOffset_SKN")[0]
        for cv in [2, 3, 4]:
            cmds.skinPercent(offset_skc, f"{offset_curve}.cv[{cv}]", transformValue=(bendy_jnt, 1))
        cmds.skinPercent(offset_skc, f"{offset_curve}.cv[0]", transformValue=(hook_joints[0], 1))
        cmds.skinPercent(offset_skc, f"{offset_curve}.cv[6]", transformValue=(hook_joints[2], 1))

        # Create bendy JNTs along curve
        helper = cmds.createNode("transform", name=f"{side}_{part}BendyHelperAim04_TRN", ss=True)
        cmds.setAttr(f"{helper}.inheritsTransform", 0)
        cmds.select(clear=True)

        bendy_joints = []
        up_trns = []
        for i, val in enumerate([0, 0.25, 0.5, 0.75, 0.95]):
            jnt = cmds.joint(name=f"{side}_{part}Bendy0{i}_JNT", rad=20)
            mp = cmds.createNode("motionPath", name=f"{side}_{part}Bendy0{i}_MPA", ss=True)
            cmds.setAttr(f"{mp}.fractionMode", True)
            cmds.setAttr(f"{mp}.uValue", val)
            cmds.connectAttr(f"{curve}.worldSpace[0]", f"{mp}.geometryPath")
            cmds.connectAttr(f"{mp}.allCoordinates", f"{jnt}.translate")
            cmds.parent(jnt, self.skinning_trn)
            bendy_joints.append(jnt)
            if i == 3:
                cmds.connectAttr(f"{mp}.allCoordinates", f"{helper}.translate")

        up_grp = cmds.createNode("transform", name=f"{side}_{part}BendyUpModule_GRP", p=parent_grp, ss=True)
        for i, val in enumerate([0, 0.25, 0.5, 0.75, 0.95]):
            up_trn = cmds.createNode("transform", name=f"{side}_{part}BendyUp0{i}_TRN")
            cmds.setAttr(f"{up_trn}.inheritsTransform", 0)
            mp = cmds.createNode("motionPath", name=f"{side}_{part}BendyUp0{i}_MPA", ss=True)
            cmds.setAttr(f"{mp}.fractionMode", True)
            cmds.setAttr(f"{mp}.uValue", val)
            cmds.connectAttr(f"{offset_curve}.worldSpace[0]", f"{mp}.geometryPath")
            cmds.connectAttr(f"{mp}.allCoordinates", f"{up_trn}.translate")
            cmds.parent(up_trn, up_grp)
            up_trns.append(up_trn)

        # Aim setup
        aim = (1, 0, 0) if side == "L" else (-1, 0, 0)
        rev_aim = (-1, 0, 0) if side == "L" else (1, 0, 0)
        up = (0, 1, 0)

        for i in range(len(bendy_joints)):
            if i != 4:
                cmds.aimConstraint(bendy_joints[i+1], bendy_joints[i], aimVector=aim, upVector=up,
                                   worldUpType="object", worldUpObject=up_trns[i], mo=False)
            else:
                cmds.aimConstraint(helper, bendy_joints[i], aimVector=rev_aim, upVector=up,
                                   worldUpType="object", worldUpObject=up_trns[i], mo=False)

        cmds.parent(curve, parent_grp)
        cmds.parent(offset_curve, parent_grp)
        cmds.parent(helper, parent_grp)

        return {
            "bendy_joints": bendy_joints,
            "curve": curve,
            "offset_curve": offset_curve,
            "skc": skc,
            "offset_skc": offset_skc,
            "bezier": bezier
        }

    def wave_handle(self, beziers, skc, bezier_off, offset_skc):
        dupe_beziers = []
        dupe_beziers_offset = []

        for i, bezier in enumerate(beziers):
            dupe = cmds.duplicate(bezier, name=bezier.replace("_CRV", "Dupe_CRV"))[0]
            dupe_off = cmds.duplicate(bezier_off[i], name=bezier_off[i].replace("_CRV", "Dupe_CRV"))[0]
            cmds.delete(dupe, ch=True)
            cmds.delete(dupe_off, ch=True)
            dupe_beziers.append(dupe)
            dupe_beziers_offset.append(dupe_off)

        # Create the wave deformer
        wave = cmds.nonLinear(dupe_beziers, dupe_beziers_offset, type="wave", name=f"{self.side}_fingerWave_HDL")
        wave_handle = wave[1]
        cmds.parent(wave_handle, cmds.listRelatives(dupe_beziers[0], parent=True, fullPath=True))

        # Center the wave deformer between joints
        positions = [cmds.xform(jnt, q=True, ws=True, t=True) for jnt in self.blend_chain]
        mid_pos = [sum(coords) / len(coords) for coords in zip(*positions)]
        cmds.xform(wave_handle, ws=True, t=mid_pos)

        # Set approximate radius based on joint spacing
        relative_x = [cmds.getAttr(jnt + ".tx") for jnt in self.blend_chain[1:]]
        if len(relative_x) == 3:
            radius = abs(sum(relative_x) / 2)
        else:
            radius = 5
        for axis in "XYZ":
            cmds.setAttr(f"{wave_handle}.scale{axis}", radius)

        # BlendShapes
        for i in range(3):
            bs = cmds.blendShape(dupe_beziers[i], beziers[i], name=f"{self.side}_bendyWave{i}_BS")[0]
            bs_off = cmds.blendShape(dupe_beziers_offset[i], bezier_off[i], name=f"{self.side}_bendyOffsetWave{i}_BS")[0]

            cmds.connectAttr(f"{self.settings_curve_ctl}.waveEnvelop", f"{bs}.{dupe_beziers[i]}")
            cmds.connectAttr(f"{self.settings_curve_ctl}.waveEnvelop", f"{bs_off}.{dupe_beziers_offset[i]}")

            # Reorder deformers (ensure blendShape is evaluated after skinCluster)
            cmds.reorderDeformers(skc[i], bs, beziers[i])
            cmds.reorderDeformers(offset_skc[i], bs_off, bezier_off[i])

        # Wave deformer attributes: combine global + finger control
        for attr in ["amplitude", "wavelength", "offset", "dropoff"]:
            pma = cmds.createNode("plusMinusAverage", name=f"{self.side}_wave_{attr}_PMA", ss=True)
            cmds.connectAttr(f"{self.settings_curve_ctl}.global{attr.capitalize()}", f"{pma}.input1D[0]", f=True)
            cmds.connectAttr(f"{self.fk_ctl_list[0]}.{attr}", f"{pma}.input1D[1]", f=True)
            cmds.connectAttr(f"{pma}.output1D", f"{wave[0]}.{attr}", f=True)
