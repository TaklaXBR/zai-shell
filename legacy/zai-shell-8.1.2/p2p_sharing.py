import socket
import threading
import json
import datetime
import uuid
import os
import base64
import hashlib
from typing import Dict, Optional, List, Tuple

from colorama import Fore, Style

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

P2P_NAME_FILE = ".zaishell_p2p_name"
P2P_ENCRYPT_FILE = ".zaishell_p2p_encrypt"
MAX_FILE_SIZE = 100 * 1024 * 1024

CHUNK_SIZE = 65536


class P2PTerminalSharing:
    """Multi-client terminal sharing via TCP sockets with E2E encryption"""
    
    DEFAULT_PORT = 5757
    
    def __init__(self):
        self.share_code = None
        self.is_host = False
        self.is_connected = False
        self.socket = None
        self.my_name = self._load_saved_name()
        self.clients = {}
        self.client_lock = threading.Lock()
        self.pending_commands = []
        self.pending_files = []
        self.safe_mode_always = True
        self.terminal_logs = []
        self.chat_messages = []
        self.receive_thread = None
        self.running = False
        self.host_port = self.DEFAULT_PORT
        self.host_name = "Host"
        self.file_transfer_progress = {}
        self.connected_users = []
        self.encryption_enabled = False
        self.encryption_key = None
        self.encryption_key_display = None
        self.fernet = None
        self.no_ai_mode = False
        self._load_encryption_state()
    
    def _load_encryption_state(self):
        try:
            if os.path.exists(P2P_ENCRYPT_FILE):
                with open(P2P_ENCRYPT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('enabled') and data.get('key'):
                        self.encryption_key = data['key'].encode('utf-8')
                        self.encryption_key_display = data.get('key_display', 'saved')
                        self.fernet = Fernet(self.encryption_key)
                        self.encryption_enabled = True
        except Exception:
            pass
    
    def _save_encryption_state(self):
        try:
            data = {
                'enabled': self.encryption_enabled,
                'key': self.encryption_key.decode('utf-8') if self.encryption_key else None,
                'key_display': self.encryption_key_display
            }
            with open(P2P_ENCRYPT_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass
    
    def _generate_session_key(self, password: str = None) -> Tuple[bytes, str]:
        if not CRYPTO_AVAILABLE:
            return None, None
        if password is None:
            key = Fernet.generate_key()
            key_display = key.decode('utf-8')[:16] + '...'
            return key, key_display
        salt = b'zaishell_p2p_salt_v8'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        key_display = f'password:{password[:8]}...' if len(password) > 8 else f'password:{password}'
        return key, key_display
    
    def show_encryption_status(self):
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}ENCRYPTION STATUS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        status = f"{Fore.GREEN}ON{Style.RESET_ALL}" if self.encryption_enabled else f"{Fore.RED}OFF{Style.RESET_ALL}"
        print(f"  Status: {status}")
        if self.encryption_enabled and self.encryption_key_display:
            print(f"  Key: {Fore.YELLOW}{self.encryption_key_display}{Style.RESET_ALL}")
        if self.encryption_enabled and self.encryption_key:
            print(f"  Full Key: {Fore.CYAN}{self.encryption_key.decode('utf-8')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"\n{Fore.WHITE}Usage:{Style.RESET_ALL}")
        print(f"  share encrypt              - Show this status")
        print(f"  share encrypt on           - Enable with last key or new random")
        print(f"  share encrypt off          - Disable encryption")
        print(f"  share encrypt random       - Generate new random key")
        print(f"  share encrypt <password>   - Use password-based key")
        print(f"  share encrypt key <key>    - Use specific Fernet key")
    
    def enable_encryption(self, mode: str = None) -> bool:
        if not CRYPTO_AVAILABLE:
            print(f"{Fore.YELLOW}Encryption requires 'cryptography' package. Install: pip install cryptography{Style.RESET_ALL}")
            return False
        
        if mode is None:
            self.show_encryption_status()
            return self.encryption_enabled
        
        if mode.lower() == 'off':
            self.encryption_enabled = False
            self.encryption_key = None
            self.encryption_key_display = None
            self.fernet = None
            self._save_encryption_state()
            print(f"{Fore.YELLOW}E2E Encryption: OFF{Style.RESET_ALL}")
            return False
        
        if mode.lower() == 'on':
            if self.encryption_key:
                self.fernet = Fernet(self.encryption_key)
                self.encryption_enabled = True
                self._save_encryption_state()
                print(f"{Fore.GREEN}E2E Encryption: ON (using saved key){Style.RESET_ALL}")
                print(f"{Fore.CYAN}Key: {self.encryption_key_display}{Style.RESET_ALL}")
                return True
            else:
                mode = 'random'
        
        if mode.lower() == 'random':
            self.encryption_key, self.encryption_key_display = self._generate_session_key(None)
            self.fernet = Fernet(self.encryption_key)
            self.encryption_enabled = True
            self._save_encryption_state()
            print(f"{Fore.GREEN}E2E Encryption: ON (Random Key){Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Full Key (share with others):{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{self.encryption_key.decode('utf-8')}{Style.RESET_ALL}")
            return True
        
        if mode.lower().startswith('key:'):
            try:
                custom_key = mode[4:].strip().encode('utf-8')
                self.fernet = Fernet(custom_key)
                self.encryption_key = custom_key
                self.encryption_key_display = f'custom:{custom_key.decode()[:16]}...'
                self.encryption_enabled = True
                self._save_encryption_state()
                print(f"{Fore.GREEN}E2E Encryption: ON (Custom Key){Style.RESET_ALL}")
                return True
            except Exception as e:
                print(f"{Fore.RED}Invalid Fernet key: {e}{Style.RESET_ALL}")
                return False
        
        self.encryption_key, self.encryption_key_display = self._generate_session_key(mode)
        self.fernet = Fernet(self.encryption_key)
        self.encryption_enabled = True
        self._save_encryption_state()
        print(f"{Fore.GREEN}E2E Encryption: ON (Password-based){Style.RESET_ALL}")
        print(f"{Fore.CYAN}Password: {mode}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Share same password with others to connect.{Style.RESET_ALL}")
        return True
    
    def _encrypt(self, data: str) -> str:
        if not self.encryption_enabled or not self.fernet:
            return data
        try:
            encrypted = self.fernet.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception:
            return data
    
    def _decrypt(self, data: str) -> str:
        if not self.encryption_enabled or not self.fernet:
            return data
        try:
            decoded = base64.b64decode(data.encode('utf-8'))
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception:
            return data
    
    def _encrypt_bytes(self, data: bytes) -> bytes:
        if not self.encryption_enabled or not self.fernet:
            return data
        try:
            return self.fernet.encrypt(data)
        except Exception:
            return data
    
    def _decrypt_bytes(self, data: bytes) -> bytes:
        if not self.encryption_enabled or not self.fernet:
            return data
        try:
            return self.fernet.decrypt(data)
        except Exception:
            return data
    
    def _load_saved_name(self) -> Optional[str]:
        try:
            if os.path.exists(P2P_NAME_FILE):
                with open(P2P_NAME_FILE, 'r', encoding='utf-8') as f:
                    name = f.read().strip()
                    return name if name else None
        except Exception:
            pass
        return None
    
    def _save_name(self, name: str):
        try:
            with open(P2P_NAME_FILE, 'w', encoding='utf-8') as f:
                f.write(name)
        except Exception:
            pass
    
    def set_name(self, new_name: str) -> bool:
        if not new_name or len(new_name) > 20:
            return False
        self.my_name = new_name
        self._save_name(new_name)
        print(f"{Fore.GREEN}Name changed to: {new_name}{Style.RESET_ALL}")
        return True
    
    def get_or_ask_name(self, default: str = "Helper") -> str:
        if self.my_name:
            print(f"{Fore.CYAN}Using saved name: {Fore.YELLOW}{self.my_name}{Style.RESET_ALL}")
            return self.my_name
        
        print(f"{Fore.CYAN}Enter your name (press Enter for '{default}'): {Style.RESET_ALL}", end="")
        name_input = input().strip()
        name = name_input if name_input else default
        self._save_name(name)
        self.my_name = name
        return name
    
    def get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def _get_unique_name(self, requested_name: str) -> str:
        with self.client_lock:
            existing_names = [info['name'] for info in self.clients.values()]
            if self.host_name:
                existing_names.append(self.host_name)
            
            if requested_name not in existing_names:
                return requested_name
            
            counter = 1
            while f"{requested_name}{counter}" in existing_names:
                counter += 1
            return f"{requested_name}{counter}"
    
    def get_connected_users(self) -> List[str]:
        users = []
        if self.is_host:
            users.append(self.host_name)
            with self.client_lock:
                for info in self.clients.values():
                    users.append(info['name'])
        else:
            users.append(self.host_name)
            users.append(self.my_name)
            for user in self.connected_users:
                if user not in users:
                    users.append(user)
        return users
    
    def find_user_by_name(self, name: str) -> Optional[str]:
        name_lower = name.lower()
        with self.client_lock:
            for client_id, info in self.clients.items():
                if info['name'].lower() == name_lower:
                    return client_id
        return None
    
    def start_sharing_session(self, port: int = None, host_name: str = None, no_ai: bool = False) -> Dict:
        if port:
            self.host_port = port
        
        self.no_ai_mode = no_ai
        
        if host_name:
            self.host_name = host_name
            self.my_name = host_name
            self._save_name(host_name)
        else:
            self.host_name = self.get_or_ask_name("Host")
            self.my_name = self.host_name
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.host_port))
            self.socket.listen(10)
            self.socket.settimeout(1)
            
            local_ip = self.get_local_ip()
            self.share_code = f"{local_ip}:{self.host_port}"
            self.is_host = True
            self.is_connected = True
            self.running = True
            self.clients = {}
            self.pending_commands = []
            self.pending_files = []
            self.terminal_logs = []
            self.chat_messages = []
            
            ai_mode_str = f"{Fore.RED}NO-AI (Direct Execute){Style.RESET_ALL}" if self.no_ai_mode else f"{Fore.GREEN}AI-Assisted{Style.RESET_ALL}"
            encrypt_str = f"{Fore.GREEN}ON{Style.RESET_ALL}" if self.encryption_enabled else f"{Fore.YELLOW}OFF{Style.RESET_ALL}"
            
            print(f"\n{Fore.GREEN}{'='*55}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}   TERMINAL SHARING STARTED - MULTI-CLIENT P2P{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*55}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Your Name: {self.host_name}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Local Address: {Fore.YELLOW}{self.share_code}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Mode: {ai_mode_str} | Encryption: {encrypt_str}{Style.RESET_ALL}")
            if self.no_ai_mode:
                print(f"{Fore.YELLOW}⚠ NO-AI MODE: Commands will execute directly without AI processing{Style.RESET_ALL}")
            print(f"\n{Fore.MAGENTA}FOR GLOBAL ACCESS:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  1. Run: ngrok tcp {self.host_port}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  2. Share the ngrok URL{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}Commands:{Style.RESET_ALL}")
            print(f"  share message <text>       - Send message to all")
            print(f"  share file <path> [user]   - Send file (default: broadcast)")
            print(f"  share list                 - List connected clients")
            print(f"  share approve/reject       - Handle commands")
            print(f"  share end                  - End session")
            print(f"\n{Fore.CYAN}Waiting for connections...{Style.RESET_ALL}\n")
            
            self.receive_thread = threading.Thread(target=self._host_accept_loop, daemon=True)
            self.receive_thread.start()
            
            return {"success": True, "local": self.share_code, "port": self.host_port}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _host_accept_loop(self):
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                client_id = str(uuid.uuid4())[:8]
                
                handler_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, addr, client_id),
                    daemon=True
                )
                handler_thread.start()
                
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    import time
                    time.sleep(0.1)
    
    def _handle_client(self, client_socket, addr, client_id):
        client_socket.settimeout(0.5)
        
        try:
            client_socket.settimeout(30)
            data = client_socket.recv(4096)
            if not data:
                client_socket.close()
                return
            
            msg = json.loads(data.decode('utf-8').strip())
            raw_name = msg.get('name', 'Helper')
            safe_name = ''.join(c for c in raw_name if c.isalnum() or c in ' -_')[:20] or 'Helper'
            unique_name = self._get_unique_name(safe_name)
            
            with self.client_lock:
                self.clients[client_id] = {
                    'socket': client_socket,
                    'name': unique_name,
                    'addr': addr,
                    'connected_at': datetime.datetime.now().isoformat()
                }
            
            all_users = self.get_connected_users()
            response = {
                'type': 'welcome',
                'your_name': unique_name,
                'host_name': self.host_name,
                'client_count': len(self.clients),
                'connected_users': all_users
            }
            self._send_to_client(client_id, response)
            
            print(f"\n{Fore.GREEN}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}New connection: {unique_name} from {addr[0]}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Total connected: {len(self.clients)}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
            self._broadcast({
                'type': 'user_joined',
                'name': unique_name,
                'client_count': len(self.clients),
                'connected_users': self.get_connected_users()
            }, exclude=client_id)
            
            self._add_log(f"[CONNECT] {unique_name} joined from {addr[0]}", "system")
            
            client_socket.settimeout(0.5)
            buffer = ""
            
            while self.running:
                try:
                    data = client_socket.recv(65536)
                    if data:
                        buffer += data.decode('utf-8')
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            if line.strip():
                                try:
                                    msg = json.loads(line)
                                    self._handle_client_message(client_id, msg)
                                except json.JSONDecodeError:
                                    pass
                    else:
                        break
                except socket.timeout:
                    continue
                except Exception:
                    break
            
        except Exception as e:
            pass
        finally:
            with self.client_lock:
                if client_id in self.clients:
                    name = self.clients[client_id]['name']
                    del self.clients[client_id]
                    print(f"\n{Fore.YELLOW}{name} disconnected. Total: {len(self.clients)}{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
                    self._broadcast({
                        'type': 'user_left',
                        'name': name,
                        'client_count': len(self.clients),
                        'connected_users': self.get_connected_users()
                    })
                    self._add_log(f"[DISCONNECT] {name} left", "system")
            try:
                client_socket.close()
            except Exception:
                pass
    
    def _handle_client_message(self, client_id: str, msg: Dict):
        with self.client_lock:
            if client_id not in self.clients:
                return
            sender_name = self.clients[client_id]['name']
        
        msg_type = msg.get("type", "")
        
        if msg_type == "command":
            cmd_text = msg.get("command", "")
            cmd_id = str(uuid.uuid4())[:8]
            
            print(f"\n{Fore.YELLOW}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}COMMAND from {sender_name}:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{cmd_text}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'='*50}{Style.RESET_ALL}")
            
            self.pending_commands.append({
                "id": cmd_id,
                "command": cmd_text,
                "from": sender_name,
                "client_id": client_id,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            self._add_log(f"[CMD REQUEST] {sender_name}: {cmd_text[:50]}", "command")
            
            print(f"{Fore.YELLOW}Type 'share approve' or 'share reject'{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "message":
            text = msg.get("text", "")
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            self.chat_messages.append({
                "sender": sender_name,
                "text": text,
                "timestamp": timestamp
            })
            
            print(f"\n{Fore.MAGENTA}[{timestamp}] {sender_name}: {text}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
            self._add_log(f"[MSG] {sender_name}: {text[:50]}", "chat")
            
            self._broadcast({
                'type': 'message',
                'sender': sender_name,
                'text': text,
                'timestamp': timestamp
            }, exclude=client_id)
            
        elif msg_type == "log_request":
            self._send_to_client(client_id, {"type": "logs", "logs": self.terminal_logs[-30:]})
            
        elif msg_type == "file_start":
            filename = msg.get("filename", "unknown")
            filesize = msg.get("filesize", 0)
            file_id = msg.get("file_id", str(uuid.uuid4())[:8])
            target_user = msg.get("target_user", None)
            checksum = msg.get("checksum", "")
            
            if filesize > MAX_FILE_SIZE:
                self._send_to_client(client_id, {
                    "type": "file_error",
                    "file_id": file_id,
                    "error": f"File too large. Max: {MAX_FILE_SIZE // (1024*1024)}MB"
                })
                return
            
            self.file_transfer_progress[file_id] = {
                "filename": filename,
                "filesize": filesize,
                "received": 0,
                "data": b"",
                "sender": sender_name,
                "client_id": client_id,
                "target_user": target_user,
                "checksum": checksum
            }
            
            target_info = f" -> {target_user}" if target_user else " (broadcast)"
            print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}FILE TRANSFER from {sender_name}{target_info}:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  File: {filename}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  Size: {self._format_size(filesize)}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
            
            self._send_to_client(client_id, {"type": "file_ready", "file_id": file_id})
            
        elif msg_type == "file_chunk":
            file_id = msg.get("file_id", "")
            chunk_data = msg.get("data", "")
            
            if file_id in self.file_transfer_progress:
                transfer = self.file_transfer_progress[file_id]
                decoded = base64.b64decode(chunk_data)
                transfer["data"] += decoded
                transfer["received"] += len(decoded)
                
                progress = (transfer["received"] / transfer["filesize"]) * 100
                print(f"\r{Fore.CYAN}Receiving: {progress:.1f}%{Style.RESET_ALL}", end="", flush=True)
                
        elif msg_type == "file_end":
            file_id = msg.get("file_id", "")
            if file_id in self.file_transfer_progress:
                transfer = self.file_transfer_progress[file_id]
                received_checksum = hashlib.md5(transfer["data"]).hexdigest()
                
                if transfer["checksum"] and received_checksum != transfer["checksum"]:
                    print(f"\n{Fore.RED}File checksum mismatch! Transfer corrupted.{Style.RESET_ALL}")
                    self._send_to_client(client_id, {
                        "type": "file_error",
                        "file_id": file_id,
                        "error": "Checksum mismatch"
                    })
                else:
                    self.pending_files.append({
                        "id": file_id,
                        "filename": transfer["filename"],
                        "data": transfer["data"],
                        "size": transfer["received"],
                        "from": transfer["sender"],
                        "client_id": client_id,
                        "target_user": transfer["target_user"],
                        "timestamp": datetime.datetime.now().isoformat()
                    })
                    
                    print(f"\n{Fore.GREEN}File received: {transfer['filename']} ({self._format_size(transfer['received'])}){Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Type 'share accept' to save or 'share deny' to reject{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
                    
                    self._add_log(f"[FILE] {transfer['sender']}: {transfer['filename']}", "file")
                    
                    self._send_to_client(client_id, {
                        "type": "file_complete",
                        "file_id": file_id,
                        "filename": transfer["filename"]
                    })
                
                del self.file_transfer_progress[file_id]
        
        elif msg_type == "file_forward":
            target_user = msg.get("target_user", "")
            if target_user:
                target_client_id = self.find_user_by_name(target_user)
                if target_client_id:
                    msg["original_sender"] = sender_name
                    self._send_to_client(target_client_id, msg)
    
    def _send_to_client(self, client_id: str, msg: Dict) -> bool:
        with self.client_lock:
            if client_id not in self.clients:
                return False
            client = self.clients[client_id]
        
        try:
            data = json.dumps(msg) + '\n'
            client['socket'].send(data.encode('utf-8'))
            return True
        except Exception:
            return False
    
    def _broadcast(self, msg: Dict, exclude: str = None):
        with self.client_lock:
            client_ids = list(self.clients.keys())
        
        for client_id in client_ids:
            if client_id != exclude:
                self._send_to_client(client_id, msg)
    
    def connect_to_session(self, address: str, my_name: str = None) -> Dict:
        if my_name:
            self.my_name = my_name
            self._save_name(my_name)
        else:
            self.my_name = self.get_or_ask_name("Helper")
        
        try:
            if ':' in address:
                parts = address.split(':')
                host = parts[0]
                port = int(parts[1])
            else:
                host = address
                port = self.DEFAULT_PORT
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(15)
            
            print(f"{Fore.CYAN}Connecting to {host}:{port}...{Style.RESET_ALL}")
            self.socket.connect((host, port))
            
            hello_msg = json.dumps({'type': 'hello', 'name': self.my_name}) + '\n'
            self.socket.send(hello_msg.encode('utf-8'))
            
            self.socket.settimeout(10)
            data = self.socket.recv(4096)
            response = json.loads(data.decode('utf-8').strip())
            
            if response.get('type') == 'welcome':
                self.my_name = response.get('your_name', self.my_name)
                self.host_name = response.get('host_name', 'Host')
                self.connected_users = response.get('connected_users', [self.host_name])
            
            self.socket.settimeout(0.5)
            self.share_code = f"{host}:{port}"
            self.is_host = False
            self.is_connected = True
            self.running = True
            self.chat_messages = []
            self.terminal_logs = []
            
            print(f"\n{Fore.GREEN}{'='*55}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}   CONNECTED - MULTI-CLIENT P2P{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*55}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Your Name: {self.my_name}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Host: {self.host_name} @ {self.share_code}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Connected Users: {', '.join(self.connected_users)}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}Commands:{Style.RESET_ALL}")
            print(f"  share message <text>       - Send message to all")
            print(f"  share file <path> [user]   - Send file (default: host)")
            print(f"  share send <command>       - Send command (needs approval)")
            print(f"  share logs                 - Request host logs")
            print(f"  share end                  - Disconnect")
            print()
            
            self.receive_thread = threading.Thread(target=self._helper_receive_loop, daemon=True)
            self.receive_thread.start()
            
            return {"success": True, "host": self.share_code, "my_name": self.my_name}
            
        except socket.timeout:
            return {"success": False, "error": "Connection timeout"}
        except ConnectionRefusedError:
            return {"success": False, "error": "Connection refused"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _helper_receive_loop(self):
        import time
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(65536)
                if data:
                    buffer += data.decode('utf-8')
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            try:
                                msg = json.loads(line)
                                self._handle_host_message(msg)
                            except json.JSONDecodeError:
                                pass
                else:
                    print(f"\n{Fore.YELLOW}Disconnected from host{Style.RESET_ALL}")
                    self.running = False
                    self.is_connected = False
                    break
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    time.sleep(0.1)
    
    def _handle_host_message(self, msg: Dict):
        msg_type = msg.get("type", "")
        
        if msg_type == "message":
            sender = msg.get("sender", "Unknown")
            text = msg.get("text", "")
            timestamp = msg.get("timestamp", datetime.datetime.now().strftime("%H:%M:%S"))
            
            self.chat_messages.append({"sender": sender, "text": text, "timestamp": timestamp})
            print(f"\n{Fore.MAGENTA}[{timestamp}] {sender}: {text}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "user_joined":
            name = msg.get("name", "Someone")
            count = msg.get("client_count", 0)
            self.connected_users = msg.get("connected_users", self.connected_users)
            print(f"\n{Fore.GREEN}{name} joined. Total clients: {count}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "user_left":
            name = msg.get("name", "Someone")
            count = msg.get("client_count", 0)
            self.connected_users = msg.get("connected_users", self.connected_users)
            print(f"\n{Fore.YELLOW}{name} left. Total clients: {count}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "approved":
            print(f"\n{Fore.GREEN}Command approved!{Style.RESET_ALL}")
            result = msg.get("result", "")
            if result:
                print(f"{Fore.WHITE}{result[:500]}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "rejected":
            print(f"\n{Fore.RED}Command rejected by host{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "logs":
            logs = msg.get("logs", [])
            print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}TERMINAL LOGS{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
            for log in logs:
                ts = log.get('timestamp', '').split('T')[1][:8] if 'T' in log.get('timestamp', '') else ''
                log_type = log.get('type', 'info')
                log_text = log.get('log', '')
                color = self._get_log_color(log_type)
                print(f"  {color}[{ts}] {log_text[:80]}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "output":
            output = msg.get("output", "")
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"\n{Fore.BLUE}[{timestamp}] [OUTPUT] {output}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "file_start":
            filename = msg.get("filename", "unknown")
            filesize = msg.get("filesize", 0)
            sender = msg.get("original_sender", msg.get("sender", "Unknown"))
            file_id = msg.get("file_id", str(uuid.uuid4())[:8])
            
            print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}INCOMING FILE from {sender}:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  File: {filename}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  Size: {self._format_size(filesize)}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
            
            self.file_transfer_progress[file_id] = {
                "filename": filename,
                "filesize": filesize,
                "received": 0,
                "data": b"",
                "sender": sender
            }
            
        elif msg_type == "file_chunk":
            file_id = msg.get("file_id", "")
            chunk_data = msg.get("data", "")
            
            if file_id in self.file_transfer_progress:
                transfer = self.file_transfer_progress[file_id]
                decoded = base64.b64decode(chunk_data)
                transfer["data"] += decoded
                transfer["received"] += len(decoded)
                
                progress = (transfer["received"] / transfer["filesize"]) * 100
                print(f"\r{Fore.CYAN}Receiving: {progress:.1f}%{Style.RESET_ALL}", end="", flush=True)
                
        elif msg_type == "file_end":
            file_id = msg.get("file_id", "")
            if file_id in self.file_transfer_progress:
                transfer = self.file_transfer_progress[file_id]
                
                self.pending_files.append({
                    "id": file_id,
                    "filename": transfer["filename"],
                    "data": transfer["data"],
                    "size": transfer["received"],
                    "from": transfer["sender"],
                    "timestamp": datetime.datetime.now().isoformat()
                })
                
                print(f"\n{Fore.GREEN}File received: {transfer['filename']} ({self._format_size(transfer['received'])}){Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Type 'share accept' to save or 'share deny' to reject{Style.RESET_ALL}")
                print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
                
                del self.file_transfer_progress[file_id]
                
        elif msg_type == "file_complete":
            filename = msg.get("filename", "")
            print(f"\n{Fore.GREEN}File transfer complete: {filename}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "file_error":
            error = msg.get("error", "Unknown error")
            print(f"\n{Fore.RED}File transfer error: {error}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
    
    def send_message(self, text: str) -> Dict:
        if not self.is_connected:
            return {"success": False, "error": "Not connected"}
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        msg = {
            "type": "message",
            "sender": self.my_name,
            "text": text,
            "timestamp": timestamp
        }
        
        self.chat_messages.append({"sender": "You", "text": text, "timestamp": timestamp})
        self._add_log(f"[MSG] You: {text[:50]}", "chat")
        
        if self.is_host:
            self._broadcast(msg)
            print(f"{Fore.GREEN}[{timestamp}] You: {text}{Style.RESET_ALL}")
        else:
            try:
                data = json.dumps(msg) + '\n'
                self.socket.send(data.encode('utf-8'))
                print(f"{Fore.GREEN}[{timestamp}] You: {text}{Style.RESET_ALL}")
            except Exception:
                return {"success": False, "error": "Failed to send"}
        
        return {"success": True}
    
    def send_command(self, command: str) -> Dict:
        if not self.is_connected or self.is_host:
            return {"success": False, "error": "Only helpers can send commands"}
        
        try:
            msg = {"type": "command", "command": command}
            data = json.dumps(msg) + '\n'
            self.socket.send(data.encode('utf-8'))
            print(f"{Fore.CYAN}Command sent, waiting for approval...{Style.RESET_ALL}")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_command_to_user(self, command: str, target_user: str = None) -> Dict:
        if not self.is_connected:
            return {"success": False, "error": "Not connected"}
        
        if self.is_host:
            if target_user:
                target_client_id = self.find_user_by_name(target_user)
                if not target_client_id:
                    return {"success": False, "error": f"User not found: {target_user}"}
                
                msg = {
                    "type": "remote_command",
                    "command": command,
                    "from": self.my_name
                }
                self._send_to_client(target_client_id, msg)
                print(f"{Fore.CYAN}Command sent to {target_user}, waiting for response...{Style.RESET_ALL}")
                self._add_log(f"[CMD SENT] -> {target_user}: {command[:50]}", "command")
                return {"success": True}
            else:
                self._broadcast({
                    "type": "remote_command",
                    "command": command,
                    "from": self.my_name
                })
                print(f"{Fore.CYAN}Command broadcast to all clients...{Style.RESET_ALL}")
                self._add_log(f"[CMD BROADCAST] {command[:50]}", "command")
                return {"success": True}
        else:
            try:
                msg = {"type": "command", "command": command, "target_user": target_user}
                data = json.dumps(msg) + '\n'
                self.socket.send(data.encode('utf-8'))
                target_info = f" for {target_user}" if target_user else ""
                print(f"{Fore.CYAN}Command sent{target_info}, waiting for approval...{Style.RESET_ALL}")
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    def send_file(self, file_path: str, target_user: str = None) -> Dict:
        if not self.is_connected:
            return {"success": False, "error": "Not connected"}
        
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            return {"success": False, "error": f"File too large. Max: {MAX_FILE_SIZE // (1024*1024)}MB"}
        
        filename = os.path.basename(file_path)
        file_id = str(uuid.uuid4())[:8]
        
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            checksum = hashlib.md5(file_data).hexdigest()
            
            if self.is_host:
                if target_user:
                    target_client_id = self.find_user_by_name(target_user)
                    if not target_client_id:
                        return {"success": False, "error": f"User not found: {target_user}"}
                    target_ids = [target_client_id]
                    print(f"{Fore.CYAN}Sending file to {target_user}...{Style.RESET_ALL}")
                else:
                    with self.client_lock:
                        target_ids = list(self.clients.keys())
                    print(f"{Fore.CYAN}Broadcasting file to all clients...{Style.RESET_ALL}")
                
                for client_id in target_ids:
                    self._send_to_client(client_id, {
                        "type": "file_start",
                        "filename": filename,
                        "filesize": file_size,
                        "file_id": file_id,
                        "sender": self.my_name,
                        "checksum": checksum
                    })
                    
                    for i in range(0, len(file_data), CHUNK_SIZE):
                        chunk = file_data[i:i + CHUNK_SIZE]
                        self._send_to_client(client_id, {
                            "type": "file_chunk",
                            "file_id": file_id,
                            "data": base64.b64encode(chunk).decode('utf-8')
                        })
                        progress = min(100, ((i + CHUNK_SIZE) / file_size) * 100)
                        print(f"\r{Fore.CYAN}Sending: {progress:.1f}%{Style.RESET_ALL}", end="", flush=True)
                    
                    self._send_to_client(client_id, {
                        "type": "file_end",
                        "file_id": file_id
                    })
                
                print(f"\n{Fore.GREEN}File sent: {filename}{Style.RESET_ALL}")
                self._add_log(f"[FILE SENT] {filename} -> {target_user or 'all'}", "file")
                
            else:
                start_msg = {
                    "type": "file_start",
                    "filename": filename,
                    "filesize": file_size,
                    "file_id": file_id,
                    "target_user": target_user,
                    "checksum": checksum
                }
                self.socket.send((json.dumps(start_msg) + '\n').encode('utf-8'))
                
                import time
                time.sleep(0.5)
                
                for i in range(0, len(file_data), CHUNK_SIZE):
                    chunk = file_data[i:i + CHUNK_SIZE]
                    chunk_msg = {
                        "type": "file_chunk",
                        "file_id": file_id,
                        "data": base64.b64encode(chunk).decode('utf-8')
                    }
                    self.socket.send((json.dumps(chunk_msg) + '\n').encode('utf-8'))
                    progress = min(100, ((i + CHUNK_SIZE) / file_size) * 100)
                    print(f"\r{Fore.CYAN}Sending: {progress:.1f}%{Style.RESET_ALL}", end="", flush=True)
                    time.sleep(0.01)
                
                end_msg = {"type": "file_end", "file_id": file_id}
                self.socket.send((json.dumps(end_msg) + '\n').encode('utf-8'))
                
                print(f"\n{Fore.CYAN}File sent, waiting for confirmation...{Style.RESET_ALL}")
            
            return {"success": True, "filename": filename, "size": file_size}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def accept_file(self, save_path: str = None) -> Dict:
        if not self.pending_files:
            return {"success": False, "error": "No pending files"}
        
        file_info = self.pending_files.pop(0)
        filename = file_info["filename"]
        file_data = file_info["data"]
        
        if save_path:
            if os.path.isdir(save_path):
                full_path = os.path.join(save_path, filename)
            else:
                full_path = save_path
        else:
            downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            if not os.path.exists(downloads_dir):
                downloads_dir = os.getcwd()
            full_path = os.path.join(downloads_dir, filename)
        
        counter = 1
        base_path = full_path
        while os.path.exists(full_path):
            name, ext = os.path.splitext(base_path)
            full_path = f"{name}_{counter}{ext}"
            counter += 1
        
        try:
            with open(full_path, 'wb') as f:
                f.write(file_data)
            
            print(f"{Fore.GREEN}File saved: {full_path}{Style.RESET_ALL}")
            self._add_log(f"[FILE SAVED] {filename} from {file_info['from']}", "file")
            return {"success": True, "path": full_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def deny_file(self) -> Dict:
        if not self.pending_files:
            return {"success": False, "error": "No pending files"}
        
        file_info = self.pending_files.pop(0)
        print(f"{Fore.YELLOW}File rejected: {file_info['filename']}{Style.RESET_ALL}")
        return {"success": True}
    
    def approve_pending(self, approve: bool = True) -> Optional[str]:
        if not self.pending_commands:
            return None
        
        cmd = self.pending_commands.pop(0)
        cmd_text = cmd["command"]
        client_id = cmd.get("client_id")
        
        if approve:
            print(f"{Fore.GREEN}Approved: {cmd_text[:50]}...{Style.RESET_ALL}")
            self._add_log(f"[CMD APPROVED] {cmd_text[:50]}", "command")
            if client_id:
                self._send_to_client(client_id, {"type": "approved", "command": cmd_text, "result": "Executing..."})
            return cmd_text
        else:
            print(f"{Fore.YELLOW}Rejected: {cmd_text[:50]}...{Style.RESET_ALL}")
            self._add_log(f"[CMD REJECTED] {cmd_text[:50]}", "command")
            if client_id:
                self._send_to_client(client_id, {"type": "rejected", "command": cmd_text})
            return None
    
    def list_clients(self):
        with self.client_lock:
            clients = list(self.clients.values())
        
        print(f"\n{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}CONNECTED CLIENTS ({len(clients)}){Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}0. {self.host_name} (Host - You){Style.RESET_ALL}")
        
        if not clients:
            print(f"  {Fore.WHITE}No other clients connected{Style.RESET_ALL}")
        else:
            for i, client in enumerate(clients, 1):
                name = client['name']
                addr = client['addr']
                print(f"  {Fore.GREEN}{i}. {name}{Style.RESET_ALL} @ {addr[0]}:{addr[1]}")
        
        print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
    
    def _add_log(self, log: str, log_type: str = "info"):
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "log": log[:500],
            "type": log_type
        }
        self.terminal_logs.append(entry)
        if len(self.terminal_logs) > 100:
            self.terminal_logs = self.terminal_logs[-100:]
    
    def _get_log_color(self, log_type: str) -> str:
        colors = {
            "system": Fore.CYAN,
            "command": Fore.YELLOW,
            "chat": Fore.MAGENTA,
            "file": Fore.GREEN,
            "output": Fore.BLUE,
            "error": Fore.RED,
            "info": Fore.WHITE
        }
        return colors.get(log_type, Fore.WHITE)
    
    def add_terminal_log(self, log: str, broadcast: bool = True):
        self._add_log(log, "output")
        
        if broadcast and self.is_connected and self.is_host:
            self._broadcast({"type": "output", "output": log[:200]})
    
    def broadcast_output(self, output: str):
        if self.is_connected and self.is_host:
            self._broadcast({"type": "output", "output": output[:500]})
    
    def request_logs(self):
        if not self.is_host and self.is_connected:
            msg = {"type": "log_request"}
            data = json.dumps(msg) + '\n'
            self.socket.send(data.encode('utf-8'))
            print(f"{Fore.CYAN}Requesting logs...{Style.RESET_ALL}")
    
    def get_pending_count(self) -> int:
        return len(self.pending_commands)
    
    def get_pending_files_count(self) -> int:
        return len(self.pending_files)
    
    @property
    def client_socket(self):
        with self.client_lock:
            if self.clients:
                first_client = list(self.clients.values())[0]
                return first_client['socket']
        return None
    
    def show_chat_history(self, count: int = 15):
        messages = self.chat_messages[-count:]
        if not messages:
            print(f"{Fore.YELLOW}No messages yet{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}CHAT HISTORY{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
        for msg in messages:
            sender = msg['sender']
            text = msg['text']
            ts = msg['timestamp']
            color = Fore.GREEN if sender == "You" else Fore.MAGENTA
            print(f"  {color}[{ts}] {sender}: {text}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
    
    def show_recent_logs(self, count: int = 15):
        if not self.is_host:
            self.request_logs()
            return
        
        logs = self.terminal_logs[-count:]
        if not logs:
            print(f"{Fore.YELLOW}No logs yet{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}TERMINAL LOGS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        for log in logs:
            ts = log['timestamp'].split('T')[1][:8]
            log_type = log.get('type', 'info')
            log_text = log['log']
            color = self._get_log_color(log_type)
            print(f"  {color}[{ts}] {log_text[:80]}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def get_p2p_context(self) -> Dict:
        if not self.is_connected:
            return {"connected": False}
        
        return {
            "connected": True,
            "is_host": self.is_host,
            "my_name": self.my_name,
            "host_name": self.host_name,
            "share_code": self.share_code,
            "connected_users": self.get_connected_users(),
            "pending_commands": len(self.pending_commands),
            "pending_files": len(self.pending_files),
            "recent_messages": self.chat_messages[-5:],
            "recent_logs": self.terminal_logs[-5:],
            "available_actions": self._get_available_actions()
        }
    
    def _get_available_actions(self) -> List[str]:
        actions = []
        if not self.is_connected:
            return ["start_session", "connect_session"]
        
        actions.extend(["send_message", "show_logs", "show_chat", "list_users", "show_status", "end_session"])
        
        if self.is_host:
            actions.extend(["send_file_to_user", "broadcast_file"])
            if self.pending_commands:
                actions.extend(["approve_command", "reject_command"])
            if self.pending_files:
                actions.extend(["accept_file", "deny_file"])
        else:
            actions.extend(["send_file", "send_command"])
            if self.pending_files:
                actions.extend(["accept_file", "deny_file"])
        
        return actions
    
    def execute_p2p_action(self, action: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        
        if action == "show_logs":
            self.show_recent_logs()
            return {"success": True}
        elif action == "show_chat":
            self.show_chat_history()
            return {"success": True}
        elif action == "list_users":
            if self.is_host:
                self.list_clients()
            else:
                users = self.get_connected_users()
                from colorama import Fore, Style
                print(f"\n{Fore.CYAN}Connected Users: {', '.join(users)}{Style.RESET_ALL}")
            return {"success": True}
        elif action == "show_status":
            return {"success": True, "context": self.get_p2p_context()}
        elif action == "send_message":
            message = params.get("message", "")
            if message:
                return self.send_message(message)
            return {"success": False, "error": "No message provided"}
        elif action == "send_file":
            file_path = params.get("file_path", "")
            target_user = params.get("target_user")
            if file_path:
                return self.send_file(file_path, target_user)
            return {"success": False, "error": "No file path provided"}
        elif action == "send_command":
            command = params.get("command", "")
            target_user = params.get("target_user")
            if command:
                return self.send_command_to_user(command, target_user)
            return {"success": False, "error": "No command provided"}
        elif action == "approve_command":
            cmd = self.approve_pending(True)
            return {"success": True, "command": cmd}
        elif action == "reject_command":
            self.approve_pending(False)
            return {"success": True}
        elif action == "accept_file":
            save_path = params.get("save_path")
            return self.accept_file(save_path)
        elif action == "deny_file":
            return self.deny_file()
        
        return {"success": False, "error": f"Unknown action: {action}"}
    
    def end_session(self):
        print(f"{Fore.YELLOW}Ending P2P session...{Style.RESET_ALL}")
        self.running = False
        
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        self.receive_thread = None
        
        with self.client_lock:
            for client_id, client in list(self.clients.items()):
                try:
                    client['socket'].close()
                except Exception:
                    pass
            self.clients.clear()
        
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        
        self.share_code = None
        self.is_connected = False
        self.is_host = False
        self.pending_commands = []
        self.pending_files = []
        self.terminal_logs = []
        self.chat_messages = []
        self.connected_users = []
        self.file_transfer_progress = {}
        print(f"{Fore.GREEN}Session ended{Style.RESET_ALL}\n")