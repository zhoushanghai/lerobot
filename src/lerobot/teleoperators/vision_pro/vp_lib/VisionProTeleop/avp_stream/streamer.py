import grpc
from avp_stream.grpc_msg import * 
from threading import Thread
from avp_stream.utils.grpc_utils import * 
import time 
import numpy as np 


YUP2ZUP = np.array([[[1, 0, 0, 0], 
                    [0, 0, -1, 0], 
                    [0, 1, 0, 0],
                    [0, 0, 0, 1]]], dtype = np.float64)


class VisionProStreamer:

    def __init__(self, ip, record = True): 

        # Vision Pro IP 
        self.ip = ip
        self.record = record 
        self.recording = [] 
        self.latest = None 
        self.axis_transform = YUP2ZUP
        self.start_streaming()

    def start_streaming(self): 

        stream_thread = Thread(target = self.stream)
        stream_thread.daemon = True  # 设置为守护线程，主程序退出时自动退出
        stream_thread.start() 
        
        # 添加超时机制，避免无限等待
        timeout = 10  # 10秒超时
        elapsed = 0
        while self.latest is None and elapsed < timeout: 
            time.sleep(0.1)
            elapsed += 0.1
        
        if self.latest is None:
            raise ConnectionError(
                f"Failed to connect to Vision Pro at {self.ip}:12345 within {timeout} seconds. "
                "Please check:\n"
                "1. Vision Pro device is running and connected to the same network\n"
                "2. Vision Pro gRPC server is running on port 12345\n"
                "3. IP address is correct\n"
                "4. Network connectivity is working\n"
                "Alternatively, use 'playback' mode with a recording file."
            )
        
        print(' == DATA IS FLOWING IN! ==')
        print('Ready to start streaming.') 


    def stream(self): 

        request = handtracking_pb2.HandUpdate()
        try:
            with grpc.insecure_channel(f"{self.ip}:12345") as channel:
                stub = handtracking_pb2_grpc.HandTrackingServiceStub(channel)
                responses = stub.StreamHandUpdates(request)
                for response in responses:
                    transformations = {
                        "left_wrist": self.axis_transform @  process_matrix(response.left_hand.wristMatrix),
                        "right_wrist": self.axis_transform @  process_matrix(response.right_hand.wristMatrix),
                        "left_fingers":   process_matrices(response.left_hand.skeleton.jointMatrices),
                        "right_fingers":  process_matrices(response.right_hand.skeleton.jointMatrices),
                        "head": rotate_head(self.axis_transform @  process_matrix(response.Head)) , 
                        "left_pinch_distance": get_pinch_distance(response.left_hand.skeleton.jointMatrices),
                        "right_pinch_distance": get_pinch_distance(response.right_hand.skeleton.jointMatrices),
                        # "rgb": response.rgb, # TODO: should figure out how to get the rgb image from vision pro 
                    }
                    transformations["right_wrist_roll"] = get_wrist_roll(transformations["right_wrist"])
                    transformations["left_wrist_roll"] = get_wrist_roll(transformations["left_wrist"])
                    if self.record: 
                        self.recording.append(transformations)
                    self.latest = transformations 

        except Exception as e:
            print(f"An error occurred while connecting to Vision Pro: {e}")
            # 不设置 self.latest，让超时机制触发
            # 异常已在超时检查中处理，这里只记录错误 

    def get_latest(self): 
        return self.latest
        
    def get_recording(self): 
        return self.recording
    

if __name__ == "__main__": 

    streamer = VisionProStreamer(ip = '10.29.230.57')
    while True: 

        latest = streamer.get_latest()
        print(latest)