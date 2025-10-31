# streamlit.py
# Streamlit-compatible port of index.js (logic-only, DOES NOT run binaries)
# Features:
# - Edit environment variables via UI
# - Generate config.json, config.yaml (nezha), tunnel.yml
# - Generate sub.txt (base64) and download
# - Upload nodes / subscriptions to UPLOAD_URL / PROJECT_URL (via HTTP)
# - Extract argo domain from uploaded boot.log or pasted text
# - Trigger "automatic access" API
# - Logs & status panel
#
# NOTE: This script intentionally DOES NOT run binaries, start background services,
# or call subprocess. It only simulates / reproduces config-generation and
# network-upload logic so it can run on share.streamlit.io.

import os
import re
import json
import base64
import textwrap
import time
from pathlib import Path
from typing import Optional, Tuple

import requests
import streamlit as st

st.set_page_config(page_title="Streamlit port of index.js (logic-only)", layout="wide")

# -------------------------
# Helpers
# -------------------------
def env_default(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

def generate_random_name() -> str:
    import random, string
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(6))

def log(msg: str, key="main"):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    msg_line = f"[{now}] {msg}"
    st.session_state.logs.append(msg_line)
    # keep last 500 lines
    if len(st.session_state.logs) > 500:
        st.session_state.logs = st.session_state.logs[-500:]

def download_response_file(filename: str, content: bytes):
    st.download_button(label=f"Download {filename}", data=content, file_name=filename)

# -------------------------
# Init session state
# -------------------------
if "logs" not in st.session_state:
    st.session_state.logs = []

if "generated" not in st.session_state:
    st.session_state.generated = {}

# -------------------------
# Sidebar: basic env / params
# -------------------------
st.sidebar.header("Environment / Settings")

UPLOAD_URL = st.sidebar.text_input("UPLOAD_URL", value=env_default("UPLOAD_URL", ""))
PROJECT_URL = st.sidebar.text_input("PROJECT_URL", value=env_default("PROJECT_URL", ""))
AUTO_ACCESS = st.sidebar.checkbox("AUTO_ACCESS", value=(env_default("AUTO_ACCESS", "false").lower() == "true"))
FILE_PATH = st.sidebar.text_input("FILE_PATH", value=env_default("FILE_PATH", "./tmp"))
SUB_PATH = st.sidebar.text_input("SUB_PATH", value=env_default("SUB_PATH", "sub"))
PORT = st.sidebar.text_input("PORT (ignored in Streamlit)", value=env_default("PORT", "3000"))
UUID = st.sidebar.text_input("UUID", value=env_default("UUID", "1c56e2c7-8c4f-4d3d-8f93-2ab64854325a"))
NEZHA_SERVER = st.sidebar.text_input("NEZHA_SERVER", value=env_default("NEZHA_SERVER", "ycv.dpdns.org:8008"))
NEZHA_PORT = st.sidebar.text_input("NEZHA_PORT", value=env_default("NEZHA_PORT", ""))
NEZHA_KEY = st.sidebar.text_input("NEZHA_KEY", value=env_default("NEZHA_KEY", "uK6lptvEoZ7TsX6yzjOxSd3RYeGCHCJj"))
ARGO_DOMAIN = st.sidebar.text_input("ARGO_DOMAIN", value=env_default("ARGO_DOMAIN", "py.a.5.a.f.0.7.4.0.1.0.0.2.ip6.arpa"))
ARGO_AUTH = st.sidebar.text_input("ARGO_AUTH", value=env_default("ARGO_AUTH", "eyJhIjoiMTZlZDI2MTFjNGE5ZGYzYjQ5NWNjYzA4NWU2MWVkN2YiLCJ0IjoiYzM5ZWU3NjYtMGU1YS00MTQzLTk1YWEtZjA5MDdhNjZmMjNmIiwicyI6Ik5ESmpaRFEyTmpFdE5tTXdNQzAwTVRrMExUazBPVFl0WkdWbE9EazRNRFpsWVdKaiJ9"))
ARGO_PORT = st.sidebar.text_input("ARGO_PORT", value=env_default("ARGO_PORT", "8051"))
CFIP = st.sidebar.text_input("CFIP", value=env_default("CFIP", "cdns.doon.eu.org"))
CFPORT = st.sidebar.text_input("CFPORT", value=env_default("CFPORT", "443"))
NAME = st.sidebar.text_input("NAME", value=env_default("NAME", "Share"))

architecture = st.sidebar.selectbox("System architecture (for URL suggestions)", options=["amd", "arm"], index=0)

# convenience random names (like original)
if "random_names" not in st.session_state:
    st.session_state.random_names = {
        "npmName": generate_random_name(),
        "webName": generate_random_name(),
        "botName": generate_random_name(),
        "phpName": generate_random_name(),
    }

