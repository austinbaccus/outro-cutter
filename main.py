import cv2
import ffmpeg
from pathlib import Path
import numpy as np
import subprocess
import json

def get_video_duration(video_path):
    """
    Get the duration of a video file in seconds.
    """
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    if fps > 0:
        return frame_count / fps
    return 0.0

def find_third_to_last_black_frame(video_path, pic_th=0.99, pix_th=0.00, duration=0.000001, use_gpu=False):
    """
    Use FFmpeg's blackdetect filter with optional GPU decoding.
    threshold: 0.0-1.0, percentage of black pixels
    """

    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'info']
    
    if use_gpu:
        # NVIDIA GPU decoding (NVDEC)
        cmd.extend([
            '-hwaccel', 'cuda',
            '-hwaccel_output_format', 'cuda',
        ])
    
    cmd.extend([
        '-i', str(video_path),
        '-vf', f'blackdetect=d={duration}',
        '-an',  # no audio
        '-f', 'null',
        '-'
    ])
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    # Parse FFmpeg output for black frames
    black_frames = []
    
    for line in result.stderr.split('\n'):
        if 'black_start' in line:
            parts = line.split()
            for part in parts:
                if part.startswith('black_start:'):
                    black_frame_timestamp = float(part.split(':')[1])
                    black_frames.append(black_frame_timestamp)


    return black_frames[-3]
    return None

def trim_video_at_black_frame(input_path, output_path, outro_time):
    """Trim video at the last black frame."""
    print(f"\nProcessing: {input_path.name}")
    
    cut_time = find_third_to_last_black_frame(input_path)
    
    if cut_time is None:
        print(f"❌ Warning: No black frame found, skipping {input_path.name}")
        return False
    
    ffmpeg.input(str(input_path), t=cut_time).output(
        str(output_path),
        codec='copy',
        loglevel='error'
    ).run()
    
    video_duration = get_video_duration(input_path)
    cut_time_from_end = video_duration - cut_time
    print(f"✅ Completed: {input_path.name}. Trimming at {cut_time_from_end:.2f}s from end...")
    return True

# Main processing
video_dir = Path("./videos")
output_dir = Path("./trimmed_videos")
output_dir.mkdir(exist_ok=True)

for video_file in video_dir.glob("*.webm"):
    output_path = output_dir / video_file.name
    trim_video_at_black_frame(video_file, output_path, 25)