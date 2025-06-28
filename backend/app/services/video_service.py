import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from typing import Dict, List
from app.core.config import settings

class VideoProcessingService:
    @staticmethod
    async def process_video_to_hls(input_path: str, stream_id: str) -> Dict[str, str]:
        """Process video file to HLS format with multiple qualities"""
        output_dir = Path(settings.CDN_DIR) / "cdn1" / stream_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Define quality levels
        qualities = [
            {"name": "1080p", "resolution": "1920x1080", "bitrate": "5000k", "suffix": "1080"},
            {"name": "720p", "resolution": "1280x720", "bitrate": "2800k", "suffix": "720"},
            {"name": "480p", "resolution": "854x480", "bitrate": "1400k", "suffix": "480"}
        ]

        playlist_urls = {}

        # Generate HLS for each quality
        for quality in qualities:
            playlist_path = output_dir / f"playlist_{quality['suffix']}.m3u8"
            segment_pattern = output_dir / f"segment_{quality['suffix']}_%03d.ts"

            cmd = [
                settings.FFMPEG_PATH,
                "-i", input_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-vf", f"scale={quality['resolution']}",
                "-b:v", quality["bitrate"],
                "-b:a", "128k",
                "-hls_time", "4",
                "-hls_playlist_type", "vod",
                "-hls_segment_filename", str(segment_pattern),
                str(playlist_path)
            ]

            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()

                if process.returncode == 0:
                    playlist_urls[quality["name"]] = f"/cdn/cdn1/{stream_id}/playlist_{quality['suffix']}.m3u8"

            except Exception as e:
                print(f"Error processing {quality['name']}: {e}")

        # Create master playlist
        master_playlist_path = output_dir / "master.m3u8"
        await VideoProcessingService._create_master_playlist(
            master_playlist_path, qualities, stream_id
        )

        # Copy to other CDN servers
        await VideoProcessingService._distribute_to_cdns(stream_id)

        return {
            "master_playlist": f"/cdn/cdn1/{stream_id}/master.m3u8",
            "qualities": playlist_urls
        }

    @staticmethod
    async def _create_master_playlist(master_path: Path, qualities: List[Dict], stream_id: str):
        """Create HLS master playlist"""
        content = "#EXTM3U\n#EXT-X-VERSION:3\n\n"

        for quality in qualities:
            bitrate = quality["bitrate"].replace("k", "000")
            resolution = quality["resolution"]
            content += f"#EXT-X-STREAM-INF:BANDWIDTH={bitrate},RESOLUTION={resolution}\n"
            content += f"playlist_{quality['suffix']}.m3u8\n\n"

        with open(master_path, "w") as f:
            f.write(content)

    @staticmethod
    async def _distribute_to_cdns(stream_id: str):
        """Copy HLS files to all CDN servers"""
        source_dir = Path(settings.CDN_DIR) / "cdn1" / stream_id

        for cdn in ["cdn2", "cdn3"]:
            dest_dir = Path(settings.CDN_DIR) / cdn / stream_id
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Copy all files
            for file_path in source_dir.glob("*"):
                dest_path = dest_dir / file_path.name
                try:
                    import shutil
                    shutil.copy2(file_path, dest_path)
                except Exception as e:
                    print(f"Error copying to {cdn}: {e}")

    @staticmethod
    async def generate_thumbnail(input_path: str, output_path: str, timestamp: str = "00:00:05"):
        """Generate video thumbnail"""
        cmd = [
            settings.FFMPEG_PATH,
            "-i", input_path,
            "-ss", timestamp,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return False
