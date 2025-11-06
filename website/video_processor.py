"""
Video Processing Service for Violation Detection
Processes video files frame-by-frame for traffic violation detection
"""

import cv2
import os
import sys
from typing import List, Dict, Any
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from road_safety_violation_detector.website.detect import ViolationDetector


class VideoProcessor:
    """Process video files for violation detection"""
    
    def __init__(self, frame_skip=30):
        """
        Initialize video processor
        
        Args:
            frame_skip (int): Process every Nth frame (default: 30 = 1fps for 30fps video)
        """
        self.detector = ViolationDetector()
        self.frame_skip = frame_skip
    
    def process_video(self, video_path: str, output_dir: str = None) -> Dict[str, Any]:
        """
        Process video file and detect violations
        
        Args:
            video_path (str): Path to video file
            output_dir (str): Directory to save output frames (optional)
            
        Returns:
            dict: Processing results including violations, frames, and metadata
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_seconds = total_frames / fps if fps > 0 else 0
        
        print(f"📹 Processing video: {os.path.basename(video_path)}")
        print(f"   Resolution: {width}x{height}")
        print(f"   FPS: {fps}")
        print(f"   Duration: {duration_seconds:.1f}s ({total_frames} frames)")
        print(f"   Sampling: Every {self.frame_skip} frames (~{fps/self.frame_skip:.1f} samples/sec)")
        
        # Process frames
        violations_timeline = []
        violation_frames = []
        frames_processed = 0
        total_violations = 0
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Skip frames based on frame_skip setting
            if frame_idx % self.frame_skip != 0:
                frame_idx += 1
                continue
            
            # Calculate timestamp
            timestamp_sec = frame_idx / fps if fps > 0 else frame_idx
            timestamp_str = self._format_timestamp(timestamp_sec)
            
            # Run detection on this frame
            result = self.detector.detect_violations(frame)
            frames_processed += 1
            
            violations = result.get('violations', [])
            if violations:
                total_violations += len(violations)
                
                # Save violation frame info
                violation_info = {
                    'frame_number': frame_idx,
                    'timestamp': timestamp_str,
                    'timestamp_seconds': timestamp_sec,
                    'violations': violations,
                    'counts': result.get('counts', {}),
                    'plate_numbers': result.get('plate_numbers', [])
                }
                violations_timeline.append(violation_info)
                
                # Save annotated frame if output directory specified
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    annotated_frame = result.get('annotated_image')
                    if annotated_frame is not None:
                        frame_filename = f"violation_frame_{frame_idx:06d}_{timestamp_str.replace(':', '-')}.jpg"
                        frame_path = os.path.join(output_dir, frame_filename)
                        cv2.imwrite(frame_path, annotated_frame)
                        violation_info['frame_path'] = frame_path
                        violation_frames.append(frame_path)
            
            frame_idx += 1
        
        cap.release()
        
        # Generate summary
        summary = {
            'video_path': video_path,
            'video_info': {
                'filename': os.path.basename(video_path),
                'resolution': f'{width}x{height}',
                'fps': fps,
                'total_frames': total_frames,
                'duration': duration_seconds
            },
            'processing_info': {
                'frames_analyzed': frames_processed,
                'frame_skip': self.frame_skip,
                'processing_rate': f'{fps/self.frame_skip:.1f} frames/sec'
            },
            'results': {
                'total_violations': total_violations,
                'violation_frames_count': len(violations_timeline),
                'violations_timeline': violations_timeline,
                'violation_frame_paths': violation_frames
            }
        }
        
        print(f"\n✅ Video processing complete!")
        print(f"   Frames analyzed: {frames_processed}")
        print(f"   Violations detected: {total_violations}")
        print(f"   Violation frames: {len(violations_timeline)}")
        
        return summary
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def create_highlight_video(self, video_path: str, violations_timeline: List[Dict], 
                               output_path: str, before_sec: int = 2, after_sec: int = 2):
        """
        Create a highlight video containing only violation moments
        
        Args:
            video_path (str): Original video path
            violations_timeline (list): List of violation moments
            output_path (str): Output video path
            before_sec (int): Seconds before violation to include
            after_sec (int): Seconds after violation to include
        """
        if not violations_timeline:
            print("No violations to create highlights")
            return None
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        for violation in violations_timeline:
            frame_num = violation['frame_number']
            start_frame = max(0, frame_num - before_sec * fps)
            end_frame = frame_num + after_sec * fps
            
            # Seek to start frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            # Write frames
            for _ in range(int(end_frame - start_frame)):
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
        
        cap.release()
        out.release()
        
        print(f"✅ Highlight video saved to: {output_path}")
        return output_path


def process_video_file(video_path: str, output_dir: str = None, frame_skip: int = 30) -> Dict[str, Any]:
    """
    Convenience function to process a video file
    
    Args:
        video_path (str): Path to video file
        output_dir (str): Directory to save output frames
        frame_skip (int): Process every Nth frame
        
    Returns:
        dict: Processing results
    """
    processor = VideoProcessor(frame_skip=frame_skip)
    return processor.process_video(video_path, output_dir)
