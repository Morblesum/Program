"""
TOPCON眼科数据管理系统
主程序入口 - FastAPI + 后台服务
"""
import threading
import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.logger import logger
from app.core.database import init_db
from app.services import file_watcher_service, db_service
from app.api.routes import router


# ========== 全局变量 ==========
file_watcher_thread = None
latest_notification = None


# ========== 生命周期管理 ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("=" * 60)
    logger.info("TOPCON眼科数据管理系统启动中...")
    logger.info("=" * 60)

    # 1. 初始化数据库
    try:
        init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

    # 2. 启动文件监听服务
    try:
        start_file_watcher()
        logger.info("文件监听服务已启动")
    except Exception as e:
        logger.error(f"文件监听服务启动失败: {e}")
        raise

    logger.info("=" * 60)
    logger.info("系统启动完成！")
    logger.info("=" * 60)

    yield

    # 关闭时执行
    logger.info("系统关闭中...")
    stop_file_watcher()
    logger.info("系统已关闭")


# ========== FastAPI应用 ==========
app = FastAPI(
    title="TOPCON眼科数据管理系统",
    description="实时监听、解析和导出TOPCON KR-1验光数据",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api/v1", tags=["数据管理"])


# ========== 辅助函数 ==========
def _safe_str(value):
    """安全转换为字符串，None返回空字符串"""
    if value is None:
        return ""
    return str(value)


def _safe_float(value):
    """安全转换为float，None保留为None"""
    if value is None:
        return None
    return value


# ========== 文件监听管理 ==========
def start_file_watcher():
    """启动文件监听服务（后台线程）"""
    global file_watcher_thread

    def build_notification(filepath, xml_data, measurement_id):
        """从解析数据构建通知"""
        patient = xml_data.get('patient_info', {})
        refraction = xml_data.get('refraction', {})
        re = refraction.get('right_eye', {})
        le = refraction.get('left_eye', {})

        # 安全获取患者姓名
        last = patient.get('last_name')
        first = patient.get('first_name')
        if last or first:
            patient_name = f"{last or ''}{first or ''}"
        else:
            patient_name = '未知'

        return {
            'measurement_id': measurement_id,
            'patient_name': patient_name,
            'patient_id': _safe_str(patient.get('patient_id')),
            'exam_date': _safe_str(xml_data.get('exam_datetime')),
            'r_sphere': _safe_float(re.get('sphere')),
            'r_cylinder': _safe_float(re.get('cylinder')),
            'r_axis': re.get('axis'),
            'l_sphere': _safe_float(le.get('sphere')),
            'l_cylinder': _safe_float(le.get('cylinder')),
            'l_axis': le.get('axis'),
            'filename': Path(filepath).name,
        }

    def watcher_thread_func():
        """监听器线程函数"""
        try:
            def on_file_processed(filepath):
                global latest_notification
                logger.info(f"检测到新XML文件，开始处理: {filepath}")
                try:
                    from app.services import TopconXMLParser
                    parser = TopconXMLParser()
                    xml_data = parser.parse(filepath)
                    measurement_id = db_service.save_measurement_data(xml_data)
                    latest_notification = build_notification(filepath, xml_data, measurement_id)
                    logger.info(f"通知已生成: {latest_notification}")
                    logger.info(f"文件处理成功: {filepath} (记录ID: {measurement_id})")
                except Exception as e:
                    logger.error(f"文件处理失败: {filepath}, 错误: {e}")

            file_watcher_service.callback = on_file_processed
            file_watcher_service.start()

            while file_watcher_service.is_running:
                time.sleep(1)
        except Exception as e:
            logger.error(f"监听器线程异常: {e}")

    file_watcher_thread = threading.Thread(
        target=watcher_thread_func,
        daemon=True,
        name="FileWatcherThread"
    )
    file_watcher_thread.start()
    logger.info("文件监听器线程已启动")


def stop_file_watcher():
    """停止文件监听服务"""
    global file_watcher_thread

    if file_watcher_thread and file_watcher_thread.is_alive():
        logger.info("正在停止文件监听器...")
        file_watcher_service.stop()
        file_watcher_thread.join(timeout=5)
        logger.info("文件监听器已停止")


# ========== 健康检查 ==========
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "TOPCON Eye Monitor",
        "watcher_running": file_watcher_service.is_running if file_watcher_service else False
    }


# ========== 通知接口 ==========
@app.get("/api/v1/notification")
async def get_notification():
    """获取最新处理结果通知（获取后清除）"""
    global latest_notification
    if latest_notification:
        data = latest_notification
        latest_notification = None
        return {"has_new": True, "data": data}
    return {"has_new": False, "data": None}


# ========== Streamlit 启动函数 ==========
def _get_streamlit_path():
    """获取 streamlit_app.py 路径（兼容 PyInstaller 打包）"""
    import sys
    if getattr(sys, 'frozen', False):
        return str(Path(sys._MEIPASS) / 'app' / 'streamlit_app.py')
    return str(Path(__file__).parent / 'streamlit_app.py')


