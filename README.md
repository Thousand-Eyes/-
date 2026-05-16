# -

財務模擬，衡量最佳財務路徑。

## `agi_math/` — Active Inference 骨架

以 Free Energy Minimization / Active Inference 為核心的決策框架，
作為「在不確定環境下尋找最佳行動路徑」的數學基底。

離散 POMDP 形式：

```
P(o | s, a) = A[a, o, s]      觀測模型
P(s'| s, a) = B[a, s', s]     動態模型
log P~(o)   = C[o]            偏好（log preferences）
P(s_0)      = D[s]            初始信念
```

Agent 維護近似後驗 Q(s)，以最小化 Expected Free Energy 選擇行動：

```
G(a) = - pragmatic_value(a) - epistemic_value(a)
```

`pragmatic_value` 把預測觀測拉向偏好 `C`；`epistemic_value` 獎勵資訊增益
（互資訊 I(s'; o | a)）。兩者天然帶出 explore / exploit 的取捨。

### 跑範例

```
pip install -r requirements.txt
python -m agi_math.financial_demo
```

範例設定：隱藏狀態為市場 regime（Bull/Bear），agent 觀察到的是自己持倉的
報酬（Gain/Flat/Loss），可選 Aggressive / Hold / Defensive 三種倉位。
Aggressive 與 Defensive 同時資訊量高且風險高，Hold 安全但無資訊 ——
EFE 應該要能在 regime 切換時更新信念並改變策略。
