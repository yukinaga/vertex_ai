import torch
import torch.nn as nn
import torch.optim as optim

# --- 1. データの準備 ---
# y = 2x + 1 の関係を持つデータを作成
torch.manual_seed(42) # 再現性のためのシード固定
X_train = torch.randn(100, 1) * 10
y_train = 2 * X_train + 1 + torch.randn(100, 1) * 2 # 少しノイズを加える

print(f"データのサンプル (X): {X_train[0]}")
print(f"データのサンプル (y): {y_train[0]}")
print("-" * 20)

# --- 2. モデルの定義 ---
# y = w*x + b 
# (入力1次元、出力1次元のシンプルな線形モデル)
model = nn.Linear(1, 1)

print(f"初期パラメータ (w): {model.weight.item():.4f}")
print(f"初期パラメータ (b): {model.bias.item():.4f}")
print("-" * 20)

# --- 3. 損失関数とオプティマイザ ---
# 損失関数 (平均二乗誤差)
criterion = nn.MSELoss()
# オプティマイザ (確率的勾配降下法) 学習率=0.01
optimizer = optim.SGD(model.parameters(), lr=0.01)

# --- 4. トレーニングループ ---
num_epochs = 100 # 学習回数

for epoch in range(num_epochs):
    # 4-1. 順伝播 (予測)
    y_pred = model(X_train)
    
    # 4-2. 損失の計算
    loss = criterion(y_pred, y_train)
    
    # 4-3. 勾配の初期化 (逆伝播の前に必須)
    optimizer.zero_grad()
    
    # 4-4. 逆伝播 (勾配の計算)
    loss.backward()
    
    # 4-5. パラメータの更新
    optimizer.step()
    
    # 10エポックごとに出力
    if (epoch + 1) % 10 == 0:
        print(f"Epoch [{epoch+1}/{num_epochs}], Loss: {loss.item():.4f}")

# --- 5. 学習結果の確認 ---
print("-" * 20)
print("学習完了！")
print(f"最終パラメータ (w): {model.weight.item():.4f} (目標値: 2.0)")
print(f"最終パラメータ (b): {model.bias.item():.4f} (目標値: 1.0)")
