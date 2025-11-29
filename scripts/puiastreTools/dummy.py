import maya.OpenMaya as om
import maya.cmds as cmds


def RayIntersect(mesh, point, direction):
    # Clear selection.
    cmds.select(cl=True)

    # Select mesh.
    om.MGlobal.selectByName(mesh)
    selList = om.MSelectionList()

    # Return an MSelectionList containing the nodes currently selected.
    om.MGlobal.getActiveSelectionList(selList)

    # Constructor that returns a new, empty MDagPath object.
    item = om.MDagPath()

    selList.getDagPath(0, item)

    # Extends the path to the specified shape node parented directly beneath
    # the transform.
    item.extendToShape()

    # Returns a new MFnMesh object attached to the given mesh node.
    fnMesh = om.MFnMesh(item)

    # Creates a 3D point with single precision coordinates.
    # passed x, y, z, w coordinates.
    raySource = om.MFloatPoint(point[0], point[1], point[2], 1.0)

    # Creates a 3D vector with specified x, y, z coordinates.
    rayDir = om.MFloatVector(direction[0], direction[1], direction[2])

    # If faceIDs are specified, then only those faces will be considered for
    # intersection.
    faceIDs = None
    # If both faceIDs and triIDs are given, then the triIDs will be interpreted
    # as face-relative and each pair of entries will be takes as a
    # (face, triangle) pair to be considered for intersection.
    triIDs = None

    # Set this to True if the faceIDs or triIDs arrays are properly sorted into
    # ascending order.
    IDsSorted = False

    # maxParam and testBothDirections flags can be used to control the radius
    # of the search around the raySource point.
    testBothDirections = False
    maxParam = 999999

    # MSpace class providing coordinate space constraints.
    # Calling space type 'kWorld'.
    worldSpace = om.MSpace.kWorld

    # If accelParams is given then the mesh builds an intersection acceleration
    # structure based on it. This is used to speed up the intersection
    # operation.
    accelParams = None
    # If true, then hits will be sorted in ascending ray-parametric order, so
    # hits behind the ray source will be first (if testing both directions).
    sortHits = True

    # Array of MFloatPoint values.
    hitPoints = om.MFloatPointArray()

    hitRayParams = om.MFloatArray()
    hitFaces = om.MIntArray()
    hitTris = None
    hitBarys1= None
    hitBarys2 = None

    # Numerical tolerance of the intersection operation.
    tolerance = 0.0001

    # Finds all intersection of a ray starting at raySource and travelling in
    # rayDirection with the mesh.
    hit = fnMesh.allIntersections(raySource, rayDir, faceIDs, triIDs, IDsSorted,
                                  worldSpace, maxParam, testBothDirections,
                                  accelParams, sortHits, hitPoints,
                                  hitRayParams, hitFaces, hitTris, hitBarys1,
                                  hitBarys2, tolerance)
    '''
    If the ray hits the mesh, the details of the intersection points will be
    returned as a tuple containing the following:
    
        * hitPoints (MFloatPointArray) - coordinates of the points hit, in the
                                         space specified by the caller.
        * hitRayParams (MFloatArray) - parametric distances along the ray to the
                                       points hit.
        * hitFaces (MIntArray) - IDs of the faces hit.
        * hitTriangles (MIntArray) - face-relative IDs if the triangle hit.
        * hitBary1s (MFloatArray - First barycentric coordinate of the points
                                   hit. If the vertices of the hitTriangle are
                                   (v1, v2, v3) then the barycentric coordinates
                                   are such that the hitPoint = 
                                   (*hitBary1)*v1 + (*hitBary2)*v2 + 
                                   (1-*hitBary1-*hitBary2)*v3.
        * hitBary2s (MFloatArray) - second barycentric coordinate of the points
                                    hit.
    
    If no point was hit then the arrays will all be empty.
    '''

'''
REFS:

https://help.autodesk.com/view/MAYAUL/2016/ENU/?guid=__py_ref_class_open_maya_1_1_m_fn_mesh_html
https://www.youtube.com/watch?v=kjp2G7ndzZc

TESTING:

import sys

sys.path.append('/home/reneem/dev/localDev')

import rayCast as rc
reload(rc)

dir = (0.0, 0.0, -1.0)
pnt = (0, 0, 3.774)
msh = "pSphereShape1"
rayCst = rc.RayIntersect(msh, pnt, dir)
firstHit = (rayCst[0].x, rayCst[0].y, rayCst[0].z)

'''

dir = (0.0, 0.0, 1.0)
pnt = (0, 0, 3.774)
msh = "pSphereShape1"
rayCst = RayIntersect(msh, pnt, dir)
# firstHit = (rayCst[0].x, rayCst[0].y, rayCst[0].z)
print(rayCst)