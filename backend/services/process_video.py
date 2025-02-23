import os
import yt_dlp
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class VideoProcessor:
    def __init__(self):
        self.download_dir = "downloaded_videos"
        self.output_dir = "processed_audio"
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        self.MAX_VIDEO_DURATION = 300  # 5 minutes in seconds

    def process_videos(self, video_urls, profile_info):
        """Process multiple videos to extract audio in parallel"""
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_url = {
                executor.submit(self._download_video, url): url 
                for url in video_urls
            }
            
            audio_paths = []
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    audio_path = future.result()
                    if audio_path:
                        audio_paths.append(audio_path)
                except Exception as e:
                    print(f"Error processing {url}: {str(e)}")
                    continue
                    
        return audio_paths[0] if audio_paths else None

    def _safe_get_abr(self, format_dict):
        """Safely get audio bitrate from format dict"""
        try:
            abr = format_dict.get('abr')
            if abr is None:
                # Try to get from tbr if abr is not available
                abr = format_dict.get('tbr')
            # Convert to float if string
            if isinstance(abr, str):
                abr = float(abr)
            return float(abr) if abr is not None else None
        except (ValueError, TypeError):
            return None

    def _get_best_audio_format(self, formats):
        """Get the best audio format with fallbacks"""
        if not formats:
            return None

        try:
            # Filter out formats without audio
            audio_formats = [f for f in formats if f.get('acodec') != 'none']
            if not audio_formats:
                return None

            # Get audio bitrates safely
            for fmt in audio_formats:
                fmt['safe_abr'] = self._safe_get_abr(fmt)

            # Try to get optimal bitrate format (64-96kbps)
            for fmt in audio_formats:
                abr = fmt['safe_abr']
                if abr is not None and 64 <= abr <= 96:
                    return fmt

            # Try to get any reasonable bitrate format (<=128kbps)
            for fmt in audio_formats:
                abr = fmt['safe_abr']
                if abr is not None and abr <= 128:
                    return fmt

            # Get audio-only format
            audio_only = next(
                (f for f in audio_formats if f.get('vcodec') == 'none'),
                None
            )
            if audio_only:
                return audio_only

            # Last resort: return first audio format
            return audio_formats[0]

        except Exception as e:
            print(f"Error selecting audio format: {str(e)}")
            return None

    def _download_video(self, url):
        """Download just the middle 5 minutes of audio using direct FFmpeg streaming"""
        try:
            start_time = time.time()
            print(f"\nProcessing URL for audio extraction: {url}")
            
            # Configure yt-dlp with multiple format attempts
            ydl_opts = {
                'quiet': True,
                'no_warnings': False,
                'format': 'bestaudio/best',
                'extract_audio': True,
                'socket_timeout': 15,
                'retries': 3
            }

            # Get video info and available formats
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        print("Could not get video info")
                        return None
                except yt_dlp.utils.DownloadError as e:
                    print(f"Error getting video info: {str(e)}")
                    return None

                duration = float(info.get('duration', 0))
                video_id = info.get('id', 'unknown')
                
                if not duration:
                    print("Could not determine content duration")
                    return None

                print(f"Content duration: {duration} seconds")
                
                # Find best audio format
                formats = info.get('formats', [])
                if not formats:
                    print("No formats available")
                    return None

                audio_format = self._get_best_audio_format(formats)
                if not audio_format:
                    print("No suitable audio format found")
                    # Try direct download as fallback
                    try:
                        print("Attempting direct download...")
                        output_path = os.path.join(self.download_dir, f"{video_id}.mp3")
                        direct_opts = ydl_opts.copy()
                        direct_opts.update({
                            'outtmpl': output_path,
                            'format': 'bestaudio/best',
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '96',
                            }]
                        })
                        ydl.params = direct_opts
                        ydl.download([url])
                        if os.path.exists(output_path):
                            return output_path
                    except Exception as e:
                        print(f"Direct download failed: {str(e)}")
                    return None

                # Calculate the middle segment with bounds checking
                start_time_segment = max(0, int((duration - self.MAX_VIDEO_DURATION) // 2))
                end_time = min(duration, start_time_segment + self.MAX_VIDEO_DURATION)
                segment_duration = end_time - start_time_segment
                print(f"Extracting segment from {start_time_segment}s to {end_time}s...")

                output_path = os.path.join(self.download_dir, f"{video_id}.mp3")
                
                # FFmpeg command with error handling
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-ss', str(start_time_segment),
                    '-i', audio_format['url'],
                    '-t', str(segment_duration),
                    '-c:a', 'libmp3lame',
                    '-ar', '44100',
                    '-ab', '96k',
                    '-ac', '2',
                    '-y',
                    '-progress', 'pipe:1',  # Output progress to stdout
                    output_path
                ]

                print("Downloading and converting audio segment...")
                try:
                    # Calculate timeout based on segment position and duration
                    # Allow more time for segments later in the video
                    base_timeout = 60  # Base timeout of 60 seconds
                    position_factor = start_time_segment / 1000  # Add 1 second per 1000 seconds of position
                    duration_factor = segment_duration / 60  # Add 1 second per minute of duration
                    timeout = base_timeout + position_factor + duration_factor

                    process = subprocess.Popen(
                        ffmpeg_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                    last_progress_time = time.time()
                    while True:
                        # Check if process has finished
                        return_code = process.poll()
                        if return_code is not None:
                            break

                        # Check for timeout
                        current_time = time.time()
                        if current_time - last_progress_time > timeout:
                            process.kill()
                            print(f"FFmpeg process timed out after {timeout:.1f}s")
                            return None

                        # Read progress
                        output = process.stdout.readline()
                        if output:
                            if 'out_time=' in output:
                                last_progress_time = current_time
                            
                        time.sleep(0.1)  # Prevent CPU overuse

                    if return_code != 0:
                        error_output = process.stderr.read()
                        print(f"Error during FFmpeg processing: {error_output}")
                        return None

                except Exception as e:
                    print(f"FFmpeg process error: {str(e)}")
                    try:
                        process.kill()
                    except:
                        pass
                    return None

                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path) / (1024 * 1024)  # Size in MB
                    elapsed = time.time() - start_time
                    print(f"Successfully downloaded and converted audio: {output_path}")
                    print(f"Size: {file_size:.2f}MB, Time: {elapsed:.1f}s, Speed: {file_size/elapsed:.2f}MB/s")
                    return output_path
                else:
                    print("Error: Failed to create output file")
                    return None

        except Exception as e:
            print(f"Error during audio extraction: {str(e)}")
            return None
