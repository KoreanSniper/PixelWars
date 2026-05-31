from __future__ import annotations

import json
import socket
import threading
import time
import argparse
import secrets
from dataclasses import dataclass, field


DEFAULT_PORT = 50505
MAX_CLIENTS = 8
MAX_NAME_LEN = 16
MAX_MESSAGE_LEN = 2048


def local_ip_hint() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


@dataclass
class OnlineState:
    connected: bool = False
    hosting: bool = False
    room_code: str = "LOCAL"
    players: list[str] = field(default_factory=list)
    ready_players: list[str] = field(default_factory=list)
    message: str = "오프라인"


def safe_player_name(name: str) -> str:
    cleaned = "".join(ch for ch in name.strip() if ch.isprintable())
    return (cleaned or "Player")[:MAX_NAME_LEN]


class OnlineMatchServer:
    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT, room_code: str | None = None) -> None:
        self.host = host
        self.port = port
        self.room_code = (room_code or secrets.token_hex(3)).strip()[:32]
        self.players: dict[socket.socket, str] = {}
        self.ready: dict[socket.socket, bool] = {}
        self.lock = threading.Lock()
        self.running = False
        self.thread: threading.Thread | None = None
        self.server_socket: socket.socket | None = None
        self.error: str | None = None

    def start(self) -> bool:
        if self.running:
            return True
        self.error = None
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen()
            self.server_socket.settimeout(0.5)
        except OSError as exc:
            self.error = str(exc)
            self.running = False
            if self.server_socket:
                try:
                    self.server_socket.close()
                except OSError:
                    pass
            self.server_socket = None
            return False
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return True

    def stop(self) -> None:
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
        with self.lock:
            sockets = list(self.players)
        for client in sockets:
            try:
                client.close()
            except OSError:
                pass

    def _run(self) -> None:
        try:
            while self.running:
                if not self.server_socket:
                    break
                try:
                    client, _ = self.server_socket.accept()
                except socket.timeout:
                    continue
                with self.lock:
                    if len(self.players) >= MAX_CLIENTS:
                        client.close()
                        continue
                client.settimeout(0.5)
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
        except OSError:
            self.running = False

    def _handle_client(self, client: socket.socket) -> None:
        name = "Player"
        buffer = ""
        try:
            while self.running:
                try:
                    chunk = client.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="ignore")
                if len(buffer) > MAX_MESSAGE_LEN:
                    break
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    if len(line) > MAX_MESSAGE_LEN:
                        break
                    data = json.loads(line)
                    if data.get("type") == "hello":
                        if str(data.get("room") or "") != self.room_code:
                            self._send(client, {"type": "error", "message": "bad room code"})
                            break
                        name = self._unique_name(safe_player_name(str(data.get("name") or "Player")))
                        with self.lock:
                            self.players[client] = name
                            self.ready[client] = False
                        self.broadcast()
                    elif data.get("type") == "ready":
                        with self.lock:
                            if client in self.players:
                                self.ready[client] = bool(data.get("ready"))
                        self.broadcast()
                    elif data.get("type") == "ping":
                        self._send(client, {"type": "pong", "time": time.time()})
        except (OSError, json.JSONDecodeError):
            pass
        finally:
            with self.lock:
                self.players.pop(client, None)
                self.ready.pop(client, None)
            try:
                client.close()
            except OSError:
                pass
            self.broadcast()

    def _unique_name(self, name: str) -> str:
        with self.lock:
            used = set(self.players.values())
        if name not in used:
            return name
        index = 2
        while f"{name} {index}" in used:
            index += 1
        return f"{name} {index}"

    def broadcast(self) -> None:
        with self.lock:
            clients = list(self.players)
            players = list(self.players.values())
            ready_players = [self.players[client] for client in clients if self.ready.get(client)]
        payload = {"type": "state", "room": self.room_code, "players": players, "ready": ready_players}
        for client in clients:
            self._send(client, payload)

    def _send(self, client: socket.socket, payload: dict) -> None:
        try:
            client.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        except OSError:
            pass


class OnlineMatchClient:
    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT, name: str = "Player", room_code: str = "LOCAL") -> None:
        self.host = host
        self.port = port
        self.name = safe_player_name(name)
        self.room_code = room_code[:32]
        self.state = OnlineState()
        self.running = False
        self.socket: socket.socket | None = None
        self.thread: threading.Thread | None = None

    def connect(self) -> bool:
        self.close()
        try:
            self.socket = socket.create_connection((self.host, self.port), timeout=1.5)
            self.socket.settimeout(0.5)
            self.running = True
            self.state.connected = True
            self.state.message = f"{self.host}:{self.port} 연결됨"
            self.thread = threading.Thread(target=self._listen, daemon=True)
            self.thread.start()
            self.send({"type": "hello", "name": self.name, "room": self.room_code})
            return True
        except OSError as exc:
            self.state = OnlineState(message=f"연결 실패: {exc}")
            self.running = False
            return False

    def close(self) -> None:
        self.running = False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.socket.close()
            except OSError:
                pass
        self.socket = None
        self.state.connected = False

    def send(self, payload: dict) -> None:
        if not self.socket:
            return
        try:
            self.socket.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        except OSError:
            self.state.connected = False
            self.state.message = "연결 끊김"

    def _listen(self) -> None:
        buffer = ""
        while self.running and self.socket:
            try:
                chunk = self.socket.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="ignore")
            if len(buffer) > MAX_MESSAGE_LEN:
                break
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                if len(line) > MAX_MESSAGE_LEN:
                    break
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "state":
                    self.state.connected = True
                    self.state.room_code = str(data.get("room", "LOCAL"))
                    self.state.players = [str(name) for name in data.get("players", [])]
                    self.state.ready_players = [str(name) for name in data.get("ready", [])]
                    self.state.message = f"온라인 로비 참가자 {len(self.state.players)}명"
        self.state.connected = False
        if self.running:
            self.state.message = "서버 연결 종료"
        self.running = False


def main() -> None:
    parser = argparse.ArgumentParser(description="PixelWars LAN lobby server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--room-code", default=None)
    args = parser.parse_args()
    server = OnlineMatchServer(host=args.host, port=args.port, room_code=args.room_code)
    if not server.start():
        print(f"서버 시작 실패: {server.error}")
        return
    print(f"PixelWars 로비 서버 실행 중: {args.host}:{args.port}")
    print(f"방 코드: {server.room_code}")
    print("종료하려면 Ctrl+C")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("서버 종료")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
