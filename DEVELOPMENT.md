# TOPCON 眼科数据管理系统 — 开发文档

## 一、项目概述

基于 TOPCON KR-1 验光仪的 XML 数据文件，实现自动监听、解析、存储、展示和导出的全流程管理系统。

- **后端：** FastAPI (REST API)
- **前端：** Streamlit (数据仪表盘)
- **打包：** PyInstaller (单文件 EXE)
- **数据库：** SQLite (SQLAlchemy ORM)

---

## 二、技术栈

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 后端 | FastAPI + Uvicorn | 0.136.1 / 0.46.0 | REST API 服务 |
| Web 前端 | Streamlit | 1.57.0 | 数据展示界面 |
| 数据库 ORM | SQLAlchemy | 2.0.49 | 数据库操作 |
| 数据库 | SQLite | - | 本地数据存储 |
| XML 解析 | lxml | 6.1.0 | TOPCON XML 数据解析 |
| 文件监听 | watchdog | 6.0.0 | 监控新增 XML 文件 |
| Excel 导出 | openpyxl | 3.1.5 | 导出报表 |
| 数据校验 | Pydantic | 2.13.4 | API 数据模式校验 |
| 打包工具 | PyInstaller | 6.20.0 | 单文件 EXE 打包 |

---

## 三、项目结构

```
眼科程序/
├── app/
│   ├── main.py                    # FastAPI 应用主入口 + 生命周期 + 文件监听 + Streamlit 子进程
│   ├── streamlit_app.py           # Streamlit 前端界面
│   ├── api/
│   │   ├── routes.py              # REST API 路由（CRUD + 统计 + 导出）
│   │   └── schemas.py             # Pydantic 数据模型
│   ├── core/
│   │   ├── config.py              # 配置管理（读取 config.yaml）
│   │   ├── database.py            # 数据库引擎 + Session 工厂
│   │   └── logger.py              # 日志配置
│   ├── models/
│   │   ├── patient.py             # 患者 ORM 模型
│   │   └── measurement.py         # 测量记录 + 测量明细 ORM 模型
│   └── services/
│       ├── database_service.py    # 数据库业务逻辑（CRUD + 统计）
│       ├── file_watcher.py        # watchdog 文件监听服务
│       ├── file_manager.py        # XML 文件管理
│       ├── xml_parser.py          # TOPCON XML 解析器
│       └── excel_exporter.py      # Excel 导出服务
├── config.yaml                    # 运行配置（监听目录、数据库路径）
├── build.spec                     # PyInstaller 打包配置
├── requirements.txt               # Python 依赖
└── tests/
    └── test_xml_parser.py         # XML 解析器单元测试
```

---

## 四、技术要点

### 4.1 架构设计

采用 **单进程双服务** 架构：
- **主线程** 运行 FastAPI（Uvicorn ASGI 服务器），端口 8088
- **子进程** 运行 Streamlit，端口 8081
- **后台线程** 运行 watchdog 文件监听器

启动流程：
1. `__main__` → 启动 FastAPI
2. FastAPI lifespan → 初始化数据库 → 启动文件监听线程 → 启动 Streamlit 子进程
3. 浏览器自动打开 `http://localhost:8081`

### 4.2 文件监听机制

```
watchdog Observer → 监控文件系统事件
    └── FileSystemEventHandler.on_created()
        └── callback(filepath)
            ├── TopconXMLParser.parse()     # 解析 XML
            ├── DatabaseService.save()      # 存入数据库
            └── build_notification()        # 生成通知
```

- 非阻塞：监听器运行在独立 daemon 线程
- 通知机制：后端保存 `latest_notification` 全局变量，前端轮询消费后清除

### 4.3 前端自动刷新（无页面重载）

前端使用 `st.components.v1.html` 注入 JavaScript，实现后台轮询：
- 每 3 秒拉取 `/api/v1/notification`
- 有新数据时：DOM 注入弹窗 → 自动点击"刷新"按钮 → Streamlit 静默 rerun
- 弹窗 8 秒后自动消失
- 用户完全无感知，不会被打断操作

```javascript
// 核心机制：跨 iframe DOM 操作
var doc = window.parent.document;   // 访问 Streamlit 主页面
fetch(API)                           // 轮询后端通知 API
  .then(data => showToast(data))     // DOM 注入弹窗
  .then(() => clickRefresh());       // 程序化点击刷新按钮
```

### 4.4 PyInstaller 打包要点

**关键配置（build.spec）：**
```python
# 1. 自动收集子模块，避免遗漏
from PyInstaller.utils.hooks import collect_submodules
streamlit_hidden = collect_submodules('streamlit')

# 2. 静态资源打包为 zip
datas=[('streamlit_static.zip', '.')]

# 3. 子进程模式：EXE 启动 FastAPI 后，fork 一个子进程运行 Streamlit
if '--streamlit' in sys.argv:
    _run_streamlit_main()  # Streamlit 子进程入口
```

### 4.5 数据库设计

三表关系：
```
Patient (患者)
    id (PK)
    patient_id (TOPCON ID, 字符串)
    name
    ...

Measurement (测量记录)
    id (PK)
    patient_id (FK → Patient.id)
    r_sphere, r_cylinder, r_axis  (右眼)
    l_sphere, l_cylinder, l_axis  (左眼)
    ...

MeasurementDetail (三次独立测量明细)
    measurement_id (FK → Measurement.id)
    eye (R/L)
    list_no (第1/2/3次)
    sphere, cylinder, axis
```

---

## 五、问题与解决

### 问题 1：打包后 Streamlit 首页 404

