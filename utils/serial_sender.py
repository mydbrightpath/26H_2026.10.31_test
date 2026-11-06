"""RDK 串口发送工具，仅负责通信，不放图像处理。

与用户原 tool_pyserial.py 一样采用 >BBhhhhB，共 11 字节。
本文件不导入原工具，避免 import 时立即打开 Windows 的 COM3。
"""

import struct
import serial


class SerialSender:
    """持有一个串口连接，发送四个有符号整数，退出时关闭连接。

    参数：
        port：str 字符串，例如 '/dev/ttyUSB0'，按 RDK 实际设备填写。
        baudrate：int 整数，例如 115200，必须与单片机一致。

    注意：创建对象时才打开串口。串口故障直接报错，主程序 finally 释放相机；
    控制端还必须自行处理数据断流超时，不能一直使用上一帧坐标。
    """

    def __init__(self, port, baudrate):
        self.ser = serial.Serial(port=port, baudrate=baudrate,
                                 timeout=0, write_timeout=0.02)

    def send_data(self, valid, x, y, distance):
        """按约定的字段顺序发送一帧二进制数据。

        参数全部为 Python int 整数，不能传列表、数组或未转换的浮点数：
            valid：1 有效，0 无效。
            x：沿杆方向相对中心的有符号位置，单位 0.1 mm。
            y：横向粗略位置，单位 0.1 mm，主要用于观察。
            distance：沿杆到中心的绝对距离，单位 0.1 mm。

        返回：None。写入不完整、超时或字段超出 int16 范围会抛出异常。
        协议：AA AF + valid/x/y/distance（各2字节，大端有符号）+ 55。
        原协议没有校验和。接收端需要按帧头、固定长度、帧尾重新同步，
        不能认为一次串口 read 就恰好等于一帧。四个字段均须在 -32768～32767。
        """
        packet = struct.pack('>BBhhhhB', 0xAA, 0xAF, valid, x, y, distance, 0x55)
        if self.ser.write(packet) != len(packet):
            raise RuntimeError('串口数据没有完整写出')

    def close(self):
        """关闭本对象打开的串口。无参数，返回 None；可在 finally 中调用。"""
        if self.ser.is_open:
            self.ser.close()
