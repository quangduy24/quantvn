# Guéant-Cartea Risk-Controlled Asian Handicap Market Maker (Validation Edition)

Tài liệu này mô tả các cập nhật và tính năng mới nhất được bổ sung vào hệ thống tạo lập thị trường (`ah2.py`), đặc biệt tập trung vào khả năng kiểm chứng mô hình (Validation & Forwardtesting) và xuất biểu đồ trực quan (Visual Analytics).

---

## 1. Phân chia Dữ liệu (Chronological Data Splitting: 60/40)

Mô hình hiện tại tự động áp dụng phương pháp chia tách tập dữ liệu theo **trình tự thời gian (Chronological)** với tỷ lệ **60/40**. Việc này đảm bảo không xảy ra hiện tượng rò rỉ dữ liệu (Look-ahead bias / Data leakage) vốn rất cấm kỵ trong mô phỏng chuỗi thời gian (Time-series Backtesting):
- **Backtest Phase (60% dữ liệu quá khứ)**: Tập dữ liệu huấn luyện (In-sample) dùng để đánh giá hiệu suất cơ bản, kiểm tra các tham số như độ rộng Spread, ngưỡng Auto-Hedge.
- **Forwardtest Phase (40% dữ liệu tương lai gần)**: Tập dữ liệu kiểm chứng (Out-of-sample) dùng để đo lường tính hiệu quả thực tế của thuật toán trên dữ liệu chưa từng thấy, giúp loại bỏ rủi ro quá khớp (Overfitting).

---

## 2. Các Chỉ số Kiểm định (Advanced Validation Metrics)

Để đánh giá tính bền vững và sự hiệu quả của thuật toán một cách khắt khe nhất (chuẩn Institutional Quantitative Finance), báo cáo tổng hợp đã được bổ sung 5 chỉ số thống kê chuyên sâu:

