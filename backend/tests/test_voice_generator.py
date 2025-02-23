import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.process_video import VideoProcessor

def test_video_processing():
    # Sample URLs to test with - mix of different durations and formats
    test_urls = [
        "https://www.youtube.com/watch?v=1-TZqOsVCNM",  # Long video
        "https://www.youtube.com/watch?v=mGY2To_HW98",  # Another format
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Very first YouTube video (short)
    ]
    
    # Sample profile info (not used but required by the interface)
    profile_info = {
        "name": "test",
        "description": "test profile"
    }
    
    # Create processor and process videos
    processor = VideoProcessor()
    result = processor.process_videos(test_urls, profile_info)
    
    if result:
        print(f"Successfully processed video. Output file: {result}")
    else:
        print("Failed to process videos")

if __name__ == "__main__":
    test_video_processing()
