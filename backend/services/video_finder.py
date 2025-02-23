import os
import requests
import json
import re

class VideoFinder:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable is not set")
            
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}"
        }

    def find_videos(self, profile_info):
        """
        Uses Perplexity to search for videos of the person speaking
        Args:
            profile_info (dict): Dictionary containing name and bio from Twitter
        Returns:
            list: List of dictionaries containing video URLs and timestamps
        """
        name = profile_info.get("name")
        bio = profile_info.get("bio", "")
        
        prompt = f"Find YouTube videos of {name} ({bio}) speaking. Requirements:  Videos must be primarily focused on {name} himself speaking directly Do not include videos of other people speaking about {name}  Maximum video length: 15 minutes  High audio quality with minimal background noise  No overlapping voices or music  For each video found, provide: The YouTube URL  return only youtube URL and nothing else"
        
        print(f"\nSearching for videos with query: {prompt}\n")
        
        try:
            response = self._query_perplexity(prompt)
            
            # Extract URLs from the response
            # The response might be a plain text with URLs, so we'll extract them
            urls = re.findall(r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+', response)
            
            if not urls:
                print("No suitable videos found")
                return []
            
            # Return list of unique URLs
            return list(set(urls))
            
        except Exception as e:
            print(f"\nError making request to Perplexity API: {str(e)}")
            raise

    def _query_perplexity(self, prompt):
        """
        Query the Perplexity API
        Args:
            prompt (str): The prompt to send to Perplexity
        Returns:
            str: The response from Perplexity
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": "sonar-reasoning-pro",  # Updated model name
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"Perplexity API error: {response.status_code} - {response.text}")
            
        return response.json()['choices'][0]['message']['content']
