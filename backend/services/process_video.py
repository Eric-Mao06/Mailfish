import os
import requests
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from urllib.parse import parse_qs, urlparse

class VideoProcessor:
    def __init__(self):
        self.download_dir = "downloaded_videos"
        self.output_dir = "processed_audio"
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        self.MAX_VIDEO_DURATION = 300  # 5 minutes in seconds
        self.RAPID_API_KEY = "c14a64b518mshe0eaa5705ea7846p14f95fjsn657a5b82a797"
        
    def _get_video_id(self, url):
        """Extract video ID from YouTube URL"""
        # Handle different YouTube URL formats
        query = urlparse(url)
        if query.hostname == 'youtu.be':
            return query.path[1:]
        if query.hostname in {'www.youtube.com', 'youtube.com'}:
            if query.path == '/watch':
                return parse_qs(query.query)['v'][0]
            if query.path[:7] == '/embed/':
                return query.path.split('/')[2]
            if query.path[:3] == '/v/':
                return query.path.split('/')[2]
        return None
        
    def _get_video_duration(self, video_id):
        """Get video duration using YouTube Data API"""
        try:
            # Using a public API endpoint to get video info
            url = f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
            response = requests.get(url)
            if response.status_code == 200:
                # Video exists, now get duration from another endpoint
                url = f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    # Extract duration from title or other metadata
                    return self.MAX_VIDEO_DURATION  # Fallback to max duration
            return None
        except Exception as e:
            print(f"Error getting video duration: {str(e)}")
            return None
        
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
        """Download audio from YouTube video using RapidAPI with time segments"""
        try:
            start_time = time.time()
            print(f"\nProcessing URL for audio extraction: {url}")
            
            # Get video ID and duration
            video_id = self._get_video_id(url)
            if not video_id:
                print("Invalid YouTube URL")
                return None
                
            duration = self._get_video_duration(video_id)
            if not duration:
                print("Could not get video duration")
                return None
                
            # Calculate middle segment
            start_time_segment = max(0, int((duration - self.MAX_VIDEO_DURATION) // 2))
            end_time_segment = min(duration, start_time_segment + self.MAX_VIDEO_DURATION)
            
            # Prepare RapidAPI request
            rapid_api_url = "https://youtube-to-mp315.p.rapidapi.com/download"
            querystring = {
                "url": url,
                "format": "mp3",
                "startTime": start_time_segment,
                "endTime": end_time_segment
            }
            headers = {
                "x-rapidapi-key": self.RAPID_API_KEY,
                "x-rapidapi-host": "youtube-to-mp315.p.rapidapi.com",
                "Content-Type": "application/json"
            }

            print(f"Extracting segment from {start_time_segment}s to {end_time_segment}s...")
            
            # Make API request to get download link
            response = requests.post(rapid_api_url, json={}, headers=headers, params=querystring)
            if response.status_code != 200:
                print(f"Error from RapidAPI: {response.text}")
                return None
                
            result = response.json()
            if 'link' not in result:
                print(f"No download link in response: {result}")
                return None
                
            # Download the MP3 file
            download_url = result['link']
            output_path = os.path.join(self.download_dir, f"{video_id}.mp3")
            
            # Download the file
            mp3_response = requests.get(download_url)
            if mp3_response.status_code != 200:
                print(f"Error downloading MP3: {mp3_response.status_code}")
                return None
                
            with open(output_path, 'wb') as f:
                f.write(mp3_response.content)
                
            elapsed = time.time() - start_time
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # Size in MB
            print(f"Successfully downloaded audio to {output_path}")
            print(f"Size: {file_size:.2f}MB, Time: {elapsed:.1f}s, Speed: {file_size/elapsed:.2f}MB/s")
            return output_path
            
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            return None

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
