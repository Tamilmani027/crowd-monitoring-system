import torch
import torch.nn as nn
from torchvision import models
import cv2
import numpy as np
import torchvision.transforms as standard_transforms

class CSRNet(nn.Module):
    def __init__(self, load_weights=False):
        super(CSRNet, self).__init__()
        self.frontend_feat = [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 'M', 512, 512, 512]
        self.backend_feat  = [512, 512, 512, 256, 128, 64]
        self.frontend = make_layers(self.frontend_feat)
        self.backend = make_layers(self.backend_feat, in_channels=512, dilation=True)
        self.output_layer = nn.Conv2d(64, 1, kernel_size=1)
        
        if not load_weights:
            mod = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1)
            self._initialize_weights()
            # Copy VGG16 weights to frontend
            fsd = self.frontend.state_dict()
            msd = mod.features.state_dict()
            for k in fsd.keys():
                fsd[k] = msd[k]
            self.frontend.load_state_dict(fsd)
            
    def forward(self, x):
        x = self.frontend(x)
        x = self.backend(x)
        x = self.output_layer(x)
        return x
        
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.normal_(m.weight, std=0.01)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

def make_layers(cfg, in_channels=3, batch_norm=False, dilation=False):
    if dilation:
        d_rate = 2
    else:
        d_rate = 1
    layers = []
    for v in cfg:
        if v == 'M':
            layers += [nn.MaxPool2d(kernel_size=2, stride=2)]
        else:
            conv2d = nn.Conv2d(in_channels, v, kernel_size=3, padding=d_rate, dilation=d_rate)
            if batch_norm:
                layers += [conv2d, nn.BatchNorm2d(v), nn.ReLU(inplace=True)]
            else:
                layers += [conv2d, nn.ReLU(inplace=True)]
            in_channels = v
    return nn.Sequential(*layers)


class CSRNetInference:
    def __init__(self, model_path, device='cpu'):
        self.device = torch.device(device)
        self.model = CSRNet()
        self.model.to(self.device)
        self.transform = standard_transforms.Compose([
            standard_transforms.ToTensor(),
            standard_transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                      std=[0.229, 0.224, 0.225]),
        ])
        
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            # If the dict has 'state_dict', use that, else use the dict directly
            state_dict = checkpoint['state_dict'] if 'state_dict' in checkpoint else checkpoint
            self.model.load_state_dict(state_dict)
            self.model.eval()
            self.loaded = True
        except Exception as e:
            print(f"Error loading CSRNet weights: {e}")
            self.loaded = False

    def predict(self, frame):
        """
        Takes an OpenCV BGR frame, returns (estimated_count, density_map_numpy)
        """
        if not self.loaded:
            return 0.0, None
            
        # Convert BGR to RGB
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Apply transforms
        img_tensor = self.transform(img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            output = self.model(img_tensor)
            
        density_map = output.squeeze().cpu().numpy()
        count = np.sum(density_map)
        
        return count, density_map
