import os
import requests
import json
import re
from exa_py import Exa

class VideoFinder:
    def __init__(self):
        self.exa = Exa(api_key="32ec3504-0167-4eee-9ffc-f0a7c8db1ec5")

    def find_videos(self, profile_info):
        """
        Uses Exa to search for videos of the person speaking
        Args:
            profile_info (dict): Dictionary containing name and bio from Twitter
        Returns:
            list: List of dictionaries containing video URLs and timestamps
        """
        name = profile_info.get("name")
        bio = profile_info.get("bio", "")
        
        prompt = f"Videos of {name} speaking. Requirements:  Videos must be primarily focused on {name} himself speaking directly Do not include videos of other people speaking about {name}  Maximum video length: 15 minutes  High audio quality with minimal background noise  No overlapping voices or music."
        
        print(f"\nSearching for videos with query: {prompt}\n")
        
        try:
            result = self.exa.search_and_contents(
                prompt,
                text=True,
                include_domains=["youtube.com"],
                num_results=3
            )
            
            # Extract URLs from the response
            urls = [item.url for item in result.results]
            
            if not urls:
                print("No suitable videos found")
                return []
            
            # Return list of unique URLs
            return list(set(urls))
            
        except Exception as e:
            print(f"\nError making request to Exa API: {str(e)}")
            raise
