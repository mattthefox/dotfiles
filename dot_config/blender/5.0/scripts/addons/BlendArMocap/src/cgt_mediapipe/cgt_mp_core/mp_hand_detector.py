import socket
import json
from .mp_detector_node import DetectorNode
from mediapipe.framework.formats import classification_pb2

class HandDetector(DetectorNode):
	"""
	Replacement HandDetector that receives Mediapipe-style hand data
	from a UDP socket instead of computing it locally.
	Keeps the original interface intact.
	"""

	def __init__(self, stream=None, hand_model_complexity=1, min_detection_confidence=0.7):
		# keep original signature
		super().__init__(stream)
		self.hand_model_complexity = hand_model_complexity
		self.min_detection_confidence = min_detection_confidence

		host = "0.0.0.0"
		port = 5005
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.bind((host, port))
		self.sock.setblocking(False)

	def update(self, data, frame):
		"""
		Receives socket packet and converts to the exact Mediapipe-compatible structure:
		[ [ (idx, [x,y,z]), ... ], [ (idx, [x,y,z]), ... ] ]
		"""
		try:
			packet, addr = self.sock.recvfrom(65535)
			packet = json.loads(packet.decode("utf-8"))
		except BlockingIOError:
			packet = {"hands": []}

		left_hands, right_hands = [], []

		for hand in packet.get("hands", []):
			landmarks = [(i, [lm["x"], lm["y"], lm["z"]]) for i, lm in enumerate(hand["landmarks"])]
			if hand["hand_index"] == 0:
				left_hands.append(landmarks)
			else:
				right_hands.append(landmarks)

		return [left_hands, right_hands], frame


	@staticmethod
	def separate_hands(hand_data):
		left_hand = [data[0] for data in hand_data if data[1][1] is False]
		right_hand = [data[0] for data in hand_data if data[1][1] is True]
		return left_hand, right_hand

	@staticmethod
	def cvt_hand_orientation(orientation: classification_pb2):
		if not orientation:
			return None
		return [[idx, "Right" in str(o)] for idx, o in enumerate(orientation)]

	def empty_data(self):
		return [[], []]

	def detected_data(self, mp_res):
		"""
		Convert received socket data to left/right hands list.
		"""
		left, right = [], []
		for hand in mp_res.get("hands", []):
			landmarks = [(lm["x"], lm["y"], lm["z"]) for lm in hand["landmarks"]]
			hand_info = {"hand_index": hand["hand_index"], "landmarks": landmarks}
			if hand["hand_index"] == 0:
				left.append(hand_info)
			else:
				right.append(hand_info)
		return [left, right]

	def contains_features(self, mp_res):
		return bool(mp_res)

	def draw_result(self, s, mp_res, mp_drawings):
		# keep method for interface; does nothing
		pass

	def close(self):
		self.sock.close()
