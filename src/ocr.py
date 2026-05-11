import numpy as np
from plugins.onnxocr.onnx_paddleocr import ONNXPaddleOcr

model = ONNXPaddleOcr(
    use_angle_cls=True,
    use_gpu=False
)

def ocr(image: np.ndarray):
    """
    Action:
        执行OCR识别
    Args:
        image: 输入图像，NumPy数组
    Returns:
        识别结果，包含文本、置信度、文本框坐标、文本框中心坐标
    """

    ocr_results = []
    result = model.ocr(image)
    for line in result[0]:
        if isinstance(line[0], (list, np.ndarray)):
            # 将 bbox 转换为 [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] 格式
            bbox = np.array(line[0]).reshape(4, 2).tolist()  # 转换为 4x2 列表
        else:
            bbox = []
        ocr_results.append({
            "text": line[1][0],  # 识别文本
            "confidence": float(line[1][1]),  # 置信度
            "bbox": bbox,  # 文本框坐标
            "center": np.mean(bbox, axis=0).tolist()  # 文本框中心坐标
        })
    return ocr_results

if __name__ == '__main__':
    import cv2
    import time
    start_time = time.time()
    ocr_results = ocr(cv2.imread('111.webp'))
    print(f"OCR识别耗时: {time.time() - start_time:.4f} 秒\n")

    for line in ocr_results:
        print(line['text'])
        print(line['confidence'])
        print(line['bbox'])
        print(line['center'])
        print("\n")

