# bare × short × c=20: UNMEASURABLE

- Benchmark ran for 8m+ with 0 completed requests (max_seconds=120)
- Pod stayed Running (no crash, no OOM)
- Pod log dominated by k8s probe /ping calls — chat completion requests reached pod but couldn't produce tokens in any reasonable time
- Trend from c=1 → c=5 → c=10: OutTok/s 101.8 → 29.3 → 19.1, extrapolation suggests c=20 effective throughput < 5 tok/s
- Interpretation: 20 concurrent forward passes on T4 cause GPU resource thrashing severe enough that token generation effectively stalls

This is itself a result. Continuous batching (vLLM) is needed to handle this concurrency.
