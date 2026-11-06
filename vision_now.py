import cv2 as cv
import numpy as np
import os
import time

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

# ==========================================
# 第二步：集中放置需要你调整的参数
# ==========================================
SHOW_IMAGE = True  # bool：True 显示窗口；无桌面运行时改 False。
SEND_SERIAL = False  # 调好视觉后改 True，不用串口时不需要导入 pyserial。
SERIAL_PORT = '/dev/ttyUSB0'  # 字符串：按 RDK 实际连接修改，不一定是这个端口。
SERIAL_BAUDRATE = 115200  # 整数：必须与单片机一致。

PIPE_LENGTH_MM = 250.0  # 浮点数：水管实际长度，25 cm = 250 mm。
PIPE_WIDTH_MM = 20.0  # 水管外宽 2 cm；用于形状和球大小的粗略筛选。
BALL_DIAMETER_MM = 10.0  # 钢球约 1 cm，仅用于估算检测大小。
#ROI
Y_ROI_TOP =   400   # ROI区域在整体图片里面，上面的像素坐标y
Y_ROI_BOTTOM = 590  # ROI区域在整体图片里面，下面的像素坐标y
X_ROI_TOP =   300   # ROI区域在整体图片里面，左面的像素坐标x
X_ROI_BOTTOM = 1700  # ROI区域在整体图片里面，右面的像素坐标x

PIPE_IS_DARK = False  # 水管比背景亮：False；比背景暗：True。
MIN_PIPE_AREA = 2000  # 最小水管轮廓面积，单位 px²，需看实际二值图调整。
MIN_PIPE_LENGTH = 160  # 最小长边像素数，排除短小背景物体。
MIN_PIPE_RATIO = 4.0  # 最小长宽比；倾斜后投影长宽比会减小，故不强求 12.5。
MIN_RECT_FILL = 0.55  # 轮廓面积 / 最小外接矩形面积，排除明显零散的目标。
VALLEY_MIN_DEPTH = 8.0  # 暗谷比两侧背景暗多少才接受，单位灰度级，不是毫米。
BALL_DARK_DIFFERENCE = 8.0  # 局部背景减去此值，得到球暗区分割阈值。

# 水管放水平时，长边在图像中的参考长度，单位 px。
# 0.0 表示还没记录。运行后放平水管，按 b 记录；按 b 可重新记录。
# 确定相机固定不动后，也可把量好的参考长度填在这里，方便无桌面启动。
# 改变相机位置、焦距、分辨率后，旧数值就不能继续使用。
HORIZONTAL_LENGTH_PX = 0.0
horizontal_length_px = HORIZONTAL_LENGTH_PX

sender = None
if SEND_SERIAL:
    # 原 tool_pyserial.py 在 import 时会立即打开 COM3，不适合直接在 RDK 导入。
    # 因此不修改、不导入它，另用一个简短工具保留它的 11 字节发送格式。
    from utils.serial_sender import SerialSender
    sender = SerialSender(SERIAL_PORT, SERIAL_BAUDRATE)

frame_number = 0
fps_start = time.monotonic()
process_fps = 0.0
last_print_time = 0.0

try:
    while True:
        # ==========================================
        # 第三步：读取一帧，并裁剪上下 ROI
        # ==========================================
        # 1. 从摄像头读取一张图片。
        # ret：有没有读取成功。
        # img：读取到的图片。
        ret, img = cap.read()
        # 2. 如果读取失败，就结束循环。
        if ret == False:
            print("读取图片失败")
            break
        # 有时也可能没有拿到图片，再检查一次。
        if img is None:
            print("没有拿到图片")
            break
        # # 3. 获取这张图片的高度和宽度。
        # height = img.shape[0]  # 高度
        # width = img.shape[1]   # 宽度
        # # 4. 检查图片大小是否符合我们的要求。
        # if width != 640:
        #     print("图片宽度不是640，实际宽度是：", width)
        #     break
        # if height != 480:
        #     print("图片高度不是480，实际高度是：", height)
        #     break

        # 5. 只保留中间的区域。
        roi = img[Y_ROI_TOP:Y_ROI_BOTTOM, X_ROI_TOP:X_ROI_BOTTOM]
        # 6. 另外复制一张，后面专门用来画框、画圆。
        preview = roi.copy()    # 单独画标记，避免影响后面在原 ROI 上计算灰度

        # ==========================================
        # 图像处理部分
        # ==========================================
        gray = cv.cvtColor(roi, cv.COLOR_BGR2GRAY)
        blur = cv.GaussianBlur(gray, (5, 5), 0)  # 抑制细小噪声，保留主体轮廓。

        # Otsu 根据当前 ROI 的灰度分布自动选择一个全局阈值。
        # threshold 的第一个返回值是阈值数值，第二个返回值才是二值图。
        binary_mode = cv.THRESH_BINARY
        if PIPE_IS_DARK:    # 水管比背景亮：False；比背景暗：True。
            binary_mode = cv.THRESH_BINARY_INV
        otsu_value, th = cv.threshold(blur, 0, 255, binary_mode + cv.THRESH_OTSU)

        #备一个3×3的小方块，作为修补二值图时使用的工具。
        kernel = np.ones(
            (3, 3), # 小方块的大小。
            dtype=np.uint8)# 数字的存储类型，这里按这个写即可。
        # 用这个小方块，对二值图做“闭运算”。先膨胀、再腐蚀，尝试补上细小裂缝。
        # 先膨胀：让白色区域向外扩一点。
        # 再腐蚀：让白色区域向内缩回来。
        th = cv.morphologyEx(
            th,     # 要处理的黑白图片。
            cv.MORPH_CLOSE, # 选择“闭运算”这种处理方式。
            kernel)  # 使用刚才准备的3×3小方块。

        #沿着白色区域的边缘，找出轮廓。
        # 此时只找到了轮廓，还没有判断哪个是水管。
        contours, hierarchy = cv.findContours(
            th, #在这张二值图中找轮廓
            cv.RETR_LIST, #列出找到的轮廓，包括内部孔洞的边界
            cv.CHAIN_APPROX_SIMPLE)#减少直线段上重复保存的点，节省存储

        #测试：画出轮廓
        for index,cnt in enumerate(contours): 
            area = cv.contourArea(cnt)
            if area < MIN_PIPE_AREA:    # 最小水管轮廓面积，单位 px²，需看实际二值图调整。
                continue
            cv.drawContours(preview,[cnt],0,(0,0,255),2)
        
        cv.imshow("img", img)
        cv.imshow("roi", roi)
        cv.imshow("draw", preview)

        if cv.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    print('用户中断程序')
finally:
    cap.release()
    cv.destroyAllWindows()
