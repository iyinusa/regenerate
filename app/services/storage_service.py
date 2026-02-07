"""
Google Cloud Storage service for reGen.
Handles upload, download, and management of video files in GCS.
"""

import os
import logging
from typing import Optional, List
from pathlib import Path
import asyncio

from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

logger = logging.getLogger(__name__)


class GCSStorageService:
    """Service for managing video files in Google Cloud Storage."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize GCS storage service.

        Args:
            bucket_name: Name of the GCS bucket (default from env: GCS_BUCKET_NAME)
            project_id: GCP project ID (default from env: GCP_PROJECT_ID)
            credentials_path: Path to service account JSON (default from env: GOOGLE_APPLICATION_CREDENTIALS)
        """
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME", "regen_videos")
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        
        # Set credentials if provided
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        
        try:
            self.client = storage.Client(project=self.project_id)
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"GCS Storage initialized: bucket={self.bucket_name}, project={self.project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise

    def _get_image_blob_path(self, user_id: str, filename: str) -> str:
        """
        Generate the GCS blob path for an image file.

        Args:
            user_id: User or guest ID
            filename: Name of the image file

        Returns:
            Full blob path in format: images/{user_id}/{filename}
        """
        return f"images/{user_id}/{filename}"

    async def upload_file_object(
        self,
        file_obj,
        user_id: str,
        filename: str,
        content_type: str,
        folder: str = "images",
        make_public: bool = True
    ) -> str:
        """
        Upload a file object (like UploadFile) to GCS.

        Args:
            file_obj: File-like object
            user_id: User or guest ID
            filename: Name of the file
            content_type: MIME type
            folder: folder name in bucket default 'images'
            make_public: Whether to make the file public

        Returns:
            Public URL
        """
        try:
            blob_path = f"{folder}/{user_id}/{filename}"
            blob = self.bucket.blob(blob_path)
            
            # Reset file pointer if needed
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
                
            # Run blocking upload in thread pool
            await asyncio.to_thread(
                blob.upload_from_file,
                file_obj,
                content_type=content_type
            )
            
            if make_public:
                try:
                    await asyncio.to_thread(blob.make_public)
                except Exception as e:
                    logger.warning(f"Could not make blob public (bucket might have uniform access control): {e}")
            
            return blob.public_url

        except Exception as e:
            logger.error(f"Failed to upload file object to GCS: {e}")
            raise GoogleCloudError(f"Upload failed: {str(e)}")

    async def upload_video(
        self,
        local_path: str,
        user_id: str,
        filename: Optional[str] = None,
        content_type: str = "video/mp4",
        make_public: bool = True
    ) -> str:
        """
        Upload a video file to GCS.

        Args:
            local_path: Path to the local video file
            user_id: User or guest ID
            filename: Optional custom filename (defaults to local filename)
            content_type: MIME type of the video
            make_public: Whether to make the video publicly accessible

        Returns:
            Public URL of the uploaded video

        Raises:
            FileNotFoundError: If local file doesn't exist
            GoogleCloudError: If upload fails
        """
        try:
            # Validate local file exists
            local_file = Path(local_path)
            if not local_file.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")

            # Use provided filename or extract from path
            if not filename:
                filename = local_file.name

            # Generate blob path
            blob_path = self._get_blob_path(user_id, filename)
            blob = self.bucket.blob(blob_path)

            # Set content type
            blob.content_type = content_type

            logger.info(f"Uploading {local_path} to gs://{self.bucket_name}/{blob_path}")

            # Upload file in a thread to avoid blocking
            await asyncio.to_thread(
                blob.upload_from_filename,
                str(local_path)
            )

            # Make public if requested
            if make_public:
                await asyncio.to_thread(blob.make_public)

            # Get public URL
            public_url = blob.public_url
            logger.info(f"Video uploaded successfully: {public_url}")

            return public_url

        except GoogleCloudError as e:
            logger.error(f"GCS upload failed for {local_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            raise

    async def download_video(
        self,
        blob_path: str,
        local_path: str
    ) -> str:
        """
        Download a video from GCS to local storage.

        Args:
            blob_path: Full path of blob in GCS (e.g., videos/user123/video.mp4)
            local_path: Local path where file should be saved

        Returns:
            Path to downloaded file

        Raises:
            GoogleCloudError: If download fails
        """
        try:
            blob = self.bucket.blob(blob_path)

            # Create parent directories if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Downloading gs://{self.bucket_name}/{blob_path} to {local_path}")

            await asyncio.to_thread(
                blob.download_to_filename,
                local_path
            )

            logger.info(f"Video downloaded successfully to {local_path}")
            return local_path

        except GoogleCloudError as e:
            logger.error(f"GCS download failed for {blob_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            raise

    async def delete_video(self, user_id: str, filename: str) -> bool:
        """
        Delete a video file from GCS.

        Args:
            user_id: User or guest ID
            filename: Name of the video file to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            blob_path = self._get_blob_path(user_id, filename)
            blob = self.bucket.blob(blob_path)

            logger.info(f"Deleting gs://{self.bucket_name}/{blob_path}")

            await asyncio.to_thread(blob.delete)

            logger.info(f"Video deleted successfully: {blob_path}")
            return True

        except GoogleCloudError as e:
            logger.error(f"Failed to delete {blob_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during deletion: {e}")
            return False

    async def delete_videos(self, user_id: str, filenames: List[str]) -> int:
        """
        Delete multiple video files from GCS.

        Args:
            user_id: User or guest ID
            filenames: List of video filenames to delete

        Returns:
            Number of successfully deleted files
        """
        deleted_count = 0
        for filename in filenames:
            if await self.delete_video(user_id, filename):
                deleted_count += 1

        logger.info(f"Deleted {deleted_count}/{len(filenames)} videos for user {user_id}")
        return deleted_count

    async def delete_file_by_url(self, public_url: str) -> bool:
        """
        Delete a file from GCS using its public URL.

        Args:
            public_url: The full public URL of the file (e.g., https://storage.googleapis.com/bucket/path/file.pdf)

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Extract blob path from public URL
            # URL format: https://storage.googleapis.com/{bucket_name}/{blob_path}
            if not public_url:
                logger.warning("Empty URL provided for deletion")
                return False
            
            # Parse the URL to extract the blob path
            prefix = f"https://storage.googleapis.com/{self.bucket_name}/"
            if not public_url.startswith(prefix):
                logger.warning(f"URL does not match expected bucket format: {public_url}")
                return False
            
            blob_path = public_url[len(prefix):]
            
            if not blob_path:
                logger.warning("Could not extract blob path from URL")
                return False
            
            blob = self.bucket.blob(blob_path)
            
            logger.info(f"Deleting file from GCS: {blob_path}")
            
            await asyncio.to_thread(blob.delete)
            
            logger.info(f"File deleted successfully: {blob_path}")
            return True

        except GoogleCloudError as e:
            logger.error(f"Failed to delete file from URL {public_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during file deletion: {e}")
            return False

    async def list_user_videos(self, user_id: str) -> List[str]:
        """
        List all videos for a specific user.

        Args:
            user_id: User or guest ID

        Returns:
            List of public URLs for user's videos
        """
        try:
            prefix = f"videos/{user_id}/"
            blobs = await asyncio.to_thread(
                list,
                self.client.list_blobs(self.bucket_name, prefix=prefix)
            )

            urls = [blob.public_url for blob in blobs]
            logger.info(f"Found {len(urls)} videos for user {user_id}")
            return urls

        except GoogleCloudError as e:
            logger.error(f"Failed to list videos for user {user_id}: {e}")
            return []

    def get_public_url(self, user_id: str, filename: str) -> str:
        """
        Get the public URL for a video without uploading.

        Args:
            user_id: User or guest ID
            filename: Name of the video file

        Returns:
            Public URL that would be used for this file
        """
        blob_path = self._get_blob_path(user_id, filename)
        return f"https://storage.googleapis.com/{self.bucket_name}/{blob_path}"

    async def video_exists(self, user_id: str, filename: str) -> bool:
        """
        Check if a video exists in GCS.

        Args:
            user_id: User or guest ID
            filename: Name of the video file

        Returns:
            True if video exists, False otherwise
        """
        try:
            blob_path = self._get_blob_path(user_id, filename)
            blob = self.bucket.blob(blob_path)
            exists = await asyncio.to_thread(blob.exists)
            return exists
        except Exception as e:
            logger.error(f"Error checking video existence: {e}")
            return False


# Singleton instance
gcs_storage = GCSStorageService()
