import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import data_export
from importlib import reload
reload(guides_manager)


class TailModule(object):

    """
    Creates a tail module with bendy setup and controllers.
    
    """

    def __init__(self):

        """
        Initializes the TailModule class, setting up paths and data structures.
        """

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")

        self.fk_controllers = []
        self.fk_grps = []

    def make(self):

        """
        Creates the tail module by importing guides, setting up bendy joints, and creating controllers.
        """
        
        self.side = "C"
        self.module_trn = cmds.createNode("transform", n=f"{self.side}_tailModule_GRP", p=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", n=f"{self.side}_tailControllers_GRP", p=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", n=f"{self.side}_tailSkinningJoints_GRP", p=self.skel_grp)
        self.import_guides()

        self.first_twist = []
        self.bendy_beziers = []
        self.bendy_beziers_dup = []
        self.bendy_offset_beziers = []

        for i, jnt in enumerate(self.tail_chain):
            if i != len(self.tail_chain) - 1:
                start = jnt
                end = self.tail_chain[i+1] if i+1 < len(self.tail_chain) else None
                name = jnt.split("_")[1]


                self.bendy_setup(start_joint=start, end_joint=end, name=name)

        for i, (ctl, grp) in enumerate(zip(self.fk_controllers, self.fk_grps)):
            if i == 0:
                self.data_exporter.append_data(
                f"{self.side}_tailModule",
                {
                    "tail00_ctl" : ctl
            }
        )
            if i > 0:
                cmds.parent(grp, self.fk_controllers[i-1])

        # self.wave()

    def lock_attrs(self, ctl, attrs):

        """
        Locks specified attributes on a controller to prevent accidental changes.
        Args:
            ctl (str): The name of the controller to lock attributes on.
            attrs (list): A list of attribute names to lock.
        
        """
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)   

    def import_guides(self):

        """
        Imports the tail guides from a specified file path and parents the first joint to the module transform.
        """

        self.tail_chain = guides_manager.guide_import(joint_name=f"{self.side}_tail00_JNT", all_descendents=True)
        cmds.parent(self.tail_chain[0], self.module_trn)

    def bendy_setup(self, start_joint, end_joint, name):

        """
        Sets up the bendy joint system for the tail module, including creating controllers, roll setup, and bendy joints.
        Args:
            start_joint (str): The name of the starting joint for the bendy setup.
            end_joint (str): The name of the ending joint for the bendy setup.
            name (str): The name to use for the bendy setup components.
        """

        bendy_module = cmds.createNode("transform", n=f"{self.side}_{name}BendyModule_GRP", ss=True, p=self.module_trn)
        skinning_module = cmds.createNode("transform", n=f"{self.side}_{name}SkinningJoints_GRP", ss=True, p=self.skinning_trn)
        controllers = cmds.createNode("transform", n=f"{self.side}_{name}Controllers_GRP", ss=True, p=self.controllers_trn)
        
        ctl, grp = curve_tool.controller_creator(f"{self.side}_{name}", suffixes=["GRP", "SDK", "OFF"])
        self.lock_attrs(ctl, ["tx", "ty", "tz", "sx", "sy", "sz", "v"])
        cmds.matchTransform(grp[0], start_joint, pos=True, rot=True)
        cmds.parent(grp[0], controllers)
        cmds.parentConstraint(ctl, start_joint, mo=True)
        self.fk_controllers.append(ctl)
        self.fk_grps.append(grp[0])

        # Create the roll setup
        roll_joint_offset = cmds.createNode("transform", n=f"{self.side}_{name}Roll_TRN", ss=True, p=bendy_module)
        cmds.select(cl=True)
        roll_joint = cmds.joint(n=f"{self.side}_{name}Roll_JNT")
        roll_joint_end = cmds.joint(n=f"{self.side}_{name}RollEnd_JNT")
        cmds.parent(roll_joint, roll_joint_offset)
        cmds.xform(roll_joint_offset, ws=True, t=cmds.xform(start_joint, q=True, ws=True, t=True))
        cmds.xform(roll_joint_end, ws=True, t=cmds.xform(end_joint, q=True, ws=True, t=True))
        cmds.parentConstraint(start_joint, roll_joint_offset, mo=True)

        ik_roll = cmds.ikHandle(n=f"{self.side}_{name}Roll_HDL", sj=roll_joint, ee=roll_joint_end, sol="ikSCsolver")[0]
        cmds.parentConstraint(end_joint, ik_roll, mo=False)
        cmds.parent(ik_roll, bendy_module)

        
        # Create the linear curve
        linear_curve = cmds.curve(d=1, p=[cmds.xform(start_joint, q=True, ws=True, t=True), cmds.xform(end_joint, q=True, ws=True, t=True)], n=f"{self.side}_{name}_CRV")
        cmds.parent(linear_curve, bendy_module)

        # Drive the curve with the start and end joints
        decompose_00 = cmds.createNode("decomposeMatrix", n=start_joint.replace("JNT", "DCM"), ss=True)
        decompose_01 = cmds.createNode("decomposeMatrix", n=end_joint.replace("JNT", "DCM"), ss=True)
        cmds.connectAttr(f"{start_joint}.worldMatrix[0]", f"{decompose_00}.inputMatrix")
        cmds.connectAttr(f"{end_joint}.worldMatrix[0]", f"{decompose_01}.inputMatrix")
        cmds.connectAttr(f"{decompose_00}.outputTranslate", f"{linear_curve}.controlPoints[0]")
        cmds.connectAttr(f"{decompose_01}.outputTranslate", f"{linear_curve}.controlPoints[1]")

        # Create the bendy joints
        hook_values = [0.0, 0.5, 1.0]
        bendy_joints = []
        for i, hook in enumerate(["Root", "Mid", "Tip"]):
            
            cmds.select(cl=True)
            mpa = cmds.createNode("motionPath", n=f"{self.side}_{name}{hook}_MPA", ss=True)

            float_constant = cmds.createNode("floatConstant", n=f"{self.side}_{name}{hook}_FLC", ss=True)
            cmds.setAttr(f"{float_constant}.inFloat", hook_values[i])
            cmds.setAttr(f"{mpa}.frontAxis", 0)
            cmds.setAttr(f"{mpa}.upAxis", 1)
            cmds.setAttr(f"{mpa}.worldUpType", 2)
            cmds.setAttr(f"{mpa}.fractionMode", 1)


            float_math = cmds.createNode("floatMath", n=f"{self.side}_{name}{hook}_FLM", ss=True)
            cmds.setAttr(f"{float_math}.operation", 2)

            cmds.connectAttr(f"{float_constant}.outFloat", f"{mpa}.uValue")
            cmds.connectAttr(f"{linear_curve}.worldSpace[0]", f"{mpa}.geometryPath")
            cmds.connectAttr(f"{float_constant}.outFloat", f"{float_math}.floatA")
            cmds.connectAttr(f"{roll_joint}.rotateX", f"{float_math}.floatB")
            cmds.connectAttr(f"{float_math}.outFloat", f"{mpa}.frontTwist")

            
            cmds.connectAttr(f"{start_joint}.worldMatrix[0]", f"{mpa}.worldUpMatrix")

            bendy_joint = cmds.joint(n=f"{self.side}_{name}{hook}_JNT")
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{bendy_joint}.translate")
            cmds.connectAttr(f"{mpa}.rotate", f"{bendy_joint}.rotate")
            cmds.parent(bendy_joint, bendy_module)
            cmds.setAttr(f"{bendy_joint}.inheritsTransform", 0)
            bendy_joints.append(bendy_joint)

        # Create the bendy controller and make constraints
        bendy_ctl, bendy_grp = curve_tool.controller_creator(f"{self.side}_{name}Bendy", suffixes=["GRP"])
        self.lock_attrs(bendy_ctl, ["sx", "sy", "sz", "v"])
        cmds.parent(bendy_grp, controllers)
        cmds.matchTransform(bendy_grp, bendy_joints[1], pos=True)
        cmds.matchTransform(bendy_grp, start_joint, rot=True) 
        cmds.parentConstraint(bendy_joints[1], bendy_grp, mo=True)
        cmds.select(cl=True)
        bendy_joint = cmds.joint(n=f"{self.side}_{name}Bendy_JNT")
        cmds.parentConstraint(bendy_ctl, bendy_joint, mo=False)
        cmds.scaleConstraint(bendy_ctl, bendy_joint, mo=False)
        cmds.parent(bendy_joint, bendy_module)
        
        # Create the bendy bezier setup
        bezier_curve = cmds.curve(d=1, p=[cmds.xform(bendy_joints[0], q=True, ws=True, t=True), cmds.xform(bendy_joints[1], q=True, ws=True, t=True), cmds.xform(bendy_joints[2], q=True, ws=True, t=True)], n=f"{self.side}_{name}Bezier_CRV")
        bezier_curve = cmds.rebuildCurve(bezier_curve, rpo=1, rt=0, end=1, kr=0, kep=1, kt=0, fr=0, s=2, d=3, tol=0.01, ch=False)
        bezier_curve_shape = cmds.rename(cmds.listRelatives(bezier_curve, s=True), f"{self.side}_{name}BendyBezier_CRVShape")
  
        
        bezier_curve_shape = cmds.listRelatives(bezier_curve, s=True)[0]
        cmds.select(bezier_curve_shape)
        cmds.nurbsCurveToBezier()

        cmds.select(f"{bezier_curve[0]}.cv[6]", f"{bezier_curve[0]}.cv[0]")
        cmds.bezierAnchorPreset(p=2)
        cmds.select(f"{bezier_curve[0]}.cv[3]")
        cmds.bezierAnchorPreset(p=1)

        cmds.parent(bezier_curve, bendy_module)
        self.bendy_beziers.append(bezier_curve)
        bendy_skin_cluster = cmds.skinCluster(bendy_joints[0], bendy_joint, bendy_joints[2], bezier_curve[0], tsb=True, n=f"{self.side}_{name}Bendy_SKIN")

        cmds.skinPercent(bendy_skin_cluster[0], f"{bezier_curve[0]}.cv[0]", transformValue=[(bendy_joints[0], 1)])
        cmds.skinPercent(bendy_skin_cluster[0], f"{bezier_curve[0]}.cv[2]", transformValue=[(bendy_joint, 1)])
        cmds.skinPercent(bendy_skin_cluster[0], f"{bezier_curve[0]}.cv[3]", transformValue=[(bendy_joint, 1)])
        cmds.skinPercent(bendy_skin_cluster[0], f"{bezier_curve[0]}.cv[4]", transformValue=[(bendy_joint, 1)])
        cmds.skinPercent(bendy_skin_cluster[0], f"{bezier_curve[0]}.cv[6]", transformValue=[(bendy_joints[2], 1)])
        
        aimers_trn = cmds.createNode("transform", n=f"{self.side}_{name}Aimmers_GRP", ss=True, p=bendy_module)
        aim_helper = cmds.createNode("transform", n=f"{self.side}_{name}AimHelper04_GRP", ss=True, p=aimers_trn)
        twist_joints = []
        for i, value in enumerate([0.05, 0.25, 0.5, 0.75, 0.95]):


            cmds.select(cl=True)
            mpa = cmds.createNode("motionPath", n=f"{self.side}_{name}Twist0{i}_MPA", ss=True)
            cmds.connectAttr(f"{bezier_curve[0]}.worldSpace[0]", f"{mpa}.geometryPath")
            cmds.setAttr(f"{mpa}.uValue", value)
            cmds.setAttr(f"{mpa}.frontAxis", 1)
            cmds.setAttr(f"{mpa}.upAxis", 2)
            cmds.setAttr(f"{mpa}.worldUpType", 4)
            cmds.setAttr(f"{mpa}.fractionMode", 1)
            cmds.setAttr(f"{mpa}.follow", 1)

            
            twist_jnt = cmds.joint(n=f"{self.side}_{name}Twist0{i}_JNT")
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{twist_jnt}.translate")
            cmds.parent(twist_jnt, skinning_module)
            twist_joints.append(twist_jnt)

            if i == 0:
                self.first_twist.append(twist_jnt)
            if i == 3:
                cmds.connectAttr(f"{mpa}.allCoordinates", f"{aim_helper}.translate")


        # Create the offset setup
        duplicate_bezier_curve = cmds.duplicate(bezier_curve, n=f"{self.side}_{name}BezierDuplicated_CRV")[0]
        self.bendy_beziers_dup.append(duplicate_bezier_curve)
        bezier_off_curve = cmds.offsetCurve(duplicate_bezier_curve, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=10, tol=0.01, sd=0, ugn=False, name=f"{self.side}_{name}BezierOffset_CRV")
        self.bendy_offset_beziers.append(bezier_off_curve[0])
        upper_bendy_shape_org = cmds.listRelatives(duplicate_bezier_curve, allDescendents=True)[-1]
        
        cmds.connectAttr(f"{upper_bendy_shape_org}.worldSpace[0]", f"{bezier_off_curve[1]}.inputCurve", f=True)
        cmds.setAttr(f"{bezier_off_curve[1]}.useGivenNormal", 1)
        cmds.setAttr(f"{bezier_off_curve[1]}.normal", 1, 0, 0, type="double3")
        cmds.parent(bezier_off_curve[0], bendy_module)
        self.upper_bendy_off_curve_shape = cmds.rename(cmds.listRelatives(bezier_off_curve[0], s=True), f"{self.side}_{name}BendyBezierOffset_CRVShape")
        

        upper_bendy_off_skin_cluster = cmds.skinCluster(bendy_joints[0], bendy_joint, bendy_joints[2], bezier_off_curve[0], tsb=True, n=f"{self.side}_{name}BendyBezierOffset_SKIN")

        cmds.skinPercent(upper_bendy_off_skin_cluster[0], f"{bezier_off_curve[0]}.cv[0]", transformValue=[bendy_joints[0], 1])
        cmds.skinPercent(upper_bendy_off_skin_cluster[0], f"{bezier_off_curve[0]}.cv[2]", transformValue=[bendy_joint, 1])
        cmds.skinPercent(upper_bendy_off_skin_cluster[0], f"{bezier_off_curve[0]}.cv[3]", transformValue=[bendy_joint, 1])
        cmds.skinPercent(upper_bendy_off_skin_cluster[0], f"{bezier_off_curve[0]}.cv[4]", transformValue=[bendy_joint, 1])
        cmds.skinPercent(upper_bendy_off_skin_cluster[0], f"{bezier_off_curve[0]}.cv[6]", transformValue=[bendy_joints[2], 1])

       
        

        aim_trns = []
        for i, value in enumerate([0.05, 0.25, 0.5, 0.75, 0.95]):
            
            mpa = cmds.createNode("motionPath", n=f"{self.side}_{name}TwistAim0{i}_MPA", ss=True)
            cmds.setAttr(f"{mpa}.fractionMode", True)
            cmds.setAttr(f"{mpa}.uValue", value)

            cmds.connectAttr(f"{bezier_off_curve[0]}.worldSpace[0]", f"{mpa}.geometryPath")
            trn = cmds.createNode("transform", n=f"{self.side}_{name}TwistAim0{i}_TRN", ss=True)
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{trn}.translate")
            
            aim_trns.append(trn)
            cmds.parent(trn, aimers_trn)
            cmds.setAttr(f"{trn}.inheritsTransform", 0)

            

        # Create the aim setup
        for i, jnt in enumerate(twist_joints):
            if "04_JNT" not in jnt:
                aim = cmds.aimConstraint(twist_joints[i+1], jnt, aim=[0, 0, -1], u=[0, 1, 0], wut="object", wuo=aim_trns[i], mo=False)
            else:
                aim = cmds.aimConstraint(aim_helper, jnt, aim=[0, 0, 1], u=[0, 1, 0], wut="object", wuo=aim_trns[i], mo=False)


    def wave(self):

        #Create a controller to drive the wave effect on the tail.

        self.wave_ctl, self.wave_grp = curve_tool.controller_creator(f"{self.side}_tailWave", suffixes=["GRP"])
        self.lock_attrs(self.wave_ctl, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"])
        cmds.addAttr(self.wave_ctl, ln="Envelope", at="float", dv=0, maxValue=1, minValue=0, keyable=True)
        cmds.addAttr(self.wave_ctl, ln="Amplitude", at="float", dv=0.1, keyable=True)
        cmds.addAttr(self.wave_ctl, ln="Wave", at="float", dv=0, keyable=True)
        cmds.addAttr(self.wave_ctl, ln="Dropoff", at="float", dv=0, keyable=True)
        
        cmds.parent(self.wave_grp, self.controllers_trn)
        cmds.matchTransform(self.wave_grp, self.first_twist[0], pos=True, rot=True)
        cmds.move(0, 200, 0, self.wave_grp,r =True)

        wave_hdl = cmds.nonLinear(self.bendy_beziers, type="wave", n=f"{self.side}_tailWave_HDL")
        cmds.parent(wave_hdl[1], self.module_trn)
        cmds.rotate(180, 90, 0, wave_hdl[1], ws=True)

        plus = len(self.bendy_beziers)

        for i, (bezier, offset) in zip(enumerate(self.bendy_beziers, self.bendy_offset_beziers)):

            cmds.connectAttr(f"{bezier}.worldSpace[0]", f"{wave_hdl[0]}.input[{i}].inputGeometry")
            cmds.connectAttr(f"{offset}.worldSpace[0]", f"{wave_hdl[0]}.input[{i+plus}].inputGeometry")
        
        for i, bezier in enumerate(self.bendy_offset_beziers):
            cmds.connectAttr(f"{wave_hdl[0]}.outputGeometry[{i}]", f"{bezier}.create")

        

        cmds.connectAttr(f"{self.wave_ctl}.Envelope", f"{wave_hdl[0]}.envelope")
        cmds.connectAttr(f"{self.wave_ctl}.Amplitude", f"{wave_hdl[0]}.amplitude")
        cmds.connectAttr(f"{self.wave_ctl}.Wave", f"{wave_hdl[0]}.wavelength")
        cmds.connectAttr(f"{self.wave_ctl}.Dropoff", f"{wave_hdl[0]}.dropoff")








            




