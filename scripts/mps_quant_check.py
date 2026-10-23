"""MPS go/no-go micro-tests for MiniMax H3 on Apple Silicon.

Uses ComfyUI's own device policy and comfy-kitchen quantized layouts on small
synthetic tensors (no model files needed). Run from the ComfyUI checkout:

    cd ~/dev/ComfyUI && .venv/bin/python ~/dev/AI_short_drama/scripts/mps_quant_check.py

Exit code 0 = all required checks passed.
"""
import os
import sys
import time

sys.argv = sys.argv[:1]  # comfy.cli_args parses argv on import
sys.path.insert(0, os.getcwd())

import torch  # noqa: E402

import comfy.model_management as mm  # noqa: E402
import comfy.ops  # noqa: E402
import comfy.quant_ops  # noqa: F401,E402  registers ComfyUI layouts
from comfy.ldm.modules import attention  # noqa: E402
from comfy_kitchen.tensor import QuantizedTensor  # noqa: E402

MPS = torch.device("mps")
results = []


def check(name, required, fn):
    try:
        ok, detail = fn()
    except Exception as e:  # report, don't abort the remaining checks
        ok, detail = False, f"{type(e).__name__}: {str(e).splitlines()[0][:120]}"
    results.append((name, required, ok))
    tag = "PASS" if ok else ("FAIL" if required else "info")
    print(f"[{tag}] {name}: {detail}")


def rel_err(a, b):
    a, b = a.float().cpu(), b.float().cpu()
    return ((a - b).abs().max() / b.abs().max()).item()


print("== ComfyUI device policy on this machine ==")
print("torch device:", mm.get_torch_device(), "| vram_state:", mm.vram_state.name)
print("text_encoder_device:", mm.text_encoder_device(), "| vae_device:", mm.vae_device())
print("supports_int8_compute(mps):", mm.supports_int8_compute(MPS))
print("disabled quant formats on mps:", sorted(comfy.ops.get_disabled_quant_formats(MPS)))
print("attention function:", attention.optimized_attention.__name__)
print(f"GPU working-set cap: {torch.mps.recommended_max_memory() / 2**30:.1f} GiB")
print()

torch.manual_seed(0)
W = torch.randn(3072, 3072, dtype=torch.bfloat16) * 0.02
X = torch.randn(64, 3072, dtype=torch.bfloat16)
REF = X.float() @ W.float().T


def int8_convrot_on_mps():
    # Diffusion model / fallback text encoder format; ComfyUI dequantizes on MPS.
    qt = QuantizedTensor.from_float(W, "TensorWiseINT8Layout", per_channel=True, convrot=True, convrot_groupsize=256)
    w = qt.to(MPS).dequantize().to(torch.float16)
    y = X.to(MPS, torch.float16) @ w.T
    e = rel_err(y, REF)
    return e < 0.05 and torch.isfinite(y).all().item(), f"dequant+matmul on mps, rel.err {e:.1e}"


def nvfp4_on_cpu():
    # Text encoder format, on the device ComfyUI actually uses for text encoders here.
    qt = QuantizedTensor.from_float(W, "TensorCoreNVFP4Layout")
    w = qt.dequantize().to(torch.bfloat16)
    y = X @ w.T
    e = rel_err(y, REF)
    return e < 0.25 and torch.isfinite(y).all().item(), f"dequant+matmul on cpu, rel.err {e:.1e}"


def nvfp4_on_mps():
    qt = QuantizedTensor.from_float(W, "TensorCoreNVFP4Layout")
    w = qt.to(MPS).dequantize()
    return True, f"works on mps too (rel.err {rel_err(X.to(MPS) @ w.T, REF):.1e})"


def int_mm_on_mps():
    torch._int_mm(torch.ones(32, 32, dtype=torch.int8, device=MPS), torch.ones(32, 32, dtype=torch.int8, device=MPS))
    return True, "native int8 matmul available"


def big_attention_on_mps():
    # #15315-style probe: B*H*L*L > 2**31 elements in one SDPA call.
    heads, L, d = 24, 16384, 128
    q, k, v = (torch.randn(1, heads, L, d, device=MPS, dtype=torch.float16) for _ in range(3))
    t = time.perf_counter()
    full = torch.nn.functional.scaled_dot_product_attention(q, k, v)
    torch.mps.synchronize()
    dt = time.perf_counter() - t
    per_head = torch.cat([torch.nn.functional.scaled_dot_product_attention(q[:, h:h+1], k[:, h:h+1], v[:, h:h+1])
                          for h in range(heads)], dim=1)
    diff = (full - per_head).abs().max().item()
    ok = torch.isfinite(full).all().item() and diff < 1e-2
    return ok, f"{heads}x{L}² scores ({heads*L*L/2**31:.1f}x INT_MAX), {dt:.2f}s, max diff vs per-head {diff:.1e}"


def comfy_attention_on_mps():
    # The attention function ComfyUI selected for this machine, vs PyTorch SDPA.
    heads, L, d = 24, 8192, 128
    q, k, v = (torch.randn(1, L, heads * d, device=MPS, dtype=torch.float16) for _ in range(3))
    t = time.perf_counter()
    out = attention.optimized_attention(q, k, v, heads)
    torch.mps.synchronize()
    dt = time.perf_counter() - t
    split = lambda x: x.view(1, L, heads, d).transpose(1, 2)  # noqa: E731
    ref = torch.nn.functional.scaled_dot_product_attention(split(q), split(k), split(v)).transpose(1, 2).reshape(1, L, -1)
    diff = (out - ref).abs().max().item()
    ok = torch.isfinite(out).all().item() and diff < 1e-2
    return ok, f"{attention.optimized_attention.__name__} {heads}x{L}², {dt:.2f}s, max diff vs SDPA {diff:.1e}"


check("int8_convrot weights on MPS (diffusion model path)", True, int8_convrot_on_mps)
check("nvfp4 weights on CPU (text encoder path)", True, nvfp4_on_cpu)
check("nvfp4 weights on MPS", False, nvfp4_on_mps)
check("torch._int_mm on MPS", False, int_mm_on_mps)
check("large attention on MPS (INT_MAX / NaN probe)", True, big_attention_on_mps)
check("ComfyUI's selected attention on MPS", True, comfy_attention_on_mps)
print(f"\npeak MPS driver memory: {torch.mps.driver_allocated_memory() / 2**30:.1f} GiB")

failed = [n for n, req, ok in results if req and not ok]
print("RESULT:", "GO" if not failed else f"NO-GO ({'; '.join(failed)})")
sys.exit(1 if failed else 0)
