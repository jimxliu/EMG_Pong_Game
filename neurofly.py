import socket
import json
import threading
import time
from typing import Callable, Optional, Tuple, Any

# Default port used by the local UDP listener (changeable)
DEFAULT_UDP_PORT = 12345


class UDPClientListener:
	"""Simple UDP listener that receives JSON packets and dispatches them via a callback.

	It binds to the provided local host/port and expects JSON messages like:
	{ "type": "emgJoystick", "data": [0.664, -0.749] }

	The callback receives two arguments: the deserialized packet (dict) and the
	sender address tuple (ip, port).
	"""

	def __init__(self, listen_host: str = "0.0.0.0", listen_port: int = DEFAULT_UDP_PORT,
				 buffer_size: int = 4096, timeout: float = 1.0) -> None:
		self.listen_host = listen_host
		self.listen_port = listen_port
		self.buffer_size = buffer_size
		self.timeout = timeout

		self._sock: Optional[socket.socket] = None
		self._thread: Optional[threading.Thread] = None
		self._running = False
		self._callback: Optional[Callable[[dict, Tuple[str, int]], Any]] = None

	def set_callback(self, cb: Callable[[dict, Tuple[str, int]], Any]) -> None:
		self._callback = cb

	def start(self) -> None:
		if self._running:
			return
		self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# Allow address reuse to avoid "address already in use" during quick restarts
		self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._sock.bind((self.listen_host, self.listen_port))
		self._sock.settimeout(self.timeout)

		self._running = True
		self._thread = threading.Thread(target=self._listen_loop, daemon=True)
		self._thread.start()

	def stop(self) -> None:
		self._running = False
		if self._sock:
			try:
				self._sock.close()
			except Exception:
				pass
		if self._thread:
			self._thread.join(timeout=1.0)

	def _listen_loop(self) -> None:
		assert self._sock is not None
		while self._running:
			try:
				data_bytes, addr = self._sock.recvfrom(self.buffer_size)
			except socket.timeout:
				continue
			except OSError:
				# Socket closed
				break

			try:
				text = data_bytes.decode("utf-8")
				packet = json.loads(text)
			except Exception:
				# Ignore malformed messages
				continue

			# If a callback is set, call it. Otherwise silently ignore.
			if self._callback:
				try:
					self._callback(packet, addr)
				except Exception:
					# Callback errors should not stop the listener
					continue


def _example_callback(packet: dict, addr: Tuple[str, int]) -> None:
	# Example usage mirroring the Unity NeuroFly usage
	if packet.get("type") == "emgJoystick" and isinstance(packet.get("data"), list):
		data = packet["data"]
		if len(data) >= 2:
			emg_x = data[0]
			emg_y = data[1]
			print(f"Received from {addr}: EMGJoystickX={emg_x}, EMGJoystickY={emg_y}")


if __name__ == "__main__":
	# Quick runnable example: listens on DEFAULT_UDP_PORT and prints incoming joystick values
	listener = UDPClientListener(listen_port=DEFAULT_UDP_PORT)
	listener.set_callback(_example_callback)
	print(f"Starting UDP listener on port {DEFAULT_UDP_PORT} (Ctrl-C to stop)")
	listener.start()
	try:
		while True:
			time.sleep(1.0)
	except KeyboardInterrupt:
		print("Stopping listener...")
		listener.stop()

