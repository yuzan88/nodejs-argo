# streamlit.py
# Logic-only port of index.js for Streamlit Cloud
# Author: 老王专用修正版
# 功能：生成配置文件、订阅、上传节点、提取 Argo 域名、添加访问任务
# 注意：Streamlit 环境无法运行二进制文件，仅用于逻辑和界面操作。

import os
import re
import json
import base64
import textwrap
import time
from pathlib import Path
from typing import Optional

import requests
import streamlit as st

st.set_page_config(page_title="Merge-Sub 配置管理面板", layout="wide")

# ========== 工具函数 ==========
def env_default(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

def generate_random_name() -> str:
    import random, string
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(6))

def log(msg: str):
    now = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{now}] {msg}")
    if len(st.session_state.logs) > 300:
        st.session_state.logs = st.session_state.logs[-300:]

def download_response_file(filename: str, content: bytes):
    st.download_button(label=f"📄 下载 {filename}", data=content, file_name=filename)

# ========== 初始化状态 ==========
if "logs" not in st.session_state:
    st.session_state.logs = []

if "generated" not in st.session_state:
    st.session_state.generated = {}

# ========== 侧边栏配置 ==========
st.sidebar.title("🔧 环境变量设置")

UPLOAD_URL = st.sidebar.text_input("UPLOAD_URL", value=env_default("UPLOAD_URL", ""))
PROJECT_URL = st.sidebar.text_input("PROJECT_URL", value=env_default("PROJECT_URL", ""))
AUTO_ACCESS = st.sidebar.checkbox("AUTO_ACCESS (自动保活)", value=(env_default("AUTO_ACCESS", "false").lower() == "true"))
FILE_PATH = st.sidebar.text_input("FILE_PATH", value=env_default("FILE_PATH", "./tmp"))
SUB_PATH = st.sidebar.text_input("SUB_PATH", value=env_default("SUB_PATH", "sub"))
UUID = st.sidebar.text_input("UUID", value=env_default("UUID", "bb3d9936-6788-448d-95bf-b45f219c2efd"))
NEZHA_SERVER = st.sidebar.text_input("NEZHA_SERVER", value=env_default("NEZHA_SERVER", "ycv.dpdns.org:8008"))
NEZHA_PORT = st.sidebar.text_input("NEZHA_PORT", value=env_default("NEZHA_PORT", ""))
NEZHA_KEY = st.sidebar.text_input("NEZHA_KEY", value=env_default("NEZHA_KEY", "uK6lptvEoZ7TsX6yzjOxSd3RYeGCHCJj"))
ARGO_DOMAIN = st.sidebar.text_input("ARGO_DOMAIN", value=env_default("ARGO_DOMAIN", "py.dajb.netlib.re"))
ARGO_AUTH = st.sidebar.text_area("ARGO_AUTH", value=env_default("ARGO_AUTH", "eyJhIjoiMTZlZDI2MTFjNGE5ZGYzYjQ5NWNjYzA4NWU2MWVkN2YiLCJ0IjoiYzM5ZWU3NjYtMGU1YS00MTQzLTk1YWEtZjA5MDdhNjZmMjNmIiwicyI6Ik5ESmpaRFEyTmpFdE5tTXdNQzAwTVRrMExUazBPVFl0WkdWbE9EazRNRFpsWVdKaiJ9"), height=100)
ARGO_PORT = st.sidebar.text_input("ARGO_PORT", value=env_default("ARGO_PORT", "8001"))
CFIP = st.sidebar.text_input("CFIP", value=env_default("CFIP", "cdns.doon.eu.org"))
CFPORT = st.sidebar.text_input("CFPORT", value=env_default("CFPORT", "443"))
NAME = st.sidebar.text_input("NAME", value=env_default("NAME", "Streamlit"))

architecture = st.sidebar.selectbox("系统架构 (仅用于URL参考)", ["amd", "arm"], index=0)

# ========== 页面标题 ==========
st.title("🌐 Merge-Sub Streamlit 配置生成工具")
st.caption("此应用用于生成配置文件、上传节点与订阅信息。⚠️ Streamlit 环境不运行真实代理进程。")

# ========== 生成配置文件 ==========
st.header("1️⃣ 生成 config.json (XRAY配置)")

