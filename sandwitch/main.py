import os
import typer
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from PIL import Image
import numpy as np
from tqdm import tqdm
import logging
from rich import print
from rich.console import Console
import time
import cv2

app = typer.Typer()
console = Console()


def get_video_files(layer_path):
    try:
        return [
            os.path.join(layer_path, f)
            for f in os.listdir(layer_path)
            if f.endswith((".mp4", ".mov", ".avi"))
        ]
    except FileNotFoundError as e:
        logging.error(f"Error accessing files in {layer_path}: {e}")
        return []


def resize_with_opencv(image, new_width, new_height):
    resized_image = cv2.resize(
        image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4
    )
    return resized_image


def resize_and_crop(clip, width, height):
    if clip.size[0] / clip.size[1] < width / height:
        clip = clip.resize(height=height)
    else:
        clip = clip.resize(width=width)
    # Use OpenCV for resizing
    clip_frame = clip.get_frame(0)
    resized_frame = resize_with_opencv(clip_frame, width, height)
    resized_clip = ImageClip(resized_frame, duration=clip.duration)
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
        while sum(c.duration for c in looped_clips if c.duration) < target_duration:
            looped_clips.append(clip)
        final_clip = CompositeVideoClip(looped_clips).set_duration(target_duration)
        final_clip = final_clip.set_fps(fps)
        retimed_clips.append(final_clip)
    return retimed_clips


def get_max_dimensions(layer_dirs):
    max_width, max_height = 0, 0
    for layer in layer_dirs:
        for video_file in get_video_files(layer):
            try:
                clip = VideoFileClip(video_file)
                max_width = max(max_width, clip.size[0])
                max_height = max(max_height, clip.size[1])
                clip.close()
            except Exception as e:
                logging.error(f"Error processing video file {video_file}: {e}")
    return max_width, max_height


@app.command()
def process_videos(
    layers_dir: str = typer.Argument(..., help="Directory containing video layers."),
    output_dir: str = typer.Argument(..., help="Directory to save the output videos."),
    output_format: str = typer.Option("mp4", help="Format of the output video."),
    verbose: bool = typer.Option(False, help="Enable verbose output."),
    dry_run: bool = typer.Option(
        False, help="Perform a dry run without saving videos."
    ),
):
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    start_time = time.time()

    if not os.path.isdir(layers_dir):
        logging.error(f"Invalid layers directory: {layers_dir}")
        return

    if not os.path.isdir(output_dir):
        logging.error(f"Invalid output directory: {output_dir}")
        return

    layer_dirs = [
        os.path.join(layers_dir, d)
        for d in os.listdir(layers_dir)
        if os.path.isdir(os.path.join(layers_dir, d))
    ]
    max_width, max_height = get_max_dimensions(layer_dirs)

    processing_start_time = time.time()
    total_videos = 0

    for layer in tqdm(layer_dirs, desc="Processing layers"):
        video_files = get_video_files(layer)
        longest_duration = 0
        fps = 30

        clips = []
        for video_file in video_files:
            try:
                clip = VideoFileClip(video_file)
                clips.append(clip)
                longest_duration = max(longest_duration, clip.duration)
            except Exception as e:
                logging.error(f"Error loading video file {video_file}: {e}")

        if not clips:
            logging.info(f"No valid video files found in layer {layer}")
            continue

        resized_clips = [resize_and_crop(clip, max_width, max_height) for clip in clips]
        retimed_clips = retime_to_match_longest(resized_clips, longest_duration, fps)

        final_clip = CompositeVideoClip(retimed_clips, size=(max_width, max_height))
        output_file = os.path.join(
            output_dir, f"{os.path.basename(layer)}_{total_videos:04d}.{output_format}"
        )

        logging.debug(f"Processed final composite video for: {output_file}")

        if not dry_run:
            logging.debug(f"Writing final composite video to: {output_file}")
            try:
                final_clip.write_videofile(output_file, codec="libx264")
            except Exception as e:
                logging.error(f"Error writing video file {output_file}: {e}")
        else:
            logging.info(f"Dry run: Video for {output_file} processed but not saved.")

        total_videos += 1

    console.print(
        f"Total processing time: {time.time() - processing_start_time:.2f} seconds"
    )
    console.print(f"Total execution time: {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":
    app()