st.sidebar.write("Generated binary names (for reference):")
st.sidebar.write(st.session_state.random_names)

# -------------------------
# Main UI
# -------------------------
st.title("Streamlit port — config & subscription generator (logic-only)")
st.caption("本页面 **不会** 在服务器上运行二进制或后台服务。它会生成配置文件、订阅信息并可上传到远端 API。")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("1) Generate config.json (xray/xr-ay style)")
    if st.button("Generate config.json"):
        cfg = {
            "log": {"access": "/dev/null", "error": "/dev/null", "loglevel": "none"},
            "inbounds": [
                {"port": int(ARGO_PORT), "protocol": "vless", "settings": {"clients": [{"id": UUID, "flow": "xtls-rprx-vision"}], "decryption": "none", "fallbacks": [{"dest": 3001}, {"path": "/vless-argo", "dest": 3002}, {"path": "/vmess-argo", "dest": 3003}, {"path": "/trojan-argo", "dest": 3004}]}, "streamSettings": {"network": "tcp"}},
                {"port": 3001, "listen": "127.0.0.1", "protocol": "vless", "settings": {"clients": [{"id": UUID}], "decryption": "none"}, "streamSettings": {"network": "tcp", "security": "none"}},
                {"port": 3002, "listen": "127.0.0.1", "protocol": "vless", "settings": {"clients": [{"id": UUID, "level": 0}], "decryption": "none"}, "streamSettings": {"network": "ws", "security": "none", "wsSettings": {"path": "/vless-argo"}}, "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "metadataOnly": False}},
                {"port": 3003, "listen": "127.0.0.1", "protocol": "vmess", "settings": {"clients": [{"id": UUID, "alterId": 0}]}, "streamSettings": {"network": "ws", "wsSettings": {"path": "/vmess-argo"}}, "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "metadataOnly": False}},
                {"port": 3004, "listen": "127.0.0.1", "protocol": "trojan", "settings": {"clients": [{"password": UUID}]}, "streamSettings": {"network": "ws", "security": "none", "wsSettings": {"path": "/trojan-argo"}}, "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "metadataOnly": False}}
            ],
            "dns": {"servers": ["https+local://8.8.8.8/dns-query"]},
            "outbounds": [{"protocol": "freedom", "tag": "direct"}, {"protocol": "blackhole", "tag": "block"}]
        }
        json_bytes = json.dumps(cfg, indent=2).encode("utf-8")
        st.session_state.generated["config.json"] = json_bytes
        log("Generated config.json")
        download_response_file("config.json", json_bytes)

    st.markdown("---")
    st.header("2) Generate Nezha config (config.yaml)")
    if st.button("Generate config.yaml (nezha client)"):
        if not NEZHA_KEY:
            st.warning("NEZHA_KEY is empty — still generated but please fill NEZHA_KEY for real use.")
        tls_ports = {"443", "8443", "2096", "2087", "2083", "2053"}
        port_token = NEZHA_SERVER.split(":")[-1] if NEZHA_SERVER else ""
        nezhatls = "true" if port_token in tls_ports else "false"
        yaml_content = textwrap.dedent(f"""\
            client_secret: {NEZHA_KEY}
            debug: false
            disable_auto_update: true
            disable_command_execute: false
            disable_force_update: true
            disable_nat: false
            disable_send_query: false
            gpu: false
            insecure_tls: true
            ip_report_period: 1800
            report_delay: 4
            server: {NEZHA_SERVER}
            skip_connection_count: true
            skip_procs_count: true
            temperature: false
            tls: {nezhatls}
            use_gitee_to_upgrade: false
            use_ipv6_country_code: false
            uuid: {UUID}
        """)
        st.session_state.generated["config.yaml"] = yaml_content.encode("utf-8")
        log("Generated config.yaml")
        download_response_file("config.yaml", yaml_content.encode("utf-8"))

    st.markdown("---")
    st.header("3) Generate tunnel.yml (Cloudflare tunnel)")

    if st.button("Generate tunnel.yml (TunnelSecret mode)"):
        if "TunnelSecret" in ARGO_AUTH:
            try:
                # try to find tunnel id inside JSON if provided
                credentials = json.loads(ARGO_AUTH)
                # best-effort extraction for tunnel id via keys/values
                tunnel_id = ""
                # the Node script used ARGO_AUTH.split('"')[11] to pick tunnel id — we attempt to find an id key
                if isinstance(credentials, dict):
                    # flatten and try to find something that looks like an id
                    found = []
                    def find_strings(obj):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                find_strings(v)
                        elif isinstance(obj, list):
                            for it in obj:
                                find_strings(it)
                        elif isinstance(obj, str):
                            found.append(obj)
                    find_strings(credentials)
                    # pick the first string that looks like an uuid-ish
                    for s in found:
                        if re.match(r"^[0-9a-fA-F\-]{8,}$", s):
                            tunnel_id = s
                            break
                if not tunnel_id:
                    tunnel_id = "TUNNEL_ID_NOT_FOUND"
                yaml_tunnel = textwrap.dedent(f"""\
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
                st.session_state.generated["tunnel.yml"] = yaml_tunnel.encode("utf-8")
                st.session_state.generated["tunnel.json"] = ARGO_AUTH.encode("utf-8")
                log("Generated tunnel.yml + tunnel.json (TunnelSecret path)")
                download_response_file("tunnel.yml", yaml_tunnel.encode("utf-8"))
                download_response_file("tunnel.json", ARGO_AUTH.encode("utf-8"))
            except Exception as e:
                st.error(f"Failed to parse ARGO_AUTH as JSON: {e}")
        else:
            st.warning("ARGO_AUTH does not contain TunnelSecret — token mode will be used on real host.")

    st.markdown("---")
    st.header("4) Generate sub.txt (base64-encoded subscriptions)")

    with st.form("sub_gen"):
        node_name_custom = st.text_input("Node name (optional). If blank, ISP-based name will be used.", value="")
        argo_domain_manual = st.text_input("Argo domain (if you have one)", value=ARGO_DOMAIN)
        generate_button = st.form_submit_button("Generate sub.txt")
        if generate_button:
            # meta info imitation: original uses curl to get ISP + region; here we fallback to CFIP or NAME
            isp = CFIP.replace(".", "_")
            nodeName = f"{NAME}-{isp}" if NAME else isp
            if node_name_custom.strip():
                nodeName = node_name_custom.strip()
            argoDomain = argo_domain_manual.strip()
            if not argoDomain:
                st.warning("No argo domain given — sub.txt will contain placeholders for host.")
            VMESS = {"v": "2", "ps": nodeName, "add": CFIP, "port": CFPORT, "id": UUID, "aid": "0", "scy": "none", "net": "ws", "type": "none", "host": argoDomain or "ARGO_DOMAIN", "path": "/vmess-argo?ed=2560", "tls": "tls", "sni": argoDomain or "ARGO_DOMAIN", "alpn": "", "fp": "firefox"}
            sub_txt = f"""vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argoDomain or CFIP}&fp=firefox&type=ws&host={argoDomain or CFIP}&path=%2Fvless-argo%3Fed%3D2560#{nodeName}

vmess://{base64.b64encode(json.dumps(VMESS).encode()).decode()}

trojan://{UUID}@{CFIP}:{CFPORT}?security=tls&sni={argoDomain or CFIP}&fp=firefox&type=ws&host={argoDomain or CFIP}&path=%2Ftrojan-argo%3Fed%3D2560#{nodeName}
"""
            encoded = base64.b64encode(sub_txt.encode("utf-8"))
            st.session_state.generated["sub.txt"] = encoded
            st.session_state.generated["sub_plain"] = sub_txt.encode("utf-8")
            log("Generated sub.txt (base64 encoded)")
            st.success("sub.txt generated")
            st.download_button("Download sub.txt (base64)", data=encoded, file_name="sub.txt")
            st.download_button("Download sub_plain.txt (plain text)", data=sub_txt.encode("utf-8"), file_name="sub_plain.txt")

    st.markdown("---")
    st.header("5) Extract Argo domain from boot.log (upload or paste)")

    uploaded = st.file_uploader("Upload boot.log (optional)", type=["log", "txt"])
    manual_log = st.text_area("—or paste boot.log contents here—", height=120)
    if st.button("Extract Argo domain"):
        content = ""
        if uploaded is not None:
            content = uploaded.read().decode("utf-8", errors="ignore")
        elif manual_log.strip():
            content = manual_log
        else:
            st.warning("No boot.log content supplied")
        if content:
            matches = re.findall(r"https?://([^ \n]*trycloudflare\.com)", content)
            if matches:
                domain = matches[0]
                st.success(f"Found Argo domain: {domain}")
                log(f"Extracted Argo domain from log: {domain}")
                st.session_state.generated["extracted_argo_domain"] = domain
            else:
                st.info("No trycloudflare domain found in provided content")

    st.markdown("---")
    st.header("6) Upload subscription / nodes (to UPLOAD_URL / PROJECT_URL)")

    st.write("This will perform the HTTP requests same as the original script. Make sure the target endpoints are reachable.")
    with st.form("upload_form"):
        upload_nodes_btn = st.form_submit_button("Upload nodes / subscriptions")
        if upload_nodes_btn:
            if not UPLOAD_URL:
                st.error("UPLOAD_URL is empty — cannot upload.")
            else:
                # if both UPLOAD_URL and PROJECT_URL present -> add-subscriptions path
                if UPLOAD_URL and PROJECT_URL:
                    if "sub.txt" not in st.session_state.generated:
                        st.error("No sub.txt generated. Generate it first.")
                    else:
                        subscriptionUrl = f"{PROJECT_URL}/{SUB_PATH}"
                        jsonData = {"subscription": [subscriptionUrl]}
                        try:
                            resp = requests.post(f"{UPLOAD_URL}/api/add-subscriptions", json=jsonData, timeout=10)
                            if resp.status_code == 200:
                                st.success("Subscription uploaded successfully")
                                log(f"Uploaded subscription to {UPLOAD_URL}/api/add-subscriptions")
                            else:
                                st.error(f"Upload returned status {resp.status_code}: {resp.text}")
                                log(f"Upload failed status {resp.status_code}")
                        except Exception as e:
                            st.error(f"Upload error: {e}")
                            log(f"Upload exception: {e}")
                else:
                    # UPLOAD_URL only -> send add-nodes; it reads list.txt in original, but here we will try sub_plain
                    if "sub_plain" not in st.session_state.generated:
                        st.error("No nodes/sub content generated. Generate sub.txt first.")
                    else:
                        nodes = [line for line in st.session_state.generated["sub_plain"].decode("utf-8").splitlines() if re.search(r"(vless|vmess|trojan|hysteria2|tuic):\/\/", line)]
                        if not nodes:
                            st.error("No nodes found in generated content.")
                        else:
                            jsonData = {"nodes": nodes}
                            try:
                                resp = requests.post(f"{UPLOAD_URL}/api/add-nodes", json=json.dumps(jsonData), headers={"Content-Type": "application/json"}, timeout=10)
                                if resp.status_code == 200:
                                    st.success("Nodes uploaded successfully")
                                    log(f"Uploaded nodes to {UPLOAD_URL}/api/add-nodes")
                                else:
                                    st.error(f"Upload returned status {resp.status_code}: {resp.text}")
                                    log(f"Upload failed status {resp.status_code}")
                            except Exception as e:
                                st.error(f"Upload error: {e}")
                                log(f"Upload exception: {e}")

    st.markdown("---")
    st.header("7) Add automatic access task (oooo.serv00.net)")
    if st.button("Trigger automatic access (POST to https://oooo.serv00.net/add-url)"):
        if not AUTO_ACCESS or not PROJECT_URL:
            st.warning("AUTO_ACCESS disabled or PROJECT_URL empty — but request will still be attempted if you want.")
        try:
            resp = requests.post("https://oooo.serv00.net/add-url", json={"url": PROJECT_URL}, timeout=10, headers={"Content-Type": "application/json"})
            if resp.status_code == 200:
                st.success("Automatic access task added")
                log("Added automatic access task")
            else:
                st.error(f"Returned {resp.status_code}: {resp.text}")
                log(f"AddVisitTask returned {resp.status_code}")
        except Exception as e:
            st.error(f"Request failed: {e}")
            log(f"AddVisitTask exception: {e}")

with col2:
    st.header("Status / Utilities")
    st.write("Quick actions & info")
    if st.button("Clear logs"):
        st.session_state.logs = []
        st.success("Logs cleared")
    st.write("Generated artifacts in this session:")
    for k in st.session_state.generated.keys():
        st.write("-", k)
    st.markdown("---")
    st.header("Suggested download URLs for binaries (info only)")
    base = "https://arm64.ssss.nyc.mn" if architecture == "arm" else "https://amd64.ssss.nyc.mn"
    st.write("web:", f"{base}/web")
    st.write("bot:", f"{base}/bot")
    st.write("agent (nezha linux agent):", f"{base}/agent (if using NEZHA_PORT)")
    st.write("v1 (nezha v1):", f"{base}/v1 (if using NEZHA v1)")
    st.markdown("---")
    st.header("Manual operations")
    st.write("You can copy the generated contents and run them on your VPS where running binaries is allowed.")

st.markdown("## Logs")
with st.expander("Execution log (most recent at bottom)", expanded=True):
    st.text("\n".join(st.session_state.logs[-200:]))

st.markdown("---")
st.caption("说明：此 Streamlit 应用复刻了原脚本的**配置/上传/生成**逻辑，但未/不能执行系统层面的二进制操作（例如 nohup、chmod、pkill、运行 cloudflared）。若需完整运行请在 Linux VPS 上运行原生脚本或等价 Python 脚本（我也可以提供该脚本）。")
