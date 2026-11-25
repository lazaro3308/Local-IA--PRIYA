import tempfile
import unittest
import importlib.util
import shutil
from pathlib import Path

from pria.tools.media import MediaError, create_slideshow_video, validate_image_files


class MediaToolTests(unittest.TestCase):
    def test_image_validation_limits_count_and_file_size(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "one.png"
            image.write_bytes(b"png")
            self.assertEqual(validate_image_files([image]), [image.resolve()])
            with self.assertRaisesRegex(MediaError, "máximo"):
                validate_image_files([image] * 5)

    def test_slideshow_refuses_to_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "one.png"
            image.write_bytes(b"png")
            output = Path(folder) / "video.mp4"
            output.write_bytes(b"keep")
            with self.assertRaisesRegex(MediaError, "já existe"):
                create_slideshow_video([image], output)
            self.assertEqual(output.read_bytes(), b"keep")

    def test_slideshow_rejects_unsupported_destination_before_running_ffmpeg(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "one.png"
            image.write_bytes(b"png")
            with self.assertRaisesRegex(MediaError, "extensão .mp4"):
                create_slideshow_video([image], Path(folder) / "video.mov")

    @unittest.skipUnless(importlib.util.find_spec("imageio_ffmpeg") or shutil.which("ffmpeg"), "FFmpeg opcional ausente")
    def test_slideshow_creates_a_real_mp4_locally(self):
        from PySide6.QtGui import QImage, QColor

        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "one.png"
            frame = QImage(32, 32, QImage.Format_RGB32)
            frame.fill(QColor("#d93448"))
            self.assertTrue(frame.save(str(image)))
            output = create_slideshow_video([image], Path(folder) / "video.mp4", 1)
            self.assertGreater(output.stat().st_size, 256)
            self.assertEqual(output.read_bytes()[4:8], b"ftyp")


if __name__ == "__main__":
    unittest.main()

