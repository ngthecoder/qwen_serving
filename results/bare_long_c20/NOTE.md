# bare × long × c=20: SKIPPED (predicted unmeasurable)

c=10 で request latency 67s (TTFT 9.4s + decode 58s)。c=20 では queueing がさらに積み上がり、request latency が 120s window を超える予想 → 0 completed requests。

bare × short × c=20 と同じ collapse pattern と推定、separate measurement は時間 effiency 的にスキップ。

Trend (bare × long):
- c=1: OutTok/s 85.7
- c=5: OutTok/s 25.4
- c=10: OutTok/s 18.0
- c=20: < 10 (extrapolation), 完了 0 requests (predicted)

vLLM 側の data と比較する時の structural evidence として、c=10 までで十分。
