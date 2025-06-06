#!/usr/bin/env python

import rospy
import rospkg
import yaml
import tf2_ros
import geometry_msgs.msg
import numpy as np
import scipy.spatial.transform as spt
from geometry_msgs.msg import Pose

def pose_to_transformation_matrix(pose):
    """
    Converts geometry_msgs/Pose to a 4x4 transformation matrix
    """
    T = np.eye(4)
    T[0,3] = pose.position.x
    T[1,3] = pose.position.y
    T[2,3] = pose.position.z
    r = spt.Rotation.from_quat([pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w])
    T[0:3, 0:3] = r.as_matrix()
    return T

def transformation_matrix_to_pose(trans_mat):   
    """
    Converts a 4x4 transformation matrix to geometry_msgs/Pose
    """
    out_pose = geometry_msgs.msg.Pose()
    out_pose.position.x = trans_mat[0,3]
    out_pose.position.y = trans_mat[1,3]
    out_pose.position.z = trans_mat[2,3]

    #convert rotation matrix to quaternion
    r = spt.Rotation.from_matrix(trans_mat[0:3, 0:3])
    quat = r.as_quat() 
    out_pose.orientation.x = quat[0]
    out_pose.orientation.y = quat[1]
    out_pose.orientation.z = quat[2]
    out_pose.orientation.w = quat[3] 
    return out_pose

def transform_backward_realsense(panda_to_camrgb_pose):
    try:
        # get ros transform between camera_base and rgb_camera_link using ros tf api
        # create tf subscriber
        tf_buffer = tf2_ros.Buffer()
        listener = tf2_ros.TransformListener(tf_buffer)

        rgb_to_cambase = tf_buffer.lookup_transform('camera_color_optical_frame', 'camera_link', rospy.Time(0), rospy.Duration(10.0))
        rgb_to_cambase_pose = Pose()
        rgb_to_cambase_pose.position.x = rgb_to_cambase.transform.translation.x
        rgb_to_cambase_pose.position.y = rgb_to_cambase.transform.translation.y
        rgb_to_cambase_pose.position.z = rgb_to_cambase.transform.translation.z
        rgb_to_cambase_pose.orientation.x = rgb_to_cambase.transform.rotation.x
        rgb_to_cambase_pose.orientation.y = rgb_to_cambase.transform.rotation.y
        rgb_to_cambase_pose.orientation.z = rgb_to_cambase.transform.rotation.z
        rgb_to_cambase_pose.orientation.w = rgb_to_cambase.transform.rotation.w
        
        rgb_to_cambase_mat = pose_to_transformation_matrix(rgb_to_cambase_pose)

        panda_to_camrgb_mat = pose_to_transformation_matrix(panda_to_camrgb_pose)

        panda_to_cambase_mat = np.matmul(panda_to_camrgb_mat, rgb_to_cambase_mat)
        panda_to_cambase_pose = transformation_matrix_to_pose(panda_to_cambase_mat)
        return panda_to_cambase_pose
    except:
        print("no transform found for Realsense camera")
        return None

def static_tf_broadcaster_realsense(static_tf_params: Pose):
    static_transformStamped = geometry_msgs.msg.TransformStamped()
    static_transformStamped.header.stamp = rospy.Time.now()
    static_transformStamped.header.frame_id = "/panda_link8" #/panda_end_effector
    static_transformStamped.child_frame_id =  "/camera_link"
    static_transformStamped.transform.translation.x = static_tf_params.position.x
    static_transformStamped.transform.translation.y = static_tf_params.position.y
    static_transformStamped.transform.translation.z = static_tf_params.position.z
    static_transformStamped.transform.rotation.x = static_tf_params.orientation.x
    static_transformStamped.transform.rotation.y = static_tf_params.orientation.y
    static_transformStamped.transform.rotation.z = static_tf_params.orientation.z
    static_transformStamped.transform.rotation.w = static_tf_params.orientation.w

    static_broadcaster = tf2_ros.StaticTransformBroadcaster()
    static_broadcaster.sendTransform(static_transformStamped)

if __name__ == '__main__':
    rospy.init_node('realsense_tf2_static_node')

    # Load static transform parameters from YAML file
    rospack = rospkg.RosPack()
    static_tf_file_realsense = rospack.get_path('manipulation') + '/config/realsense_tf.yaml'

    with open(static_tf_file_realsense, 'r') as f:
        static_tf_params_realsense = yaml.load(f, Loader=yaml.FullLoader)

    static_tf_pose_realsense = Pose()
    static_tf_pose_realsense.position.x = static_tf_params_realsense["pose"]['translation']['x']
    static_tf_pose_realsense.position.y = static_tf_params_realsense["pose"]['translation']['y']
    static_tf_pose_realsense.position.z = static_tf_params_realsense["pose"]['translation']['z']
    static_tf_pose_realsense.orientation.x = static_tf_params_realsense["pose"]['rotation']['x']
    static_tf_pose_realsense.orientation.y = static_tf_params_realsense["pose"]['rotation']['y']
    static_tf_pose_realsense.orientation.z = static_tf_params_realsense["pose"]['rotation']['z']
    static_tf_pose_realsense.orientation.w = static_tf_params_realsense["pose"]['rotation']['w']
    corrected_static_tf_pose_realsense = transform_backward_realsense(static_tf_pose_realsense)
    
    # Publish static transform message
    rate = rospy.Rate(0.5) # 0.5hz
    while not rospy.is_shutdown():
        static_tf_broadcaster_realsense(corrected_static_tf_pose_realsense) if corrected_static_tf_pose_realsense else None
        rate.sleep()