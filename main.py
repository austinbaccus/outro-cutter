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

def trim_last_n_seconds(input_path, output_path, seconds=8):
    """
    Trim the last N seconds from a video.
    """
    print(f"Processing: {input_path.name}")
    
    # Get video duration
    duration = get_video_duration(input_path)
    
    if duration <= seconds:
        print(f"  Warning: Video is only {duration:.2f}s, skipping")
        return False
    
    cut_time = duration - seconds
    print(f"  Trimming at {cut_time:.2f}s (removing last {seconds}s)...")
    
    ffmpeg.input(str(input_path), t=cut_time).output(
        str(output_path),
        codec='copy',
        loglevel='error'
    ).run()
    
    print(f"✅ Completed: {input_path.name}")
    return True

def find_first_black_frame_from_end(video_path, threshold=2, search_seconds=120):
    """
    Search backwards from the end, cut at the FIRST black frame encountered.
    threshold: max average pixel brightness (0-255) to consider black
    search_seconds: how many seconds from the end to search
    """
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"  Total frames: {frame_count}, FPS: {fps}")
    
    # Calculate search range
    search_frames = int(fps * search_seconds)
    start_frame = max(0, frame_count - search_frames)
    
    # Search backwards from the last frame
    for frame_num in range(frame_count - 1, start_frame, -1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray)
        
        is_black = avg_brightness < threshold
        
        # First black frame we encounter going backwards
        if is_black:
            cap.release()
            timestamp = frame_num / fps
            print(f"  Found black frame at {timestamp:.2f}s (frame {frame_num})")
            return timestamp
    
    cap.release()
    print(f"  No black frames found in last {search_seconds} seconds")
    return None

def trim_video_at_black_frame(input_path, output_path):
    """Trim video at the last black frame."""
    print(f"\nProcessing: {input_path.name}")
    
    cut_time = find_first_black_frame_from_end(input_path)
    
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
dir_videos = Path("./videos")
dir_trimmed = Path("./videos_trimmed")
dir_final = Path("./videos_final")

for video_file in dir_videos.glob("*.webm"):
    trim_last_n_seconds(video_file, dir_trimmed / video_file.name, seconds=13)
    trim_video_at_black_frame(dir_trimmed / video_file.name, dir_final / video_file.name)