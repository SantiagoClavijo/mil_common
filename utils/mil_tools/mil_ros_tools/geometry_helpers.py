from __future__ import division
import numpy as np
import tf.transformations as trans
from msg_helpers import numpy_quat_pair_to_pose
from geometry_msgs.msg import Quaternion


def rotate_vect_by_quat(v, q):
    '''
    Rotate a vector by a quaterion.
    v' = q*vq

    q should be [x,y,z,w] (standard ros convention)
    '''
    cq = np.array([-q[0], -q[1], -q[2], q[3]])
    cq_v = trans.quaternion_multiply(cq, v)
    v = trans.quaternion_multiply(cq_v, q)
    v[1:] *= -1  # Only seemed to work when I flipped this around, is there a problem with the math here?
    return np.array(v)[:3]


def make_rotation(vector_a, vector_b):
    '''Determine a 3D rotation that rotates A onto B
        In other words, we want a matrix R that aligns a with b

        >> R = make_rotation(a, b)
        >> p = R.dot(a)
        >> np.cross(p, a)
        >>>  array([0.0, 0.0, 0.0])

        [1] Calculate Rotation Matrix to align Vector A to Vector B in 3d?
            http://math.stackexchange.com/questions/180418
        [2] N. Ho, Finding Optimal Rotation...Between Corresponding 3D Points
            http://nghiaho.com/?page_id=671
    '''
    unit_a = normalize(vector_a)
    unit_b = normalize(vector_b)

    v = np.cross(unit_a, unit_b)
    s = np.linalg.norm(v)

    c = np.dot(unit_a, unit_b)

    skew_cross = skew_symmetric_cross(v)
    skew_squared = np.linalg.matrix_power(skew_cross, 2)

    if np.isclose(c, 1.0, atol=1e-4):
        R = np.eye(3)
        return R
    elif np.isclose(c, -1.0, atol=1e-4):
        R = np.eye(3)
        R[2, 2] *= -1
        return R

    normalization = (1 - c) / (s ** 2)

    R = np.eye(3) + skew_cross + (skew_squared * normalization)

    # Address the reflection case
    if np.linalg.det(R) < 0:
        R[:, 3] *= -1

    return R


def skew_symmetric_cross(a):
    '''Return the skew symmetric matrix representation of a vector
        [1] https://en.wikipedia.org/wiki/Cross_product#Skew-symmetric_matrix
    '''
    assert len(a) == 3, "a must be in R3"
    skew_symm = np.array([
        [+0.00, -a[2], +a[1]],
        [+a[2], +0.00, -a[0]],
        [-a[1], +a[0], +0.00],
    ], dtype=np.float32)
    return skew_symm


def deskew(A):
    return np.array([A[2, 1], A[0, 2], A[1, 0]], dtype=np.float32)


def normalize(vector):
    return vector / np.linalg.norm(vector)


def compose_transformation(R, t):
    '''Compose a transformation from a rotation matrix and a translation matrix'''
    transformation = np.zeros((4, 4))
    transformation[:3, :3] = R
    transformation[3, :3] = t
    transformation[3, 3] = 1.0
    return transformation


def project_pt_to_plane(point, plane_normal):
    dist = np.dot(plane_normal, point)
    projected = point - (dist * plane_normal)
    return projected


def clip_norm(vector, lower_bound, upper_bound):
    '''Return a vector pointing the same direction as $vector,
        with maximum norm $bound
        if norm(vector) < bound, return vector unchanged

        Like np.clip, but for vector norms
    '''
    norm = np.linalg.norm(vector)
    if lower_bound < norm < upper_bound:
        return np.copy(vector)
    if norm < lower_bound:
        v_new = (vector * lower_bound) / norm
    else:
        v_new = (vector * upper_bound) / norm
    return v_new


def quaternion_matrix(q):
    mat_h = trans.quaternion_matrix(q)
    return mat_h[:3, :3] / mat_h[3, 3]


def quat_to_euler(q):
    ''' Approximate a quaternion as a euler rotation vector'''

    euler_rot_vec = trans.euler_from_quaternion([q.x, q.y, q.z, q.w])
    final = np.array(([euler_rot_vec[0], euler_rot_vec[1], euler_rot_vec[2]]))
    return final


def quat_to_rotvec(q):
    '''
    Convert a quaternion to a rotation vector
    '''
    # For unit quaternion, return 0 0 0
    if np.all(np.isclose(q[0:3], 0)):
        return np.array([0., 0., 0.])
    if q[3] < 0:
        q = -q
    q = trans.unit_vector(q)
    angle = np.arccos(q[3]) * 2
    norm = np.linalg.norm(q)
    axis = q[0:3] / norm
    return axis * angle


def euler_to_quat(rotvec):
    ''' convert a euler rotation vector into a ROS quaternion '''

    quat = trans.quaternion_from_euler(rotvec[0], rotvec[1], rotvec[2])
    return Quaternion(quat[0], quat[1], quat[2], quat[3])


def random_pose(_min, _max):
    ''' Gives a random pose in the xyz range `_min` to `_max` '''
    pos = np.random.uniform(low=_min, high=_max, size=3)
    quat = trans.random_quaternion()
    return numpy_quat_pair_to_pose(pos, quat)
