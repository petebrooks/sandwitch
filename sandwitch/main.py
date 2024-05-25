import os
import typer
from moviepy.editor import VideoFileClip, CompositeVideoClip
from moviepy.video.fx.resize import resize as moviepy_resize
from PIL import Image
import numpy as np
from tqdm import tqdm
import logging
from rich import print
from rich.console import Console
from rich.table import Table
import time
import cv2

app = typer.Typer()
console = Console()


def get_video_files(layer_path):
    return [
        os.path.join(layer_path, f)
        for f in os.listdir(layer_path)
        if f.endswith((".mp4", ".mov", ".avi"))
    ]


def resize_and_crop(clip, width, height):
    if clip.size[0] / clip.size[1] < width / height:
        clip = clip.resize(height=height)
    else:
        clip = clip.resize(width=width)
    resized_clip = moviepy_resize(clip, newsize=(width, height), apply_to_mask=True)
    return resized_clip.crop(
        width=width,
        height=height,
        x_center=resized_clip.w / 2,
        y_center=resized_clip.h / 2,
    )


def resizer(pic, newsize):
    pilim = Image.fromarray(pic)
    resized_pil = pilim.resize(newsize[::-1], Image.LANCZOS)
    return np.array(resized_pil)


def retime_to_match_longest(clips, target_duration, fps):
    retimed_clips = []
    for clip in clips:
        duration = clip.duration
        looped_clips = [clip]
        while sum(c.duration for c in looped_clips) < target_duration:
            looped_clips.append(clip)
        final_clip = CompositeVideoClip(looped_clips).set_duration(target_duration)
        final_clip = final_clip.set_fps(fps)
        retimed_clips.append(final_clip)
    return retimed_clips


def get_max_dimensions(layer_dirs):
    max_width, max_height = 0, 0
    for layer in layer_dirs:
        for video_file in get_video_files(layer):
            clip = VideoFileClip(video_file)
            max_width = max(max_width, clip.size[0])
            max_height = max(max_height, clip.size[1])
            clip.close()
    return max_width, max_height


def resize_with_opencv(image_path, new_width, new_height):
    image = cv2.imread(image_path)
    resized_image = cv2.resize(
        image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4
    )
    return resized_image


@app.command()
def process_videos(layers_dir: str, output_dir: str, output_format: str = "mp4"):
    start_time = time.time()
    layer_dirs = [
        os.path.join(layers_dir, d)
        for d in os.listdir(layers_dir)
        if os.path.isdir(os.path.join(layers_dir, d))
    ]
    max_width, max_height = get_max_dimensions(layer_dirs)

    processing_start_time = time.time()
    total_videos = 0

    for layer in layer_dirs:
        video_files = get_video_files(layer)
        longest_duration = 0
        fps = 30

        clips = []
        for video_file in video_files:
            clip = VideoFileClip(video_file)
            clips.append(clip)
            longest_duration = max(longest_duration, clip.duration)

        resized_clips = [resize_and_crop(clip, max_width, max_height) for clip in clips]
        retimed_clips = retime_to_match_longest(resized_clips, longest_duration, fps)

        final_clip = CompositeVideoClip(retimed_clips, size=(max_width, max_height))
        output_file = os.path.join(
            output_dir, f"{os.path.basename(layer)}_{total_videos:04d}.{output_format}"
        )

        final_clip.write_videofile(output_file, codec="libx264")
        total_videos += 1

    console.print(
        f"Total processing time: {time.time() - processing_start_time:.2f} seconds"
    )
    console.print(f"Total execution time: {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":
    app()
