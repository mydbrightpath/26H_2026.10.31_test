import time
import serial  # 导入串口通信库 (pyserial)
import struct  # 导入二进制数据打包库


# ==========================================
# 第一步：初始化串口配置与连接
# ==========================================
# Windows 系统下通常是 'COM3', 'COM4' 等
# Linux/树莓派/Jetson 下通常是 '/dev/ttyUSB0' 或 '/dev/ttyAMA0'
# 波特率必须和单片机保持一致，常用 115200 或 9600
ser = serial.Serial(port='COM3', baudrate=115200, timeout=0.5)


# ==========================================
# 第二步：构建数据打包与发送函数
# 要发送什么数据就在这里面加：
# 1、形参个数
# 2、struct.pack()里面的数据类型
# 3、struct.pack()里面的待发送数据格式（data1……）
# ==========================================
def send_data(data1, data2, data3, data4):
    """
    将控制数据打包成二进字节流并发送给单片机
    如果需要更多/更少的数据直接在这里修改就可以了
    """
    
    # 协议格式设计：
    # > : 大端序传输
    # B : 1字节无符号整数 (0~255) -> 用于帧头 (0xAA, 0xAF) 和 帧尾 (0x55)
    # h : 2字节有符号整数 (-32768~32767) -> 用于数据 (flag, x, y, angle)
    # x ：只负责跳过包头包尾，不会检查是否正确(2x：跳过 2 字节包头，x：跳过 1 字节包尾)
    # 结构：[0xAA][0xAF] [data1][data2][data3][data4] [0x55]  (共 11 个字节)

    data_packet = struct.pack(
        '>BB hhhh B', 0xAA, 0xAF, data1, data2, data3, data4, 0x55
        #               B       B   h       h       h       h   B   
    )

    # 将打包好的二进制数据写入串口
    ser.write(data_packet)


# ==========================================
# 第三步：构建数据接收读取函数（可选，根据控制反馈需求）
# 要更改接收的东西需要改的地方：
# 1、struct.unpack()里面对应的变量类型
# 2、receive_data_id类里面序号所对应的名字
# 3、接收数据的顺序 与 struct.unpack()里面的变量类型 和 receive_data_id类里面序号所对应的名字 的顺序一一对应
# 
# 知识点：
# [:2] 完整写出来就是 [0 : 2]，提取从开头（索引 0）开始、到索引 2 之前（不包括 2）的前 2 个元素。
# [-1:] 把最后一个元素单独拿出来,提取包含最后一个元素的新列表
# ==========================================
def receive_data():
    """从单片机读取串口反馈数据"""
    try:
        if ser and ser.isOpen() and ser.in_waiting > 0:
            # 读取等待缓冲区中的所有数据
            rx_data = ser.read(ser.in_waiting)
            #有数据才进行解析操作
            if rx_data is not None:
                #检测包头、包尾
                if (rx_data[:2] == b"\xAA\xAF") & (rx_data[-1:] == b"\x55"):   
                    #提取出除了包头包尾外实际需要的数据
                    receive_data = struct.unpack(">2x HHH x", rx_data)  #2x：跳过 2 字节包头，x：跳过 1 字节包尾，x 只负责跳过，不会检查包头包尾是否正确
                    print(f'收到单片机回复: {receive_data}')
                    return receive_data
    except struct.error:    #如果接收到的字节数错误，会报"struct.error"
        print("需要一个正确字节的缓冲区。当前传入数据总字节数错误")
        


# ==========================================
# 用类构建状态机：
# 这个代表的是接收串口数据列表receive_datas的序号，
# 更直观的看出来当前列表对应序号里面储存的值的作用
# 
# 
# ==========================================
class receive_data_id:
    """ 用类构建状态机：
        这个代表的是接收串口数据列表receive_datas的序号,
        更直观的看出来当前列表对应序号里面储存的值的作用

        名字即为其对应含义
    """
    IDLE = 0
    READ_SENSOR = 1
    MOVE_ARM = 2

# # 使用
# receive_datas[IDLE] #等价于receive_datas[0]






# ==========================================
# 第四步：串口通信测试 / 运行主循环
# ==========================================
if __name__ == '__main__':
    try:
        print('开始串口通信测试 (按 Ctrl+C 退出)...')

        while True:
            # 模拟视觉识别到的特征数据
            test_flag = 1
            test_x = 320
            test_y = 240
            test_angle = 45

            # 1. 发送数据
            send_data(data1=test_flag, data2=test_x, data3=test_y, data4=test_angle)
            # print(
            #     f'已发送: Flag={test_flag}, X={test_x}, Y={test_y},'
            #     f' Angle={test_angle}'
            # )

            # 2. 接收反馈（如果有）
            receive_datas = receive_data()   # 模拟接收的数据

            # 3. 控制发送频率（避免频繁发送挤爆单片机串口缓冲区）
            time.sleep(0.05)  # 20Hz 发送频率

    except KeyboardInterrupt:
        print('\n中断程序!')

    # ==========================================
    # 第五步：释放与关闭串口资源
    # ==========================================
    finally:
        if ser and ser.isOpen():
            ser.close()
            print('串口已安全关闭。')




# ==========================================
# 不作为函数使用，用来说明大端传输和接收的数据是什么样子处理的
# ==========================================
#大端传输 16位有符号整数
def send_int16_data(num):
    """ 将一个 16位有符号 数据打包成二进制字节流并发送给单片机
        数据: -32768~32767
        将传进来的数据拆成 高八位,低八位分开的两个uint8
    """
    #将Python的有符号整数转换为 16 位补码无符号的 (高字节, 低字节)
    # & 0xFFFF 作用：将负数限制在 16 位补码范围内（如 -120 转换为 0xFF88）
    num_16bit = num & 0xFFFF

    #强制类型转换,将列表转换为bytearray类型,bytearray的元素必须是字节
    data_packet = bytearray(
        [
        #提取出高八位
        (num_16bit >> 8) & 0xFF,    #0xFF:1111 1111
        #提取出低八位
        num_16bit & 0xFF,
        ]
    )
    # 将打包好的二进制数据写入串口
    ser.write(data_packet)