**现象：** EXE 运行后打开浏览器显示 404，API 正常但界面无法访问

**根因：** Streamlit 的 `starlette_app.py` 中通过 `from ... import` 在模块加载时捕获了 `create_streamlit_static_assets_routes` 的引用。只 monkey-patch `starlette_static_routes` 模块无法影响已导入的引用。

**解决：** 同时替换两个命名空间中的引用：
```python
# 1. 替换 starlette_static_routes 模块级引用
import streamlit.web.server.starlette.starlette_static_routes as ssr
ssr.file_util = fu  # 指向解压后的静态文件

# 2. 替换 starlette_app 已导入的引用
import streamlit.web.server.starlette.starlette_app as sa
sa.create_streamlit_static_assets_routes = ssr.create_streamlit_static_assets_routes

# 3. 强制关闭 dev_mode
streamlit.config.set_option('global.developmentMode', False)
```

**知识点：** Python `from module import name` 语法会创建本地引用绑定，修改原模块的 `name` 不会影响已导入的绑定。

### 问题 2：患者 ID 显示为数据库外键而非 TOPCON ID

**现象：** 前端表格中 patient_id 显示为 1、2、3 等数字，而非 TOPCON 设备导出的真实 ID

**根因：** 两个问题叠加：
1. `database_service.py` 中返回了 `m.patient_id`（OR M 模型的 FK 字段，指向 Patient 表的主键），应返回 `m.patient.patient_id`（关联对象上的 TOPCON ID 字段）
2. Pydantic schema 中 `patient_id` 类型定义为 `Optional[int]`，将字符串 ID 强制转换

**解决：**
```python
# database_service.py — 取关联对象的字段
'patient_id': m.patient.patient_id,  # 不是 m.patient_id

# schemas.py — 类型改为字符串
patient_id: Optional[str] = None  # 不是 Optional[int]
```

### 问题 3：自动刷新导致页面频繁重载

**现象：** 前端自动刷新时整个页面闪烁，用户查看数据时被打断

**根因：** 使用 `st.rerun()` 完整重载页面

**解决：** 重构为 JavaScript 后台轮询 + DOM 弹窗 + 静默刷新：
- 页面不退刷新（`st.rerun()` 在 Streamlit 1.57+ 不再触发浏览器重载）
- 新数据通过 DOM 操作注入 Toast 弹窗
- JavaScript 自动点击刷新按钮获取最新数据

### 问题 4：EXE 双击打开两个浏览器窗口

**现象：** 启动 EXE 后弹出两个浏览器标签页

**根因：** Streamlit 自身也会检测并打开浏览器，即使传了 `--server.headless=true` 参数

**解决：** 在 Streamlit import 后强制设置配置：
```python
import streamlit.config as stconfig
stconfig.set_option('server.headless', True)           # 禁止 Streamlit 开浏览器
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"       # 环境变量双重保险
```

### 问题 5：PyInstaller 打包后缺少 Streamlit 子模块

**现象：** `ModuleNotFoundError: No module named 'streamlit.runtime.scriptrunner.magic_funcs'`

**根因：** Streamlit 模块树庞大，手动列出 hiddenimports 必然遗漏

**解决：** 使用 `collect_submodules()` 自动收集：
```python
from PyInstaller.utils.hooks import collect_submodules
streamlit_hidden = collect_submodules('streamlit')
watchdog_hidden = collect_submodules('watchdog')
starlette_hidden = collect_submodules('starlette')
hiddenimports = streamlit_hidden + watchdog_hidden + starlette_hidden + [...]
```

### 问题 6：国内无法连接 GitHub

**现象：** `git push` 报 `Failed to connect to github.com port 443`

**根因：** GitHub 在国内被墙

**解决：** 配置 git 走 Clash 代理：
```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

### 问题 7：前端 JavaScript 注入方式选择

**历程：**
1. 最初用 `st.markdown()` 写 `<script>` 标签 → Streamlit 自动过滤 script 标签，不执行
2. 改用 `st.components.v1.html()` → 可执行 JS，但通过 iframe 隔离
3. iframe 中无法直接操作主页面 → 通过 `window.parent.document` 跨 iframe 操作 DOM
4. Streamlit 1.57 起 `st.components.v1.html` 被标记为 deprecated，未来需迁移到 `st.iframe`

---

## 六、端口配置

| 服务 | 端口 | 访问地址 |
|------|------|----------|
| FastAPI 后端 | 8088 | `http://localhost:8088` |
| Streamlit 前端 | 8081 | `http://localhost:8081` |

端口在 `app/main.py` 和 `app/streamlit_app.py` 中硬编码。如需修改，需同时更改以下位置：
- `main.py`：`uvicorn.run(port=...)`, `_run_streamlit_main()`, `_launch_streamlit_subprocess()`, `_open_browser()`, logger 消息
- `streamlit_app.py`：`API_BASE` 变量, JavaScript `fetch()` URL

---

## 七、开发与构建命令

```bash
# 开发运行
python app/main.py

# 单独运行前端（调试用）
streamlit run app/streamlit_app.py --server.port 8081

# 打包 EXE
python -m PyInstaller build.spec

# 输出位置
dist/TOPCON眼科数据管理系统.exe
```

## 八、Git 配置参考

```bash
# 身份配置
git config --global user.email "your@email.com"
git config --global user.name "yourname"

# 代理配置（Clash）
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890

# 关联远程仓库
git remote add origin https://github.com/你的用户名/仓库名.git

# 推送
git push -u origin main
```

---

> 开发日期：2026-05-09 | 技术栈：Python 3.14 + FastAPI + Streamlit + SQLAlchemy + PyInstaller