if st.button("生成 config.json"):
    cfg = {
        "log": {"access": "/dev/null", "error": "/dev/null", "loglevel": "none"},
        "inbounds": [
            {"port": int(ARGO_PORT), "protocol": "vless", "settings": {"clients": [{"id": UUID, "flow": "xtls-rprx-vision"}], "decryption": "none", "fallbacks": [{"dest": 3001}, {"path": "/vless-argo", "dest": 3002}, {"path": "/vmess-argo", "dest": 3003}, {"path": "/trojan-argo", "dest": 3004}]}, "streamSettings": {"network": "tcp"}},
        ],
        "dns": {"servers": ["https+local://8.8.8.8/dns-query"]},
        "outbounds": [{"protocol": "freedom"}, {"protocol": "blackhole"}]
    }
    json_bytes = json.dumps(cfg, indent=2).encode("utf-8")
    st.session_state.generated["config.json"] = json_bytes
    log("✅ 生成 config.json 成功")
    download_response_file("config.json", json_bytes)

# ========== 生成哪吒配置 ==========
st.header("2️⃣ 生成 config.yaml (哪吒客户端)")

if st.button("生成 config.yaml"):
    tls_ports = {"443", "8443", "2096", "2087", "2083", "2053"}
    port_token = NEZHA_SERVER.split(":")[-1] if NEZHA_SERVER else ""
    nezhatls = "true" if port_token in tls_ports else "false"
    yaml_content = textwrap.dedent(f"""
    client_secret: {NEZHA_KEY}
    debug: false
    disable_auto_update: true
    disable_command_execute: false
    server: {NEZHA_SERVER}
    tls: {nezhatls}
    uuid: {UUID}
    """)
    st.session_state.generated["config.yaml"] = yaml_content.encode()
    log("✅ 生成 config.yaml 成功")
    download_response_file("config.yaml", yaml_content.encode())

# ========== 生成隧道配置 ==========
st.header("3️⃣ 生成 tunnel.yml (Cloudflare Argo)")

if st.button("生成 tunnel.yml (TunnelSecret模式)"):
    if "TunnelSecret" in ARGO_AUTH:
        tunnel_id = "unknown-id"
        try:
            data = json.loads(ARGO_AUTH)
            for k, v in data.items():
                if isinstance(v, str) and len(v) > 20:
                    tunnel_id = v
                    break
        except Exception:
            pass
        yaml_tunnel = textwrap.dedent(f"""
        tunnel: {tunnel_id}
        credentials-file: {Path(FILE_PATH) / 'tunnel.json'}
        protocol: http2
        ingress:
          - hostname: {ARGO_DOMAIN}
            service: http://localhost:{ARGO_PORT}
            originRequest:
              noTLSVerify: true
          - service: http_status:404
        """)
        st.session_state.generated["tunnel.yml"] = yaml_tunnel.encode()
        st.session_state.generated["tunnel.json"] = ARGO_AUTH.encode()
        log("✅ 生成 tunnel.yml + tunnel.json 成功")
        download_response_file("tunnel.yml", yaml_tunnel.encode())
        download_response_file("tunnel.json", ARGO_AUTH.encode())
    else:
        st.warning("当前 ARGO_AUTH 不包含 TunnelSecret，非固定隧道。")

# ========== 生成订阅 ==========
st.header("4️⃣ 生成 sub.txt (节点订阅)")

with st.form("sub_gen_form"):
    node_name_custom = st.text_input("节点名称（可自定义）", value=NAME)
    argo_domain_manual = st.text_input("Argo 域名（留空则使用变量）", value=ARGO_DOMAIN)
    submitted = st.form_submit_button("生成订阅")

