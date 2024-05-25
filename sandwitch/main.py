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

app = typer.Typer()


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
    return resized_clip.crop(width=width, height=height, x_center=resized_clip.w / 2, y_center=resized_clip.h / 2)


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


def resizer(pic, newsize):
    pilim = Image.fromarray(pic)
    resized_pil = pilim.resize(newsize[::-1], Image.LANCZOS)
    return np.array(resized_pil)


def get_max_dimensions(layer_dirs):
    max_width, max_height = 0, 0
    for layer in layer_dirs:
        for video_file in get_video_files(layer):
            clip = VideoFileClip(video_file)
            max_width = max(max_width, clip.size[0])
            max_height = max(max_height, clip.size[1])
            clip.close()
    return max_width, max_height


@app.command()
def composite_videos(
    root_dir: str = typer.Argument(
        ..., help="Root directory containing layer directories"
    ),
    output_dir: str = typer.Argument(
        ..., help="Output directory for composited videos"
    ),
    width: int = typer.Option(None, help="Target video width"),
    height: int = typer.Option(None, help="Target video height"),
    fps: int = typer.Option(30, help="Target frame rate"),
    dry_run: bool = typer.Option(
        False, help="Print the number of output videos that would be created"
    ),
    output_format: str = typer.Option("mp4", help="Output video format"),
    file_name_prefix: str = typer.Option(
        "composite", help="Prefix for output video file names"
    ),
    log_file: str = typer.Option(None, help="Log file to capture detailed output"),
    verbose: bool = typer.Option(
        False, help="Enable verbose mode for more detailed output"
    ),
):
    if log_file:
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    layer_dirs = sorted(
        [
            os.path.join(root_dir, d)
            for d in os.listdir(root_dir)
            if os.path.isdir(os.path.join(root_dir, d)) and d.startswith("layer_")
        ]
    )

    console = Console()

    if width is None or height is None:
        width, height = get_max_dimensions(layer_dirs)
        typer.echo(f"Defaulting to maximum dimensions: width={width}, height={height}")

    if dry_run:
        num_combinations = 1
        detailed_info = []

        for layer in layer_dirs:
            video_files = get_video_files(layer)
            num_combinations *= len(video_files)
            if verbose:
                detailed_info.append((layer, video_files))

        if verbose:
            table = Table(title="Dry Run Details")
            table.add_column("Layer", style="cyan", no_wrap=True)
            table.add_column("Video Files", style="magenta", no_wrap=True)

            for layer, video_files in detailed_info:
                home_dir = os.path.expanduser("~")
                truncated_files = [
                    video_file.replace(home_dir, "~") for video_file in video_files
                ]
                terminal_width = console.size.width
                home_dir = os.path.expanduser("~")
                truncated_layer = layer.replace(home_dir, "~")
                max_layer_length = max(len(truncated_layer) for truncated_layer, _ in detailed_info)
                max_file_length = terminal_width - max_layer_length - 10  # Adjust for padding

                formatted_files = [
                    (file if len(file) <= max_file_length else "..." + file[-max_file_length:])
                    for file in truncated_files
                ]
                table.add_row(
                    truncated_layer if len(truncated_layer) <= max_layer_length else "..." + truncated_layer[-max_layer_length:],
                    "\n".join(formatted_files)
                )

            console.print(table)
        console.print(f"[bold green]Number of output videos that would be created: {num_combinations}[/bold green]")
        return

    os.makedirs(output_dir, exist_ok=True)

    video_files_layer_0 = get_video_files(layer_dirs[0])
    total_videos = 0

    for i, video_file_0 in enumerate(
        tqdm(video_files_layer_0, desc="Processing videos")
    ):
        base_clip = VideoFileClip(video_file_0).without_audio().set_fps(fps)
        combinations = [[base_clip]]

        for layer in layer_dirs[1:]:
            new_combinations = []
            for combo in combinations:
                for video_file in get_video_files(layer):
                    new_clip = VideoFileClip(video_file).without_audio().set_fps(fps)
                    new_combinations.append(combo + [new_clip])
            combinations = new_combinations

        for j, combo in enumerate(combinations):
            longest_duration = max(clip.duration for clip in combo)
            resized_clips = [resize_and_crop(clip, width, height) for clip in combo]
            retimed_clips = retime_to_match_longest(
                resized_clips, longest_duration, fps
            )
            final_clip = CompositeVideoClip(retimed_clips, size=(width, height))
            output_file = os.path.join(
                output_dir, f"{file_name_prefix}_{total_videos:04d}.{output_format}"
            )
            final_clip.write_videofile(output_file, codec="libx264")
            total_videos += 1


if __name__ == "__main__":
    app()
