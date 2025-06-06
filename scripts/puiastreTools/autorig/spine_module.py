"""
Finger module for dragon rigging system
"""
import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import data_export
from importlib import reload
reload(data_export)    

class SpineModule():
    """
    Class to create a spine module in a Maya rigging setup.
    This module handles the creation of spine joints, controllers, and various systems such as stretch, reverse, offset, squash, and volume preservation.
    """
    def __init__(self):
        """
        Initializes the SpineModule class, setting up paths and data exporters.
        
        Args:
            self: Instance of the SpineModule class.
        """
        
        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")


    def make(self):
        """
        Creates the spine module, including the spine chain, controllers, and various systems.

        Args:
            self: Instance of the SpineModule class.
        """

        self.module_trn = cmds.createNode("transform", name=f"C_spineModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"C_spineControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"C_spineSkinning_GRP", ss=True, p=self.skel_grp)

        self.create_chain()
        self.spine_module()
        self.stretch_system()
        self.reverse_system()
        self.offset_system()
        self.squash_system()
        self.volume_preservation_system()

        self.data_exporter.append_data(f"C_spineModule", 
                                    {"lastSpineJnt": self.sub_spine_joints[-1],
                                    "localChest": self.localChest_ctl,
                                    "localHip": self.spine_hip_ctl,
                                    "body" : self.body_ctl,
                                    "body_grp" : self.body_ctl_grp
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

    def create_chain(self):
        """
        Creates the spine joint chain by importing guides and parenting the first joint to the module transform.

        Args:
            self: Instance of the SpineModule class.
        """
        
        self.blend_chain = guides_manager.guide_import(
            joint_name=f"C_spine01_JNT",
            all_descendents=True)
        cmds.parent(self.blend_chain[0], self.module_trn)

    def spine_module(self):
        """
        Creates the spine module by setting up the IK spline handle, controllers, and constraints.

        Args:
            self: Instance of the SpineModule class.
        """

        positions = [cmds.xform(joint, query=True, worldSpace=True, translation=True) for joint in (self.blend_chain[0], self.blend_chain[-1])]
        self.ik_curve = cmds.curve(degree=1, point=positions, name="C_spine_CRV")
        cmds.rebuildCurve(self.ik_curve, rpo=True, rt=0, end=True, kr=False, kcp=False, kep=True, kt=True, fr=False, s=1, d=2, tol=0.01)
        cmds.delete(self.ik_curve, ch=True)
        self.ik_sc = cmds.ikHandle(sj=self.blend_chain[0], ee=self.blend_chain[-1], sol="ikSplineSolver", n="C_spine_HDL", curve=self.ik_curve, createCurve=False, parentCurve=False) [0]# Create an IK spline handle using the existing self.ik_curve
        self.curve_shape = cmds.listRelatives(self.ik_curve, shapes=True)[0]

        cmds.parent(self.ik_curve, self.ik_sc, self.module_trn) 

        self.spine_ctl = []
        self.spine_grp = []

        for i in range(1, 4):
            value = 0 if i == 1 else (-1 if i == 3 else 0)
            if i == 1 or i == 3:
                ctl, ctl_grp = curve_tool.controller_creator(f"C_spine0{i}", suffixes = ["GRP"])
                
            else:
                ctl, ctl_grp = curve_tool.controller_creator(f"C_spineTan", suffixes = ["GRP", "SPC"])
                cmds.addAttr(ctl, shortName="spaceSwitchSep", niceName="spaceSwitch_____", enumName="_____",attributeType="enum", keyable=True)
                cmds.setAttr(ctl+".spaceSwitchSep", channelBox=True, lock=True)
                cmds.addAttr(ctl, shortName="spineFollow", niceName="Spine Follow", maxValue=1, minValue=0, defaultValue=0, keyable=True)


            self.lock_attr(ctl)
            cmds.matchTransform(ctl_grp[0], self.blend_chain[value], pos=True, rot=True)
            cv_point = cmds.pointPosition(f"{self.curve_shape}.cv[{i-1}]", w=True)
            cmds.xform(ctl_grp, ws=True, translation=cv_point)
            

            self.spine_ctl.append(ctl) 
            self.spine_grp.append(ctl_grp) 

            dcm = cmds.createNode("decomposeMatrix", n=f"C_spine0{i}_DCM") 
            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{dcm}.inputMatrix")
            cmds.connectAttr(f"{dcm}.outputTranslate", f"{self.curve_shape}.controlPoints[{i-1}]")

        cmds.parent(self.spine_grp[0][0], self.controllers_trn)
        cmds.parent(self.spine_grp[2][0], self.spine_ctl[0])        
        cmds.parent(self.spine_grp[1][0], self.controllers_trn)

        parent = cmds.parentConstraint(self.spine_ctl[0], self.spine_ctl[2], self.spine_grp[1][1], mo=True)[0]

        cmds.connectAttr(f"{self.spine_ctl[1]}.spineFollow", f"{parent}.{self.spine_ctl[0]}W0")
        rev = cmds.createNode("reverse", n="C_spineRev")
        cmds.connectAttr(f"{self.spine_ctl[1]}.spineFollow", f"{rev}.inputX")
        cmds.connectAttr(f"{rev}.outputX", f"{parent}.{self.spine_ctl[2]}W1")

        self.chest_fix = cmds.joint(name = "C_localChest_JNT")
        cmds.delete(cmds.parentConstraint(self.spine_ctl[-1], self.chest_fix, mo=False))
        cmds.parent(self.chest_fix, self.module_trn)
        self.localChest_ctl, localChest_grp = curve_tool.controller_creator(f"C_localChest", suffixes = ["GRP"])
        cmds.matchTransform(localChest_grp[0], self.blend_chain[-1], pos=True, rot=True)
        cmds.pointConstraint(self.blend_chain[-1], localChest_grp[0], mo=False)
        cmds.orientConstraint(self.spine_ctl[2], localChest_grp[0], mo=True)
        cmds.parentConstraint(self.localChest_ctl, self.chest_fix, mo=True)

        self.spine_hip_ctl, self.spine_hip_ctl_grp = curve_tool.controller_creator(f"C_localHip", suffixes = ["GRP"])
        position, rotation = guides_manager.guide_import(joint_name=f"C_localHip")

        cmds.matchTransform(self.spine_hip_ctl_grp[0], self.blend_chain[0], pos=True, rot=True)
        cmds.xform(self.spine_hip_ctl_grp[0], ws=True, translation=position)
        
        self.lock_attr(self.spine_hip_ctl)
        self.lock_attr(self.localChest_ctl)

        self.body_ctl, self.body_ctl_grp = curve_tool.controller_creator(f"C_body", suffixes = ["GRP"])
        cmds.matchTransform(self.body_ctl_grp[0], self.spine_grp[0][0])

        cmds.parent(self.spine_grp[0][0], self.body_ctl) 

        self.lock_attr(self.body_ctl)
        
        # movable_ctl = cmds.circle(n="C_movablePivot_CTL", ch=False, normal=(0,1,0))[0] 
        movable_ctl, movable_ctl_grp = curve_tool.controller_creator(f"C_movablePivot", suffixes = [])
        cmds.matchTransform(movable_ctl, self.spine_grp[0][0]) 
        cmds.parent(movable_ctl, self.body_ctl) 

        cmds.connectAttr(f"{movable_ctl}.translate", f"{self.body_ctl}.rotatePivot") 
        cmds.connectAttr(f"{movable_ctl}.translate", f"{self.body_ctl}.scalePivot") 

        dummy_body = cmds.createNode("transform", n="C_dummyBody_TRN", p=self.body_ctl) 
        cmds.parentConstraint(dummy_body, self.spine_hip_ctl_grp[0], mo=True) 

        self.localHip = cmds.duplicate(self.blend_chain[0], n=f"C_localHip_JNT", parentOnly=True)
        cmds.scaleConstraint(self.controllers_trn, self.localHip) 

        cmds.parent(localChest_grp[0], self.spine_hip_ctl_grp[0], self.body_ctl_grp[0], self.controllers_trn)

        cmds.parentConstraint(self.spine_hip_ctl, self.localHip)

        cmds.setAttr(f"{self.ik_sc}.dTwistControlEnable", 1) 
        cmds.setAttr(f"{self.ik_sc}.dWorldUpType", 4)
        cmds.setAttr(f"{self.ik_sc}.dForwardAxis", 4)
        cmds.setAttr(f"{self.ik_sc}.dWorldUpAxis", 0)
        cmds.setAttr(f"{self.ik_sc}.dWorldUpVectorX", 0)
        cmds.setAttr(f"{self.ik_sc}.dWorldUpVectorY", 1)
        cmds.setAttr(f"{self.ik_sc}.dWorldUpVectorZ", 0)
        cmds.setAttr(f"{self.ik_sc}.dWorldUpVectorEndX", 0)
        cmds.setAttr(f"{self.ik_sc}.dWorldUpVectorEndY", 1)
        cmds.setAttr(f"{self.ik_sc}.dWorldUpVectorEndZ", 0)
        cmds.connectAttr(f"{self.spine_ctl[0]}.worldMatrix[0]", f"{self.ik_sc}.dWorldUpMatrix")
        cmds.connectAttr(f"{self.spine_ctl[2]}.worldMatrix[0]", f"{self.ik_sc}.dWorldUpMatrixEnd")

    def stretch_system(self):
        """
        Creates the stretch system for the spine module, including attributes and nodes for stretch and squash functionality.
        
        Args:
            self: Instance of the SpineModule class.
        """
           
        cmds.addAttr(self.body_ctl, shortName="STRETCH", niceName="STRETCH_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.body_ctl+".STRETCH", channelBox=True, lock=True)
        cmds.addAttr(self.body_ctl, shortName="stretch", niceName="Stretch", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(self.body_ctl, shortName="stretchMin", niceName="Stretch Min", maxValue=1, minValue=0.001,defaultValue=0.8, keyable=True)
        cmds.addAttr(self.body_ctl, shortName="stretchMax", niceName="Stretch Max", minValue=1,defaultValue=1.2, keyable=True)
        cmds.addAttr(self.body_ctl, shortName="offset", niceName="Offset", maxValue=1, minValue=0,defaultValue=0, keyable=True)

        cmds.addAttr(self.body_ctl, shortName="SQUASH", niceName="SQUASH_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.body_ctl+".SQUASH", channelBox=True, lock=True)
        cmds.addAttr(self.body_ctl, shortName="volumePreservation", niceName="Volume Preservation", maxValue=1, minValue=0,defaultValue=1, keyable=True)
        cmds.addAttr(self.body_ctl, shortName="falloff", niceName="Falloff", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(self.body_ctl, shortName="maxPos", niceName="Max Pos", maxValue=1, minValue=0,defaultValue=0.5, keyable=True)

        cmds.addAttr(self.body_ctl, shortName="attachedFk", niceName="FK_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.body_ctl+".attachedFk", channelBox=True, lock=True)
        cmds.addAttr(self.body_ctl, shortName="attachedFKVis", niceName="Attached FK Visibility", attributeType="bool", keyable=True)


        nodes_to_create = {
            "C_spine_CIN": ("curveInfo", None), #0
            "C_spineStretchFactor_FLM": ("floatMath", 3), #1
            "C_spineStretchFactor_CLM": ("clamp", None), #2
            "C_spineInitialArcLegth_FLM": ("floatMath", 2), #3
            "C_spineBaseStretch_FLC": ("floatConstant", None), #4
            "C_spineStretch_BTA": ("blendTwoAttr", None), # 5
            "C_spineStretchValue_FLM": ("floatMath", 2),# 6
        }

        created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        cmds.connectAttr(created_nodes[0] + ".arcLength", created_nodes[1]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[2]+".inputR")
        cmds.connectAttr(created_nodes[3] + ".outFloat", created_nodes[1]+".floatB")
        cmds.connectAttr(created_nodes[2] + ".outputR", created_nodes[5]+".input[1]")
        cmds.connectAttr(created_nodes[4] + ".outFloat", created_nodes[5]+".input[0]")
        cmds.connectAttr(created_nodes[5] + ".output", created_nodes[6]+".floatA")
        cmds.setAttr(created_nodes[4]+".inFloat", 1)
        cmds.connectAttr(f"{self.body_ctl}.stretch", created_nodes[5]+".attributesBlender")
        cmds.connectAttr(f"{self.body_ctl}.stretchMax", created_nodes[2]+".maxR")
        cmds.connectAttr(f"{self.body_ctl}.stretchMin", created_nodes[2]+".minR")
        cmds.connectAttr(f"{self.ik_curve}.worldSpace[0]", created_nodes[0]+".inputCurve")
        cmds.setAttr(created_nodes[3]+".floatB", cmds.getAttr(created_nodes[0]+".arcLength"))
        cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", created_nodes[3]+".floatA")
        cmds.setAttr(created_nodes[6]+".floatB", cmds.getAttr(f"{self.blend_chain[2]}.translateZ"))
        for joint in self.blend_chain[1:]:
            cmds.connectAttr(created_nodes[6]+".outFloat", f"{joint}.translateZ")

        self.stretch_float_math = created_nodes[6]

    def reverse_system(self):
        """
        Creates the reverse system for the spine module, including a reversed curve and an IK spline handle for the reversed chain.

        Args:
            self: Instance of the SpineModule class.
        """

        reversed_curve = cmds.reverseCurve(self.ik_curve, name="C_spineReversed_CRV",  ch=True, rpo=False)
        cmds.parent(reversed_curve[0], self.module_trn ) 
        reversed_joints = cmds.duplicate(self.blend_chain[0], renameChildren=True)

        self.reverse_chain = []
        for i, joint in enumerate(reversed(reversed_joints)):
            if "effector" in joint:
                reversed_joints.remove(joint)
                cmds.delete(joint)
                
            else:
                renamed_joint = cmds.rename(joint, f"C_spineReversed0{i}_JNT")
                if i != 5:
                    cmds.parent(renamed_joint, world=True)
                self.reverse_chain.append(renamed_joint) 
        for i, joint in enumerate(self.reverse_chain):
            if i != 0:
                cmds.parent(joint, self.reverse_chain[i-1])


        cmds.parent(self.reverse_chain[0], self.module_trn)
        hdl = cmds.ikHandle(sj=self.reverse_chain[0], ee=self.reverse_chain[-1], sol="ikSplineSolver", n="C_spineReversed_HDL", parentCurve=False, curve=reversed_curve[0], createCurve=False) # Create an IK spline handle
        cmds.parent(hdl[0], self.module_trn) 


        negate_flm = cmds.createNode("floatMath", n="C_spineNegateStretchValue_FLM")
        cmds.setAttr("C_spineNegateStretchValue_FLM.operation", 2)
        cmds.setAttr("C_spineNegateStretchValue_FLM.floatB", -1)
        cmds.connectAttr(self.stretch_float_math+".outFloat", f"{negate_flm}.floatA")

        for joint in self.reverse_chain[1:]:
            cmds.connectAttr(negate_flm+".outFloat", f"{joint}.translateZ")

    def offset_system(self):
        """
        Creates the offset system for the spine module, including nodes for decomposing matrices, nearest point on curve, float constants, and blend two attributes.

        Args:
            self: Instance of the SpineModule class.
        """
        nodes_to_create = {
            "C_spineReversed05_DCM": ("decomposeMatrix", None),
            "C_spineOffset_NPC": ("nearestPointOnCurve", None),
            "C_spineOffsetInitialValue_FLC": ("floatConstant", None),
            "C_spineOffset_BTA": ("blendTwoAttr", None),
        }

        created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        cmds.connectAttr(created_nodes[0] + ".outputTranslate", created_nodes[1]+".inPosition")
        cmds.connectAttr(created_nodes[1] + ".parameter", created_nodes[3]+".input[1]")
        cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[3]+".input[0]")
        cmds.connectAttr(f"{self.body_ctl}.offset", created_nodes[3]+".attributesBlender")
        cmds.connectAttr(f"{self.reverse_chain[-1]}.worldMatrix[0]", created_nodes[0]+".inputMatrix")
        cmds.connectAttr(f"{self.curve_shape}.worldSpace[0]", created_nodes[1]+".inputCurve")
        cmds.connectAttr(f"{created_nodes[3]}.output", self.ik_sc +".offset")
        cmds.setAttr(created_nodes[2]+".inFloat", 0)

    def squash_system(self):
        """
        Creates the squash system for the spine module, including a transform node for spine settings, attributes for stretch and squash, and a curve for squash deformation.

        Args:
            self: Instance of the SpineModule class.
        """

        translations = []

        self.spine_settings_trn = cmds.createNode("transform", n="C_spineSettings_TRN", parent=self.module_trn)
        for attribute in ["translateX","translateY","translateZ","rotateX","rotateY","rotateZ","scaleX","scaleY","scaleZ","visibility"]:
            cmds.setAttr(f"{self.spine_settings_trn}.{attribute}", lock=True, keyable=False, channelBox=False)

        cmds.addAttr(self.spine_settings_trn, shortName="maxStretchLength", niceName="Max Stretch Length", minValue=1,defaultValue=2, keyable=True)
        cmds.addAttr(self.spine_settings_trn, shortName="minStretchLength", niceName="Min Stretch Length", maxValue=1, minValue=0.001,defaultValue=0.5, keyable=True)
        cmds.addAttr(self.spine_settings_trn, shortName="maxStretchEffect", niceName="Max Stretch Effect", minValue=1,defaultValue=2, keyable=True)
        cmds.addAttr(self.spine_settings_trn, shortName="minStretchEffect", niceName="Min Stretch Effect", maxValue=1, minValue=0.001,defaultValue=0.5, keyable=True)
        
        cmds.addAttr(self.spine_settings_trn, shortName="VolumeSep", niceName="Volume_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.spine_settings_trn+".VolumeSep", channelBox=True, lock=True)
        
        for i in range(len(self.blend_chain)):
            if i == 0:
                default_value = 0.05
            if i == len(self.blend_chain)-1:
                default_value = 0.95
            else:
                default_value = (1/(len(self.blend_chain)-1))*i
            cmds.addAttr(self.spine_settings_trn, shortName=f"spine0{i+1}SquashPercentage", niceName="Spine01 Squash Percentage", maxValue=1, minValue=0,defaultValue=default_value, keyable=True)
        
        for joint in self.blend_chain:
            translation = cmds.xform(f"{joint}", query=True, worldSpace=True, translation=True)
            translations.append(translation)
        squash_curve = cmds.curve(p=translations, d=1, n="C_spineSquash_CRV")
        cmds.parent(squash_curve, self.module_trn)
        

        for i, joint in enumerate(self.blend_chain):
            dcm = cmds.createNode("decomposeMatrix", n=f"C_{joint}Squash_DCM")
            cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{dcm}.inputMatrix")
            cmds.connectAttr(f"{dcm}.outputTranslate", f"{squash_curve}.controlPoints[{i}]")

        nodes_to_create = {
            "C_spineSquash_CIN": ("curveInfo", None),
            "C_spineSquashBaseLength_FLM": ("floatMath", 2),
            "C_spineSquashFactor_FLM": ("floatMath", 3),
        }

        created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            created_nodes.append(node)
            if operation is not None:   
                cmds.setAttr(f'{node}.operation', operation)

        cmds.connectAttr(f"{squash_curve}.worldSpace[0]", created_nodes[0]+".inputCurve")
        cmds.connectAttr(created_nodes[0] + ".arcLength", created_nodes[2]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[2]+".floatB") 
        cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", created_nodes[1]+".floatA") 
        cmds.setAttr(created_nodes[1]+".floatB", cmds.getAttr(created_nodes[0]+".arcLength"))

        self.squash_factor_fml = created_nodes[2]


    def volume_preservation_system(self):
        """
        Creates the volume preservation system for the spine module, including remap value nodes, float math nodes, and connections to squash joints.

        Args:
            self: Instance of the SpineModule class.
        """
                
        squash_joints = self.attached_fk()
       
        nodes_to_create = {
            "C_spineVolumeLowBound_RMV": ("remapValue", None),# 0
            "C_spineVolumeHighBound_RMV": ("remapValue", None),# 1
            "C_spineVolumeLowBoundNegative_FLM": ("floatMath", 1),# 2
            "C_spineVolumeHighBoundNegative_FLM": ("floatMath", 1),# 3
            "C_spineVolumeSquashDelta_FLM": ("floatMath", 1), # 4
            "C_spineVolumeStretchDelta_FLM": ("floatMath", 1), # 5
        } 

        main_created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            main_created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)
        values = [0.001, 0.999]
        for i in range(0,2):
            cmds.connectAttr(f"{self.body_ctl}.falloff", f"{main_created_nodes[i]}.inputValue")
            cmds.connectAttr(f"{self.body_ctl}.maxPos", f"{main_created_nodes[i]}.outputMin")
            cmds.setAttr(f"{main_created_nodes[i]}.outputMax", values[i])
            cmds.connectAttr(f"{main_created_nodes[i]}.outValue", f"{main_created_nodes[i+2]}.floatB")

        cmds.setAttr(f"{main_created_nodes[2]}.floatA", 0)
        cmds.setAttr(f"{main_created_nodes[3]}.floatA", 2)
        cmds.setAttr(f"{main_created_nodes[4]}.floatB", 1)
        cmds.setAttr(f"{main_created_nodes[5]}.floatA", 1)
        cmds.connectAttr(f"{self.spine_settings_trn}.maxStretchEffect", f"{main_created_nodes[4]}.floatA")
        cmds.connectAttr(f"{self.spine_settings_trn}.minStretchEffect", f"{main_created_nodes[5]}.floatB")

        for i, joint in enumerate(squash_joints):
            nodes_to_create = {
                f"C_spineVolumeSquashFactor0{i+1}_FLM": ("floatMath", 2), # 0
                f"C_spineVolumeStretchFactor0{i+1}_FLM": ("floatMath", 2), # 1
                f"C_spineVolumeStretchFullValue0{i+1}_FLM": ("floatMath", 1), # 2
                f"C_spineVolumeSquashFullValue0{i+1}_FLM": ("floatMath", 0), # 3
                f"C_spineVolume0{i+1}_RMV": ("remapValue", None), # 4
                f"C_spineVolumeFactor0{i+1}_RMV": ("remapValue", None), # 5
            }

            created_nodes = []
            for node_name, (node_type, operation) in nodes_to_create.items():
                node = cmds.createNode(node_type, name=node_name)
                created_nodes.append(node)
                if operation is not None:
                    cmds.setAttr(f'{node}.operation', operation)

            cmds.connectAttr(f"{self.spine_settings_trn}.spine0{i+1}SquashPercentage", f"{created_nodes[5]}.inputValue")
            cmds.connectAttr(f"{main_created_nodes[2]}.outFloat", f"{created_nodes[5]}.value[0].value_Position")
            cmds.connectAttr(f"{main_created_nodes[0]}.outValue", f"{created_nodes[5]}.value[1].value_Position")
            cmds.connectAttr(f"{main_created_nodes[1]}.outValue", f"{created_nodes[5]}.value[2].value_Position")
            cmds.connectAttr(f"{main_created_nodes[3]}.outFloat", f"{created_nodes[5]}.value[3].value_Position")


            cmds.connectAttr(created_nodes[0] + ".outFloat", created_nodes[3]+".floatA")
            cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[2]+".floatB")
            cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[4]+".value[2].value_FloatValue")
            cmds.connectAttr(created_nodes[3] + ".outFloat", created_nodes[4]+".value[0].value_FloatValue")
            cmds.connectAttr(self.squash_factor_fml + ".outFloat", created_nodes[4]+".inputValue")
            cmds.setAttr(f"{created_nodes[3]}.floatB", 1)
            cmds.setAttr(f"{created_nodes[2]}.floatA", 1)

            cmds.connectAttr(f"{main_created_nodes[4]}.outFloat", created_nodes[0]+".floatA")
            cmds.connectAttr(f"{main_created_nodes[5]}.outFloat", created_nodes[1]+".floatA")
            cmds.connectAttr(f"{created_nodes[5]}.outValue", created_nodes[0]+".floatB")
            cmds.connectAttr(f"{created_nodes[5]}.outValue", created_nodes[1]+".floatB")

            cmds.connectAttr(f"{self.spine_settings_trn}.maxStretchLength", f"{created_nodes[4]}.value[2].value_Position")
            cmds.connectAttr(f"{self.spine_settings_trn}.minStretchLength", f"{created_nodes[4]}.value[0].value_Position")   
            cmds.connectAttr(f"{created_nodes[4]}.outValue",f"{joint}.scaleY")   
            cmds.connectAttr(f"{created_nodes[4]}.outValue",f"{joint}.scaleZ")   


            values = [-1, 1, 1, -1]
            for i in range(0,4):
                cmds.setAttr(f"{created_nodes[5]}.value[{i}].value_Interp", 2)
                cmds.setAttr(f"{created_nodes[5]}.value[{i}].value_FloatValue", values[i])

    def attached_fk(self):
        """
        Creates the attached FK controllers for the spine module, including sub-spine controllers and joints.

        Args:
            self: Instance of the SpineModule class.
        Returns:
            list: A list of sub-spine joint names created for the attached FK system.
        """
        
        main_spine_joint = []
        for joint in self.blend_chain:
            if "effector" in joint:
                    self.blend_chain.remove(joint)
            else:
                main_spine_joint.append(f"{joint}")

        ctls_sub_spine = []
        sub_spine_ctl_trn = cmds.createNode("transform", n="C_subSpineControllers_GRP", parent=self.masterWalk_ctl)
        cmds.setAttr(f"{sub_spine_ctl_trn}.inheritsTransform", 0)
        cmds.connectAttr(f"{self.body_ctl}.attachedFKVis", f"{sub_spine_ctl_trn}.visibility")
        for i, joint in enumerate(main_spine_joint):
            
            ctl, controller_grp = curve_tool.controller_creator(f"C_subSpineFk0{i+1}", suffixes = ["GRP"])
            self.lock_attr(ctl)
                

            cmds.parent(controller_grp[0], sub_spine_ctl_trn)
            if i == 0:
                cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{controller_grp[0]}.offsetParentMatrix")
            else:
                mmt = cmds.createNode("multMatrix", n=f"C_spineSubAttachedFk0{i+1}_MMT")
                if i == len(self.blend_chain)-1:
                    cmds.connectAttr(f"{self.chest_fix}.worldMatrix[0]", f"{mmt}.matrixIn[0]")
                else:
                    cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{mmt}.matrixIn[0]")
                cmds.connectAttr(f"{main_spine_joint[i-1]}.worldInverseMatrix[0]", f"{mmt}.matrixIn[1]")
                cmds.connectAttr(f"{ctls_sub_spine[i-1]}.worldMatrix[0]", f"{mmt}.matrixIn[2]")
                cmds.connectAttr(f"{mmt}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix")
            ctls_sub_spine.append(ctl)

        self.sub_spine_joints = []
        for i, joint in enumerate(main_spine_joint):
            cmds.select(clear=True)
            new_joint = cmds.joint(joint, name=f"C_subSpineFk0{i+1}_JNT")
            cmds.setAttr(f"{new_joint}.inheritsTransform", 0)

            cmds.parent(new_joint, self.skinning_trn)

            cmds.connectAttr(f"{ctls_sub_spine[i]}.worldMatrix[0]", f"{new_joint}.offsetParentMatrix")
            for attr in ["translateX","translateY","translateZ"]:
                cmds.setAttr(f"{new_joint}.{attr}", 0)
            self.sub_spine_joints.append(new_joint)

        cmds.select(clear=True)
        self.local_hip_joint = cmds.joint(n="C_localHipSkinning_JNT")
        cmds.parent(self.local_hip_joint, self.skinning_trn)
        cmds.connectAttr(f"{self.localHip[0]}.worldMatrix[0]", f"{self.local_hip_joint}.offsetParentMatrix")

        return self.sub_spine_joints

