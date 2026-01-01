import socket
import threading
import json
import datetime
import uuid
import os
from typing import Dict, Optional, List

from colorama import Fore, Style

P2P_NAME_FILE = ".zaishell_p2p_name"


class P2PTerminalSharing:
    """Multi-client terminal sharing via TCP sockets"""
    
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
        self.safe_mode_always = True
        self.terminal_logs = []
        self.chat_messages = []
        self.receive_thread = None
        self.running = False
        self.host_port = self.DEFAULT_PORT
        self.host_name = "Host"
    
    def _load_saved_name(self) -> Optional[str]:
        """Load saved name from file"""
        try:
            if os.path.exists(P2P_NAME_FILE):
                with open(P2P_NAME_FILE, 'r', encoding='utf-8') as f:
                    name = f.read().strip()
                    return name if name else None
        except:
            pass
        return None
    
    def _save_name(self, name: str):
        """Save name to file for persistence"""
        try:
            with open(P2P_NAME_FILE, 'w', encoding='utf-8') as f:
                f.write(name)
        except:
            pass
    
    def set_name(self, new_name: str) -> bool:
        """Change and save username"""
        if not new_name or len(new_name) > 20:
            return False
        self.my_name = new_name
        self._save_name(new_name)
        print(f"{Fore.GREEN}Name changed to: {new_name}{Style.RESET_ALL}")
        return True
    
    def get_or_ask_name(self, default: str = "Helper") -> str:
        """Get saved name or ask user for name"""
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
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def _get_unique_name(self, requested_name: str) -> str:
        """Generate unique name if duplicates exist"""
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
    
    def start_sharing_session(self, port: int = None, host_name: str = None) -> Dict:
        """Start hosting a sharing session - REAL TCP SERVER WITH MULTI-CLIENT"""
        if port:
            self.host_port = port
        
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
            self.terminal_logs = []
            self.chat_messages = []
            
            print(f"\n{Fore.GREEN}{'='*55}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}   TERMINAL SHARING STARTED - MULTI-CLIENT P2P{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*55}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Your Name: {self.host_name}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Local Address: {Fore.YELLOW}{self.share_code}{Style.RESET_ALL}")
            print(f"\n{Fore.MAGENTA}FOR GLOBAL ACCESS:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  1. Run: ngrok tcp {self.host_port}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  2. Share the ngrok URL{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}Commands:{Style.RESET_ALL}")
            print(f"  share message <text>  - Send message to all")
            print(f"  share list            - List connected clients")
            print(f"  share approve/reject  - Handle commands")
            print(f"  share end             - End session")
            print(f"\n{Fore.CYAN}Waiting for connections...{Style.RESET_ALL}\n")
            
            self.receive_thread = threading.Thread(target=self._host_accept_loop, daemon=True)
            self.receive_thread.start()
            
            return {"success": True, "local": self.share_code, "port": self.host_port}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _host_accept_loop(self):
        """Accept multiple client connections"""
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
            except:
                if self.running:
                    import time
                    time.sleep(0.1)
    
    def _handle_client(self, client_socket, addr, client_id):
        """Handle individual client connection"""
        client_socket.settimeout(0.5)
        
        try:
            client_socket.settimeout(30)
            data = client_socket.recv(4096)
            if not data:
                client_socket.close()
                return
            
            msg = json.loads(data.decode('utf-8').strip())
            requested_name = msg.get('name', 'Helper')
            unique_name = self._get_unique_name(requested_name)
            
            with self.client_lock:
                self.clients[client_id] = {
                    'socket': client_socket,
                    'name': unique_name,
                    'addr': addr,
                    'connected_at': datetime.datetime.now().isoformat()
                }
            
            response = {
                'type': 'welcome',
                'your_name': unique_name,
                'host_name': self.host_name,
                'client_count': len(self.clients)
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
                'client_count': len(self.clients)
            }, exclude=client_id)
            
            client_socket.settimeout(0.5)
            buffer = ""
            
            while self.running:
                try:
                    data = client_socket.recv(4096)
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
                except:
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
                        'client_count': len(self.clients)
                    })
            try:
                client_socket.close()
            except:
                pass
    
    def _handle_client_message(self, client_id: str, msg: Dict):
        """Handle message from a specific client"""
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
            
            self._broadcast({
                'type': 'message',
                'sender': sender_name,
                'text': text,
                'timestamp': timestamp
            }, exclude=client_id)
            
        elif msg_type == "log_request":
            self._send_to_client(client_id, {"type": "logs", "logs": self.terminal_logs[-20:]})
    
    def _send_to_client(self, client_id: str, msg: Dict) -> bool:
        """Send message to specific client"""
        with self.client_lock:
            if client_id not in self.clients:
                return False
            client = self.clients[client_id]
        
        try:
            data = json.dumps(msg) + '\n'
            client['socket'].send(data.encode('utf-8'))
            return True
        except:
            return False
    
    def _broadcast(self, msg: Dict, exclude: str = None):
        """Broadcast message to all connected clients"""
        with self.client_lock:
            client_ids = list(self.clients.keys())
        
        for client_id in client_ids:
            if client_id != exclude:
                self._send_to_client(client_id, msg)
    
    def connect_to_session(self, address: str, my_name: str = None) -> Dict:
        """Connect to a host as helper"""
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
            
            self.socket.settimeout(0.5)
            self.share_code = f"{host}:{port}"
            self.is_host = False
            self.is_connected = True
            self.running = True
            self.chat_messages = []
            
            print(f"\n{Fore.GREEN}{'='*55}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}   CONNECTED - MULTI-CLIENT P2P{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*55}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Your Name: {self.my_name}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Host: {self.host_name} @ {self.share_code}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}Commands:{Style.RESET_ALL}")
            print(f"  share message <text>  - Send message to all")
            print(f"  share send <command>  - Send command (needs approval)")
            print(f"  share logs            - Request host logs")
            print(f"  share end             - Disconnect")
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
        """Helper: receive messages from host"""
        import time
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(4096)
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
            except:
                if self.running:
                    time.sleep(0.1)
    
    def _handle_host_message(self, msg: Dict):
        """Handle messages from host or relayed from other clients"""
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
            print(f"\n{Fore.GREEN}{name} joined. Total clients: {count}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "user_left":
            name = msg.get("name", "Someone")
            count = msg.get("client_count", 0)
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
            print(f"\n{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}HOST TERMINAL LOGS{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
            for log in logs:
                ts = log.get('timestamp', '').split('T')[1][:8] if 'T' in log.get('timestamp', '') else ''
                print(f"  [{ts}] {log.get('log', '')[:80]}")
            print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
            
        elif msg_type == "output":
            output = msg.get("output", "")
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"\n{Fore.BLUE}[{timestamp}] [OUTPUT] {output}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You >>> {Style.RESET_ALL}", end="", flush=True)
    
    def send_message(self, text: str) -> Dict:
        """Send chat message"""
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
        
        if self.is_host:
            self._broadcast(msg)
            print(f"{Fore.GREEN}[{timestamp}] You: {text}{Style.RESET_ALL}")
        else:
            try:
                data = json.dumps(msg) + '\n'
                self.socket.send(data.encode('utf-8'))
                print(f"{Fore.GREEN}[{timestamp}] You: {text}{Style.RESET_ALL}")
            except:
                return {"success": False, "error": "Failed to send"}
        
        return {"success": True}
    
    def send_command(self, command: str) -> Dict:
        """Helper: send command to host"""
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
    
    def approve_pending(self, approve: bool = True) -> Optional[str]:
        """Host: approve/reject pending command"""
        if not self.pending_commands:
            return None
        
        cmd = self.pending_commands.pop(0)
        cmd_text = cmd["command"]
        client_id = cmd.get("client_id")
        
        if approve:
            print(f"{Fore.GREEN}Approved: {cmd_text[:50]}...{Style.RESET_ALL}")
            if client_id:
                self._send_to_client(client_id, {"type": "approved", "command": cmd_text, "result": "Executing..."})
            return cmd_text
        else:
            print(f"{Fore.YELLOW}Rejected: {cmd_text[:50]}...{Style.RESET_ALL}")
            if client_id:
                self._send_to_client(client_id, {"type": "rejected", "command": cmd_text})
            return None
    
    def list_clients(self):
        """List all connected clients"""
        with self.client_lock:
            clients = list(self.clients.values())
        
        print(f"\n{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}CONNECTED CLIENTS ({len(clients)}){Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
        
        if not clients:
            print(f"  {Fore.YELLOW}No clients connected{Style.RESET_ALL}")
        else:
            for i, client in enumerate(clients, 1):
                name = client['name']
                addr = client['addr']
                print(f"  {i}. {Fore.GREEN}{name}{Style.RESET_ALL} @ {addr[0]}:{addr[1]}")
        
        print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
    
    def add_terminal_log(self, log: str, broadcast: bool = True):
        """Add and broadcast log"""
        entry = {"timestamp": datetime.datetime.now().isoformat(), "log": log[:500]}
        self.terminal_logs.append(entry)
        if len(self.terminal_logs) > 100:
            self.terminal_logs = self.terminal_logs[-100:]
        
        if broadcast and self.is_connected and self.is_host:
            self._broadcast({"type": "output", "output": log[:200]})
    
    def broadcast_output(self, output: str):
        """Broadcast output to all"""
        if self.is_connected and self.is_host:
            self._broadcast({"type": "output", "output": output[:500]})
    
    def request_logs(self):
        """Request logs from host"""
        if not self.is_host and self.is_connected:
            msg = {"type": "log_request"}
            data = json.dumps(msg) + '\n'
            self.socket.send(data.encode('utf-8'))
            print(f"{Fore.CYAN}Requesting logs...{Style.RESET_ALL}")
    
    def get_pending_count(self) -> int:
        return len(self.pending_commands)
    
    @property
    def client_socket(self):
        """Compatibility: return first client socket or None"""
        with self.client_lock:
            if self.clients:
                first_client = list(self.clients.values())[0]
                return first_client['socket']
        return None
    
    def show_chat_history(self, count: int = 15):
        """Show chat history"""
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
    
    def show_recent_logs(self, count: int = 10):
        """Show logs"""
        if not self.is_host:
            self.request_logs()
            return
        
        logs = self.terminal_logs[-count:]
        if not logs:
            print(f"{Fore.YELLOW}No logs yet{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}TERMINAL LOGS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
        for log in logs:
            ts = log['timestamp'].split('T')[1][:8]
            print(f"  [{ts}] {log['log'][:80]}")
        print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
    
    def end_session(self):
        """End session"""
        print(f"{Fore.YELLOW}Ending P2P session...{Style.RESET_ALL}")
        self.running = False
        
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        self.receive_thread = None
        
        with self.client_lock:
            for client_id, client in list(self.clients.items()):
                try:
                    client['socket'].close()
                except:
                    pass
            self.clients.clear()
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.share_code = None
        self.is_connected = False
        self.is_host = False
        self.my_name = None
        self.pending_commands = []
        self.terminal_logs = []
        self.chat_messages = []
        print(f"{Fore.GREEN}Session ended{Style.RESET_ALL}\n")
