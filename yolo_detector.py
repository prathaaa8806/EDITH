# detection/yolo_detector.py
from importlib import import_module

# Load OpenCV dynamically so static analyzers do not report a missing import
# when the package is installed in a different Python environment.
cv2 = import_module("cv2")
# Load Ultralytics dynamically so static analyzers do not report a missing
# import when the dependency is installed in a different Python environment.
YOLO = import_module("ultralytics").YOLO

class PersonDetector:
    def __init__(self):
        # YOLOv8 Nano model (Fastest for real-time CPU/GPU)
        self.model = YOLO('yolov8n.pt') 

    def process_frame(self, frame):
        """
        Takes raw frame from camera, detects persons and returns count + annotated frame.
        """
        if frame is None:
            return 0, None

        # Resize for faster FPS on laptop CPU
        frame_resized = cv2.resize(frame, (640, 480))

        # Run detection strictly for person class (id=0) with optimal confidence
        results = self.model(frame_resized, classes=[0], conf=0.45, verbose=False)

        # Total person count
        person_count = len(results[0].boxes)

        # Draw bounding boxes
        annotated_frame = results[0].plot()

        # Convert BGR (OpenCV) to RGB (Streamlit)
        rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

        return person_count, rgb_frame