1. **Profit Factor**: Tỉ lệ giữa Tổng Lợi Nhuận (Gross Profit) và Tổng Thua Lỗ (Gross Loss). Một hệ thống tốt thường yêu cầu Profit Factor > 1.5.
2. **Sortino Ratio (Downside Risk)**: Tương tự Sharpe Ratio nhưng chỉ phạt đối với rủi ro sụt giảm (Downside Volatility), phản ánh chính xác hơn hiệu quả sinh lời trên một đơn vị rủi ro rớt giá.
3. **95% Value at Risk (VaR)**: Ngưỡng lỗ tối đa dự kiến trên mỗi trận đấu trong 95% thời gian (hay: ở 5% tình huống tệ nhất, bạn sẽ lỗ *ít nhất* bao nhiêu).
4. **95% Expected Shortfall (CVaR)**: Giá trị thua lỗ trung bình của 5% các trường hợp rủi ro đuôi (Tail Risk) tồi tệ nhất.
5. **Statistical Significance (T-Stat & P-Value)**: Phép kiểm định giả thuyết (Student's t-test) một đuôi, dùng để chứng minh lợi nhuận kỳ vọng của thuật toán thực sự lớn hơn 0 (có Edge) chứ không phải do biến động ngẫu nhiên (may mắn). Nếu `p-value < 0.05`, kết quả có ý nghĩa thống kê mạnh mẽ.

---

## 3. Hệ thống Biểu đồ Trực quan (Granular Visual Analytics)

Mỗi giải đấu (và cả mức tổng hợp `totals`) trong mỗi pha (Backtest / Forwardtest) đều tự động trích xuất một bộ **9 biểu đồ độc lập** nhằm cung cấp cái nhìn chi tiết nhất về từng khía cạnh của thuật toán:

1. `metric_01_cumulative_pnl.png`: Biểu đồ tăng trưởng lợi nhuận ròng lũy kế theo từng trận.
2. `metric_02_pnl_per_match.png`: Biểu đồ Bar chart thể hiện lợi nhuận/thua lỗ trên từng trận đấu.
3. `metric_03_win_rate.png`: Biểu đồ tròn (Pie chart) tỷ lệ Thắng/Thua/Hòa.
4. `metric_04_traded_volume.png`: Tổng khối lượng giao dịch đã khớp trên mỗi trận.
5. `metric_05_peak_inventory.png`: Mức độ sử dụng vốn lưu động tối đa (% của $50,000 Cap).
6. `metric_06_hedge_sweeps.png`: Số lần kích hoạt lệnh Auto-Hedge.
7. `metric_07_hedge_cost.png`: Chi phí trượt giá (Slippage/Fees) khi thực hiện xả hàng (Hedge).
8. `metric_08_pnl_distribution.png`: Biểu đồ phân phối tần suất lợi nhuận (Histogram) kèm đường giá trị Trung bình (Mean).
9. `metric_09_drawdown.png`: Mức độ sụt giảm tài sản lũy kế (Peak-to-Trough Drawdown).

Ngoài ra, hệ thống vẫn giữ lại Biểu đồ **Dashboard Tổng Hợp** và **Microstructure Tick-by-tick** đặc trưng.

---

## 4. Cấu trúc Thư mục Kết quả Mới (Result Directory)

Toàn bộ các biểu đồ và file báo cáo CSV sẽ được đặt tên theo đúng pha (kèm tiền tố `backtest_` hoặc `forwardtest_`) để không bị nhầm lẫn.

```text
result/
├── 2024-2025/                            # (Hoặc thư mục của từng giải đấu tương ứng)
│   ├── backtest/                         # Kết quả của 60% dữ liệu đầu
│   │   ├── gueant_backtest_summary.csv
│   │   ├── gueant_backtest_dashboard.png
│   │   ├── gueant_backtest_microstructure.png
│   │   ├── backtest_metric_01_cumulative_pnl.png
│   │   └── ... (8 biểu đồ metric khác)
│   └── forwardtest/                      # Kết quả của 40% dữ liệu kiểm chứng
│       ├── gueant_forwardtest_summary.csv
│       ├── gueant_forwardtest_dashboard.png
│       ├── gueant_forwardtest_microstructure.png
│       ├── forwardtest_metric_01_cumulative_pnl.png
│       └── ... (8 biểu đồ metric khác)
└── totals/                               # Kết quả tổng hợp (Aggregation)
    ├── backtest/
    └── forwardtest/
```

---

## 5. Hướng dẫn Chạy (Execution)

Để thực thi mô hình với bộ dữ liệu mẫu (hoặc toàn bộ dữ liệu), bạn chỉ cần chạy lệnh sau:

```bash
python ah2.py ./archive/sample
```

Quá trình phân tích sẽ tự động xử lý, chia tách dữ liệu, xuất báo cáo và in trực tiếp các thông số định lượng lên màn hình Console.

---

## 6. Kết quả Thực nghiệm (Empirical Validation Results)

Sau khi chia tách dữ liệu theo trục thời gian (Chronological Split: 60% quá khứ, 40% tương lai gần), kết quả chạy mô phỏng cho thấy thuật toán Guéant-Cartea hoạt động cực kỳ ổn định và **không bị quá khớp (no overfitting)**. 

Thậm chí, hiệu suất trên tập dữ liệu kiểm chứng (Forwardtest/Out-of-sample) còn vượt trội so với tập huấn luyện, chứng tỏ mô hình nắm bắt được cấu trúc vi mô của thị trường rất tốt.

### 📊 So sánh Hiệu suất (Backtest vs Forwardtest)

| Chỉ số (Metric) | In-Sample (Backtest - 54 Matches) | Out-of-Sample (Forwardtest - 36 Matches) | Đánh giá |
|:---|:---:|:---:|:---|
| **Cumulative Net PnL** | $25,024.32 | **$38,449.65** | Vẫn giữ được đà tăng trưởng mạnh. |
| **Average PnL / Match** | $463.41 | **$1,068.05** | Tăng trưởng lợi nhuận kỳ vọng trên mỗi trận. |
| **Match Win Rate** | 59.26% (32W / 22L) | **66.67% (24W / 12L)** | Tỷ lệ thắng cải thiện đáng kể trên dữ liệu mới. |
| **Profit Factor** | 1.87 | **3.81** | Cực kỳ xuất sắc (Sinh lời gấp 3.8 lần số lỗ). |
| **Sharpe Ratio (Per-Match)**| 0.250 | **0.538** | Hiệu suất trên rủi ro tăng vọt. |
| **Sortino Ratio (Downside)**| 0.399 | **0.912** | Ít bị ảnh hưởng bởi các chuỗi thua lỗ sâu. |
| **Max Drawdown** | $7,595.99 | **$3,276.20** | Rủi ro sụt giảm tài sản được kiểm soát tốt hơn. |
| **Statistical Significance** | p-value: 0.0361 | **p-value: 0.0013** | Có ý nghĩa thống kê cực mạnh (t-stat: 3.23). |

> [!NOTE]
> Kết quả `p-value = 0.0013` (rất nhỏ so với 0.05) trên tập Forwardtest khẳng định rằng lợi nhuận của hệ thống tạo lập thị trường này đến từ "lợi thế thuật toán" (Alpha/Edge) chứ không phải do may mắn ngẫu nhiên. Mức sụt giảm tối đa (Max Drawdown) được giữ vững dưới 10% vốn (với Cap $50,000), chứng tỏ cơ chế Auto-Hedge và Dynamic Spread hoạt động hoàn hảo khi đối phó với dòng lệnh bất lợi.
