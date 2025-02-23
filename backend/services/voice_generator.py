import os
import requests
from dotenv import load_dotenv

class VoiceGenerator:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"
        self.output_dir = "generated_voices"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_voice_clone(self, audio_path, voice_name, description=None, remove_background_noise=True):
        """
        Generate a voice clone using ElevenLabs API
        Args:
            audio_path (str): Path to the audio file to use for voice cloning
            voice_name (str): Name for the generated voice
            description (str, optional): Description of the voice
            remove_background_noise (bool): Whether to remove background noise
        Returns:
            dict: Response from ElevenLabs API containing voice_id and verification status
        """
        try:
            print(f"\nGenerating voice clone for: {voice_name}")
            
            # Verify audio file exists
            if not os.path.exists(audio_path):
                print(f"Error: Audio file not found at {audio_path}")
                return None
                
            # Prepare API endpoint
            url = f"{self.base_url}/voices/add"
            
            # Prepare headers
            headers = {
                "xi-api-key": self.api_key
            }
            
            # Prepare form data
            files = {
                'files': ('audio.mp3', open(audio_path, 'rb'), 'audio/mpeg')
            }
            
            data = {
                'name': voice_name,
                'remove_background_noise': str(remove_background_noise).lower()
            }
            
            if description:
                data['description'] = description
            
            # Make API request
            print("Sending request to ElevenLabs API...")
            response = requests.post(url, headers=headers, data=data, files=files)
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                print(f"Successfully created voice clone! Voice ID: {result['voice_id']}")
                
                # Save voice ID for future reference
                self._save_voice_id(voice_name, result['voice_id'])
                
                return result
            else:
                print(f"Error creating voice clone: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error generating voice clone: {str(e)}")
            return None
        finally:
            # Ensure file is closed
            if 'files' in locals() and hasattr(files['files'][1], 'close'):
                files['files'][1].close()

    def _save_voice_id(self, voice_name, voice_id):
        """
        Save voice ID to a file for future reference
        """
        try:
            voice_file = os.path.join(self.output_dir, "voice_ids.txt")
            with open(voice_file, "a") as f:
                f.write(f"{voice_name}: {voice_id}\n")
        except Exception as e:
            print(f"Error saving voice ID: {str(e)}")

    def get_saved_voice_id(self, voice_name):
        """
        Retrieve a previously saved voice ID
        """
        try:
            voice_file = os.path.join(self.output_dir, "voice_ids.txt")
            if not os.path.exists(voice_file):
                return None
                
            with open(voice_file, "r") as f:
                for line in f:
                    if line.startswith(f"{voice_name}: "):
                        return line.split(": ")[1].strip()
            return None
        except Exception as e:
            print(f"Error reading voice ID: {str(e)}")
            return None

    def text_to_speech(self, voice_id, text):
        """
        Generate speech from text using a specific voice
        Args:
            voice_id (str): ID of the voice to use
            text (str): Text to convert to speech
        Returns:
            bytes: Audio data in MP3 format
        """
        try:
            print(f"\nGenerating speech using voice ID: {voice_id}")
            
            # Prepare API endpoint
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            
            # Prepare headers
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Prepare request data
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            # Make API request
            print("Sending request to ElevenLabs API...")
            response = requests.post(url, headers=headers, json=data)
            
            # Check response
            if response.status_code == 200:
                print("Successfully generated speech!")
                return response.content
            else:
                print(f"Error generating speech: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error in text-to-speech: {str(e)}")
            return None
