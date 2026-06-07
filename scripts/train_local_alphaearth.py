import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import datetime

# --- 1. AlphaEarth 核心组件：STP (Space-Time-Precision) 编码器 ---
class STPBlock(nn.Module):
    """
    Space-Time-Precision (STP) Encoder Block
    论文中描述：包含1/16空间自注意力、1/8时间自注意力、1/2精度3x3卷积
    """
    def __init__(self, channels=64):
        super().__init__()
        # Precision 分支 (1/2 分辨率): 保留局部纹理，使用卷积
        self.prec_conv = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True)
        )
        # Space 分支 (1/16 分辨率): 空间全局感受野，使用自注意力
        self.space_attn = nn.MultiheadAttention(embed_dim=channels, num_heads=4, batch_first=True)
        
        # Time 分支 (1/8 分辨率): 时序注意力 (简化版，仅作展示)
        self.time_attn = nn.MultiheadAttention(embed_dim=channels, num_heads=4, batch_first=True)

    def forward(self, x_prec, x_space, x_time):
        # 1. 运行 Precision 卷积 [B, C, H/2, W/2]
        out_prec = self.prec_conv(x_prec)
        
        # 2. 运行 Space Attention (展平后运算) [B, C, H/16, W/16]
        B, C, H_s, W_s = x_space.shape
        x_space_flat = x_space.view(B, C, -1).permute(0, 2, 1) # [B, H*W, C]
        out_space, _ = self.space_attn(x_space_flat, x_space_flat, x_space_flat)
        out_space = out_space.permute(0, 2, 1).view(B, C, H_s, W_s)
        
        # 3. 运行 Time Attention [B, C, H/8, W/8]
        B, C, H_t, W_t = x_time.shape
        x_time_flat = x_time.view(B, C, -1).permute(0, 2, 1)
        out_time, _ = self.time_attn(x_time_flat, x_time_flat, x_time_flat)
        out_time = out_time.permute(0, 2, 1).view(B, C, H_t, W_t)
        
        # 4. Laplacian Pyramid Exchange (信息交换)
        # 论文中：不同分辨率特征通过上采样/下采样相互补充
        out_space_up = F.interpolate(out_space, size=out_prec.shape[2:], mode='bilinear')
        out_time_up  = F.interpolate(out_time, size=out_prec.shape[2:], mode='bilinear')
        
        # 将空隙特征和时序特征融合到精度分支上
        out_fused = out_prec + out_space_up + out_time_up
        return out_fused

class LocalAlphaEarthEncoder(nn.Module):
    """
    轻量化的本地 AlphaEarth 编码器
    用于县/镇/村级别的空间数据集（10m分辨率，128x128 Patch = 1.28km^2）
    """
    def __init__(self, in_channels=5, z_dim=64):
        super().__init__()
        self.proj = nn.Conv2d(in_channels, z_dim, kernel_size=1)
        self.stp_block = STPBlock(channels=z_dim)
        # 输出使用全局平均池化得到 64 维
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        
    def forward(self, x):
        # x: [B, C_in, 128, 128]
        feat = self.proj(x)
        
        # AlphaEarth的STP结构将特征分配到3个尺度
        # 1/2 尺度用于 Precision 卷积
        x_prec = F.interpolate(feat, scale_factor=0.5, mode='bilinear')
        # 1/8 尺度用于 Time 注意力
        x_time = F.interpolate(feat, scale_factor=0.125, mode='bilinear')
        # 1/16 尺度用于 Space 注意力
        x_space = F.interpolate(feat, scale_factor=0.0625, mode='bilinear')
        
        # 过STP块
        o_fused = self.stp_block(x_prec, x_space, x_time)
        
        # 聚合生成最终 64 维 embedding
        z = self.pool(o_fused).flatten(1) # [B, 64]
        
        # L2 归一化，使其分布在单位超球面 S^63
        z = F.normalize(z, p=2, dim=1)
        return z

# --- 2. 隐式解码器 (Implicit Decoder) ---
class ImplicitDecoder(nn.Module):
    """
    隐式解码器，尝试从 64 维的 z 还原输入的卫星影像特征。
    实际论文中解码器包括时间条件，为简化本地复现去除了时间戳输入。
    """
    def __init__(self, z_dim=64, out_channels=5):
        super().__init__()
        self.fc = nn.Linear(z_dim, 256)
        self.up = nn.Sequential(
            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=1, padding=0), # -> 4x4
            nn.ReLU(),
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),  # -> 8x8
            nn.ReLU(),
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),   # -> 16x16
            nn.ReLU(),
            nn.ConvTranspose2d(32, 16, kernel_size=4, stride=2, padding=1),   # -> 32x32
            nn.ReLU(),
            nn.ConvTranspose2d(16, 8, kernel_size=4, stride=2, padding=1),    # -> 64x64
            nn.ReLU(),
            nn.ConvTranspose2d(8, out_channels, kernel_size=4, stride=2, padding=1) # -> 128x128
        )
    def forward(self, z):
        x = self.fc(z).view(-1, 256, 1, 1)
        return self.up(x)