if submitted:
    isp = CFIP.replace(".", "_")
    nodeName = node_name_custom or f"{NAME}-{isp}" or isp
    argoDomain = argo_domain_manual or ARGO_DOMAIN or CFIP
    VMESS = {
        "v": "2", "ps": nodeName, "add": CFIP, "port": CFPORT,
        "id": UUID, "aid": "0", "scy": "none", "net": "ws",
        "type": "none", "host": argoDomain, "path": "/vmess-argo?ed=2560",
        "tls": "tls", "sni": argoDomain, "fp": "firefox"
    }
    sub_txt = f"""vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argoDomain}&fp=firefox&type=ws&host={argoDomain}&path=%2Fvless-argo%3Fed%3D2560#{nodeName}

vmess://{base64.b64encode(json.dumps(VMESS).encode()).decode()}

trojan://{UUID}@{CFIP}:{CFPORT}?security=tls&sni={argoDomain}&fp=firefox&type=ws&host={argoDomain}&path=%2Ftrojan-argo%3Fed%3D2560#{nodeName}
"""
    encoded = base64.b64encode(sub_txt.encode())
    st.session_state.generated["sub.txt"] = encoded
    st.session_state.generated["sub_plain"] = sub_txt.encode()
    log("✅ 生成 sub.txt 成功")
    st.success("订阅生成成功，请下载 ↓")

    # ✅ 下载按钮放在表单外
    st.download_button("下载 Base64 订阅文件 sub.txt", data=encoded, file_name="sub.txt")
    st.download_button("下载 明文订阅文件 sub_plain.txt", data=sub_txt.encode(), file_name="sub_plain.txt")

# ========== 提取域名 ==========
st.header("5️⃣ 提取 Argo 临时域名")

uploaded = st.file_uploader("上传 boot.log（可选）", type=["log", "txt"])
manual_text = st.text_area("或直接粘贴日志：", height=120)

if st.button("提取 trycloudflare 域名"):
    content = ""
    if uploaded:
        content = uploaded.read().decode("utf-8", errors="ignore")
    elif manual_text.strip():
        content = manual_text
    matches = re.findall(r"https?://([^ \n]*trycloudflare\.com)", content)
    if matches:
        domain = matches[0]
        st.success(f"找到域名：{domain}")
        log(f"提取到 Argo 域名：{domain}")
        st.session_state.generated["ARGO_EXTRACTED"] = domain
    else:
        st.warning("未找到 trycloudflare 域名。")

# ========== 上传节点 ==========
st.header("6️⃣ 上传节点/订阅信息")

if st.button("上传到 UPLOAD_URL / PROJECT_URL"):
    if not UPLOAD_URL:
        st.error("UPLOAD_URL 未填写。")
    else:
        try:
            if UPLOAD_URL and PROJECT_URL:
                suburl = f"{PROJECT_URL}/{SUB_PATH}"
                resp = requests.post(f"{UPLOAD_URL}/api/add-subscriptions",
                                     json={"subscription": [suburl]}, timeout=10)
                if resp.status_code == 200:
                    st.success("✅ 订阅上传成功")
                    log("上传订阅成功")
                else:
                    st.error(f"上传失败: {resp.status_code}")
            else:
                nodes = []
                if "sub_plain" in st.session_state.generated:
                    text = st.session_state.generated["sub_plain"].decode()
                    nodes = [l for l in text.splitlines() if re.search(r"(vless|vmess|trojan)", l)]
                if not nodes:
                    st.warning("未找到节点信息")
                else:
                    resp = requests.post(f"{UPLOAD_URL}/api/add-nodes",
                                         json={"nodes": nodes}, timeout=10)
                    if resp.status_code == 200:
                        st.success("✅ 节点上传成功")
                        log("上传节点成功")
                    else:
                        st.error(f"上传失败: {resp.status_code}")
        except Exception as e:
            st.error(f"请求出错: {e}")
            log(f"上传错误: {e}")

# ========== 自动访问任务 ==========
st.header("7️⃣ 添加自动访问任务 (oooo.serv00.net)")

if st.button("添加访问任务"):
    if not PROJECT_URL:
        st.warning("PROJECT_URL 未填写。")
    else:
        try:
            resp = requests.post("https://oooo.serv00.net/add-url",
                                 json={"url": PROJECT_URL}, timeout=10)
            if resp.status_code == 200:
                st.success("✅ 添加任务成功")
                log("添加自动访问任务成功")
            else:
                st.error(f"失败: {resp.status_code}")
        except Exception as e:
            st.error(str(e))
            log(f"添加访问任务异常: {e}")

# ========== 侧栏状态 ==========
st.sidebar.markdown("---")
st.sidebar.subheader("🧩 状态与文件")
if st.sidebar.button("清空日志"):
    st.session_state.logs = []
for k in st.session_state.generated.keys():
    st.sidebar.write(f"- {k}")

# ========== 日志 ==========
st.markdown("## 📜 执行日志")
st.text("\n".join(st.session_state.logs[-200:]))

st.caption("© 老王专用版本 - 仅逻辑演示用途，不运行真实代理服务。")
