# controller/controller.py (模拟控制器)

import httpx
import random
import time
import logging

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- 配置 ---
BACKEND_URL = "http://localhost:8000"
# 从后端main.py获取NPC列表
NPC_IDS = ["npc_1", "npc_2", "npc_3", "npc_4", "npc_5"]
# 假设的地图边界（与前端scene尺寸匹配，需要你手动放置图片后确认）
MAP_WIDTH = 1472
MAP_HEIGHT = 1104
CHARACTER_SIZE = 50  # 角色图标的尺寸，避免跑到最边缘


def send_move_command(npc_id: str, x: int, y: int):
    """向后端发送移动指令的函数"""
    url = f"{BACKEND_URL}/command/move/{npc_id}"
    payload = {"target_x": x, "target_y": y}
    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload, timeout=5.0)
            if response.status_code == 200:
                logger.info(f"✅ 指令成功: 移动 {npc_id} 到 ({x}, {y})")
            else:
                logger.error(f"❌ 指令失败: {response.status_code} - {response.text}")
    except httpx.RequestError as e:
        logger.error(f"🔌 连接错误: 无法连接到后端 {url}。请确保后端服务器正在运行。")


def main():
    """主循环，模拟用户不断发送指令"""
    logger.info("🤖 SimVerse 控制器已启动...")
    logger.info("按下 Ctrl+C 停止。")

    while True:
        try:
            # 1. 随机选择一个NPC
            target_npc = random.choice(NPC_IDS)

            # 2. 随机生成一个目标坐标
            target_x = random.randint(0, MAP_WIDTH - CHARACTER_SIZE)
            target_y = random.randint(0, MAP_HEIGHT - CHARACTER_SIZE)

            # 3. 发送指令
            send_move_command(target_npc, target_x, target_y)

            # 4. 暂停随机时间，模拟真实用户操作间隔
            time.sleep(random.uniform(1.0, 3.0))

        except KeyboardInterrupt:
            logger.info("\n🛑 SimVerse 控制器已停止。")
            break
        except Exception as e:
            logger.error(f"发生未知错误: {e}")
            time.sleep(5)  # 出错后等待5秒再继续


if __name__ == "__main__":
    main()
