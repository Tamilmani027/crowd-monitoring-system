import logging
from dataclasses import dataclass
from ultralytics import YOLO
from config import Config
import torch

# We lazily import CSRNet to avoid issues if torch is not installed properly
try:
    from services.csrnet import CSRNetInference
except ImportError:
    CSRNetInference = None

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class DetectionOutput:
    boxes: list
    person_count: int
    is_csrnet: bool = False
    density_map: object = None


class CrowdDetector:
    def __init__(self, model_path: str = 'yolov8n.pt', use_bytetrack: bool = False):
        self.model = YOLO(model_path)
        self.use_bytetrack = use_bytetrack
        self.csrnet_model_path = getattr(Config, 'CSRNET_MODEL_PATH', 'PartAmodel_best.pth.tar')
        
        self.csrnet = None
        # We will initialize CSRNet lazily when first needed to save memory if it's off by default

    def _init_csrnet(self):
        if self.csrnet is None and CSRNetInference is not None:
            logger.info("Loading CSRNet model for density estimation fallback...")
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.csrnet = CSRNetInference(self.csrnet_model_path, device=device)

    def detect_people(self, frame, use_csrnet=False, csrnet_threshold=30):
        # 1. Run YOLO

        if self.use_bytetrack:
            results = self.model.track(frame, classes=[0], conf=0.5, verbose=False, persist=True, tracker='bytetrack.yaml')
        else:
            results = self.model(frame, classes=[0], conf=0.5, verbose=False)
            
        result = results[0]
        boxes = list(result.boxes)
        person_count = len(boxes)
        
        # 2. Check if CSRNet fallback is needed
        if use_csrnet:
            self._init_csrnet()
            
        if use_csrnet and self.csrnet is not None and self.csrnet.loaded:
            if person_count >= csrnet_threshold:
                logger.info(f"Dense crowd detected ({person_count} >= {csrnet_threshold}). Switching to CSRNet.")
                est_count, density_map = self.csrnet.predict(frame)
                
                # CSRNet count can be a float, round it to nearest int
                est_count_int = int(round(est_count))
                
                # We return the boxes from YOLO just in case, but overwrite the count
                return DetectionOutput(
                    boxes=boxes, 
                    person_count=est_count_int,
                    is_csrnet=True,
                    density_map=density_map
                )

        return DetectionOutput(boxes=boxes, person_count=person_count, is_csrnet=False, density_map=None)
