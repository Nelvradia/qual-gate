# VRAM Budget Checklist

GPU memory allocation for local inference on RTX 4080 (16GB).

## Current Hardware: RTX 4080 16GB

| Component | VRAM | Notes |
|-----------|------|-------|
| Model (8B Q4) | ~5 GB | Single model loaded |
| KV Cache (per context) | ~1-2 GB | Depends on context length |
| Embedding model | ~0.5 GB | nomic-embed-text |
| CUDA overhead | ~0.5 GB | Driver, runtime |
| **Available for inference** | **~8-10 GB** | After model load |

## Checks
- [ ] Only one LLM model loaded at a time (no simultaneous models on 16GB)
- [ ] KV cache eviction policy configured
- [ ] Model loading is lazy (load on first request, not on startup)
- [ ] Fallback behavior when VRAM exhausted (queue, not crash)
- [ ] VRAM monitoring metric exposed (Prometheus)

## Future: Dual RTX 3090 NVLink (48GB pooled)
- [ ] NVLink bridge validated (tensor parallelism working)
- [ ] Model tier routing configured (8B on single GPU, 32B across both)
- [ ] VRAM allocation documented per model tier
