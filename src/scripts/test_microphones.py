"""
🎤 Microphone Testing Script
This script helps you identify and test available microphones on your system.
"""

import pyaudio
import wave
import time
from pathlib import Path
from termcolor import cprint

CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5

def list_microphones():
    """List all available audio input devices"""
    p = pyaudio.PyAudio()
    
    cprint("\n🎤 Available Audio Input Devices:", "cyan")
    cprint("-" * 50, "cyan")
    
    input_devices = []
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info.get('maxInputChannels') > 0:  # Only show input devices
            input_devices.append((i, dev_info))
            cprint(f"Device {i}: {dev_info.get('name')}", "yellow")
            cprint(f"    Max Input Channels: {dev_info.get('maxInputChannels')}", "white")
            cprint(f"    Default Sample Rate: {dev_info.get('defaultSampleRate')}", "white")
            cprint("-" * 50, "cyan")
    
    p.terminate()
    return input_devices

def test_microphone(device_index):
    """Test a specific microphone by recording a short audio clip"""
    p = pyaudio.PyAudio()
    
    # Create output directory if it doesn't exist
    output_dir = Path("test_recordings")
    output_dir.mkdir(exist_ok=True)
    
    # Get device info
    dev_info = p.get_device_info_by_index(device_index)
    device_name = dev_info.get('name').replace(' ', '_')
    
    # Output file path
    output_file = output_dir / f"test_recording_{device_index}_{device_name}.wav"
    
    try:
        cprint(f"\n🎙️ Testing device {device_index}: {dev_info.get('name')}", "cyan")
        cprint(f"Recording for {RECORD_SECONDS} seconds...", "yellow")
        
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK
        )
        
        frames = []
        
        # Record audio
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            # Print progress
            if i % 10 == 0:
                cprint(".", "green", end="", flush=True)
        
        cprint("\n✅ Recording completed!", "green")
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Save the recorded audio to a WAV file
        with wave.open(str(output_file), 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        
        cprint(f"📁 Recording saved to: {output_file}", "cyan")
        
    except Exception as e:
        cprint(f"\n❌ Error testing device {device_index}: {str(e)}", "red")
    
    finally:
        p.terminate()

def main():
    """Main function to run the microphone testing script"""
    cprint("\n🎤 Moon Dev's Microphone Testing Script", "cyan")
    cprint("This script will help you test your available microphones\n", "cyan")
    
    # List all available microphones
    input_devices = list_microphones()
    
    if not input_devices:
        cprint("\n❌ No input devices found!", "red")
        return
    
    while True:
        try:
            cprint("\nOptions:", "cyan")
            cprint("1. Test a specific microphone", "yellow")
            cprint("2. List microphones again", "yellow")
            cprint("3. Exit", "yellow")
            
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == "1":
                device_index = input("\nEnter the device number to test: ").strip()
                try:
                    device_index = int(device_index)
                    if device_index < 0 or device_index >= pyaudio.PyAudio().get_device_count():
                        cprint("❌ Invalid device number!", "red")
                        continue
                    test_microphone(device_index)
                except ValueError:
                    cprint("❌ Please enter a valid number!", "red")
            
            elif choice == "2":
                list_microphones()
            
            elif choice == "3":
                cprint("\n👋 Goodbye!", "cyan")
                break
            
            else:
                cprint("❌ Invalid choice! Please enter 1, 2, or 3", "red")
                
        except KeyboardInterrupt:
            cprint("\n\n👋 Goodbye!", "cyan")
            break
        except Exception as e:
            cprint(f"\n❌ An error occurred: {str(e)}", "red")
            break

if __name__ == "__main__":
    main() 