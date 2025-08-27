# backend/main.py (后端服务器 - FastAPI)

import asyncio
import json
import logging
from typing import Dict, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="SimVerse Engine - Backend")

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有HTTP头
)

# --- 应用启动事件 ---
@app.on_event("startup")
async def startup_event():
    """应用启动时执行的事件处理"""
    logger.info("🚀 SimVerse Engine 后端服务启动中...")
    logger.info("📡 WebSocket 端点: ws://localhost:8000/ws")
    logger.info("🎮 指令端点: http://localhost:8000/command/move/{npc_id}")
    logger.info("🌐 根路径: http://localhost:8000/")
    logger.info("⏰ NPC移动超时: 30秒")
    logger.info("✅ 后端服务已启动完成，正在监听端口 8000")
    
    # 启动超时检查任务
    asyncio.create_task(periodic_timeout_check())

async def periodic_timeout_check():
    """定期检查NPC移动超时"""
    while True:
        try:
            check_movement_timeouts()
            await asyncio.sleep(10)  # 每10秒检查一次
        except Exception as e:
            logger.error(f"❌ 超时检查任务失败: {e}")
            await asyncio.sleep(10)  # 出错后等待10秒再继续

# --- 根路径欢迎页 ---
@app.get("/", response_class=HTMLResponse)
async def root():
    """
    根路径欢迎页，提供后端状态信息和API端点说明
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SimVerse Engine - 后端服务</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #1e3c72, #2a5298);
                color: white;
                margin: 0;
                padding: 40px;
                min-height: 100vh;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 16px;
                padding: 40px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            h1 {
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                background: linear-gradient(45deg, #fff, #e0e0e0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .status {
                background: rgba(3, 201, 136, 0.2);
                border: 1px solid #03c988;
                border-radius: 8px;
                padding: 15px;
                margin: 20px 0;
                text-align: center;
            }
            .endpoint {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 20px;
                margin: 15px 0;
                border-left: 4px solid #03a9f4;
            }
            .endpoint h3 {
                margin-top: 0;
                color: #03a9f4;
            }
            .endpoint code {
                background: rgba(0, 0, 0, 0.3);
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
            }
            .footer {
                text-align: center;
                margin-top: 30px;
                opacity: 0.7;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 SimVerse Engine 后端服务</h1>
            
            <div class="status">
                <h2>✅ 服务状态：运行正常</h2>
                <p>后端服务已成功启动，正在监听端口 8000</p>
            </div>
            
            <div class="endpoint">
                <h3>🔌 WebSocket 连接端点</h3>
                <p><code>ws://localhost:8000/ws</code></p>
                <p>用于前端客户端建立实时连接，接收游戏状态更新</p>
            </div>
            
            <div class="endpoint">
                <h3>🎮 指令接收端点</h3>
                <p><code>POST /command/move/{npc_id}</code></p>
                <p>接收来自控制器的移动指令，格式：<code>{"target_x": int, "target_y": int}</code></p>
            </div>
            
            <div class="endpoint">
                <h3>📊 API 文档</h3>
                <p><a href="/docs" style="color: #03a9f4;">Swagger UI 文档</a></p>
                <p><a href="/redoc" style="color: #03a9f4;">ReDoc 文档</a></p>
            </div>
            
            <div class="footer">
                <p>SimVerse Engine - 轻量级2D实时模拟引擎</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# --- 连接管理器 ---
class ConnectionManager:
    """管理WebSocket连接的单例类"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_connections: Dict[str, WebSocket] = {}  # client_id到WebSocket的映射
        self.connection_counter = 0  # 用于生成唯一的client_id

    async def connect(self, websocket: WebSocket) -> str:
        """接受并添加一个新的WebSocket连接，返回分配的client_id"""
        await websocket.accept()
        self.connection_counter += 1
        client_id = f"client_{self.connection_counter}_{int(time.time())}"
        
        self.active_connections.append(websocket)
        self.client_connections[client_id] = websocket
        
        logger.info(f"新客户端连接: {client_id}, 总连接数: {len(self.active_connections)}")
        return client_id

    def disconnect(self, websocket: WebSocket, client_id: str = None):
        """断开并移除一个WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # 如果提供了client_id，从映射中移除
        if client_id and client_id in self.client_connections:
            del self.client_connections[client_id]
        else:
            # 如果没有提供client_id，遍历查找并移除
            to_remove = []
            for cid, conn in self.client_connections.items():
                if conn == websocket:
                    to_remove.append(cid)
            
            for cid in to_remove:
                del self.client_connections[cid]
        
        logger.info(f"客户端断开: {client_id or 'unknown'}, 剩余连接: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """向所有连接的客户端广播消息"""
        disconnected_connections = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except RuntimeError as e:
                # 连接已关闭，标记为需要移除
                if "Cannot call" in str(e):
                    disconnected_connections.append(connection)
                else:
                    logger.error(f"发送消息时发生错误: {e}")
            except Exception as e:
                logger.error(f"发送消息时发生未知错误: {e}")
                disconnected_connections.append(connection)
        
        # 移除断开的连接
        for conn in disconnected_connections:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
                # 同时从client_connections中移除
                to_remove = []
                for cid, websocket_conn in self.client_connections.items():
                    if websocket_conn == conn:
                        to_remove.append(cid)
                
                for cid in to_remove:
                    del self.client_connections[cid]
                
                logger.info(f"清理断开的连接，剩余 {len(self.active_connections)} 个连接")

manager = ConnectionManager()

# --- 地图和障碍物定义 (基于map_with_grid.png精确标定) ---
# 地图尺寸（基于assets/game-map.png的实际尺寸）
MAP_WIDTH_PX = 1472
MAP_HEIGHT_PX = 1104
# 网格化精度：每个网格单元代表的像素数
GRID_SIZE = 32
# 计算网格维度
GRID_WIDTH = MAP_WIDTH_PX // GRID_SIZE  # 结果: 46
GRID_HEIGHT = MAP_HEIGHT_PX // GRID_SIZE  # 结果: 34

# 创建二维数组表示地图网格（1=可通行, 0=障碍物）
def create_empty_grid() -> List[List[int]]:
    """创建一个空的地图网格，默认全部可通行"""
    return [[1 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

def add_rect_obstacle(matrix: List[List[int]], x: int, y: int, w: int, h: int) -> None:
    """
    在地图网格中添加矩形障碍物
    
    参数:
        matrix: 地图网格二维数组
        x, y: 矩形左上角的网格坐标
        w, h: 矩形的宽度和高度（网格单位）
    """
    for row in range(max(0, y), min(GRID_HEIGHT, y + h)):
        for col in range(max(0, x), min(GRID_WIDTH, x + w)):
            matrix[row][col] = 0  # 标记为障碍物

# 创建地图网格并标记障碍物
MAP_GRID = create_empty_grid()

# === 精确障碍物定义 (基于map_with_grid.png施工图) ===

# === 建筑物 ===
# --- 右侧的大房子 ---
# 位置：地图右侧中央的大型建筑
# 网格坐标：x=34, y=11, 宽度=13格, 高度=16格
add_rect_obstacle(MAP_GRID, 34, 11, 13, 16)

# --- 左下角的小房子 ---
# 位置：地图左下角的小型建筑
# 网格坐标：x=3, y=28, 宽度=6格, 高度=4格
add_rect_obstacle(MAP_GRID, 3, 28, 6, 4)

# === 树木 (精确标定) ===
# --- 大树1（右侧大房子旁）---
# 位置：大房子右侧的大树
# 网格坐标：x=47, y=14, 宽度=3格, 高度=3格（树干）
add_rect_obstacle(MAP_GRID, 47, 14, 3, 3)
# 树冠部分
add_rect_obstacle(MAP_GRID, 46, 11, 5, 3)

# --- 大树2（地图中上部）---
# 位置：地图中上部的单独大树
# 网格坐标：x=22, y=5, 宽度=3格, 高度=3格（树干）
add_rect_obstacle(MAP_GRID, 22, 5, 3, 3)
# 树冠部分
add_rect_obstacle(MAP_GRID, 20, 2, 7, 3)

# --- 大树3（地图中部）---
# 位置：地图中部的大树
# 网格坐标：x=10, y=15, 宽度=3格, 高度=3格（树干）
add_rect_obstacle(MAP_GRID, 10, 15, 3, 3)
# 树冠部分
add_rect_obstacle(MAP_GRID, 8, 12, 7, 3)

# --- 大树4（地图左侧）---
# 位置：地图左侧的大树
# 网格坐标：x=2, y=20, 宽度=3格, 高度=3格（树干）
add_rect_obstacle(MAP_GRID, 2, 20, 3, 3)
# 树冠部分
add_rect_obstacle(MAP_GRID, 1, 17, 5, 3)

# === 地形障碍 ===
# --- 小河 ---
# 位置：地图底部的河流，横贯东西
# 网格坐标：x=1, y=32, 宽度=46格, 高度=2格
add_rect_obstacle(MAP_GRID, 1, 32, 46, 2)

# === 田埂系统 (精确标定) ===
# --- 主水平田埂 ---
# 位置：地图中部的水平主田埂
# 网格坐标：x=6, y=18, 宽度=32格, 高度=1格
add_rect_obstacle(MAP_GRID, 6, 18, 32, 1)

# --- 次水平田埂（上方）---
# 位置：地图上部的水平田埂
# 网格坐标：x=15, y=8, 宽度=20格, 高度=1格
add_rect_obstacle(MAP_GRID, 15, 8, 20, 1)

# --- 垂直田埂1（左侧）---
# 位置：地图左侧的垂直田埂
# 网格坐标：x=15, y=9, 宽度=1格, 高度=8格
add_rect_obstacle(MAP_GRID, 15, 9, 1, 8)

# --- 垂直田埂2（中部）---
# 位置：地图中部的垂直田埂
# 网格坐标：x=30, y=12, 宽度=1格, 高度=5格
add_rect_obstacle(MAP_GRID, 30, 12, 1, 5)

# --- 垂直田埂3（右侧）---
# 位置：地图右侧的垂直田埂
# 网格坐标：x=42, y=14, 宽度=1格, 高度=3格
add_rect_obstacle(MAP_GRID, 42, 14, 1, 3)

# === 其他障碍物 ===
# --- 石头群1（地图中上部）---
# 位置：地图中上部的石头群
# 网格坐标：x=35, y=6, 宽度=2格, 高度=2格
add_rect_obstacle(MAP_GRID, 35, 6, 2, 2)

# --- 石头群2（地图中部）---
# 位置：地图中部的石头群
# 网格坐标：x=18, y=22, 宽度=2格, 高度=2格
add_rect_obstacle(MAP_GRID, 18, 22, 2, 2)

# --- 灌木丛1（地图左侧）---
# 位置：地图左侧的灌木丛
# 网格坐标：x=8, y=25, 宽度=3格, 高度=2格
add_rect_obstacle(MAP_GRID, 8, 25, 3, 2)

# --- 灌木丛2（地图右侧）---
# 位置：地图右侧的灌木丛
# 网格坐标：x=38, y=25, 宽度=3格, 高度=2格
add_rect_obstacle(MAP_GRID, 38, 25, 3, 2)

# --- 游戏状态管理 ---
# 内存中的游戏世界状态
GAME_STATE: Dict[str, Dict] = {
    "npc_1": {"id": "npc_1", "name": "玩家1", "x": 150, "y": 250, "type": "player", "state": "idle"},
    "npc_2": {"id": "npc_2", "name": "玩家2", "x": 300, "y": 400, "type": "player", "state": "idle"},
    "npc_3": {"id": "npc_3", "name": "守卫", "x": 200, "y": 500, "type": "guard", "state": "idle"},
    "npc_4": {"id": "npc_4", "name": "商人", "x": 450, "y": 350, "type": "npc", "state": "idle"},
    "npc_5": {"id": "npc_5", "name": "向导", "x": 400, "y": 200, "type": "npc", "state": "idle"},
}

# --- A*寻路系统初始化 ---
# 使用地图网格初始化寻路网格
PATH_GRID = Grid(matrix=MAP_GRID)
# 创建A*寻路器，允许对角线移动
FINDER = AStarFinder(diagonal_movement=DiagonalMovement.always)

# --- NPC状态超时管理 ---
# NPC移动超时时间（秒）
MOVEMENT_TIMEOUT = 30  # 30秒后自动重置状态
# NPC状态开始时间记录
NPC_STATE_START_TIMES: Dict[str, float] = {}

def pixel_to_grid(x: int, y: int) -> tuple[int, int]:
    """将像素坐标转换为网格坐标"""
    grid_x = x // GRID_SIZE
    grid_y = y // GRID_SIZE
    return grid_x, grid_y

def grid_to_pixel(grid_x: int, grid_y: int) -> tuple[int, int]:
    """将网格坐标转换为像素坐标（转换为网格中心点）"""
    pixel_x = grid_x * GRID_SIZE + GRID_SIZE // 2
    pixel_y = grid_y * GRID_SIZE + GRID_SIZE // 2
    return pixel_x, pixel_y

def convert_path_to_pixels(path: List[tuple[int, int]]) -> List[Dict[str, int]]:
    """
    将网格坐标路径转换为像素坐标路径
    
    参数:
        path: 网格坐标路径列表
        
    返回:
        像素坐标路径列表，每个点包含x和y坐标
    """
    pixel_path = []
    for grid_x, grid_y in path:
        pixel_x, pixel_y = grid_to_pixel(grid_x, grid_y)
        pixel_path.append({"x": pixel_x, "y": pixel_y})
    return pixel_path

import time

def check_movement_timeouts():
    """
    检查NPC移动超时并自动重置状态
    """
    current_time = time.time()
    timed_out_npcs = []
    
    for npc_id, start_time in NPC_STATE_START_TIMES.items():
        if current_time - start_time > MOVEMENT_TIMEOUT:
            timed_out_npcs.append(npc_id)
    
    for npc_id in timed_out_npcs:
        if npc_id in GAME_STATE and GAME_STATE[npc_id]["state"] == "walking":
            logger.warning(f"⏰ NPC {npc_id} 移动超时({MOVEMENT_TIMEOUT}秒)，自动重置状态")
            GAME_STATE[npc_id]["state"] = "idle"
            del NPC_STATE_START_TIMES[npc_id]
            
            # 广播状态更新
            state_update = {
                "action": "state_update",
                "data": GAME_STATE
            }
            asyncio.create_task(manager.broadcast(json.dumps(state_update)))

# --- WebSocket 端点 ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """处理前端渲染客户端的WebSocket连接"""
    client_id = await manager.connect(websocket)
    
    # 客户端初次连接时，发送连接确认消息和当前完整游戏状态
    connection_message = {
        "action": "connection_established",
        "client_id": client_id,
        "message": "成功连接到SimVerse Engine",
        "game_state": GAME_STATE
    }
    await websocket.send_text(json.dumps(connection_message))
    
    try:
        while True:
            # 接收来自客户端的消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理来自前端的移动完成事件
            if message.get("event") == "move_complete":
                npc_id = message.get("npc_id")
                await handle_move_complete(npc_id)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
        logger.info(f"客户端 {client_id} 已断开连接。")
    except Exception as e:
        logger.error(f"WebSocket消息处理错误: {str(e)}")
        manager.disconnect(websocket, client_id)

async def handle_move_complete(npc_id: str):
    """
    处理前端发来的移动完成事件
    
    参数:
        npc_id: 完成移动的NPC ID
    """
    if npc_id not in GAME_STATE:
        logger.warning(f"❌ 收到未知NPC的移动完成事件: {npc_id}")
        return
    
    npc = GAME_STATE[npc_id]
    npc_name = npc["name"]
    
    logger.info(f"✅ 收到NPC {npc_name} ({npc_id}) 的移动完成事件")
    
    # 将NPC状态恢复为idle
    npc["state"] = "idle"
    # 清理状态时间记录
    if npc_id in NPC_STATE_START_TIMES:
        del NPC_STATE_START_TIMES[npc_id]
    
    # 构建状态更新消息
    state_update = {
        "action": "state_update",
        "data": GAME_STATE
    }
    
    # 向所有前端广播状态更新
    logger.info(f"📡 向 {len(manager.active_connections)} 个客户端广播状态更新")
    await manager.broadcast(json.dumps(state_update))

# --- 状态管理API端点 ---
@app.post("/admin/reset_npc_state/{npc_id}")
async def reset_npc_state(npc_id: str):
    """
    管理员API：重置指定NPC的状态为idle
    用于处理状态卡死的情况
    """
    if npc_id not in GAME_STATE:
        return JSONResponse(status_code=404, content={"message": f"错误: NPC ID '{npc_id}' 不存在"})
    
    npc = GAME_STATE[npc_id]
    old_state = npc["state"]
    npc["state"] = "idle"
    # 清理状态时间记录
    if npc_id in NPC_STATE_START_TIMES:
        del NPC_STATE_START_TIMES[npc_id]
    
    logger.info(f"🔧 重置NPC {npc['name']} ({npc_id}) 状态: {old_state} → idle")
    
    # 广播状态更新
    state_update = {
        "action": "state_update",
        "data": GAME_STATE
    }
    await manager.broadcast(json.dumps(state_update))
    
    return JSONResponse(status_code=200, content={"message": f"NPC {npc['name']} 状态已重置为idle"})

@app.get("/admin/npc_states")
async def get_npc_states():
    """
    管理员API：获取所有NPC的当前状态
    """
    states = {}
    for npc_id, npc in GAME_STATE.items():
        states[npc_id] = {
            "name": npc["name"],
            "state": npc["state"],
            "position": {"x": npc["x"], "y": npc["y"]}
        }
    
    return JSONResponse(status_code=200, content={"npc_states": states})

# --- HTTP API 指令端点 ---
from pydantic import BaseModel

class MoveCommand(BaseModel):
    target_x: int
    target_y: int

class InteractiveMoveCommand(BaseModel):
    npc_id: str
    target_x: int
    target_y: int

@app.post("/command/move/{npc_id}")
async def move_npc(npc_id: str, command: MoveCommand):
    """
    接收来自控制器（模拟手机端）的移动指令
    使用A*算法进行路径查找，然后向前端发送路径指令执行动画
    """
    # 检查NPC是否存在
    if npc_id not in GAME_STATE:
        logger.warning(f"❌ 无效的NPC ID: '{npc_id}'，当前可用的NPC: {list(GAME_STATE.keys())}")
        return JSONResponse(status_code=404, content={"message": f"错误: NPC ID '{npc_id}' 不存在"})
    
    npc = GAME_STATE[npc_id]
    npc_name = npc["name"]
    
    # 检查NPC状态是否为idle
    if npc["state"] != "idle":
        logger.warning(f"❌ NPC {npc_name} ({npc_id}) 当前状态为 '{npc['state']}'，无法执行移动指令")
        return JSONResponse(
            status_code=409, 
            content={"message": f"错误: NPC {npc_name} 正在移动中，请等待完成"}
        )
    
    try:
        # 将像素坐标转换为网格坐标
        start_grid_x, start_grid_y = pixel_to_grid(npc["x"], npc["y"])
        target_grid_x, target_grid_y = pixel_to_grid(command.target_x, command.target_y)
        
        # 边界检查
        start_grid_x = max(0, min(GRID_WIDTH - 1, start_grid_x))
        start_grid_y = max(0, min(GRID_HEIGHT - 1, start_grid_y))
        target_grid_x = max(0, min(GRID_WIDTH - 1, target_grid_x))
        target_grid_y = max(0, min(GRID_HEIGHT - 1, target_grid_y))
        
        logger.info(f"🎮 收到移动指令: {npc_name} ({npc_id})")
        logger.info(f"📍 像素坐标: ({npc['x']}, {npc['y']}) → ({command.target_x}, {command.target_y})")
        logger.info(f"🗂️ 网格坐标: ({start_grid_x}, {start_grid_y}) → ({target_grid_x}, {target_grid_y})")
        
        # 使用A*算法查找路径
        start_node = PATH_GRID.node(start_grid_x, start_grid_y)
        end_node = PATH_GRID.node(target_grid_x, target_grid_y)
        
        path, runs = FINDER.find_path(start_node, end_node, PATH_GRID)
        
        if path:
            logger.info(f"🛤️ A*寻路成功: 找到包含{len(path)}个节点的路径，耗时{runs}次运行")
            
            # 将网格坐标路径转换为像素坐标路径
            pixel_path = convert_path_to_pixels(path)
            
            # 将NPC状态设置为walking（表示正在执行动画）
            npc["state"] = "walking"
            # 记录状态开始时间
            NPC_STATE_START_TIMES[npc_id] = time.time()
            
            # 构建路径指令消息
            path_command = {
                "action": "move_along_path",
                "data": {
                    "npc_id": npc_id,
                    "path": pixel_path
                }
            }
            
            # 向所有前端广播路径指令
            logger.info(f"📡 向 {len(manager.active_connections)} 个客户端广播路径指令")
            await manager.broadcast(json.dumps(path_command))
            
            return JSONResponse(
                status_code=200, 
                content={
                    "message": f"指令已执行: {npc_name} 开始沿路径移动到 ({command.target_x}, {command.target_y})",
                    "path_length": len(path),
                    "action": "path_command_sent"
                }
            )
        else:
            logger.warning(f"❌ A*寻路失败: 无法从 ({start_grid_x}, {start_grid_y}) 到达 ({target_grid_x}, {target_grid_y})")
            return JSONResponse(
                status_code=400,
                content={"message": f"错误: 无法找到从当前位置到目标位置的可行路径"}
            )
            
    except Exception as e:
        logger.error(f"❌ 移动指令处理失败: {str(e)}")
        # 确保NPC状态恢复为idle
        if npc_id in GAME_STATE:
            GAME_STATE[npc_id]["state"] = "idle"
        return JSONResponse(
            status_code=500,
            content={"message": f"内部错误: 移动指令处理失败"}
        )

@app.post("/command/interactive_move")
async def interactive_move_npc(command: InteractiveMoveCommand):
    """
    交互式移动指令端点，用于Web控制器
    接收包含npc_id、target_x和target_y的完整移动指令
    """
    npc_id = command.npc_id
    
    # 检查NPC是否存在
    if npc_id not in GAME_STATE:
        logger.warning(f"❌ 无效的NPC ID: '{npc_id}'，当前可用的NPC: {list(GAME_STATE.keys())}")
        return JSONResponse(status_code=404, content={"message": f"错误: NPC ID '{npc_id}' 不存在"})
    
    npc = GAME_STATE[npc_id]
    npc_name = npc["name"]
    
    # 检查NPC状态是否为idle
    if npc["state"] != "idle":
        logger.warning(f"❌ NPC {npc_name} ({npc_id}) 当前状态为 '{npc['state']}'，无法执行移动指令")
        return JSONResponse(
            status_code=409, 
            content={"message": f"错误: NPC {npc_name} 正在移动中，请等待完成"}
        )
    
    try:
        # 将像素坐标转换为网格坐标
        start_grid_x, start_grid_y = pixel_to_grid(npc["x"], npc["y"])
        target_grid_x, target_grid_y = pixel_to_grid(command.target_x, command.target_y)
        
        # 边界检查
        start_grid_x = max(0, min(GRID_WIDTH - 1, start_grid_x))
        start_grid_y = max(0, min(GRID_HEIGHT - 1, start_grid_y))
        target_grid_x = max(0, min(GRID_WIDTH - 1, target_grid_x))
        target_grid_y = max(0, min(GRID_HEIGHT - 1, target_grid_y))
        
        logger.info(f"🎮 收到交互式移动指令: {npc_name} ({npc_id})")
        logger.info(f"📍 像素坐标: ({npc['x']}, {npc['y']}) → ({command.target_x}, {command.target_y})")
        logger.info(f"🗂️ 网格坐标: ({start_grid_x}, {start_grid_y}) → ({target_grid_x}, {target_grid_y})")
        
        # 使用A*算法查找路径
        start_node = PATH_GRID.node(start_grid_x, start_grid_y)
        end_node = PATH_GRID.node(target_grid_x, target_grid_y)
        
        path, runs = FINDER.find_path(start_node, end_node, PATH_GRID)
        
        if path:
            logger.info(f"🛤️ A*寻路成功: 找到包含{len(path)}个节点的路径，耗时{runs}次运行")
            
            # 将网格坐标路径转换为像素坐标路径
            pixel_path = convert_path_to_pixels(path)
            
            # 将NPC状态设置为walking（表示正在执行动画）
            npc["state"] = "walking"
            # 记录状态开始时间
            NPC_STATE_START_TIMES[npc_id] = time.time()
            
            # 构建路径指令消息
            path_command = {
                "action": "move_along_path",
                "data": {
                    "npc_id": npc_id,
                    "path": pixel_path
                }
            }
            
            # 向所有前端广播路径指令
            logger.info(f"📡 向 {len(manager.active_connections)} 个客户端广播路径指令")
            await manager.broadcast(json.dumps(path_command))
            
            return JSONResponse(
                status_code=200, 
                content={
                    "message": f"指令已执行: {npc_name} 开始沿路径移动到 ({command.target_x}, {command.target_y})",
                    "path_length": len(path),
                    "action": "path_command_sent"
                }
            )
        else:
            logger.warning(f"❌ A*寻路失败: 无法从 ({start_grid_x}, {start_grid_y}) 到达 ({target_grid_x}, {target_grid_y})")
            return JSONResponse(
                status_code=400,
                content={"message": f"错误: 无法找到从当前位置到目标位置的可行路径"}
            )
            
    except Exception as e:
        logger.error(f"❌ 交互式移动指令处理失败: {str(e)}")
        # 确保NPC状态恢复为idle
        if npc_id in GAME_STATE:
            GAME_STATE[npc_id]["state"] = "idle"
        return JSONResponse(
            status_code=500,
            content={"message": f"内部错误: 移动指令处理失败"}
        )