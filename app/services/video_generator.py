import os
import asyncio
import logging
import uuid
import base64
import time
from typing import List, Optional, Tuple, Any
from pathlib import Path

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Try to import moviepy
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False
    logger.warning("moviepy not installed. Video stitching will be disabled.")

class VideoGenerator:
    """Service to handle AI video generation and stitching."""
    
    def __init__(self, output_dir: str = "app/static/videos", base_url: str = "/videos"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = self.output_dir.resolve()
        self.base_url = base_url
        
    async def test_client_connection(self, client: genai.Client) -> bool:
        """Test if the Gemini client is properly connected and can make basic calls."""
        try:
            logger.info("Testing Gemini client connection...")
            
            # Try a simple text generation call first
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=["Hello, this is a test."]
            )
            
            if response and response.text:
                logger.info("Gemini client connection test successful")
                logger.info(f"Test response: {response.text[:100]}...")
                return True
            else:
                logger.error("Gemini client test failed - no response")
                return False
                
        except Exception as e:
            logger.error(f"Gemini client connection test failed: {e}")
            return False
    
    async def generate_segment(
        self, 
        client: genai.Client, 
        prompt: str, 
        duration_seconds: int = 8,
        aspect_ratio: str = "16:9",
        resolution: str = "1080p",
        video_reference: Optional[Any] = None
    ) -> Tuple[str, Any]:
        """
        Generate a single video segment using Gemini Veo.
        Returns tuple of (filename, video_object) for continuity.
        """
        try:
            logger.info(f"Generating video segment ({duration_seconds}s) with prompt: {prompt[:100]}...")
            logger.info(f"Video reference provided: {video_reference is not None}")
            logger.info(f"Config: duration={duration_seconds}s, resolution={resolution}, aspect_ratio={aspect_ratio}")
            
            # Using correct Veo model as per requirements
            model_name = "veo-3.1-fast-generate-preview"
            
            # Configure generation settings with proper validation
            logger.info(f"Creating video config with: duration={duration_seconds}, resolution={resolution}, aspect_ratio={aspect_ratio}")
            
            # Ensure parameters are valid for Veo
            valid_resolutions = ["720p", "1080p", "4k"]  
            valid_aspect_ratios = ["16:9", "9:16"]
            
            if resolution not in valid_resolutions:
                resolution = "1080p"
                logger.warning(f"Invalid resolution, defaulting to {resolution}")
            
            if aspect_ratio not in valid_aspect_ratios:
                aspect_ratio = "16:9" 
                logger.warning(f"Invalid aspect ratio, defaulting to {aspect_ratio}")
                
            if duration_seconds < 1 or duration_seconds > 10:
                duration_seconds = 8
                logger.warning(f"Invalid duration, defaulting to {duration_seconds}s")
            
            config = types.GenerateVideosConfig(
                duration_seconds=duration_seconds,
                resolution=resolution,
                aspect_ratio=aspect_ratio
            )
            
            # Handle video reference and optimize prompt for Veo
            original_prompt = prompt
            if video_reference:
                prompt = f"[Continue from previous scene] {prompt}"
                logger.info(f"Added continuity prompt prefix")
            
            # Optimize prompt for Veo (max ~500 characters recommended)
            if len(prompt) > 500:
                prompt = prompt[:497] + "..."
                logger.info(f"Truncated prompt from {len(original_prompt)} to {len(prompt)} characters")
            
            logger.info(f"Final prompt: {prompt}")
            
            # Call Gemini API to generate video
            logger.info(f"Calling Gemini API with model: {model_name}")
            logger.info(f"Prompt length: {len(prompt)} characters")
            logger.info(f"Config: duration={duration_seconds}s, resolution={resolution}, aspect_ratio={aspect_ratio}")
            
            # Make single API call - no retries to avoid rate limits
            logger.info("Calling Gemini Veo API...")
            operation = await asyncio.to_thread(
                client.models.generate_videos,
                model=model_name,
                prompt=prompt,
                config=config
            )
            logger.info("Video generation API call succeeded")
                
            logger.info(f"Operation started: {operation.name}, done: {operation.done}")
            
            # Poll the operation status until the video is ready
            # Following Gemini Veo API documentation exactly
            poll_count = 0
            max_polls = 60  # 10 minutes max (60 polls × 10 seconds)
            while not operation.done and poll_count < max_polls:
                logger.info("Waiting for video generation to complete...")
                await asyncio.sleep(10)
                # Pass the operation object itself, not operation.name
                operation = await asyncio.to_thread(
                    client.operations.get,
                    operation
                )
                poll_count += 1
                if poll_count % 6 == 0:  # Log every minute
                    logger.info(f"Still generating... ({poll_count * 10}s elapsed)")
            
            if not operation.done:
                raise TimeoutError(f"Video generation timed out after {max_polls * 10} seconds")
            
            # Get the generated video
            if not operation.response or not operation.response.generated_videos:
                raise ValueError("No video generated from Gemini API")
                
            generated_video = operation.response.generated_videos[0]
            logger.info(f"Generated video received: {type(generated_video)}")
            
            # Save to file
            filename = f"segment_{uuid.uuid4().hex[:8]}.mp4"
            filepath = self.output_dir / filename
            
            # Download and save the video following Gemini Veo API documentation
            try:
                # Download the file from Gemini
                logger.info(f"Downloading video file...")
                video_file = generated_video.video
                
                # Use client.files.download to get the actual video data
                await asyncio.to_thread(
                    client.files.download,
                    file=video_file
                )
                
                # Save the video to the specified filepath
                await asyncio.to_thread(
                    video_file.save,
                    str(filepath)
                )
                
                logger.info(f"Video segment saved to {filepath}")
                
                # Verify the file was created and has content
                if not filepath.exists():
                    raise FileNotFoundError(f"Video file was not created at {filepath}")
                    
                file_size = filepath.stat().st_size
                if file_size == 0:
                    raise ValueError(f"Video file is empty at {filepath}")
                    
                logger.info(f"Video file verified: {file_size} bytes")
                
                # Return filename and the video object for continuity reference
                return filename, video_file
                
            except Exception as save_error:
                logger.error(f"Failed to download/save video: {save_error}")
                logger.error(f"Generated video type: {type(generated_video)}")
                if hasattr(generated_video, 'video'):
                    logger.error(f"Video file type: {type(generated_video.video)}")
                raise
            
        except Exception as e:
            logger.error(f"Failed to generate video segment: {e}")
            raise

    def merge_videos(self, file_list: List[str], output_name: str = None) -> str:
        """
        Merge multiple video segments into one final video.
        Follows the exact implementation pattern from requirements.
        """
        if not HAS_MOVIEPY:
            raise ImportError("moviepy is not installed/working")
            
        if not output_name:
            output_name = f"final_{len(file_list) * 8}s_video.mp4"
            
        output_path = self.output_dir / output_name
        
        # Get full paths for inputs
        input_paths = [str(self.output_dir / fname) for fname in file_list]
        
        # Validate existence
        valid_paths = [p for p in input_paths if os.path.exists(p)]
        if len(valid_paths) != len(input_paths):
            logger.warning(f"Some video segments are missing. Merging only {len(valid_paths)} of {len(input_paths)}.")
        
        if not valid_paths:
            raise FileNotFoundError("No valid video segments to merge")
            
        try:
            logger.info(f"Merging {len(valid_paths)} videos...")
            
            # MoviePy processing as per requirements sample
            clips = [VideoFileClip(path) for path in valid_paths]
            
            # This joins them end-to-end
            final_clip = concatenate_videoclips(clips, method="compose")
            
            final_clip.write_videofile(
                str(output_path), 
                codec="libx264", 
                audio_codec="aac"
            )
            
            # Close clips to free up memory
            for clip in clips:
                clip.close()
            final_clip.close()
            
            logger.info(f"Merged video saved to {output_path}")
            return output_name
            
        except Exception as e:
            logger.error(f"Failed to merge videos: {e}")
            raise
    
    async def stitch_videos(self, video_filenames: List[str], output_filename: str = None) -> str:
        """
        Async wrapper for merge_videos to maintain backward compatibility.
        """
        return await asyncio.to_thread(
            self.merge_videos,
            video_filenames,
            output_filename
        )

    def get_url(self, filename: str) -> str:
        """Get the accessible URL for a video filename."""
        return f"{self.base_url}/{filename}"
    
    def create_user_video_folder(self, user_id: str) -> Path:
        """Create user-specific folder for video storage."""
        user_folder = self.output_dir / f"user_{user_id}"
        user_folder.mkdir(parents=True, exist_ok=True)
        return user_folder

# Singleton instance
video_generator = VideoGenerator()
