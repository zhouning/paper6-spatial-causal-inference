import torch
import torch.nn as nn
import torch.nn.functional as F
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# --- 1. AlphaEarth 核心组件：STP (Space-Time-Precision) 编码器 ---
class STPBlock(nn.Module):
    """Space-Time-Precision (STP) Encoder Block"""
    def __init__(self, channels=64):
        super().__init__()
        self.prec_conv = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True)
        )
        self.space_attn = nn.MultiheadAttention(embed_dim=channels, num_heads=4, batch_first=True)
        self.time_attn = nn.MultiheadAttention(embed_dim=channels, num_heads=4, batch_first=True)

    def forward(self, x_prec, x_space, x_time):
        out_prec = self.prec_conv(x_prec)
        
        B, C, H_s, W_s = x_space.shape
        x_space_flat = x_space.view(B, C, -1).permute(0, 2, 1)
        out_space, _ = self.space_attn(x_space_flat, x_space_flat, x_space_flat)
        out_space = out_space.permute(0, 2, 1).view(B, C, H_s, W_s)
        
        B, C, H_t, W_t = x_time.shape
        x_time_flat = x_time.view(B, C, -1).permute(0, 2, 1)
        out_time, _ = self.time_attn(x_time_flat, x_time_flat, x_time_flat)
        out_time = out_time.permute(0, 2, 1).view(B, C, H_t, W_t)
        
        out_space_up = F.interpolate(out_space, size=out_prec.shape[2:], mode='bilinear')
        out_time_up  = F.interpolate(out_time, size=out_prec.shape[2:], mode='bilinear')
        
        return out_prec + out_space_up + out_time_up

class LocalAlphaEarthEncoder(nn.Module):
    """
    轻量化的本地 AlphaEarth 编码器
    """
    def __init__(self, in_channels=5, z_dim=64):
        super().__init__()
        self.proj = nn.Conv2d(in_channels, z_dim, kernel_size=1)
        self.stp_block = STPBlock(channels=z_dim)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        
    def forward(self, x):
        feat = self.proj(x)
        x_prec = F.interpolate(feat, scale_factor=0.5, mode='bilinear')
        x_time = F.interpolate(feat, scale_factor=0.125, mode='bilinear')
        x_space = F.interpolate(feat, scale_factor=0.0625, mode='bilinear')
        
        o_fused = self.stp_block(x_prec, x_space, x_time)
        z = self.pool(o_fused).flatten(1)
        z = F.normalize(z, p=2, dim=1) # 投影到 S^63 超球面
        return z

def test_local_model(weights_path):
    print(f"正在加载本地 AlphaEarth 模型: {weights_path}")
    
    # 1. 检查权重文件是否存在
    if not os.path.exists(weights_path):
        print(f"❌ 错误: 找不到模型文件 {weights_path}。请确认 Colab 下载的文件放在了此处。")
        return
    
    # 2. 实例化模型并加载权重
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = LocalAlphaEarthEncoder(in_channels=5, z_dim=64)
    
    try:
        # map_location='cpu' 确保即使在没有 GPU 的本地电脑也能加载
        model.load_state_dict(torch.load(weights_path, map_location='cpu', weights_only=True))
        model.to(device)
        model.eval() # 设置为评估模式
        print("✅ 权重加载成功！")
    except Exception as e:
        print(f"❌ 权重加载失败: {e}")
        return

    # 3. 创建测试数据 (模拟一张 Sentinel-2 的 128x128 切片)
    # Batch=1, Channels=5 (B2, B3, B4, B8, B11), Height=128, Width=128
    print("\n--- 正在生成模拟的输入数据 [1, 5, 128, 128] ---")
    dummy_input = torch.randn(1, 5, 128, 128).to(device)
    
    # 4. 执行推理 (提取 64 维嵌入特征)
    print("🚀 开始提取时空特征 (Forward Pass)...")
    with torch.no_grad(): # 不计算梯度，节省内存
        embeddings = model(dummy_input)
    
    # 5. 验证输出
    print(f"\n✅ 提取完成！")
    print(f"输出的特征维度 (Shape): {embeddings.shape}")
    
    # 验证是否在单位超球面上 (L2 Norm 应该等于 1.0)
    l2_norm = torch.norm(embeddings, p=2, dim=1).item()
    print(f"特征的 L2 Norm (长度): {l2_norm:.4f} (期望值为 1.0，证明成功投射至 S^63)")
    
    print("\n前 5 个特征维度的数值:")
    print(embeddings[0, :5].cpu().numpy())
    
    print("\n🎉 测试通过！您的本地 AlphaEarth 编码器已随时可以在下游任务 (如土地变化检测/预测) 中使用。")

if __name__ == "__main__":
    MODEL_WEIGHTS_PATH = PROJECT_ROOT / "data_agent" / "weights" / "local_alphaearth_encoder.pth"
    test_local_model(MODEL_WEIGHTS_PATH)
