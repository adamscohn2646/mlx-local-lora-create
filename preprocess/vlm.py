from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from preprocess.logging_util import append_error
from preprocess.vlm_image import prepare_vlm_image


@dataclass
class VlmResult:
    text: str
    timing_ms: int
    model_id: str


def _normalize_output(output: Any) -> str:
    if hasattr(output, "text"):
        text = str(output.text)
    elif isinstance(output, str):
        text = output
    elif isinstance(output, dict) and "text" in output:
        text = str(output["text"])
    else:
        text = str(output)
    return text.replace("\x00", "").strip()


class VlmEngine:
    """Thin mlx-vlm wrapper — loads model once per engine instance."""

    def __init__(self) -> None:
        self._model_id: str | None = None
        self._model: Any = None
        self._processor: Any = None

    def load_model(self, model_id: str) -> None:
        if self._model_id == model_id and self._model is not None:
            return
        try:
            from mlx_vlm import load as vlm_load
        except ImportError as exc:
            raise RuntimeError(
                "mlx-vlm is not installed. Install with: pip install mlx-vlm"
            ) from exc

        self._model, self._processor = vlm_load(model_id)
        self._model_id = model_id

    def _format_prompt(self, user_prompt: str) -> str:
        from mlx_vlm.prompt_utils import apply_chat_template

        config = self._model.config
        formatted = apply_chat_template(
            self._processor,
            config,
            user_prompt,
            num_images=1,
            num_audios=0,
        )
        if not isinstance(formatted, str) or not formatted.strip():
            raise RuntimeError("Failed to format VLM prompt with chat template.")
        return formatted

    def generate(
        self,
        model_id: str,
        prompt: str,
        image_path: Path,
        params: dict[str, Any],
    ) -> VlmResult:
        self.load_model(model_id)
        try:
            from mlx_vlm import generate as vlm_generate
        except ImportError as exc:
            raise RuntimeError(
                "mlx-vlm is not installed. Install with: pip install mlx-vlm"
            ) from exc

        gen_kwargs: dict[str, Any] = {
            "max_tokens": int(params.get("max_tokens", 2048)),
            "temperature": float(params.get("temperature", 0.2)),
            "top_p": float(params.get("top_p", 0.95)),
            "verbose": False,
        }
        if "top_k" in params:
            gen_kwargs["top_k"] = int(params["top_k"])
        if "repetition_penalty" in params:
            gen_kwargs["repetition_penalty"] = float(params["repetition_penalty"])
        if "min_p" in params:
            gen_kwargs["min_p"] = float(params["min_p"])

        max_long_side = int(params.get("vlm_max_long_side", 1024))
        vlm_image_path = prepare_vlm_image(image_path, max_long_side=max_long_side)
        prompt_to_use = self._format_prompt(prompt)
        image_arg = [str(vlm_image_path)]

        started = time.perf_counter()
        output = vlm_generate(
            self._model,
            self._processor,
            prompt=prompt_to_use,
            image=image_arg,
            **gen_kwargs,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return VlmResult(text=_normalize_output(output), timing_ms=elapsed_ms, model_id=model_id)


def generate_caption(
    engine: VlmEngine,
    *,
    model_id: str,
    prompt: str,
    image_path: Path,
    params: dict[str, Any],
) -> VlmResult:
    try:
        return engine.generate(model_id, prompt, image_path, params)
    except Exception as exc:
        append_error(
            "preprocess.vlm",
            type(exc).__name__,
            str(exc),
            context={"image": str(image_path), "model_id": model_id},
            exc=exc,
        )
        raise