def _patch_importlib_metadata():
    """Monkey-patch importlib.metadata 以兼容 PyInstaller 打包环境"""
    import sys
    if not getattr(sys, 'frozen', False):
        return
    try:
        from importlib import metadata as ilm
        _known_versions = {
            'streamlit': '1.57.0', 'watchdog': '6.0.0', 'fastapi': '0.136.1',
            'starlette': '1.0.0', 'uvicorn': '0.46.0', 'pydantic': '2.13.4',
            'sqlalchemy': '2.0.49', 'openpyxl': '3.1.5', 'lxml': '6.1.0', 'pandas': '3.0.2',
        }
        _orig_version = ilm.version
        def _patched_version(package_name):
            try:
                return _orig_version(package_name)
            except Exception:
                if package_name in _known_versions:
                    return _known_versions[package_name]
                raise
        ilm.version = _patched_version
    except Exception:
        pass


def _launch_streamlit_subprocess():
    """启动 Streamlit 子进程"""
    import sys
    import subprocess
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    if getattr(sys, 'frozen', False):
        cmd = [sys.executable, '--streamlit']
    else:
        streamlit_path = _get_streamlit_path()
        cmd = [
            sys.executable, '-m', 'streamlit', 'run', streamlit_path,
            '--server.headless=true', '--server.port=8081',
            '--browser.serverAddress=localhost',
            '--browser.gatherUsageStats=false',
            '--global.developmentMode=false',
        ]
    try:
        stderr_file = open(str(log_dir / 'streamlit_subprocess.log'), 'w')
        stdout_file = open(str(log_dir / 'streamlit_stdout.log'), 'w')
        proc = subprocess.Popen(cmd, stdout=stdout_file, stderr=stderr_file)
        logger.info(f"Streamlit 子进程已启动 (PID: {proc.pid})")
        return True
    except Exception as e:
        logger.error(f"Streamlit 子进程启动失败: {e}")
        return False


def _extract_static_zip():
    """解压 streamlit 静态资源 zip 并强制注入路由"""
    import sys, os, zipfile, tempfile

    if not getattr(sys, 'frozen', False):
        return

    zip_path = os.path.join(sys._MEIPASS, 'streamlit_static.zip')
    if not os.path.exists(zip_path):
        return

    extract_dir = os.path.join(tempfile.gettempdir(), 'streamlit_static')
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

    # Patch get_static_dir so Streamlit finds our extracted static files
    import streamlit.file_util as fu
    fu.get_static_dir = lambda: extract_dir

    # Patch starlette_static_routes module-level references
    import streamlit.web.server.starlette.starlette_static_routes as ssr
    ssr.file_util = fu

    # starlette_app imports create_streamlit_static_assets_routes into its own
    # namespace at module load time — replace that binding directly
    import streamlit.web.server.starlette.starlette_app as sa
    sa.create_streamlit_static_assets_routes = ssr.create_streamlit_static_assets_routes

    # Force dev_mode off so the static-routes guard in starlette_app passes
    # Also prevent Streamlit from opening its own browser
    import streamlit.config as stconfig
    stconfig.set_option('global.developmentMode', False)
    stconfig.set_option('server.headless', True)


def _run_streamlit_main():
    """在主线程运行 Streamlit"""
    import sys, os
    _patch_importlib_metadata()
    _extract_static_zip()
    streamlit_path = _get_streamlit_path()
    sys.argv = [
        "streamlit", "run", streamlit_path,
        "--server.headless=true", "--server.port=8081",
        "--browser.serverAddress=localhost",
    ]
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_SERVER_PORT"] = "8081"
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    os.environ["STREAMLIT_SERVER_ENABLE_STATIC_SERVING"] = "true"
    from streamlit.web import bootstrap
    bootstrap.run(
        streamlit_path, is_hello=False, args=[],
        flag_options={
            'server.headless': True, 'server.port': 8081,
            'browser.serverAddress': 'localhost',
            'global.developmentMode': False,
        },
    )


def _open_browser():
    """等待 Streamlit 就绪后打开浏览器"""
    import webbrowser
    import socket
    for _ in range(30):
        time.sleep(1)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(('localhost', 8081))
            s.close()
            webbrowser.open("http://localhost:8081")
            logger.info("已打开浏览器: http://localhost:8081")
            return
        except (socket.error, ConnectionRefusedError):
            pass
    logger.warning("Streamlit 启动超时，浏览器未打开")


# ========== 主程序 ==========
if __name__ == "__main__":
    import sys
    import uvicorn

    if '--streamlit' in sys.argv:
        try:
            _run_streamlit_main()
        except SystemExit:
            pass
        sys.exit(0)

    logger.info("TOPCON眼科数据管理系统 v1.0.0")
    logger.info("后端 API: http://localhost:8088")
    logger.info("前端界面: http://localhost:8081")

    _launch_streamlit_subprocess()
    threading.Thread(target=_open_browser, daemon=True, name="BrowserOpener").start()

    logger.info("启动 FastAPI 服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8088, log_level="info")
