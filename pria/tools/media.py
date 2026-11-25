"""Local image validation and slideshow video creation."""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path


class MediaError(RuntimeError):
    pass


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_VIDEO_IMAGES = 20


def validate_image_files(
    paths: list[str | Path], *, max_images: int = 4, max_total_bytes: int = 20 * 1024 * 1024,
) -> list[Path]:
    """Validate user-selected image files without opening or modifying them."""
    if not paths:
        raise MediaError("Selecione pelo menos uma imagem.")
    if len(paths) > max_images:
        raise MediaError(f"Selecione no máximo {max_images} imagens por vez.")
    result = []
    total = 0
    for raw in paths:
        path = Path(raw).expanduser().resolve()
        if path.suffix.casefold() not in IMAGE_EXTENSIONS or not path.is_file():
            raise MediaError(f"Arquivo de imagem inválido ou não encontrado: {path.name}")
        size = path.stat().st_size
        if size <= 0 or size > MAX_IMAGE_BYTES:
            raise MediaError(f"A imagem {path.name} está vazia ou excede 15 MiB.")
        total += size
        result.append(path)
    if total > max_total_bytes:
        raise MediaError(f"O conjunto de imagens excede {max_total_bytes // (1024 * 1024)} MiB.")
    return result


def _ffmpeg_path() -> str:
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if Path(path).is_file():
            return path
    except (ImportError, RuntimeError, OSError):
        pass
    path = shutil.which("ffmpeg")
    if path:
        return path
    raise MediaError("FFmpeg não está instalado. Rode instalar.cmd para adicionar o componente local de vídeo.")


def create_slideshow_video(
    image_paths: list[str | Path],
    output_path: str | Path,
    seconds_per_image: float = 3.0,
    *,
    width: int = 1280,
    height: int = 720,
    timeout_seconds: int = 180,
) -> Path:
    """Create an MP4 slideshow from still images with local FFmpeg; never overwrites."""
    images = validate_image_files(
        image_paths, max_images=MAX_VIDEO_IMAGES, max_total_bytes=300 * 1024 * 1024,
    )
    if not 1 <= seconds_per_image <= 12:
        raise MediaError("A duração de cada imagem deve ficar entre 1 e 12 segundos.")
    output = Path(output_path).expanduser().resolve()
    if output.suffix.casefold() != ".mp4":
        raise MediaError("Escolha um arquivo de saída com extensão .mp4.")
    if output.exists():
        raise MediaError("O arquivo de destino já existe; escolha outro nome para evitar sobrescrevê-lo.")
    if width < 320 or height < 240 or width % 2 or height % 2:
        raise MediaError("A resolução precisa ter pelo menos 320×240 e dimensões pares.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output.with_name(f".{output.stem}.pria-{uuid.uuid4().hex}.tmp.mp4")
    filters = []
    inputs = []
    for index, image in enumerate(images):
        inputs.extend(["-loop", "1", "-framerate", "30", "-t", str(float(seconds_per_image)), "-i", str(image)])
        filters.append(
            f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v{index}]"
        )
    joined = "".join(f"[v{index}]" for index in range(len(images)))
    filters.append(f"{joined}concat=n={len(images)}:v=1:a=0[outv]")
    command = [
        _ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y", *inputs,
        "-filter_complex", ";".join(filters), "-map", "[outv]", "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-t", str(float(seconds_per_image) * len(images)), "-f", "mp4", str(temp_path),
    ]
    try:
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            raise MediaError("A criação excedeu o limite de 3 minutos e foi interrompida.") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or "FFmpeg encerrou sem detalhes.").strip()[-1200:]
            raise MediaError(f"FFmpeg não conseguiu criar o vídeo: {detail}")
        if not temp_path.is_file() or temp_path.stat().st_size < 256:
            raise MediaError("FFmpeg terminou, mas não gerou um MP4 válido.")
        # On Windows, rename fails if a destination appeared during rendering.
        os.rename(temp_path, output)
        return output
    finally:
        temp_path.unlink(missing_ok=True)

