import cv2 as cv
import numpy as np
import os
import time



if __name__ == "__main__":
    # ==========================================
    # 第一步：外设配置
    # ==========================================
    # 在 linux 终端输入 echo $DISPLAY 可以查看当前图形显示地址。
    # os.environ['DISPLAY'] = 'localhost:10.0'。
    # SSH 转发地址可能变化，直接沿用系统已有 DISPLAY，不强制覆盖它。
    # 若 echo $DISPLAY 没有输出，先配置图形桌面或将下面 SHOW_IMAGE 改为 False。

    # cap = cv.VideoCapture('/dev/video0', cv.CAP_V4L2)  # RDK/Linux USB 相机。
    cap = cv.VideoCapture(1)  # 在 Windows 上使用时，用这一行替换上一行。

    if not cap.isOpened():
        print(' Error: 无法打开 USB 摄像头！请检查 USB 连接和 /dev/videoX 设备号')
        exit()

    # 有的 USB 相机只有 MJPG 格式才支持 640×480、120 FPS。
    # 这里向驱动请求该格式；是否支持，要以相机公布的模式和实际采集为准。
    # 设置图像传输格式
    # # 第一步：生成代表 MJPG 格式的编号。
    # format_code = cv.VideoWriter_fourcc('M', 'J', 'P', 'G')
    # # 第二步：把这个格式编号交给摄像头。
    # cap.set(cv.CAP_PROP_FOURCC, format_code)
    #每一张画面的宽度是 640 像素
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)  
    #高度：480 像素
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)  
    #希望摄像头每秒提供 120 张图像
    cap.set(cv.CAP_PROP_FPS, 120)   #FPS 的意思是“每秒多少帧”，一帧就是一张图像。
    # 请求缩小缓存，部分驱动可能忽略此设置
    cap.set(cv.CAP_PROP_BUFFERSIZE, 1)  #缓存”可以理解为：摄像头已经拍好了，但程序还没来得及处理的图像暂存区。这一行是尝试减少读取旧画面的情况
    print('驱动报告的宽、高、FPS：',
        cap.get(cv.CAP_PROP_FRAME_WIDTH), #cap.get(...)  查询：驱动报告它是多少。
        cap.get(cv.CAP_PROP_FRAME_HEIGHT),
        cap.get(cv.CAP_PROP_FPS)) #120.0 是驱动报告的配置值,不是用计时器实测出来的处理速度。

    #ROI
    Y_ROI_TOP =   430   # ROI区域在整体图片里面，上面的像素坐标y
    Y_ROI_BOTTOM = 560  # ROI区域在整体图片里面，下面的像素坐标y
    X_ROI_TOP =   370   # ROI区域在整体图片里面，左面的像素坐标x
    X_ROI_BOTTOM = 1700  # ROI区域在整体图片里面，右面的像素坐标x

    try:
        while True:
            ret, img = cap.read()  # ret 是 bool；img 是 uint8 类型的 BGR 三维数组。
            # 原图大小为：宽 640、高 480。
            # 保留第 180～299 行，横向全部保留。
            roi = img[Y_ROI_TOP:Y_ROI_BOTTOM, X_ROI_TOP:X_ROI_BOTTOM]

            # 复制原图，专门用于画出 ROI 的位置。
            # 这样画线就不会改变后面用来识别的原始图像。
            show_img = img.copy()

            # 在完整画面上，用绿色框标出保留区域。
            # rectangle 的点坐标写法是 (x, y)，与数组切片的顺序不同！
            # 左上角：(0, 180)
            # 右下角：(639, 299)
            cv.rectangle(show_img, (X_ROI_TOP, Y_ROI_TOP), (X_ROI_BOTTOM, Y_ROI_BOTTOM), (0, 255, 0), 1)

            # 显示完整画面，你会看到中间有一个绿色长框。
            cv.imshow('full image', show_img)

            # 显示裁出来的区域，它应该是一个宽而矮的图像。
            cv.imshow('ROI', roi)

            i = cv.waitKey(1)
            if i == ord('q'):
                break

    except KeyboardInterrupt:
        print('用户中断程序')
    finally:
        cap.release()
        cv.destroyAllWindows()