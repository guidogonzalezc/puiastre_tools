"""
Finger module for dragon rigging system
"""
import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
import re
from puiastreTools.utils import guides_manager
from puiastreTools.utils import data_export
from importlib import reload
import maya.api.OpenMaya as om 
from puiastreTools.autorig.matrix_spaceSwitch import get_offset_matrix
reload(data_export)    

class MembraneModule():
    def __init__(self):
        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")


    def lock_attr(self, ctl, attrs = ["visibility"], ro=True):
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

    def make(self, side):

        self.side = side   

        self.thumb_joints = self.data_exporter.get_data(f"{self.side}_fingerThumb", "bendy_joints")
        self.index_joints = self.data_exporter.get_data(f"{self.side}_fingerIndex", "bendy_joints")
        self.middle_joints = self.data_exporter.get_data(f"{self.side}_fingerMiddle", "bendy_joints")
        self.ring_joints = self.data_exporter.get_data(f"{self.side}_fingerRing", "bendy_joints")
        self.pinky_joints = self.data_exporter.get_data(f"{self.side}_fingerPinky", "bendy_joints")
        self.attr_ctl = self.data_exporter.get_data(f"{self.side}_fingerThumb", "settingsAttr") 

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_membraneModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_membraneControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        cmds.setAttr(f"{self.controllers_trn}.inheritsTransform", 0)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_membraneSkinning_GRP", ss=True, p=self.skel_grp)

        fingers_chains = []

        cmds.addAttr(self.attr_ctl, longName='Dynamics______', attributeType='enum', enumName='_______')

        cmds.addAttr(self.attr_ctl, longName='enableDynamics', attributeType='bool', keyable=True)

        cmds.addAttr(self.attr_ctl, longName='pointLock', attributeType='enum', enumName='No Attach:Base:Tip:BothEnds', keyable=True)
        cmds.setAttr(f"{self.attr_ctl}.pointLock", 1) 

        cmds.addAttr(self.attr_ctl, longName='Values_______', attributeType='enum', enumName='_______')

        cmds.addAttr(self.attr_ctl, longName='startFrame', attributeType='float', defaultValue=1.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='animFollowBase', attributeType='float', defaultValue=1.0, minValue=0.0, maxValue=1.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='animFollowTip', attributeType='float', defaultValue=0.1, minValue=0.0, maxValue=1.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='animFollowDamp', attributeType='float', defaultValue=0.2, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='mass', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='drag', attributeType='float', defaultValue=0.1, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='damp', attributeType='float', defaultValue=2, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='stiffness', attributeType='float', defaultValue=2, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='Turbulence_______', attributeType='enum', enumName='_______')

        cmds.addAttr(self.attr_ctl, longName='turbulenceIntensity', attributeType='float', defaultValue=250.0, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='turbulenceFrequency', attributeType='float', defaultValue=150, minValue=0.0, keyable=True)

        cmds.addAttr(self.attr_ctl, longName='turbulenceSpeed', attributeType='float', defaultValue=10, minValue=0.0, keyable=True)

        for enum in ["Dynamics______", "Values_______", "Turbulence_______"]:
            cmds.setAttr(f"{self.attr_ctl}.{enum}", channelBox=True, lock=True)


        for name in [self.thumb_joints, self.index_joints, self.middle_joints, self.ring_joints, self.pinky_joints]:
            if name:
                fingers_chains.append(name)


        for i in range(len(fingers_chains)-1):

            if fingers_chains[i+1]:
                joint01 = fingers_chains[i]
                joint02 = fingers_chains[i+1]

                self.create_nurbs_curve(joint01, joint02)

        self.main_membrans()

    def get_closest_joint(self, target_joint, joint_list):
        target_pos = om.MVector(*cmds.xform(target_joint, q=True, ws=True, t=True))
        
        closest_joint = None
        min_distance = float('inf')

        for joint in joint_list:            
            joint_pos = om.MVector(*cmds.xform(joint, q=True, ws=True, t=True))
            distance = (target_pos - joint_pos).length()
            
            if distance < min_distance:
                min_distance = distance
                closest_joint = joint

        return closest_joint

    def create_nurbs_curve(self, joint01, joint02):
            
        def build_finger_string(joint_names):
            return ''.join(re.search(r'finger([A-Za-z]+)\d', name).group(1) for name in joint_names if re.search(r'finger([A-Za-z]+)\d', name))

        result = build_finger_string([joint01[0], joint02[0]])

        self.module_indiv_grp = cmds.createNode("transform", name=f"{self.side}_membrane{result}Module_GRP", ss=True, parent=self.module_trn)


        points = [(i + 1, 0, 0) for i in range(len(joint01) // 2)]

        curve = cmds.curve(d=1, p=points, name=f"{self.side}_membrane{result}_CRV")
        cmds.rebuildCurve(curve, rpo=True, rt=False, end=True, kr=False, kcp=True, kep=True, kt=True, s=4, d=1, tol=1e-06)
        cmds.delete(curve, ch=True)  
        cmds.parent(curve, self.module_indiv_grp)


        


        hairSystem = cmds.createNode("hairSystem", name=f"{self.side}_membraneShape{result}_HS", ss=True)
        if cmds.objExists("time1"):
            time = "time1"  
        else:   
            time = cmds.createNode("time", name="time1", ss=True)

        follicle = cmds.createNode("follicle", name=f"{self.side}_membraneShape{result}_FOL", ss=True)

        for child in [hairSystem, follicle]:
            parent = cmds.listRelatives(child, parent=True, type="transform")[0]
            cmds.rename(parent, child.replace("Shape", ""))
            cmds.parent(parent, self.module_indiv_grp)

        curve_shape = cmds.listRelatives(curve, shapes=True)[0]
        dupe = cmds.duplicate(curve_shape, name=f"{self.side}_membrane{result}_Shape", rr=True)

        cmds.connectAttr(f"{time}.outTime", f"{hairSystem}.currentTime")
        cmds.connectAttr(f"{hairSystem}.outputHair[0]", f"{follicle}.currentPosition")

        cmds.connectAttr(f"{curve_shape}.local", f"{follicle}.startPosition")
        cmds.connectAttr(f"{follicle}.outHair", f"{hairSystem}.inputHair[0]")
        cmds.connectAttr(f"{follicle}.outCurve", f"{dupe[0]}.create")

        remap_value = cmds.createNode("remapValue", name=f"{self.side}_membrane{result}_RMV", ss=True)
        cmds.connectAttr(f"{self.attr_ctl}.enableDynamics", f"{remap_value}.inputValue")
        cmds.setAttr(f"{remap_value}.inputMin", 0)
        cmds.setAttr(f"{remap_value}.inputMax", 1)
        cmds.setAttr(f"{remap_value}.outputMin", 1)
        cmds.setAttr(f"{remap_value}.outputMax", 2)

        cmds.connectAttr(f"{remap_value}.outValue", f"{hairSystem}.simulationMethod")
        cmds.connectAttr(f"{self.attr_ctl}.pointLock", f"{follicle}.pointLock")

        cmds.connectAttr(f"{self.attr_ctl}.startFrame", f"{hairSystem}.startFrame")
        cmds.connectAttr(f"{self.attr_ctl}.animFollowDamp", f"{hairSystem}.attractionDamp")
        cmds.connectAttr(f"{self.attr_ctl}.animFollowBase", f"{hairSystem}.attractionScale[0].attractionScale_FloatValue")
        cmds.connectAttr(f"{self.attr_ctl}.animFollowTip", f"{hairSystem}.attractionScale[1].attractionScale_FloatValue")
        cmds.connectAttr(f"{self.attr_ctl}.damp", f"{hairSystem}.damp")
        cmds.connectAttr(f"{self.attr_ctl}.drag", f"{hairSystem}.drag")
        cmds.connectAttr(f"{self.attr_ctl}.mass", f"{hairSystem}.mass")
        cmds.connectAttr(f"{self.attr_ctl}.stiffness", f"{hairSystem}.stiffness")
        cmds.connectAttr(f"{self.attr_ctl}.turbulenceFrequency", f"{hairSystem}.turbulenceFrequency")
        cmds.connectAttr(f"{self.attr_ctl}.turbulenceIntensity", f"{hairSystem}.turbulenceStrength")
        cmds.connectAttr(f"{self.attr_ctl}.turbulenceSpeed", f"{hairSystem}.turbulenceSpeed")

        cmds.setAttr(f"{follicle}.restPose", 1)
        cmds.setAttr(f"{follicle}.startDirection", 1)
        cmds.setAttr(f"{follicle}.collide", 0)
        cmds.setAttr(f"{hairSystem}.collide", 0)



        nurbs_joints = []
        wtas=[]
        for i in range(1, len(joint01), 2):
            wta = cmds.createNode("wtAddMatrix", name=f"{self.side}_membran{result}0{i}_WTA", ss=True)
            wtas.append(wta)
            cmds.connectAttr(f"{joint01[i]}.worldMatrix", f"{wta}.wtMatrix[0].matrixIn")
            cmds.connectAttr(f"{joint02[i]}.worldMatrix", f"{wta}.wtMatrix[1].matrixIn")
            cmds.setAttr(f"{wta}.wtMatrix[0].weightIn", 0.5)
            cmds.setAttr(f"{wta}.wtMatrix[1].weightIn", 0.5)
            dcp = cmds.createNode("decomposeMatrix", name=f"{self.side}_membran{result}0{i}_DCP", ss=True)
            cmds.connectAttr(f"{wta}.matrixSum", f"{dcp}.inputMatrix")

            cmds.connectAttr(f"{dcp}.outputTranslate", f"{curve}.controlPoints[{i//2}]")

            cmds.disconnectAttr(f"{dcp}.outputTranslate", f"{curve}.controlPoints[{i//2}]")

            cmds.select(clear=True)
            joint = cmds.joint(name=f"{self.side}_membrane{result}0{i}NurbsSkin_JNT")
            cmds.connectAttr(f"{wta}.matrixSum", f"{joint}.offsetParentMatrix")
            cmds.parent(joint, self.module_indiv_grp)
            nurbs_joints.append(joint)

        

        dupe_skinning = cmds.duplicate(dupe[0], name=f"{self.side}_membrane{result}_SkinningShape", rr=True)
        


        blendShape = cmds.blendShape(dupe[0], dupe_skinning[0], name=f"{self.side}_membrane{result}_BS", origin="world")[0]
        cmds.setAttr(f"{blendShape}.{dupe[0]}", 1)

        skincluster = cmds.skinCluster(nurbs_joints , dupe_skinning[0], tsb=True, name=f"{self.side}_membrane{result}_SKIN", maximumInfluences=1, normalizeWeights=1)[0]

        composes = []

        for value in range(0, 4):
            parameter = 0.25 * value

            mpa = cmds.createNode("motionPath", name=f"{self.side}_membrane{result}0{value}_MPA", ss=True)
            cmds.connectAttr(f"{dupe_skinning[0]}.worldSpace", f"{mpa}.geometryPath")
            cmds.setAttr(f"{mpa}.uValue", parameter)
            cmp = cmds.createNode("composeMatrix", name=f"{self.side}_membrane{result}0{value}_CMP", ss=True)
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{cmp}.inputTranslate")


            composes.append(cmp)


        skinning_joints = []

        for i, compoes in enumerate(composes):

            aimmatrix = cmds.createNode("aimMatrix", name=f"{self.side}_membrane{result}0{value}_AM", ss=True)
            cmds.connectAttr(f"{compoes}.outputMatrix", f"{aimmatrix}.inputMatrix")


            if len(composes)-1 == i:
                cmds.connectAttr(f"{composes[i-1]}.outputMatrix", f"{aimmatrix}.primary.primaryTargetMatrix")
                cmds.setAttr(f"{aimmatrix}.primaryInputAxis", -1, 0, 0, type="double3")

                

            else:
                cmds.connectAttr(f"{composes[i+1]}.outputMatrix", f"{aimmatrix}.primary.primaryTargetMatrix")
                cmds.setAttr(f"{aimmatrix}.primaryInputAxis", 1, 0, 0, type="double3")

            if i == 0:
                z = 0
            elif i == 1:
                z = int(len(wtas) / 2)
            elif i == 2:
                z = -1

            cmds.connectAttr(f"{wtas[z]}.matrixSum", f"{aimmatrix}.secondary.secondaryTargetMatrix")
            cmds.setAttr(f"{aimmatrix}.secondaryInputAxis", 0, 0, 1, type="double3")
            cmds.setAttr(f"{aimmatrix}.secondaryMode", 2)
            cmds.setAttr(f"{aimmatrix}.secondaryTargetVector", 0, 0, 1, type="double3")


            ctl, grp = curve_tool.controller_creator(f"{self.side}_membrane{result}0{i}", suffixes=["GRP"])
            self.lock_attr(ctl)
            cmds.connectAttr(f"{aimmatrix}.outputMatrix", f"{grp[0]}.offsetParentMatrix")

            cmds.parent(grp[0], self.controllers_trn)
            

            cmds.select(clear=True)
            skinning_joint = cmds.joint(name=f"{self.side}_membrane{result}0{i}_JNT")
            skinning_joints.append(skinning_joint)
            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{skinning_joint}.offsetParentMatrix")
            cmds.parent(skinning_joint, self.skinning_trn)  

        for i, end_joint in enumerate(skinning_joints):
            closest01 = self.get_closest_joint(skinning_joints[i], joint01)
            closest02 = self.get_closest_joint(skinning_joints[i], joint02)


            distance_between = cmds.createNode("distanceBetween", name=f"{self.side}_membrane{result}0{i}_DB", ss=True)
            cmds.connectAttr(f"{closest01}.worldMatrix[0]", f"{distance_between}.inMatrix1")
            cmds.connectAttr(f"{closest02}.worldMatrix[0]", f"{distance_between}.inMatrix2")
        
            float_math = cmds.createNode("floatMath", name=f"{self.side}_membrane{result}0{i}_FLM", ss=True)
            cmds.connectAttr(f"{distance_between}.distance", f"{float_math}.floatA")
            cmds.setAttr(f"{float_math}.floatB", cmds.getAttr(f"{distance_between}.distance"))
            cmds.setAttr(f"{float_math}.operation", 3)

            cond = cmds.createNode("condition", name=f"{self.side}_membrane{result}0{i}_COND", ss=True)
            cmds.connectAttr(f"{distance_between}.distance", f"{cond}.firstTerm")
            cmds.connectAttr(f"{float_math}.outFloat", f"{cond}.colorIfTrueR")
            cmds.setAttr(f"{cond}.secondTerm", cmds.getAttr(f"{distance_between}.distance"))
            cmds.setAttr(f"{cond}.operation", 4)
            cmds.setAttr(f"{cond}.colorIfFalseR", 1)

            cmds.connectAttr(f"{cond}.outColorR", f"{end_joint}.scaleZ")    


    def main_membrans(self):

        self.upper = self.data_exporter.get_data( f"{self.side}_armModule", "armUpperTwist")
        self.lower = self.data_exporter.get_data( f"{self.side}_armModule", "armLowerTwist")
        self.thumb_01 = self.data_exporter.get_data(f"{self.side}_fingerThumb", "bendy_joints")[0]

        tail00 = self.data_exporter.get_data("C_tailModule", "tail00_ctl")

        
        pos01, rot01 = guides_manager.guide_import(joint_name=f"{self.side}_outerMembran02")
        cmds.select(clear=True)
        temp_joint = cmds.joint(name=f"{self.side}_tempMembran01_JNT")
        cmds.xform(temp_joint, ws=True, translation=pos01)
        cmds.xform(temp_joint, ws=True, rotation=rot01)
        
        closest = self.get_closest_joint(temp_joint, self.thumb_joints)
        cmds.delete(temp_joint)

        name = ["inner", "outer"]
        secondary_parents = [tail00, closest]

        for i, parent in enumerate([self.upper, [self.lower]]):

            pos01, rot01 = guides_manager.guide_import(joint_name=f"{self.side}_{name[i]}Membran01")
            pos02, rot02 = guides_manager.guide_import(joint_name=f"{self.side}_{name[i]}Membran02")

            ctl01, grp01 = curve_tool.controller_creator(f"{self.side}_{name[i]}Membran01", suffixes=["GRP"])
            cmds.xform(grp01[0], ws=True, translation=pos01)
            cmds.xform(grp01[0], ws=True, rotation=rot01)

            

            
            ctl02, grp02 = curve_tool.controller_creator(f"{self.side}_{name[i]}Membran02", suffixes=["GRP"])
            cmds.xform(grp02[0], ws=True, translation=pos02)
            cmds.xform(grp02[0], ws=True, rotation=rot02)

            cmds.parent(grp01[0], grp02[0], self.controllers_trn)
            parent = cmds.parentConstraint(parent, grp01[0], maintainOffset=True)[0]
            parent02 = cmds.parentConstraint(secondary_parents[i],ctl01, grp02[0], maintainOffset=True)[0]

            cmds.setAttr(f"{parent}.interpType", 2)
            cmds.setAttr(f"{parent02}.interpType", 2)

            if name == "outer":
                cmds.setAttr(f"{parent}.{parent[0]}W0", 0.4)
                cmds.setAttr(f"{parent}.{parent[1]}W0", 0.6)

            for z, ctl in enumerate([ctl01, ctl02]):
                cmds.select(clear=True)
                joint = cmds.joint(name=f"{self.side}_{name[i]}Membran0{z}_JNT")
                cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{joint}.offsetParentMatrix")
                cmds.parent(joint, self.skinning_trn)
                


