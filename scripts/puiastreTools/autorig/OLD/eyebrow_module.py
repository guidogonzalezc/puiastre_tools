import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import data_export
from importlib import reload
reload(guides_manager)

class EyebrowModule():

    def __init__(self):

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.head_ctl = self.data_exporter.get_data("C_neckModule", "head_ctl")

    def make(self, side):

        self.side = side

        self.module_trn = cmds.createNode("transform", n=f"{side}_eyebrowModule_GRP", p=self.modules_grp)
        self.skinning_trn = cmds.createNode("transform", n=f"{side}_eyebrowSkinningJoints_GRP", p=self.skel_grp)
        self.controllers_trn = cmds.createNode("transform", n=f"{side}_eyebrowControllers_GRP")
        cmds.parent(self.controllers_trn, "C_head_CTL")

        self.eyebrow = guides_manager.guide_import(joint_name=f"{side}_eyebrow_JNT", all_descendents=True)
        

        for i, jnt in enumerate(self.eyebrow):
            if i != 0:
                cmds.parent(jnt, self.skinning_trn)
        
        self.eyebrow_jnts = cmds.listRelatives(self.skinning_trn, allDescendents=True, type="joint")
        self.head_nurbs = cmds.listRelatives(self.head_ctl, allDescendents=True, type="nurbsSurface")
        # cmds.parent(self.head_nurbs, self.module_trn)

        cmds.delete(self.eyebrow[0])
        self.bezier()
        self.controller_creation()
        self.local_projected()
        self.local_setup()

    def local(self, ctl, grp):

        """
        This function sets the local space for a controller and its group.
        It connects the controller's worldMatrix to the group's offsetParentMatrix.
        """

        mult_matrix = cmds.createNode("multMatrix", n=ctl.replace("CTL", "MMX"), ss=True)
        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{mult_matrix}.matrixIn[0]")
        cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]")
        grp_local = cmds.createNode("transform", n=ctl.replace("_CTL", "Local_GRP"), ss=True)
        trn_local = cmds.createNode("transform", n=ctl.replace("_CTL", "Local_TRN"), ss=True)
        cmds.parent(trn_local, grp_local)
        cmds.matchTransform(grp_local, grp, pos=True, rot=True, scl=True)
        cmds.parent(grp_local, self.module_trn)
        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{trn_local}.offsetParentMatrix")

        return grp_local, trn_local

    
    def bezier(self):

        p1 = cmds.xform(self.eyebrow_jnts[0], q=True, ws=True, t=True)
        p2 = cmds.xform(self.eyebrow_jnts[len(self.eyebrow_jnts)//2], q=True, ws=True, t=True)
        p3 = cmds.xform(self.eyebrow_jnts[-1], q=True, ws=True, t=True)

        self.eyebrow_bezier = cmds.curve(
            n=f"{self.side}_eyebrowBezier_CRV",
            d=1,
            p=[p1, p2, p3]
        )

        self.eyebrow_bezier = cmds.rebuildCurve(self.eyebrow_bezier, s=0, ch=False, rpo=True, kr=0, kcp=0, kt=1)[0]
        cmds.reverseCurve(self.eyebrow_bezier, ch=False)
        cmds.parent(self.eyebrow_bezier, self.module_trn)

        cmds.select(self.eyebrow_bezier)
        cmds.nurbsCurveToBezier()

        cmds.select(f"{self.eyebrow_bezier}.cv[0]")
        cmds.bezierAnchorPreset(p=1)
        cmds.select(f"{self.eyebrow_bezier}.cv[6]")
        cmds.bezierAnchorPreset(p=1)
        cmds.select(f"{self.eyebrow_bezier}.cv[3]")
        cmds.bezierAnchorPreset(p=0)
        
        self.bezier_cvs = cmds.ls(f"{self.eyebrow_bezier}.cv[*]", fl=True)

    
    def controller_creation(self):
        
    
        self.eyebrow_main_ctl, self.eyebrow_main_grp = curve_tool.controller_creator(f"{self.side}_eyebrowMain", ["GRP", "OFF"])
        cmds.matchTransform(self.eyebrow_main_grp[0], self.eyebrow_jnts[len(self.eyebrow_jnts)//2], pos=True, rot=True)
        main_local_grp, main_local_trn = self.local(self.eyebrow_main_ctl, self.eyebrow_main_grp[0])
        cmds.parent(self.eyebrow_main_grp[0], self.controllers_trn)

        self.eyebrow_controllers = []
        self.eyebrows_grps = []
        local_grps = []
        local_trns = []

        for i, cv in enumerate(self.bezier_cvs):

            if i == 1 or i == (len(self.bezier_cvs) - 2):

                ctl, grp = curve_tool.controller_creator(f"{self.side}_eyebrow0{i}Tan", ["GRP"])
                cmds.xform(grp[0], r=True, t=cmds.xform(cv, q=True, ws=True, t=True))
                local_grp, local_trn = self.local(ctl, grp[0])
                
                if i == 1:
                    cmds.parent(grp[0], self.eyebrow_controllers[-1])
                    cmds.parent(local_grp, local_trns[-1])

            else:

                ctl, grp = curve_tool.controller_creator(f"{self.side}_eyebrow0{i}", ["GRP"])
                cmds.xform(grp[0], ws=True, t=cmds.xform(cv, q=True, ws=True, t=True))
                local_grp, local_trn = self.local(ctl, grp[0])
                cmds.parent(local_grp, main_local_trn)
                cmds.parent(grp[0], self.eyebrow_main_ctl)

            if i == (len(self.bezier_cvs) - 1): 
                cmds.parent(self.eyebrows_grps[-1], ctl)
                cmds.parent(local_grps[-1], local_trn)

            
            cmds.xform(local_grp, ws=True, t=cmds.xform(cv, q=True, ws=True, t=True))
            
            self.eyebrow_controllers.append(ctl)
            self.eyebrows_grps.append(grp)
            local_grps.append(local_grp)
            local_trns.append(local_trn)
    

    def local_projected(self):

        local_jnts_grp = cmds.createNode("transform", n=f"{self.side}_eyebrowLocalJoints_GRP", p=self.module_trn)
        projected_jnts_grp = cmds.createNode("transform", n=f"{self.side}_eyebrowProjectedJoints_GRP", p=self.module_trn)
        self.local_jnts = []

        for jnt in self.eyebrow_jnts:
            cmds.select(clear=True)
            local_jnt = cmds.joint(n=jnt.replace("_JNT", "Local_JNT"))
            cmds.matchTransform(local_jnt, jnt, pos=True, rot=True)
            cmds.parent(local_jnt, local_jnts_grp)

            self.local_jnts.append(local_jnt)

        self.projected_jnts = []

        for jnt in self.eyebrow_jnts:
            cmds.select(clear=True)
            projected_jnt = cmds.joint(n=jnt.replace("_JNT", "Projected_JNT"))
            cmds.matchTransform(projected_jnt, jnt, pos=True, rot=True)
            cmds.parent(projected_jnt, projected_jnts_grp)

            self.projected_jnts.append(projected_jnt)

    def local_setup(self):

        self.offset_bezier = cmds.offsetCurve(self.eyebrow_bezier, ch=True, rn=False, cb=2, st=True, cl=True, cr=0, d=-3, tol=0.01, sd=0, ugn=False, name=f"{self.side}_EyebrowBezierOffset_CRV", normal=[1, 0, 0])
        self.offset_bezier_shape = cmds.listRelatives(self.offset_bezier, shapes=True)
        cmds.disconnectAttr(f"{self.offset_bezier[1]}.outputCurve[0]", f"{self.offset_bezier_shape[0]}.create")
        cmds.delete(self.offset_bezier[1])
        cmds.parent(self.offset_bezier[0], self.module_trn)

        for i, jnt in enumerate(self.local_jnts):

            cmds.select(clear=True)
            mpa = cmds.createNode("motionPath", n=jnt.replace("JNT", "MPA"), ss=True)
            cmds.setAttr(f"{mpa}.uValue",  (len(self.local_jnts) - 1) / i)
            cmds.connectAttr(f"{self.offset_bezier[0]}.worldSpace[0]", f"{mpa}.geometryPath")
            trn = cmds.createNode("transform", n=jnt.replace("JNT", "TRN"), ss=True)
            cmds.matchTransform(trn, jnt, pos=True, rot=True)

            aim_matrix = cmds.createNode("aimMatrix", n=jnt.replace("JNT", "AMX"), ss=True)
            cmds.connectAttr(f"{mpa}.allCoordinates", f"{trn}.translate")
            
            cmds.parent(trn, self.module_trn)
