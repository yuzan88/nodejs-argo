import os
import sys
import json
import base64
import random
import string
import subprocess
import threading
import time
import requests
from pathlib import Path
import streamlit as st

# 环境变量配置（使用你的实际值）
UPLOAD_URL = os.getenv('UPLOAD_URL', '')
PROJECT_URL = os.getenv('PROJECT_URL', '')
AUTO_ACCESS = os.getenv('AUTO_ACCESS', 'false').lower() == 'true'
FILE_PATH = os.getenv('FILE_PATH', './tmp')
SUB_PATH = os.getenv('SUB_PATH', 'sub')
PORT = int(os.getenv('SERVER_PORT', os.getenv('PORT', '3210')))
UUID = os.getenv('UUID', 'bb3d9936-6788-448d-95bf-b45f219c2efd')
NEZHA_SERVER = os.getenv('NEZHA_SERVER', 'ycv.dpdns.org:8008')
NEZHA_PORT = os.getenv('NEZHA_PORT', '')
NEZHA_KEY = os.getenv('NEZHA_KEY', 'uK6lptvEoZ7TsX6yzjOxSd3RYeGCHCJj')
ARGO_DOMAIN = os.getenv('ARGO_DOMAIN', 'py.dajb.netlib.re')
ARGO_AUTH = os.getenv('ARGO_AUTH', 'eyJhIjoiMTZlZDI2MTFjNGE5ZGYzYjQ5NWNjYzA4NWU2MWVkN2YiLCJ0IjoiYzM5ZWU3NjYtMGU1YS00MTQzLTk1YWEtZjA5MDdhNjZmMjNmIiwicyI6Ik5ESmpaRFEyTmpFdE5tTXdNQzAwTVRrMExUazBPVFl0WkdWbE9EazRNRFpsWVdKaiJ9')
ARGO_PORT = int(os.getenv('ARGO_PORT', '8001'))
CFIP = os.getenv('CFIP', 'cdns.doon.eu.org')
CFPORT = int(os.getenv('CFPORT', '443'))
NAME = os.getenv('NAME', 'Streamlit')

# 创建运行目录
Path(FILE_PATH).mkdir(exist_ok=True)

# 生成订阅内容（不依赖外部服务）
def generate_subscription_content():
    """直接生成订阅内容，不依赖外部下载和服务"""
    
    # 使用固定的 Argo 域名
    argo_domain = ARGO_DOMAIN
    
    # 生成节点名称
    isp = "Cloudflare"  # 简化版本，不使用 curl 获取地理位置
    node_name = f"{NAME}-{isp}" if NAME else isp
    
    # 生成 VMESS 配置
    vmess_config = {
        "v": "2",
        "ps": node_name,
        "add": CFIP,
        "port": CFPORT,
        "id": UUID,
        "aid": "0",
        "scy": "none",
        "net": "ws",
        "type": "none",
        "host": argo_domain,
        "path": "/vmess-argo?ed=2560",
        "tls": "tls",
        "sni": argo_domain,
        "alpn": "",
        "fp": "firefox"
    }
    
    vmess_base64 = base64.b64encode(json.dumps(vmess_config).encode()).decode()
    
    sub_txt = f"""vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&fp=firefox&type=ws&host={argo_domain}&path=%2Fvless-argo%3Fed%3D2560#{node_name}

vmess://{vmess_base64}

trojan://{UUID}@{CFIP}:{CFPORT}?security=tls&sni={argo_domain}&fp=firefox&type=ws&host={argo_domain}&path=%2Ftrojan-argo%3Fed%3D2560#{node_name}"""
    
    return sub_txt

def save_subscription_file():
    """保存订阅文件"""
    try:
        content = generate_subscription_content()
        sub_base64 = base64.b64encode(content.encode()).decode()
        
        sub_path = os.path.join(FILE_PATH, 'sub.txt')
        with open(sub_path, 'w') as f:
            f.write(sub_base64)
        
        print(f"订阅文件已生成: {sub_path}")
        return True
    except Exception as e:
        print(f"生成订阅文件失败: {e}")
        return False

# 启动时生成订阅文件
if not os.path.exists(os.path.join(FILE_PATH, 'sub.txt')):
    save_subscription_file()

