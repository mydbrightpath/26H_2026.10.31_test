"""
这个模块是用来手动标定ROI范围的
需要标定的时候运行这个文件即可
"""

import cv2 as cv

# 定义一个鼠标点击事件函数
def mouse_callback(event, x, y, flags, param):
    if event == cv.EVENT_LBUTTONDOWN:  # 当鼠标左键被按下时
        print(f"鼠标点击了位置: x = {x}, y = {y}")



if __name__ == "__main__":
    flag = input({"输入e:只找在原始图像中的坐标,输入w:对比两张图片的xy"})
    #-------------找到在摄像头传来的原始图像中的坐标--------------------------
    if flag == "e":
        # 打开 USB 摄像头
        # 参数 0 通常代表电脑默认摄像头或插入的第一个 USB 摄像头
        # 如果打不开，可以尝试改成 1 或 2
        # cap = cv.VideoCapture('/dev/video0',cv.CAP_V4L2)  #linux系统上的打开方法
        cap = cv.VideoCapture(1)    #电脑上的打开方法


        # 可选：设置摄像头的分辨率（例如设置为 640x480保证处理流畅度，还可设置为1080p:1920x1080）
        #每一张画面的宽度是 1920 像素
        cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)  
        #高度：1080 像素
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)  
        #希望摄像头每秒提供 120 张图像
        cap.set(cv.CAP_PROP_FPS, 120)   #FPS 的意思是“每秒多少帧”，一帧就是一张图像。
        # 请求缩小缓存，部分驱动可能忽略此设置
        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)  #缓存”可以理解为：摄像头已经拍好了，但程序还没来得及处理的图像暂存区。这一行是尝试减少读取旧画面的情况
        print('驱动报告的宽、高、FPS：',
        cap.get(cv.CAP_PROP_FRAME_WIDTH), #cap.get(...)  查询：驱动报告它是多少。
        cap.get(cv.CAP_PROP_FRAME_HEIGHT),
        cap.get(cv.CAP_PROP_FPS)) #120.0 是驱动报告的配置值,不是用计时器实测出来的处理速度。

        cv.namedWindow("Find Coordinates", cv.WINDOW_NORMAL)

        # 绑定鼠标事件到这个窗口
        cv.setMouseCallback("Find Coordinates", mouse_callback)

        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            cv.imshow("Find Coordinates", frame)

            if cv.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv.destroyAllWindows()



    #用来对比一张图片完全版和截取部分图像版的坐标x、y最小值、最大值是否一致
    if flag == "w":
    # 打开 USB 摄像头
        # 参数 0 通常代表电脑默认摄像头或插入的第一个 USB 摄像头
        # 如果打不开，可以尝试改成 1 或 2
        cap = cv.VideoCapture('/dev/video0',cv.CAP_V4L2)  #linux系统上的打开方法
        # cap = cv.VideoCapture(1)    #电脑上的打开方法
    
    
        # 可选：设置摄像头的分辨率（例如设置为 640x480保证处理流畅度，还可设置为1080p:1920x1080）
        cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)
        cv.namedWindow("Find Coordinates1", cv.WINDOW_NORMAL)
        cv.namedWindow("Find Coordinates2", cv.WINDOW_NORMAL)
    
        # 绑定鼠标事件到这个窗口
        cv.setMouseCallback("Find Coordinates1", mouse_callback)
        cv.setMouseCallback("Find Coordinates2", mouse_callback)
    
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            y1_1,y1_2,x1_1,x1_2 = 54,1045,690,1398
            img1 = frame[y1_1 : y1_2,x1_1 :x1_2] #抠出全部A4纸
            y2_1,y2_2,x2_1,x2_2 = 54,536,690,1398
            img2 = frame[y2_1 : y2_2,x2_1 :x2_2] #抠出A4纸上半部分
            
            cv.imshow("Find Coordinates1", img1)
            cv.imshow("Find Coordinates2", img2)
            
    
            if cv.waitKey(1) & 0xFF == ord("q"):
                break
    
        cap.release()
        cv.destroyAllWindows()