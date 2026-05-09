"""
TOPCON眼科数据管理系统
Streamlit前端界面
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os

# 页面配置
st.set_page_config(
    page_title="TOPCON 验光数据管理系统",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
    }
    .notification-toast {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin: 0.5rem 0 1rem 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    .stats-row {
        display: flex;
        gap: 2rem;
        justify-content: center;
        margin-bottom: 0.5rem;
    }
    .stats-item {
        text-align: center;
        padding: 0.5rem 1.5rem;
        background: #f8f9fa;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = "http://localhost:8088/api/v1"


# ========== 工具函数 ==========
def fetch_data(endpoint, params=None):
    try:
        response = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def check_notification():
    try:
        response = requests.get(f"{API_BASE}/notification", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"has_new": False, "data": None}


def delete_record(mid):
    try:
        response = requests.delete(f"{API_BASE}/measurements/{mid}", timeout=10)
        response.raise_for_status()
        return True
    except Exception:
        return False


def export_excel(columns, start_date, end_date, patient_search):
    try:
        payload = {
            "columns": columns if columns else None,
            "start_date": start_date.strftime('%Y-%m-%d %H:%M:%S') if start_date else None,
            "end_date": end_date.strftime('%Y-%m-%d %H:%M:%S') if end_date else None,
            "patient_search": patient_search if patient_search else None
        }
        response = requests.post(f"{API_BASE}/export/excel", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


# ========== 主界面 ==========
st.markdown('<h1 class="main-header">👁️ TOPCON KR-1 验光数据管理</h1>', unsafe_allow_html=True)

# ========== 通知弹窗 ==========
notification = check_notification()
if notification.get('has_new') and notification.get('data'):
    d = notification['data']
    st.markdown(f"""
    <div class="notification-toast">
        <h4>📋 新检查结果 — {d.get('patient_name', '未知')}</h4>
        <p>患者ID: {d.get('patient_id', '')} | 检查时间: {d.get('exam_date', '')}</p>
        <div style="display:flex; gap:2rem; margin-top:0.5rem;">
            <div><strong>👁️ 右眼</strong><br>球镜: {d.get('r_sphere', '-')}D | 柱镜: {d.get('r_cylinder', '-')}D | 轴位: {d.get('r_axis', '-')}°</div>
            <div><strong>👁️ 左眼</strong><br>球镜: {d.get('l_sphere', '-')}D | 柱镜: {d.get('l_cylinder', '-')}D | 轴位: {d.get('l_axis', '-')}°</div>
        </div>
        <p style="margin-top:0.5rem; font-size:0.8rem; opacity:0.8;">📁 {d.get('filename', '')}</p>
    </div>
    """, unsafe_allow_html=True)

# ========== 侧边栏 ==========
st.sidebar.header("🔍 筛选条件")

date_filter = st.sidebar.date_input("日期范围", value=[])
start_date = None
end_date = None
if len(date_filter) == 2:
    start_date = datetime.combine(date_filter[0], datetime.min.time())
    end_date = datetime.combine(date_filter[1], datetime.max.time())

patient_search = st.sidebar.text_input("患者搜索", placeholder="ID / 编号 / 姓名...")

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🔄 刷新", use_container_width=True):
        st.rerun()
with col2:
    auto_refresh = st.checkbox("自动刷新", value=True)

st.sidebar.divider()

# 导出
st.sidebar.markdown("**📥 导出Excel**")
columns_info = fetch_data("export/columns")
available_columns = columns_info['columns'] if columns_info else []
selected_columns = st.sidebar.multiselect(
    "选择导出列",
    options=[c['key'] for c in available_columns],
    default=[c['key'] for c in available_columns[:10]] if available_columns else [],
    format_func=lambda x: next((c['header'] for c in available_columns if c['key'] == x), x),
    label_visibility="collapsed"
)
if st.sidebar.button("📥 导出Excel", use_container_width=True):
    with st.spinner("导出中..."):
        result = export_excel(selected_columns, start_date, end_date, patient_search)
        if result:
            st.sidebar.success(f"✅ 已导出 {result['count']} 条")
            if os.path.exists(result['filepath']):
                with open(result['filepath'], 'rb') as f:
                    st.sidebar.download_button(
                        label="⬇️ 下载文件",
                        data=f,
                        file_name=os.path.basename(result['filepath']),
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True
                    )

st.sidebar.divider()

# 删除
st.sidebar.markdown("**🗑️ 删除记录**")
delete_id = st.sidebar.number_input("记录ID", min_value=1, step=1, label_visibility="collapsed")
if st.sidebar.button("🗑️ 删除", use_container_width=True):
    if delete_record(delete_id):
        st.sidebar.success(f"已删除 ID: {delete_id}")
        st.rerun()
    else:
        st.sidebar.error("删除失败")

# ========== 统计数据 ==========
stats = fetch_data("statistics")
if stats:
    cols = st.columns([1, 1, 3])
    with cols[0]:
        st.metric("总记录", stats['total_count'])
    with cols[1]:
        st.metric("今日新增", stats['today_count'])

# ========== 数据表格 ==========
params = {"skip": 0, "limit": 1000}
if start_date:
    params["start_date"] = start_date.strftime('%Y-%m-%d %H:%M:%S')
if end_date:
    params["end_date"] = end_date.strftime('%Y-%m-%d %H:%M:%S')
if patient_search:
    params["patient_search"] = patient_search

measurements = fetch_data("measurements", params)

if measurements:
    df = pd.DataFrame(measurements)
    df_display = df[[
        'patient_id', 'patient_no', 'exam_date',
        'r_sphere', 'r_cylinder', 'r_axis',
        'l_sphere', 'l_cylinder', 'l_axis',
        'file_created_at'
    ]].copy()
    df_display.columns = [
        '患者ID', '编号', '检查时间',
        '右球镜', '右柱镜', '右轴位',
        '左球镜', '左柱镜', '左轴位',
        '接收时间'
    ]
    st.dataframe(df_display, width="stretch", height=420, hide_index=True,
                 column_config={
                     '右球镜': st.column_config.NumberColumn(format='%.2f D'),
                     '右柱镜': st.column_config.NumberColumn(format='%.2f D'),
                     '右轴位': st.column_config.NumberColumn(format='%d °'),
                     '左球镜': st.column_config.NumberColumn(format='%.2f D'),
                     '左柱镜': st.column_config.NumberColumn(format='%.2f D'),
                     '左轴位': st.column_config.NumberColumn(format='%d °'),
                 })

    # 测量明细
    with st.expander("🔬 查看三次独立测量明细"):
        selected_id = st.selectbox(
            "选择记录",
            options=[m['id'] for m in measurements],
            format_func=lambda x: f"ID {x}"
        )
        if selected_id:
            rec = next((m for m in measurements if m['id'] == selected_id), None)
            if rec and rec.get('details'):
                for eye_label, eye_key in [('👁️ 右眼 (R)', 'R'), ('👁️ 左眼 (L)', 'L')]:
                    st.markdown(f"**{eye_label}**")
                    details = [d for d in rec['details'] if d.get('eye') == eye_key]
                    if details:
                        cols = st.columns(len(details))
                        for i, d in enumerate(details):
                            with cols[i]:
                                st.markdown(f"*第{d['list_no']}次*")
                                st.write(f"球镜: {d.get('sphere', '-')}D")
                                st.write(f"柱镜: {d.get('cylinder', '-')}D")
                                st.write(f"轴位: {d.get('axis', '-')}°")
                    else:
                        st.info("无数据")
else:
    st.info("暂无数据，请将XML文件放入程序目录")

# ========== 后台轮询 ==========
if auto_refresh:
    st.components.v1.html("""
    <script>
    (function() {
        if (window._topconPolling) return;
        window._topconPolling = true;

        var doc = window.parent.document;
        var API = 'http://localhost:8088/api/v1/notification';

        function showToast(d) {
            var old = doc.getElementById('topcon-toast');
            if (old) old.remove();
            var t = doc.createElement('div');
            t.id = 'topcon-toast';
            t.innerHTML = '<div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;'
                + 'padding:1rem 1.5rem;border-radius:12px;margin:0.5rem 0 1rem 0;'
                + 'box-shadow:0 4px 15px rgba(102,126,234,0.4);animation:fadeIn 0.3s;">'
                + '<h4>📋 新检查结果 — ' + (d.patient_name || '未知') + '</h4>'
                + '<p>患者ID: ' + (d.patient_id || '') + ' | 检查时间: ' + (d.exam_date || '') + '</p>'
                + '<div style="display:flex;gap:2rem;margin-top:0.5rem;">'
                + '<div><strong>👁️ 右眼</strong><br>球镜: ' + (d.r_sphere || '-') + 'D | 柱镜: ' + (d.r_cylinder || '-') + 'D | 轴位: ' + (d.r_axis || '-') + '°</div>'
                + '<div><strong>👁️ 左眼</strong><br>球镜: ' + (d.l_sphere || '-') + 'D | 柱镜: ' + (d.l_cylinder || '-') + 'D | 轴位: ' + (d.l_axis || '-') + '°</div>'
                + '</div>'
                + '<p style="margin-top:0.5rem;font-size:0.8rem;opacity:0.8;">📁 ' + (d.filename || '') + '</p>'
                + '</div>';
            var main = doc.querySelector('[data-testid="stAppViewContainer"]');
            if (main) main.insertBefore(t, main.firstChild);
            setTimeout(function() { t.style.opacity = '0'; t.style.transition = 'opacity 0.5s'; }, 8000);
            setTimeout(function() { if (t.parentNode) t.remove(); }, 9000);
        }

        function clickRefresh() {
            var btns = doc.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                if (btns[i].innerText && btns[i].innerText.indexOf('刷新') !== -1) {
                    btns[i].click();
                    return;
                }
            }
        }

        function poll() {
            fetch(API)
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.has_new && data.data) {
                        showToast(data.data);
                        setTimeout(clickRefresh, 600);
                    }
                })
                .catch(function(e) { console.log('poll error:', e); })
                .finally(function() { setTimeout(poll, 3000); });
        }

        setTimeout(poll, 3000);
    })();
    </script>
    """, height=0)
