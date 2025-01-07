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
