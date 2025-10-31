import streamlit as st
import os
import base64
import time
from pathlib import Path

st.set_page_config(page_title="Nodejs-Argo 状态面板", layout="centered")

st.title("🚀 Nodejs-Argo 部署状态")

# 显示环境变量信息（调试用）
st.sidebar.subheader("🔧 环境变量状态")
st.sidebar.text(f"FILE_PATH: {os.getenv('FILE_PATH', './tmp')}")
st.sidebar.text(f"ARGO_DOMAIN: {os.getenv('ARGO_DOMAIN', '未设置')}")
st.sidebar.text(f"UUID: {os.getenv('UUID', '未设置')}")

# 检查后端服务状态
def check_backend_status():
    sub_path = os.getenv("FILE_PATH", "./tmp") + "/sub.txt"
    
    if os.path.exists(sub_path):
        file_size = os.path.getsize(sub_path)
        st.success(f"✅ 后端服务运行正常 (文件大小: {file_size} bytes)")
        return True
    else:
        st.error("❌ 后端服务未正常运行或订阅文件未生成")
        st.info("💡 可能的原因：")
        st.write("- 后端服务正在启动中（请等待1-2分钟）")
        st.write("- 环境变量配置错误")
        st.write("- 文件路径权限问题")
        return False

# 显示服务状态
st.subheader("🔄 服务状态")
backend_status = check_backend_status()

if backend_status:
    st.success("所有服务已启动 ✅")
else:
    st.warning("服务启动中或遇到问题 ⚠️")

# 显示订阅链接
sub_path = os.getenv("FILE_PATH", "./tmp") + "/sub.txt"
if os.path.exists(sub_path):
    try:
        with open(sub_path, "r") as f:
            sub_raw = f.read().strip()
        
        if sub_raw:  # 确保文件不为空
            st.subheader("📡 节点订阅链接")
            
            # 尝试解码
            try:
                decoded = base64.b64decode(sub_raw).decode("utf-8")
                st.success("✅ 订阅链接解码成功")
                
                # 显示原始base64（备用）
                with st.expander("📋 Base64 格式订阅"):
                    st.code(sub_raw, language="text")
                
                # 显示解码后的链接
                st.subheader("🔗 解码后的订阅链接")
                for line in decoded.strip().split("\n"):
                    if line.strip():  # 只显示非空行
                        st.code(line, language="text")
                        
            except Exception as e:
                st.error(f"❌ 订阅解码失败: {e}")
                st.info("显示原始内容:")
                st.code(sub_raw, language="text")
        else:
            st.warning("订阅文件为空，可能后端还在生成中")
            
    except Exception as e:
        st.error(f"读取订阅文件失败: {e}")
else:
    st.warning("尚未生成订阅链接")
    st.info("""
    **可能的原因和解决方案：**
    1. **等待启动**: 后端服务可能需要1-2分钟来完全启动
    2. **检查日志**: 查看应用日志确认后端是否正常运行
    3. **环境变量**: 确认所有必要的环境变量已正确设置
    4. **文件权限**: 检查文件路径的读写权限
    """)

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

# 手动刷新按钮
if st.button("🔄 刷新状态"):
    st.rerun()

# 显示最后更新时间
st.caption(f"最后更新: {time.strftime('%Y-%m-%d %H:%M:%S')}")
