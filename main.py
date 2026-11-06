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
#每一张画面的宽度是 640 像素
cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)  
#高度：480 像素
cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)  
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
ROI_TOP = 180  # 上边去掉的像素数。
ROI_BOTTOM = 180  # 下边去掉的像素数；剩余高度为 480-180-180=120。

PIPE_IS_DARK = False  # 水管比背景亮：False；比背景暗：True。
MIN_PIPE_AREA = 1000  # 最小水管轮廓面积，单位 px²，需看实际二值图调整。
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
        ret, img = cap.read()  # ret 是 bool；img 是 uint8 类型的 BGR 三维数组。
        if not ret or img is None:
            print('无法读取摄像头画面，程序退出')
            break
        if img.shape[1] != 640 or img.shape[0] != 480:
            # 不悄悄缩放，否则你以为的 180 px 裁剪和实际取图就不是同一件事。
            print('相机没有输出 640×480，实际尺寸为：', img.shape)
            break

        # 数组切片先写 y（行），再写 x（列）；结束下标不包含在结果里。
        # 因此取原图第 180～299 行、全部 640 列，得到 640×120 的 ROI。
        roi = img[ROI_TOP:480 - ROI_BOTTOM, :]
        preview = roi.copy()  # 单独画标记，避免影响后面在原 ROI 上计算灰度。
        gray = cv.cvtColor(roi, cv.COLOR_BGR2GRAY)
        blur = cv.GaussianBlur(gray, (5, 5), 0)  # 抑制细小噪声，保留主体轮廓。

        # Otsu 根据当前 ROI 的灰度分布自动选择一个全局阈值。
        # threshold 的第一个返回值是阈值数值，第二个返回值才是二值图。
        binary_mode = cv.THRESH_BINARY
        if PIPE_IS_DARK:
            binary_mode = cv.THRESH_BINARY_INV
        otsu_value, th = cv.threshold(blur, 0, 255, binary_mode + cv.THRESH_OTSU)
        kernel = np.ones((3, 3), dtype=np.uint8)
        th = cv.morphologyEx(th, cv.MORPH_CLOSE, kernel)  # 填补小裂缝。
        contours, hierarchy = cv.findContours(th, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)

        # 每一帧先清空结果；没有识别到时，不能沿用上一帧的旧球坐标。
        pipe_rect = None
        pipe_area = 0.0
        current_length_px = 0.0
        ball_valid = False
        ball_roi_px = None
        ball_level_px = None
        x_mm = 0.0
        y_mm = 0.0
        distance_mm = 0.0
        status = 'PIPE LOST'
        straight_view = np.zeros((80, 640, 3), dtype=np.uint8)
        ball_mask_view = np.zeros((80, 640), dtype=np.uint8)

        # ==========================================
        # 第四步：最小外接矩形筛选水管
        # ==========================================
        for cnt in contours:
            area = cv.contourArea(cnt)
            if area < MIN_PIPE_AREA:
                continue
            rect = cv.minAreaRect(cnt)
            # rect 为元组：((中心x,中心y), (边长1,边长2), 旋转角度)。
            # 它的宽高和角度约定容易混淆；下面只取边长大小，不直接使用角度。
            side1, side2 = rect[1]
            long_side = max(side1, side2)
            short_side = min(side1, side2)
            if short_side < 8 or long_side < MIN_PIPE_LENGTH:
                continue
            if long_side / short_side < MIN_PIPE_RATIO:
                continue
            if area / (long_side * short_side) < MIN_RECT_FILL:
                continue

            box = cv.boxPoints(rect)  # float32 数组，形状 (4,2)，四个顶点。
            # ROI 把水管切断时不能用剩下那截长度来换算，所以放弃该候选。
            if (np.min(box[:, 0]) <= 1 or np.max(box[:, 0]) >= 638 or
                    np.min(box[:, 1]) <= 1 or np.max(box[:, 1]) >= 118):
                continue
            if area > pipe_area:
                pipe_area = area
                pipe_rect = rect

        if pipe_rect is not None:
            status = 'BALL LOST'
            box = cv.boxPoints(pipe_rect)
            # 当前安装方式要求水管长轴大致从画面左侧指向右侧。
            # 先按 x 排序分出左侧两点、右侧两点，再按 y 分出上、下。
            # 这套简单排序不适用于水管在画面中近乎竖直的情况。
            points_x = box[np.argsort(box[:, 0])]
            left = points_x[:2]
            right = points_x[2:]
            left = left[np.argsort(left[:, 1])]
            right = right[np.argsort(right[:, 1])]
            # 顺序为：左上、右上、右下、左下。
            src = np.float32([left[0], right[0], right[1], left[1]])
            left_middle = (left[0] + left[1]) / 2.0
            right_middle = (right[0] + right[1]) / 2.0
            current_length_px = float(np.linalg.norm(right_middle - left_middle))
            current_width_px = float(np.linalg.norm(left[1] - left[0]))

            # 将最小矩形旋正，方便沿水管方向逐列寻找暗谷。
            # 这里不强制把长宽比变成 25:2，否则就提前抹掉了你要用的长度变化。
            # 最小外接矩形本身不含梯形透视信息，这一步只是旋正/重采样，
            # 不能称为消除了真实拍摄透视。后面的长度还原仍按你的比例模型计算。
            out_w = int(round(current_length_px)) + 1
            out_h = int(round(current_width_px)) + 1
            dst = np.float32([[0, 0], [out_w - 1, 0],
                              [out_w - 1, out_h - 1], [0, out_h - 1]])
            matrix = cv.getPerspectiveTransform(src, dst)
            inverse_matrix = cv.getPerspectiveTransform(dst, src)
            straight = cv.warpPerspective(roi, matrix, (out_w, out_h))
            straight_gray = cv.cvtColor(straight, cv.COLOR_BGR2GRAY)
            straight_view = straight.copy()
            cv.polylines(preview, [np.int32(np.round(src))], True, (0, 255, 255), 2)

            # ==========================================
            # 第五步：在矩形内部用一维亮度暗谷定位小球
            # ==========================================
            # 暗谷：沿长边方向，球所在的几列平均亮度比两旁低。
            # 先用暗谷找横向范围，再从原灰度图分割暗区，提取实际检测轮廓。
            # 钢球如果只产生亮斑、没有明显暗谷，本方法会失效，需要调整照明。
            diameter_px = BALL_DIAMETER_MM / PIPE_WIDTH_MM * current_width_px
            # 这个直径只是粗估。倾斜、球心高度与槽平面不同都会影响它。
            margin_y = max(1, int(out_h * 0.20))  # 排除上下槽壁和边沿刻度。
            inside = straight_gray[margin_y:out_h - margin_y, :]
            profile = np.mean(inside, axis=0).astype(np.float32)
            # axis=0 表示把每一列的多行像素求平均，得到长度 out_w 的一维数组。
            smooth_size = max(3, int(diameter_px * 0.3))
            if smooth_size % 2 == 0:
                smooth_size += 1  # 高斯核尺寸需要奇数。
            smooth = cv.GaussianBlur(profile.reshape(1, -1), (smooth_size, 1), 0)[0]
            # 大窗口平均值当作局部背景；背景减去小窗口亮度，就是暗谷深度。
            background_size = max(9, int(diameter_px * 4))
            background = cv.blur(smooth.reshape(1, -1), (background_size, 1))[0]
            valley_depth = background - smooth
            end_margin = max(2, int(diameter_px * 0.6))
            valley_depth[:end_margin] = -1
            valley_depth[-end_margin:] = -1  # 排除端盖；球紧贴端盖时可能检测不到。
            valley_x = int(np.argmax(valley_depth))
            depth = float(valley_depth[valley_x])

            ball_mask = np.zeros_like(straight_gray)
            if depth >= VALLEY_MIN_DEPTH:
                # 在暗谷附近约两个球直径宽的范围内，寻找低于局部背景的像素。
                search_left = max(end_margin, valley_x - int(diameter_px))
                search_right = min(out_w - end_margin, valley_x + int(diameter_px) + 1)
                local_gray = straight_gray[margin_y:out_h - margin_y,
                                           search_left:search_right]
                dark_threshold = max(0.0, float(background[valley_x]) - BALL_DARK_DIFFERENCE)
                _, local_mask = cv.threshold(local_gray, dark_threshold, 255, cv.THRESH_BINARY_INV)
                local_mask = cv.morphologyEx(local_mask, cv.MORPH_CLOSE, kernel)
                ball_mask[margin_y:out_h - margin_y, search_left:search_right] = local_mask
                ball_contours, _ = cv.findContours(ball_mask, cv.RETR_EXTERNAL,
                                                   cv.CHAIN_APPROX_SIMPLE)
                candidates = []  # 列表：只存满足条件的 OpenCV 轮廓数组。
                expected_area = np.pi * (diameter_px / 2.0) ** 2
                for ball_cnt in ball_contours:
                    area = cv.contourArea(ball_cnt)
                    if area < expected_area * 0.12 or area > expected_area * 1.8:
                        continue
                    bx, by, bw, bh = cv.boundingRect(ball_cnt)
                    if bw < diameter_px * 0.3 or bh < diameter_px * 0.3:
                        continue
                    if bw / bh < 0.35 or bw / bh > 2.8:
                        continue
                    # 接触搜索区左右边界的暗区可能被裁断，不能放心计算中心。
                    if bx <= search_left or bx + bw >= search_right:
                        continue
                    moments = cv.moments(ball_cnt)
                    if moments['m00'] == 0:
                        continue
                    cx = moments['m10'] / moments['m00']
                    if abs(cx - valley_x) > diameter_px * 0.7:
                        continue
                    candidates.append(ball_cnt)

                # 同一范围出现多个合格暗区时不猜测球在哪，当前帧判为无效。
                if len(candidates) == 1:
                    ball_cnt = candidates[0]
                    moments = cv.moments(ball_cnt)
                    ball_x = moments['m10'] / moments['m00']
                    ball_y = moments['m01'] / moments['m00']
                    cv.drawContours(straight_view, [ball_cnt], -1, (0, 255, 0), 1)
                    circle_center, radius = cv.minEnclosingCircle(ball_cnt)
                    cv.circle(straight_view, tuple(np.int32(np.round(circle_center))),
                              int(round(radius)), (0, 255, 0), 1)

                    # 把检测轮廓和球心变回 ROI 坐标，画在实际画面中。
                    contour_roi = cv.perspectiveTransform(ball_cnt.astype(np.float32), inverse_matrix)
                    cv.polylines(preview, [np.int32(np.round(contour_roi))], True, (0, 255, 0), 1)
                    point = np.float32([[[ball_x, ball_y]]])  # 形状 (1,1,2)。
                    point_roi = cv.perspectiveTransform(point, inverse_matrix)[0, 0]
                    ball_roi_px = (float(point_roi[0]), float(point_roi[1]))
                    cv.circle(preview, tuple(np.int32(np.round(point_roi))), 4, (0, 0, 255), -1)

                    # ==========================================
                    # 第六步：以左端为基准，用长度比还原水平坐标
                    # ==========================================
                    # 旋正图坐标 ball_x 对应的当前原图轴向距离：
                    current_ball_px = ball_x / (out_w - 1) * current_length_px
                    if horizontal_length_px > 0:
                        # 相似比例：s水平 / s当前 = L水平 / L当前。
                        # 注意 s 必须是“到左端的距离”，不能直接用原图的绝对 x。
                        ball_level_px = current_ball_px * horizontal_length_px / current_length_px
                        center_level_px = horizontal_length_px / 2.0
                        mm_per_level_px = PIPE_LENGTH_MM / horizontal_length_px
                        x_mm = (ball_level_px - center_level_px) * mm_per_level_px
                        # y 用外宽粗略换算，供观察；槽只沿长边运动，控制主要用 x_mm。
                        y_mm = (ball_y / (out_h - 1) - 0.5) * PIPE_WIDTH_MM
                        distance_mm = abs(x_mm)  # 沿杆方向到中心的距离，不是二维欧氏距离。
                        ball_valid = True
                        status = 'BALL OK'
                    else:
                        status = 'LEVEL PIPE, PRESS b'

            ball_mask_view = ball_mask
            center_straight = np.float32([[[(out_w - 1) / 2.0, (out_h - 1) / 2.0]]])
            center_roi = cv.perspectiveTransform(center_straight, inverse_matrix)[0, 0]
            cv.drawMarker(preview, tuple(np.int32(np.round(center_roi))), (255, 0, 0),
                          cv.MARKER_CROSS, 10, 1)
            cv.line(straight_view, (int((out_w - 1) / 2), 0),
                    (int((out_w - 1) / 2), out_h - 1), (255, 0, 0), 1)

        # ==========================================
        # 第七步：发送结果、显示图像与退出
        # ==========================================
        # 顺序沿用原工具的四个 int16：有效位、x、y、距离。
        # 后三个量都乘 10 后取整，单位 0.1 mm；不代表精度真的达到 0.1 mm。
        # 无效时后三项填零，接收端必须先判断有效位，不能把无效零当球在中心。
        if sender is not None:
            if ball_valid:
                sender.send_data(1, int(round(x_mm * 10)), int(round(y_mm * 10)),
                                 int(round(distance_mm * 10)))
            else:
                sender.send_data(0, 0, 0, 0)

        frame_number += 1
        now = time.monotonic()
        if now - fps_start >= 1.0:
            process_fps = frame_number / (now - fps_start)
            frame_number = 0
            fps_start = now
        if now - last_print_time >= 0.5:
            print('状态:', status, 'x(mm):', round(x_mm, 2),
                  '当前长度(px):', round(current_length_px, 1), '处理FPS:', round(process_fps, 1))
            last_print_time = now  # 限制打印频率，不 sleep 拖慢主循环。

        if SHOW_IMAGE:
            cv.putText(preview, status, (5, 18), cv.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
            cv.putText(preview, 'x=%.1f mm  d=%.1f mm  FPS=%.1f' %
                       (x_mm, distance_mm, process_fps), (5, 38),
                       cv.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
            cv.imshow('roi result', preview)
            cv.imshow('pipe binary', th)
            cv.imshow('straight pipe', straight_view)
            cv.imshow('ball dark mask', ball_mask_view)
            key = cv.waitKey(1) & 0xFF
            if key == ord('b') and pipe_rect is not None:
                horizontal_length_px = current_length_px
                print('已记录水平长度(px)：', horizontal_length_px,
                      '。请确认记录时水管确实水平，且黄色矩形对应整根水管。')
            if key == ord('q'):
                break

except KeyboardInterrupt:
    print('用户中断程序')
finally:
    cap.release()
    if sender is not None:
        sender.close()
    cv.destroyAllWindows()
