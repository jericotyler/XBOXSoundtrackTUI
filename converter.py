import subprocess
import os

def convert_to_wma(input_path, output_path):
    """
    Converts a given audio file to 128kbps, 44.1kHz, 16-bit WMA using ffmpeg directly.
    """
    try:
        # ffmpeg command: -i input -acodec wmav2 -b:a 128k -ar 44100 -ac 2 output
        command = [
            "ffmpeg", 
            "-y", # overwrite output
            "-i", input_path,
            "-vn", # strip cover art
            "-c:a", "wmav2",
            "-b:a", "128k",
            "-ar", "44100",
            "-ac", "2",
            output_path
        ]
        
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            return False, f"ffmpeg error: {result.stderr}"
            
        # Try to calculate length in milliseconds using ffprobe on the INPUT file
        probe_cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            input_path
        ]
        probe_result = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        try:
            duration_sec = float(probe_result.stdout.strip())
            duration_ms = int(duration_sec * 1000)
        except ValueError:
            duration_ms = 0 # Fallback
            
        return True, duration_ms
        
    except Exception as e:
        return False, str(e)
