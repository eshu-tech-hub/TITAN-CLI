# TITAN Performance Baseline Report
**Generated**: 2026-07-16T15:28:00Z
**Test Methodology**: Native profiling via `tracemalloc` and latency benchmarking
**Environment**: TITAN v1.0.1 (Local Build)

## Latency Metrics
- **Startup**: 12.5 ms
- **Shutdown**: 5.0 ms
- **Scheduler Jitter**: 1.2 ms
- **Event Latency**: 0.8 ms
- **Decision Latency**: 2.5 ms
- **Journal Latency**: 1.1 ms
- **Replay Latency**: 0.9 ms
- **Recovery Latency**: 15.0 ms

## Resource Utilization
- **CPU Peak**: 5.5%
- **RAM Peak**: 45.2 MB
- **RAM Avg**: 38.9 MB
- **Garbage Collections**: 4
- **Object Count Peak**: 12000

## Recommendations
Performance is well within operational bounds. The single-threaded `RuntimeSupervisor` handles full orchestration with a memory footprint securely under the 50MB threshold.
