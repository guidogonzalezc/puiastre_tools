import maya.cmds as cmds
from puiastreTools.utils import curve_tool
from puiastreTools.utils import guide_creation
from puiastreTools.utils import data_export
import maya.api.OpenMaya as om
from importlib import reload
reload(data_export)


class SpikesModule(object):
    
    def __init__(self):

        data_exporter = data_export.DataExport()

        self.modules_grp = data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = data_exporter.get_data("basic_structure", "masterWalk_CTL")

    def make(self):

        """
        Create the spikes module
        
        """

        self.side = "C"

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_spikesModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_spikesControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_spikesSkinning_GRP", ss=True, parent=self.skel_grp)


        for side in ["L", "R"]:
            self.guides_import(side)
            self.spike(side, self.upper_spike[0])
            self.spike(side, self.lateral_spike[0])
    
    def guides_import(self, side):

        """
        Import all the spikes joints that exist in the guides file.
        
        """

        self.upper_spike = guide_creation.guide_import(joint_name=f"{side}_upperSpike*_GUIDE", all_descendents=True)
        self.lateral_spike = guide_creation.guide_import(joint_name=f"{side}_lateralSpike*_GUIDE", all_descendents=True)
        cmds.parent(self.upper_spike[0], self.lateral_spike[0], self.module_trn)
    
    def lock_attrs(self, ctl, attrs):
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def spike_build(self):

        self.attrs_ctl, self.attrs_grp = curve_tool.controller_creator(f"{self.side}_spikeAttributes", ["GRP"])
        cmds.move(0, 250, 0, self.attrs_grp, r=True) # Move it up
        self.lock_attrs(self.attrs_ctl, ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.addAttr(self.attrs_ctl, ln="Envelope", at="float", dv=0, maxValue=1, minValue=0, keyable=True)
        cmds.addAttr(self.attrs_ctl, ln="Amplitude", at="float", dv=0.1, keyable=True)
        cmds.addAttr(self.attrs_ctl, ln="Wave", at="float", dv=0, keyable=True)
        cmds.addAttr(self.attrs_ctl, ln="Dropoff", at="float", dv=0, keyable=True)

    def spike(self, side, spike_guides):

        name = spike_guides[0].split("_")[1]
        curve = cmds.curve(n=f"{side}_{name}_CRV", d=1, p=[cmds.xform(jnt, q=True, ws=True, t=True) for jnt in self.spike_guides]) # Create a curve with the joints positions
        cmds.parent(curve, self.module_trn)

        sine_hdl = cmds.nonLinear(curve, type="sine", n=f"{side}_{name}Sine_")
        cmds.parent(sine_hdl[1], self.module_trn)
        cmds.rotate(90, 0, 0, sine_hdl[1], ws=True)


        for i, guide in enumerate(spike_guides):

            decompose_node = cmds.createNode("decomposeMatrix", name=f"{guide.replace('_GUIDE', '_DCM')}", ss=True) # Create a decompose matrix node for each guide
            cmds.connectAttr(f"{guide}.worldMatrix[0]", f"{decompose_node}.inputMatrix") # Connect the guide world matrix to the decompose node
            tweak_node = cmds.createNode("tweak", name=f"{guide.replace('_GUIDE', '_TWK')}", ss=True) # Create a tweak node for each guide
            cmds.connectAttr(f"{decompose_node}.outputTranslate", f"{tweak_node}.plist[0].controlPoints[{i}]")
            cmds.connectAttr(f"{tweak_node}.plist[0].controlPoints[{i}]", f"{curve}.tweakLocation")
            compose_matrix = cmds.createNode("composeMatrix", name=f"{guide.replace('_GUIDE', '_CMT')}", ss=True)
            cmds.connectAttr(f"{decompose_node}.editPoints[{i}]", f"{compose_matrix}.inputTranslate")
            jnt = cmds.createNode("joint", name=guide.replace("_GUIDE", "_JNT"), ss=True, p=self.skinning_trn)
            cmds.connectAttr(f"{compose_matrix}.outputMatrix", f"{jnt}.offsetParentMatrix") # Connect the compose matrix output to the joint offset parent matrix
        

        # Create a controller for the curve and the sine handle
        self.ctl, self.grp = curve_tool.controller_creator(f"{side}_{name}", ["GRP"])
        cmds.parent(self.grp, self.controllers_trn)
        cmds.matchTransform(self.grp, match_jnt, pos=True, rot=True, scl=False)
        self.lock_attrs(self.ctl, ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.addAttr(self.ctl, ln="Envelope", at="float", dv=0, maxValue=1, minValue=0, keyable=True)
        cmds.addAttr(self.ctl, ln="Amplitude", at="float", dv=0.1, keyable=True)
        cmds.addAttr(self.ctl, ln="Wave", at="float", dv=0, keyable=True)
        cmds.addAttr(self.ctl, ln="Offset", at="float", dv=0, keyable=True)
        cmds.addAttr(self.ctl, ln="Dropoff", at="float", dv=0, keyable=True)
        cmds.connectAttr(f"{self.ctl}.Envelope", f"{sine_hdl}.envelope")
        cmds.connectAttr(f"{self.ctl}.Amplitude", f"{sine_hdl[0]}.amplitude")
        cmds.connectAttr(f"{self.ctl}.Wave", f"{sine_hdl[0]}.wavelength")
        cmds.connectAttr(f"{self.ctl}.Offset", f"{sine_hdl[0]}.offset")
        cmds.connectAttr(f"{self.ctl}.Dropoff", f"{sine_hdl[0]}.dropoff")
        

        cmds.delete(match_jnt)



def get_closest_vertex(mesh, target_pos):
    
    sel = om.MSelectionList()
    sel.add(mesh)
    dagPath = sel.getDagPath(0)
    mfnMesh = om.MFnMesh(dagPath)
    verts = mfnMesh.getPoints(om.MSpace.kWorld)
    
    min_dist = float('inf')
    closest_index = -1

    for i, v in enumerate(verts):
        dist = (om.MVector(v) - om.MVector(target_pos)).length()
        if dist < min_dist:
            min_dist = dist
            closest_index = i

    return closest_index

def get_uv_from_vertex(mesh, vertex_index):
    sel = om.MSelectionList()
    sel.add(mesh)
    dagPath = sel.getDagPath(0)
    mfnMesh = om.MFnMesh(dagPath)
    uv_set = mfnMesh.currentUVSetName()

    faceIt = om.MItMeshPolygon(dagPath)
    while not faceIt.isDone():
        verts = faceIt.getVertices()
        if vertex_index in verts:
            for i in range(faceIt.polygonVertexCount()):
                if faceIt.vertexIndex(i) == vertex_index:
                    uv = faceIt.getUV(i, uv_set)
                    return uv
        faceIt.next()
    return (0.0, 0.0)

def create_uv_pin(joint, mesh):
    joint_pos = cmds.xform(joint, q=True, ws=True, t=True)
    closest_vtx_index = get_closest_vertex(mesh, joint_pos)

    u, v = get_uv_from_vertex(mesh, closest_vtx_index)

    name = joint.replace("JNT", "UVP")

    uv_pin = cmds.createNode('uvPin', name=f"{name}", ss=True)

    cmds.connectAttr(mesh + ".worldMesh", uv_pin + ".deformedGeometry")

    cmds.setAttr(uv_pin + ".tangentAxis", 1)

    cmds.setAttr(uv_pin + ".coordinate[0].coordinateU", u)
    cmds.setAttr(uv_pin + ".coordinate[0].coordinateV", v)

    for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
        cmds.setAttr(joint + "." + attr, 0)

    cmds.connectAttr(uv_pin + ".outputMatrix[0]", joint + ".offsetParentMatrix")
