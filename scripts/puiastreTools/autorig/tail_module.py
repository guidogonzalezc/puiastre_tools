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
        self.fk_jnts = []
        self.first_twist = []
        self.bendy_beziers = []
        self.bendy_skin_clusters = []
        self.bendy_offset_beziers = []
        self.bendy_offset_skin_clusters = []

    def make(self):

        """
        Creates the tail module by importing guides, setting up bendy joints, and creating controllers.
        """
        
        self.side = "C"
        self.module_trn = cmds.createNode("transform", n=f"{self.side}_tailModule_GRP", p=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", n=f"{self.side}_tailControllers_GRP", p=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", n=f"{self.side}_tailSkinningJoints_GRP", p=self.skel_grp)
        self.localHip = self.data_exporter.get_data("C_spineModule", "localHip")
        self.import_guides()
        self.create_ik_fk_setup()


        for i, jnt in enumerate(self.fk_chain):
            if i != len(self.fk_chain) - 1:
                start = jnt
                end = self.fk_chain[i+1] if i+1 < len(self.fk_chain) else None
                name = self.tail_chain[i].split("_")[1]


                self.bendy_setup(start_joint=start, end_joint=end, blend_start=self.tail_chain[i], blend_end=self.tail_chain[i+1], name=name)

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

        self.ik_setup()
        self.wave(self.bendy_beziers, self.bendy_skin_clusters, self.bendy_offset_beziers, self.bendy_offset_skin_clusters)

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



    def create_ik_fk_setup(self):
        
        """
        Creates the IK and FK chains for the tail module.
        This method is currently a placeholder and does not implement any functionality.
        """

        #Create the tail settings controller and group
        
        cmds.addAttr(self.localHip, longName="tailSettings", niceName="TAIL SETTINGS___", at="enum", enumName="____", keyable=True)
        cmds.setAttr(f"{self.localHip}.tailSettings", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.localHip, shortName="switchIkFk", niceName="Switch IK --> FK", at="float", dv=1, minValue=0, maxValue=1, keyable=True)
        cmds.addAttr(self.localHip, shortName="Amplitude", at="float", dv=0, keyable=True)
        cmds.addAttr(self.localHip, shortName="Wavelength", at="float", dv=0, keyable=True)
        cmds.addAttr(self.localHip, shortName="Offset", at="float", dv=0, keyable=True)
        cmds.addAttr(self.localHip, shortName="Dropoff", at="float", dv=0, keyable=True)
        
        # Create the IK and FK chains
        self.ik_chain = []
        self.fk_chain = []

        for jnt in self.tail_chain:
            pair_blend = cmds.createNode("pairBlend", n=jnt.replace("JNT", "PBL"), ss=True)
            for i in range(2):
            
                cmds.select(cl=True)
                if i == 0:
                    ik_jnt = cmds.joint(n=jnt.replace("_JNT", "Ik_JNT"))
                    cmds.matchTransform(ik_jnt, jnt, pos=True, rot=True)
                    cmds.connectAttr(f"{ik_jnt}.translate", f"{pair_blend}.inTranslate1")
                    cmds.connectAttr(f"{ik_jnt}.rotate", f"{pair_blend}.inRotate1")
                    if self.ik_chain:
                        cmds.parent(ik_jnt, self.ik_chain[-1])
                    self.ik_chain.append(ik_jnt)
                else:
                    cmds.select(clear=True)
                    fk_jnt = cmds.joint(n=jnt.replace("_JNT", "Fk_JNT"))
                    cmds.matchTransform(fk_jnt, jnt, pos=True, rot=True)
                    cmds.connectAttr(f"{fk_jnt}.translate", f"{pair_blend}.inTranslate2")
                    cmds.connectAttr(f"{fk_jnt}.rotate", f"{pair_blend}.inRotate2")
                    if self.fk_chain:
                        cmds.parent(fk_jnt, self.fk_chain[-1])
                    self.fk_chain.append(fk_jnt)
                    cmds.connectAttr(f"{pair_blend}.outTranslate", f"{jnt}.translate")
            cmds.connectAttr(f"{pair_blend}.outRotate", f"{jnt}.rotate")
            cmds.connectAttr(f"{self.localHip}.switchIkFk", f"{pair_blend}.weight")

        cmds.parent(self.ik_chain[0], self.fk_chain[0], self.module_trn)


        
    def fk_constraint(self, previous_jnt, jnt, grp):

        """
        Creates a parent with matrixes constraint between a controller and a joint.
        Args:
            ctl (str): The name of the controller to constrain.
            jnt (str): The name of the joint to constrain.
        """

        if len(self.fk_controllers) == 0:
            cmds.connectAttr(f"{jnt}.worldMatrix[0]", f"{grp}.offsetParentMatrix")
        else:
            ctl = grp.replace("GRP", "CTL")
            mult_matrix = cmds.createNode("multMatrix", n=jnt.replace("JNT", "MMX"), ss=True)
            cmds.connectAttr(f"{jnt}.worldMatrix[0]", f"{mult_matrix}.matrixIn[0]")
            cmds.connectAttr(f"{previous_jnt}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]")
            cmds.connectAttr(f"{self.fk_controllers[-1]}.worldMatrix[0]", f"{mult_matrix}.matrixIn[2]")
            cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{grp}.offsetParentMatrix")
            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{jnt}.offsetParentMatrix")

    def bendy_setup(self, start_joint, end_joint, blend_start, blend_end, name):

        """
        Sets up the bendy joint system for the tail module, including creating controllers, roll setup, and bendy joints.
        Args:
            start_joint (str): The name of the starting joint for the bendy setup.
            end_joint (str): The name of the ending joint for the bendy setup.
            name (str): The name to use for the bendy setup components.
        """

        bendy_module = cmds.createNode("transform", n=f"{self.side}_{name}BendyModule_GRP", ss=True, p=self.module_trn)
        skinning_module = cmds.createNode("transform", n=f"{self.side}_{name}SkinningJoints_GRP", ss=True, p=self.skinning_trn)
        fk_controllers = cmds.createNode("transform", n=f"{self.side}_{name}FkControllers_GRP", ss=True, p=self.controllers_trn)
        controllers = cmds.createNode("transform", n=f"{self.side}_{name}Controllers_GRP", ss=True, p=fk_controllers)
        
        cmds.connectAttr(f"{self.localHip}.switchIkFk", f"{fk_controllers}.visibility")

        index = len(self.fk_controllers)
        
        ctl, grp = curve_tool.controller_creator(f"{self.side}_{name}", suffixes=["GRP", "SDK", "OFF"])
        self.lock_attrs(ctl, ["tx", "ty", "tz", "sx", "sy", "sz", "v"])
        cmds.matchTransform(grp[0], start_joint, pos=True, rot=True)
        cmds.parent(grp[0], controllers)
        cmds.parentConstraint(ctl, start_joint)
        # self.fk_constraint(self.tail_chain[index-1], self.tail_chain[index], grp[0])
        # if index != 0:
        #     cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{start_joint}.offsetParentMatrix")
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
        cmds.connectAttr(f"{blend_start}.worldMatrix[0]", f"{decompose_00}.inputMatrix")
        cmds.connectAttr(f"{blend_end}.worldMatrix[0]", f"{decompose_01}.inputMatrix")
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
        cmds.parent(bendy_grp, self.controllers_trn)
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
        self.bendy_beziers.append(bezier_curve[0])
        bendy_skin_cluster = cmds.skinCluster(bendy_joints[0], bendy_joint, bendy_joints[2], bezier_curve[0], tsb=True, n=f"{self.side}_{name}Bendy_SKIN")
        self.bendy_skin_clusters.append(bendy_skin_cluster)

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
            cmds.parent(twist_jnt, skinning_module)
            twist_joints.append(twist_jnt)
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{twist_jnt}.translate")
            if i == 0:
                self.first_twist.append(twist_jnt)
            if i == 3:
                cmds.connectAttr(f"{mpa}.allCoordinates", f"{aim_helper}.translate")

    # for i, twist_jnt in enumerate(twist_joints):

        #     aim_matrix = cmds.createNode("aimMatrix", n=f"{self.side}_{name}Twist0{i}_AMT", ss=True)
        #     cmds.setAttr(f"{aim_matrix}.primaryMode", 1)
        #     cmds.setAttr(f"{aim_matrix}.secondaryMode", 1)
        #     cmds.setAttr(f"{aim_matrix}.secondaryInputAxisX", 0)
        #     cmds.setAttr(f"{aim_matrix}.secondaryInputAxisY", 0)
        #     cmds.setAttr(f"{aim_matrix}.secondaryInputAxisZ", -1)

        #     compose_matrix = cmds.createNode("composeMatrix", n=f"{self.side}_{name}Twist0{i}_CMP", ss=True)
            
        #     cmds.connectAttr(f"{mpa}.allCoordinates", f"{compose_matrix}.inputTranslate")
        #     cmds.connectAttr(f"{compose_matrix}.outputMatrix", f"{aim_matrix}.inputMatrix")
        #     cmds.connectAttr(f"{twist_jnt[i+1]}.worldMatrix[0]", f"{aim_matrix}.primaryTargetMatrix")     



        # Create the offset setup
        duplicate_bezier_curve = cmds.duplicate(bezier_curve, n=f"{self.side}_{name}BezierDuplicated_CRV")[0]
        bezier_off_curve = cmds.offsetCurve(duplicate_bezier_curve, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=10, tol=0.01, sd=0, ugn=False, name=f"{self.side}_{name}BezierOffset_CRV")
        self.bendy_offset_beziers.append(bezier_off_curve[0])
        upper_bendy_shape_org = cmds.listRelatives(duplicate_bezier_curve, allDescendents=True)[-1]
        
        cmds.connectAttr(f"{upper_bendy_shape_org}.worldSpace[0]", f"{bezier_off_curve[1]}.inputCurve", f=True)
        cmds.setAttr(f"{bezier_off_curve[1]}.useGivenNormal", 1)
        cmds.setAttr(f"{bezier_off_curve[1]}.normal", 1, 0, 0, type="double3")
        cmds.parent(bezier_off_curve[0], bendy_module)
        self.upper_bendy_off_curve_shape = cmds.rename(cmds.listRelatives(bezier_off_curve[0], s=True), f"{self.side}_{name}BendyBezierOffset_CRVShape")
        

        upper_bendy_off_skin_cluster = cmds.skinCluster(bendy_joints[0], bendy_joint, bendy_joints[2], bezier_off_curve[0], tsb=True, n=f"{self.side}_{name}BendyBezierOffset_SKIN")
        self.bendy_offset_skin_clusters.append(upper_bendy_off_skin_cluster)

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


    def ik_setup(self):

        """
        Set up the IK tail system, creating IK handles and constraints.

        """
        

        controllers = cmds.createNode("transform", n=f"{self.side}_tailIkControllers_GRP", ss=True, p=self.controllers_trn)
        reverse = cmds.createNode("reverse", n=f"{self.side}_tailIkReverse_RVS", ss=True)
        cmds.connectAttr(f"{self.localHip}.switchIkFk", f"{reverse}.inputX")
        cmds.connectAttr(f"{reverse}.outputX", f"{controllers}.visibility")

        self.tail_ctl, self.tail_grp = curve_tool.controller_creator(f"{self.side}_tailIkRoot", suffixes=["GRP"])
        self.tail_ctl_mid, self.tail_grp_mid = curve_tool.controller_creator(f"{self.side}_tailIkMid", suffixes=["GRP"])
        self.tail_ctl_end, self.tail_grp_end = curve_tool.controller_creator(f"{self.side}_tailIkEnd", suffixes=["GRP"])
        self.lock_attrs(self.tail_ctl, ["sx", "sy", "sz", "v"])
        self.lock_attrs(self.tail_ctl_mid, ["sx", "sy", "sz", "v"])
        self.lock_attrs(self.tail_ctl_end, ["sx", "sy", "sz", "v"])
        cmds.parent(self.tail_grp, self.tail_grp_mid, self.tail_grp_end, controllers)

        self.ik_spring_hdl = cmds.ikHandle(sj=self.ik_chain[0], ee=self.ik_chain[-1], sol="ikSplineSolver", n=f"{self.side}_tailIkSpline_HDL", createCurve=True,  ns=3)
        cmds.parent(self.ik_spring_hdl[0], self.module_trn)
        self.ik_curve = self.ik_spring_hdl[2]
        self.ik_curve = cmds.rename(self.ik_curve, f"{self.side}_tailIkCurve_CRV")

        self.tail_start_jnt_offset = cmds.createNode("transform", n=f"{self.side}_tailStart_OFFSET", p=self.module_trn)
        self.tail_start_jnt = cmds.createNode("joint", n=f"{self.side}_tailStart_JNT", p=self.tail_start_jnt_offset)
        cmds.matchTransform(self.tail_start_jnt_offset, self.tail_chain[0], pos=True, rot=True, scl=False)
        cmds.matchTransform(self.tail_grp, self.tail_start_jnt_offset, pos=True, rot=True)
        cmds.parentConstraint(self.tail_ctl, self.tail_start_jnt_offset, mo=False)

        self.tail_mid_jnt_offset = cmds.createNode("transform", n=f"{self.side}_tailMid_OFFSET", p=self.module_trn)
        self.tail_mid_jnt = cmds.createNode("joint", n=f"{self.side}_tailMid_JNT", p=self.tail_mid_jnt_offset)
        cmds.matchTransform(self.tail_mid_jnt_offset, self.ik_chain[len(self.ik_chain)//2], pos=True, rot=True, scl=False)
        cmds.matchTransform(self.tail_grp_mid, self.tail_mid_jnt_offset, pos=True, rot=True)
        cmds.parentConstraint(self.tail_ctl_mid, self.tail_mid_jnt_offset, mo=False)

        self.tail_end_jnt_offset = cmds.createNode("transform", n=f"{self.side}_tailEnd_OFFSET", p=self.module_trn)
        self.tail_end_jnt = cmds.createNode("joint", n=f"{self.side}_tailEnd_JNT", p=self.tail_end_jnt_offset)
        cmds.matchTransform(self.tail_end_jnt_offset, self.tail_chain[-1], pos=True, rot=True, scl=False)
        cmds.matchTransform(self.tail_grp_end, self.tail_end_jnt_offset, pos=True, rot=True)
        
        # Skin the curve to the joints
        self.curve_skin_cluster = cmds.skinCluster(self.tail_start_jnt, self.tail_mid_jnt, self.tail_end_jnt, self.ik_curve, tsb=True, n=f"{self.side}_tailSkinCluster_SKIN", mi=5)

        # Set the spline with the correct settings
        cmds.setAttr(f"{self.ik_spring_hdl[0]}.dTwistControlEnable", 1)
        cmds.setAttr(f"{self.ik_spring_hdl[0]}.dWorldUpType", 4)
        cmds.setAttr(f"{self.ik_spring_hdl[0]}.dForwardAxis", 4)
        cmds.connectAttr(f"{self.tail_ctl}.worldMatrix[0]", f"{self.ik_spring_hdl[0]}.dWorldUpMatrix")
        cmds.connectAttr(f"{self.tail_ctl_end}.worldMatrix[0]", f"{self.ik_spring_hdl[0]}.dWorldUpMatrixEnd")
        cmds.parentConstraint(self.tail_ctl_end, self.tail_end_jnt, mo=False)


    def wave(self, beziers= [], skin = [], offset_bezier=[], offset_skin=[]):

        #Create a controller to drive the wave effect on the tail.
        
        duplicated_beziers = []
        duplicated_offset_beziers = []
        bezier_shapes = []

        for i, bezier in enumerate(beziers):
            print(bezier, offset_bezier[i])

            dup_bezier = cmds.duplicate(bezier, n=bezier.replace("_CRV", "Dup_CRV"))
            dup_offset_bezier = cmds.duplicate(offset_bezier[i], n=offset_bezier[i].replace("_CRV", "Dup_CRV"))
            bezier_shapes.append(cmds.listRelatives(dup_bezier[0], s=True)[0])
            
            cmds.delete(dup_bezier[0], ch=True)
            cmds.delete(dup_offset_bezier[0], ch=True)
            duplicated_beziers.append(dup_bezier[0])
            duplicated_offset_beziers.append(dup_offset_bezier[0])

            cmds.parent(dup_bezier, dup_offset_bezier, self.module_trn)

        dupe_parent = cmds.listRelatives(duplicated_beziers, p=True, fullPath=True)
        wave = cmds.nonLinear(duplicated_beziers, duplicated_offset_beziers, type="wave", n=f"{self.side}_tailWave_HDL")
        cmds.parent(wave[1], dupe_parent)
        cmds.matchTransform(wave[1], self.tail_chain[len(self.tail_chain)//2], pos=True, rot=True)
        cmds.rotate(0, 90, 0, wave[1], r=True, os=True, fo=True)

        blendshape00 = cmds.blendShape(duplicated_beziers[0], beziers[0], n=f"{self.side}_tailWave00_BS")[0]
        blendshape01 = cmds.blendShape(duplicated_beziers[1], beziers[1], n=f"{self.side}_tailWave01_BS")[0]
        blendshape02 = cmds.blendShape(duplicated_beziers[2], beziers[2], n=f"{self.side}_tailWave02_BS")[0]
        blendshape03 = cmds.blendShape(duplicated_beziers[3], beziers[3], n=f"{self.side}_tailWave03_BS")[0]
        blendshape04 = cmds.blendShape(duplicated_beziers[4], beziers[4], n=f"{self.side}_tailWave04_BS")[0]
        blendshape05 = cmds.blendShape(duplicated_beziers[5], beziers[5], n=f"{self.side}_tailWave05_BS")[0]

        blendshape00_offset = cmds.blendShape(duplicated_offset_beziers[0], offset_bezier[0], n=f"{self.side}_tailWave00Offset_BS")[0]
        blendshape01_offset = cmds.blendShape(duplicated_offset_beziers[1], offset_bezier[1], n=f"{self.side}_tailWave01Offset_BS")[0]
        blendshape02_offset = cmds.blendShape(duplicated_offset_beziers[2], offset_bezier[2], n=f"{self.side}_tailWave02Offset_BS")[0]
        blendshape03_offset = cmds.blendShape(duplicated_offset_beziers[3], offset_bezier[3], n=f"{self.side}_tailWave03Offset_BS")[0]
        blendshape04_offset = cmds.blendShape(duplicated_offset_beziers[4], offset_bezier[4], n=f"{self.side}_tailWave04Offset_BS")[0]
        blendshape05_offset = cmds.blendShape(duplicated_offset_beziers[5], offset_bezier[5], n=f"{self.side}_tailWave05Offset_BS")[0]

        bl_beziers = [blendshape00, blendshape01, blendshape02, blendshape03, blendshape04, blendshape05]
        bl_offset_beziers = [blendshape00_offset, blendshape01_offset, blendshape02_offset, blendshape03_offset, blendshape04_offset, blendshape05_offset]

        for i, (bezier, offset_bez) in enumerate(zip(bl_beziers, bl_offset_beziers)):

            cmds.connectAttr(f"{self.localHip}.Wavelength", f"{bezier}.{duplicated_beziers[i]}", f=True)
            cmds.connectAttr(f"{self.localHip}.Wavelength", f"{offset_bez}.{duplicated_offset_beziers[i]}", f=True)

        for attr in ["Amplitude", "Offset", "Dropoff"]:
            cmds.connectAttr(f"{self.localHip}.{attr}", f"{wave[0]}.{attr.lower()}", f=True)

        for i, (bls, off_bls) in enumerate(zip(bl_beziers, bl_offset_beziers)):

            cmds.reorderDeformers(skin[i][0], bls, beziers[i])
            cmds.reorderDeformers(offset_skin[i][0], off_bls, offset_bezier[i])  
