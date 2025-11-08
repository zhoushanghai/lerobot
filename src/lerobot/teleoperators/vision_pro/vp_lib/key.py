import threading
from pynput import keyboard
import time

class KeyboardListener:

    def __init__(self):
        # 1. 这才是你需要的“内部的值”：一个存储按键的集合
        self._pressed_keys = set()
        self._lock = threading.Lock()
        self._listener = None
        
        # 启动监听线程
        self._listener_thread = threading.Thread(
            target=self._run_listener, 
            daemon=True # 设置为守护线程，主程序退出时自动结束
        )
        self._listener_thread.start()

    def _on_press(self, key):
        """内部回调：按键按下"""
        with self._lock:
            # 将按键对象添加到集合中
            self._pressed_keys.add(key)

    def _on_release(self, key):
        """内部回调：按键释放"""
        with self._lock:
            # 从集合中安全地移除按键
            # .discard() 在元素不存在时不会报错
            self._pressed_keys.discard(key)

    def _run_listener(self):
        print("[KeyboardListener] 后台监听线程已启动。")
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        # .run() 会阻塞此线程，直到 .stop() 被调用
        self._listener.run()
        print("[KeyboardListener] 后台监听线程已停止。")

    # --- 2. 这里是“获取这个值”的方法 ---
    @property
    def current_keys(self) -> set:
        """
        (属性) 获取当前所有被按下的按键的集合。
        这就是你需要的“当前按下的值”。
        
        用法:
        keys_set = keyboard.current_keys
        if keys_set:
            print(f"当前按下的键有: {keys_set}")
        """
        with self._lock:
            # 返回集合的副本，确保线程安全
            return self._pressed_keys.copy()
            
    def stop(self):
        if self._listener:
            self._listener.stop()

# 全局键盘监听器实例
keyboard_detect = KeyboardListener()




# test 
if __name__ == "__main__":
    while True:
        keys = keyboard_detect.current_keys
        if keys:
            print(f"当前按下的键有: {keys}")
        time.sleep(0.1)