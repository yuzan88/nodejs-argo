import streamlit as st
import os
import base64

st.set_page_config(page_title="Nodejs-Argo 状态面板", layout="centered")

st.title("🚀 Nodejs-Argo 部署状态")
st.success("所有服务已启动 ✅")

# 显示订阅链接
sub_path = os.getenv("FILE_PATH", "./tmp") + "/sub.txt"
if os.path.exists(sub_path):
    with open(sub_path, "r") as f:
        sub_raw = f.read()
    try:
        decoded = base64.b64decode(sub_raw).decode("utf-8")
        st.subheader("📡 节点订阅链接")
        for line in decoded.strip().split("\n"):
            st.code(line, language="text")
    except Exception as e:
        st.error(f"订阅解码失败: {e}")
else:
    st.warning("尚未生成订阅链接")

# 显示 Argo 域名
argo_domain = os.getenv("ARGO_DOMAIN", "")
if argo_domain:
    st.info(f"🌐 当前 Argo 域名: `{argo_domain}`")
else:
    st.warning("未检测到 Argo 域名")

# 显示 UUID
uuid = os.getenv("UUID", "")
if uuid:
    st.text(f"🔑 UUID: {uuid}")