# --- 3. 损失函数 ---
def batch_uniformity_loss(z):
    """
    Batch Uniformity Loss (论文图2C)
    确保 Embedding 在单位超球面上均匀分布，防止模型坍缩到单一点
    """
    # z: [B, 64], 必须已进行 L2 归一化
    # 计算所有样本间的余弦相似度矩阵
    sim_matrix = torch.mm(z, z.t())
    # 遮蔽对角线（自己和自己的相似度）
    mask = torch.eye(z.shape[0], dtype=torch.bool, device=z.device)
    sim_matrix.masked_fill_(mask, 0.0)
    # 最小化其他样本间相似度的绝对值均值（使其正交分布）
    loss = torch.mean(torch.abs(sim_matrix))
    return loss

import glob
from pathlib import Path
from torch.utils.data import Dataset, DataLoader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DATA_DIR = PROJECT_ROOT / "data_agent" / "weights" / "raw_data"

# --- 4. 数据集加载 (Dataset) ---
class AlphaEarthDataset(Dataset):
    """
    加载由 DataFusionPipeline 生成的 .pt 切片
    """
    def __init__(self, data_dir=None):
        super().__init__()
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_RAW_DATA_DIR
        # 递归查找所有 .pt 文件
        self.files = glob.glob(os.path.join(str(self.data_dir), "**", "*.pt"), recursive=True)
        if not self.files:
            print(f"警告: 在 {self.data_dir} 未找到任何 .pt 切片文件。")

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        file_path = self.files[idx]
        # 读取 Tensor [C, H, W]
        tensor = torch.load(file_path, weights_only=True)
        return tensor

# --- 5. 本地迭代训练循环 (Training Loop) ---
def train_model(epochs=10, batch_size=16, learning_rate=1e-3, data_dir=None):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 初始化 Local AlphaEarth 模型...")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用计算设备: {device}")
    
    in_channels = 5
    encoder = LocalAlphaEarthEncoder(in_channels=in_channels, z_dim=64).to(device)
    decoder = ImplicitDecoder(z_dim=64, out_channels=in_channels).to(device)
    
    dataset = AlphaEarthDataset(data_dir=data_dir)
    if len(dataset) == 0:
        print("请先通过 DataFusionPipeline 准备数据。")
        return
        
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    
    optimizer = torch.optim.AdamW(list(encoder.parameters()) + list(decoder.parameters()), lr=learning_rate)
    
    print(f"开始训练，总数据量: {len(dataset)} 个切片, Batch Size: {batch_size}, 共 {epochs} Epochs")
    
    for epoch in range(epochs):
        encoder.train()
        decoder.train()
        
        epoch_loss_rec = 0.0
        epoch_loss_uni = 0.0
        
        for batch_idx, batch_data in enumerate(dataloader):
            batch_data = batch_data.to(device) # [B, 5, 128, 128]
            
            optimizer.zero_grad()
            
            # 前向传播
            embeddings = encoder(batch_data)
            reconstructed = decoder(embeddings)
            
            # 计算损失
            loss_rec = F.mse_loss(reconstructed, batch_data)
            loss_uni = batch_uniformity_loss(embeddings)
            
            total_loss = loss_rec + 0.1 * loss_uni
            
            # 反向传播 & 优化
            total_loss.backward()
            optimizer.step()
            
            epoch_loss_rec += loss_rec.item()
            epoch_loss_uni += loss_uni.item()
            
            if batch_idx % 10 == 0:
                print(f"Epoch [{epoch+1}/{epochs}] Batch [{batch_idx}/{len(dataloader)}] - "
                      f"Rec Loss: {loss_rec.item():.4f}, Uni Loss: {loss_uni.item():.4f}")
                      
        # 每个 Epoch 结束，打印平均 Loss
        avg_rec = epoch_loss_rec / len(dataloader)
        avg_uni = epoch_loss_uni / len(dataloader)
        print(f"==== Epoch {epoch+1} 结束 ==== 平均 Rec Loss: {avg_rec:.4f}, 平均 Uni Loss: {avg_uni:.4f}")
        
        # 保存权重
        weights_dir = Path(data_dir).parent if data_dir else PROJECT_ROOT / "data_agent" / "weights"
        save_path = weights_dir / "local_alphaearth_encoder.pth"
        torch.save(encoder.state_dict(), save_path)
        print(f"权重已保存至: {save_path}")
        
    print("🎉 训练完成！")

if __name__ == "__main__":
    train_model(epochs=5, batch_size=4)
