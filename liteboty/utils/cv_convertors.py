import base64

import cv2
import numpy as np


def bytes_to_cv_image(byte_image):
    """将二进制图像转换成 CV 可读图像"""

    # 将二进制数据解码为 NumPy 数组
    nparr = np.frombuffer(byte_image, np.uint8)

    # 解码为 OpenCV 图像格式
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return image


def ndarray_to_bytes(ndarray_image):
    _, buffer = cv2.imencode('.png', ndarray_image)
    bin_image = buffer.tobytes()
    return bin_image


def bytes_to_base64(byte_image):
    return base64.b64encode(byte_image).decode('utf-8')


def base64_to_bytes(base64_image):
    return base64.b64decode(base64_image.encode('utf-8'))


def nv12_bytes_to_nv12(nv12_data_bytes, width, height):
    # NV12 格式: Y平面 + UV平面 (交错存储)
    # Y平面大小: width * height
    # UV平面大小: width * height / 2

    y_size = width * height

    # 从字节流中提取 Y 和 UV 平面
    y_plane = np.frombuffer(nv12_data_bytes[:y_size], dtype=np.uint8).reshape((height, width))
    uv_plane = np.frombuffer(nv12_data_bytes[y_size:], dtype=np.uint8).reshape((height // 2, width // 2, 2))

    # 合并 Y 和 UV 平面
    # 这里将 UV 平面和 Y 平面合并成一个单一的 NV12 格式图像
    nv12_image = np.empty((height + height // 2, width), dtype=np.uint8)
    nv12_image[:height, :] = y_plane
    nv12_image[height:, :] = uv_plane.reshape((-1, width))

    return nv12_image
