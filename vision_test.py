import cv2 as cv
import os


if __name__ == "__main__":
    print("test begin")
    # ==========================================
    # 第一步：外设配置
    # ==========================================

    #在linux终端上输入这行命令:echo $DISPLAY 输出的所有结果赋值过来,例如:'localhost:11.0'
    #这样就可以把图像直接显示出来
    # os.environ['DISPLAY'] = 'localhost:10.0'


    # 打开 USB 摄像头
    # 参数 0 通常代表电脑默认摄像头或插入的第一个 USB 摄像头
    # 如果打不开，可以尝试改成 1 或 2
    # cap = cv.VideoCapture('/dev/video0',cv.CAP_V4L2)  #linux系统上的打开方法
    cap = cv.VideoCapture(1)    #电脑上的打开方法


    # 检查摄像头是否成功打开
    if not cap.isOpened():
        print(' Error: 无法打开 USB 摄像头！' \
        '请检查 USB 连接或修改设备索引号 (如改用 cap = cv.VideoCapture(1))')
        exit()

    # 可选：设置摄像头的分辨率（例如设置为 640x480保证处理流畅度，还可设置为1080p:1920x1080）
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)

    while True:
        # 逐帧读取图像
        # ret: bool 类型，True 表示成功读取到一帧图片；frame: 当前帧的彩色图像矩阵 (BGR)
        ret, img = cap.read()
        if not ret or img is None:
            print("无法获取画面帧，正在重试...")
            exit()  

        # #--------------图像处理部分------------#
        # #将图像转为灰度图
        # gray = cv.cvtColor(img,cv.COLOR_BGR2GRAY)
        # #高斯模糊和阈值分割和二值化
        # blur = cv.GaussianBlur(gray,(5,5),0)
        # ret,th = cv.threshold(blur,0,255,cv.THRESH_BINARY+cv.THRESH_OTSU)
        # #提取轮廓
        # contours,hierarchy = cv.findContours(th,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)


        # for index,cnt in enumerate(contours):   #遍历元素的同时获得其索引
        # #(1)多边形近似，提取每个碎片对应顶点    得到id,vertices_px
        #     #轮廓面积过滤
        #     if cv.contourArea(cnt) < 100:
        #                 continue
        #     #计算单个轮廓cnt的周长(弧长)
        #     peri = cv.arcLength(cnt,True)   #第二个参数Ture表示轮廓是"闭合"的
        #     # 保留不规则片的真实拐角；10% 会把四边形误简化成三角形。用2%比较好
        #     epsilon = 0.01 * peri
        #     #执行多边形近似，提取到这个轮廓的多边形的顶点
        #     approx = cv.approxPolyDP(cnt,epsilon,True)  #第二个参数Ture表示轮廓是"闭合"的
        #     #将输出结果，即顶点的数组 从三维数组变成二维数组
        #     vertices_px = approx.reshape(-1,2)
        #     #测试:画出其边界
        #     cv.drawContours(img,[cnt],0,(0,0,255),2)
        

        
        # # ==========================================
        # # 图像显示与退出部分
        # # ==========================================        
        window_name = "img"
        # 创建窗口，并指定为 WINDOW_NORMAL（允许自由调整大小/放大）
        cv.namedWindow(window_name, cv.WINDOW_NORMAL)
        #（可选）直接通过代码设定窗口的初始放大尺寸，比如宽 800、高 600
        cv.resizeWindow(window_name, 768, 432)
        #调整图片显示位置
        cv.moveWindow(window_name, 50, 50)  # 原图窗口放在屏幕左侧 (10, 10) 位置

        cv.imshow(window_name,img)

        i = cv.waitKey(1)
        if i == ord('q'):
            break