# Streamlit 前端界面
def main():
    st.set_page_config(
        page_title="Nodejs-Argo 状态面板", 
        layout="centered",
        page_icon="🚀"
    )
    
    st.title("🚀 Nodejs-Argo 部署状态")
    
    # 显示环境状态
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Argo 隧道", "已配置" if ARGO_DOMAIN else "未配置")
    
    with col2:
        st.metric("哪吒监控", "已配置" if NEZHA_SERVER and NEZHA_KEY else "未配置")
    
    with col3:
        st.metric("UUID", "已设置" if UUID else "未设置")
    
    # 显示订阅链接
    st.subheader("📡 节点订阅链接")
    
    sub_path = os.path.join(FILE_PATH, 'sub.txt')
    if os.path.exists(sub_path):
        try:
            with open(sub_path, "r") as f:
                sub_raw = f.read().strip()
            
            if sub_raw:
                # 解码显示
                decoded = base64.b64decode(sub_raw).decode("utf-8")
                
                st.success("✅ 订阅链接生成成功")
                
                # 显示每个节点链接
                st.subheader("🔗 节点配置")
                for i, line in enumerate(decoded.strip().split("\n")):
                    if line.strip():
                        with st.expander(f"节点 {i+1}: {line.split('#')[-1] if '#' in line else '未知'}", expanded=i==0):
                            st.code(line, language="text")
                            
                            # 添加复制按钮
                            if st.button(f"📋 复制节点 {i+1}", key=f"copy_{i}"):
                                st.code(line, language="text")
                                st.success("已复制到剪贴板（请手动复制）")
                
                # 显示 Base64 订阅（用于订阅器）
                st.subheader("📦 Base64 订阅内容")
                st.info("将以下内容复制到订阅器中：")
                st.code(sub_raw, language="text")
                
            else:
                st.warning("订阅文件为空")
                if st.button("🔄 重新生成订阅"):
                    if save_subscription_file():
                        st.rerun()
                    
        except Exception as e:
            st.error(f"读取订阅文件失败: {e}")
            if st.button("🔄 重新生成订阅"):
                if save_subscription_file():
                    st.rerun()
    else:
        st.error("订阅文件不存在")
        if st.button("🔄 生成订阅"):
            if save_subscription_file():
                st.rerun()
    
    # 显示配置信息
    st.subheader("⚙️ 当前配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**基础配置**")
        st.text(f"UUID: {UUID}")
        st.text(f"ARGO 域名: {ARGO_DOMAIN}")
        st.text(f"优选IP: {CFIP}:{CFPORT}")
        st.text(f"节点名称: {NAME}")
    
    with col2:
        st.info("**服务状态**")
        st.text(f"哪吒服务器: {NEZHA_SERVER}")
        st.text(f"文件路径: {FILE_PATH}")
        st.text(f"订阅路径: /{SUB_PATH}")
    
    # 手动生成订阅区域
    st.subheader("🔧 手动配置")
    
    with st.expander("高级选项"):
        custom_uuid = st.text_input("自定义 UUID", value=UUID)
        custom_domain = st.text_input("自定义域名", value=ARGO_DOMAIN)
        custom_name = st.text_input("自定义节点名", value=NAME)
        
        if st.button("🔄 使用新配置生成订阅"):
            global UUID, ARGO_DOMAIN, NAME
            UUID = custom_uuid
            ARGO_DOMAIN = custom_domain
            NAME = custom_name
            if save_subscription_file():
                st.success("订阅已更新！")
                st.rerun()
    
    # 使用说明
    st.subheader("📖 使用说明")
    
    st.markdown("""
    1. **复制节点链接**: 点击上方的节点链接，复制到对应的客户端
    2. **订阅使用**: 复制 Base64 内容到订阅器
    3. **支持协议**: VLESS、VMESS、Trojan
    4. **网络类型**: WebSocket over TLS
    5. **传输安全**: TLS 加密
    """)
    
    # 技术支持信息
    st.caption("💡 技术支持: 如遇到问题，请检查环境变量配置和网络连接")

# 在 Streamlit Cloud 中直接运行前端
if __name__ == "__main__":
    main()



