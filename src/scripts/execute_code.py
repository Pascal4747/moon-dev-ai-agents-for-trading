"""
🚀 Moon Dev's Code Executor
Moves to position, executes code, and captures screenshot

2/1- stuck here - working on execute_code.py trying to get the click to work, it currently moves the mouse to the right position, but doesnt click. the goal is to get it to click on that poistion of the screen which is my code editor, then it can use my code running short cut in order to run the code... then it can screenshot the error or the successful output and then send to another ai in order to fix it. this allows for an infinite loop of ai to be working on my code
"""

import pyautogui
import time
from pathlib import Path
from termcolor import cprint
from datetime import datetime
import Quartz
import sys
import os
from Quartz import CoreGraphics as CG
import AppKit
import subprocess

# Configuration - Moon Dev's target coordinates (DO NOT ADJUST THESE)
TARGET_X = -2686
TARGET_Y = -1144

# AI Debug coordinates
DEBUG_X = -1487
DEBUG_Y = -251

# Easily configurable settings
SCREENSHOT_WIDTH = 1500    # Width in pixels
SCREENSHOT_HEIGHT = 2200   # Height in pixels
CLICK_PAUSE = 2.0         # Pause after movement before clicking
ACTIVATION_PAUSE = 1.0    # Pause after click to ensure window activation
EXECUTE_PAUSE = 5.0       # Pause after cmd+return before screenshot
MOVEMENT_SPEED = 1.0      # Speed of cursor movement (seconds)

def get_display_bounds():
    """Get all display bounds including negative coordinates"""
    try:
        # Create array for display IDs
        max_displays = 32
        display_count = CG.CGGetActiveDisplayList(max_displays, None, None)[1]
        active_displays = CG.CGGetActiveDisplayList(display_count, None, None)[0]
        
        displays = []
        for display in active_displays:
            bounds = CG.CGDisplayBounds(display)
            displays.append({
                'id': display,
                'x': bounds.origin.x,
                'y': bounds.origin.y,
                'width': bounds.size.width,
                'height': bounds.size.height
            })
            
        return displays
    except Exception as e:
        cprint(f"❌ Error getting displays: {e}", "red")
        return []

def move_mouse_cg(x, y, debug=True):
    """Move mouse using CoreGraphics with display bounds checking"""
    try:
        if debug:
            displays = get_display_bounds()
            cprint("\n🖥️ Display Information:", "cyan")
            for i, display in enumerate(displays, 1):
                cprint(f"  ├─ Display {i}: Origin({display['x']}, {display['y']}) Size({display['width']}x{display['height']})", "cyan")
        
        # Get current position for verification
        current = CG.CGEventGetLocation(CG.CGEventCreate(None))
        cprint(f"\n📍 Starting position: ({int(current.x)}, {int(current.y)})", "yellow")
        
         # Create smooth movement
        steps = 20
        start_x, start_y = current.x, current.y
        
        for i in range(steps + 1):
            # Calculate intermediate position
            current_x = start_x + (x - start_x) * i / steps
            current_y = start_y + (y - start_y) * i / steps
            
            # Create point for movement
            point = CG.CGPoint(current_x, current_y)
            
            # Move cursor
            CG.CGWarpMouseCursorPosition(point)
            
            # Small pause between movements
            time.sleep(MOVEMENT_SPEED / steps)
            
            if debug and i % 5 == 0:
                pos = CG.CGEventGetLocation(CG.CGEventCreate(None))
                cprint(f"  ├─ Step {i}: Moving to ({int(current_x)}, {int(current_y)}) At: ({int(pos.x)}, {int(pos.y)})", "cyan")
        
        # Final position check
        final_pos = CG.CGEventGetLocation(CG.CGEventCreate(None))
        cprint(f"📍 Final position: ({int(final_pos.x)}, {int(final_pos.y)})", "yellow")
        
        # Create and post a mouse moved event
        point = CG.CGPoint(x, y)
        event = CG.CGEventCreateMouseEvent(None, CG.kCGEventMouseMoved, point, CG.kCGMouseButtonLeft)
        CG.CGEventPost(CG.kCGHIDEventTap, event)
        
        success = abs(final_pos.x - x) <= 10 and abs(final_pos.y - y) <= 10
        if not success:
            cprint(f"⚠️ Warning: Expected ({x}, {y}) but got ({int(final_pos.x)}, {int(final_pos.y)})", "yellow")
        
        return success
        
    except Exception as e:
        cprint(f"❌ Error moving mouse: {e}", "red")
        return False

def activate_vscode():
    """Activate VSCode application"""
    try:
        # Get VSCode app
        workspace = AppKit.NSWorkspace.sharedWorkspace()
        apps = workspace.runningApplications()
        
        # Find VSCode
        vscode_app = None
        for app in apps:
            if 'Code' in app.localizedName():
                vscode_app = app
                break
        
        if vscode_app:
            cprint("\n🎯 Found VSCode, activating...", "cyan")
            vscode_app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
            time.sleep(0.5)  # Wait for activation
            return True
        else:
            cprint("❌ VSCode not found running!", "red")
            return False
            
    except Exception as e:
        cprint(f"❌ Error activating VSCode: {e}", "red")
        return False

def simple_click(double_click=True):
    """Simple click at current position with optional double-click using pyautogui"""
    try:
        # Get current position for logging
        pos = CG.CGEventGetLocation(CG.CGEventCreate(None))
        cprint(f"🖱️ {'Double' if double_click else 'Single'} clicking at: ({int(pos.x)}, {int(pos.y)})", "cyan")
        
        # Use pyautogui for clicking
        time.sleep(0.8)  # Pause before clicking
        
        if double_click:
            pyautogui.click(clicks=2, interval=0.3)  # Double click with 0.3s between clicks
        else:
            pyautogui.click()
            
        time.sleep(0.8)  # Pause after clicking
        
        return True
        
    except Exception as e:
        cprint(f"❌ Error clicking: {e}", "red")
        return False

def setup_directories():
    """Setup necessary directories"""
    data_dir = Path("src/data/code_runner")
    screenshot_dir = data_dir / "screenshots"
    data_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    return screenshot_dir

def click_with_applescript():
    """Use AppleScript to click and activate window"""
    try:
        # AppleScript to click and activate
        script = '''
        tell application "System Events"
            set currentPosition to {%d, %d}
            click at currentPosition
            delay 0.3
            click at currentPosition
            delay 0.3
            click at currentPosition
        end tell
        ''' % (TARGET_X, TARGET_Y)
        
        cprint("🍎 Using AppleScript for clicking...", "cyan")
        subprocess.run(['osascript', '-e', script], capture_output=True)
        return True
    except Exception as e:
        cprint(f"❌ Error with AppleScript click: {e}", "red")
        return False

def quick_click():
    """Quick and direct click using CoreGraphics"""
    try:
        # First try CoreGraphics click
        cprint("🖱️ Attempting click...", "cyan")
        
        # Get current position
        pos = CG.CGEventGetLocation(CG.CGEventCreate(None))
        
        # Create and post mouse events
        mouse_down = CG.CGEventCreateMouseEvent(None, CG.kCGEventLeftMouseDown, pos, CG.kCGMouseButtonLeft)
        mouse_up = CG.CGEventCreateMouseEvent(None, CG.kCGEventLeftMouseUp, pos, CG.kCGMouseButtonLeft)
        
        # Click with proper timing
        time.sleep(0.3)  # Small pause before
        CG.CGEventPost(CG.kCGHIDEventTap, mouse_down)
        time.sleep(0.2)  # Hold the click
        CG.CGEventPost(CG.kCGHIDEventTap, mouse_up)
        time.sleep(0.3)  # Pause after
        
        return True
    except Exception as e:
        cprint(f"❌ Error clicking: {e}", "red")
        return False

def send_command_return():
    """Send Command+Return using CoreGraphics events"""
    try:
        # Create Command key down event
        cmd_down = CG.CGEventCreateKeyboardEvent(None, 0x37, True)  # 0x37 is Command
        CG.CGEventPost(CG.kCGHIDEventTap, cmd_down)
        time.sleep(0.1)
        
        # Create Return key down/up events
        return_down = CG.CGEventCreateKeyboardEvent(None, 0x24, True)  # 0x24 is Return
        return_up = CG.CGEventCreateKeyboardEvent(None, 0x24, False)
        
        # Set command flag
        CG.CGEventSetFlags(return_down, CG.kCGEventFlagMaskCommand)
        CG.CGEventSetFlags(return_up, CG.kCGEventFlagMaskCommand)
        
        # Post events
        CG.CGEventPost(CG.kCGHIDEventTap, return_down)
        time.sleep(0.1)
        CG.CGEventPost(CG.kCGHIDEventTap, return_up)
        time.sleep(0.1)
        
        # Release Command key
        cmd_up = CG.CGEventCreateKeyboardEvent(None, 0x37, False)
        CG.CGEventPost(CG.kCGHIDEventTap, cmd_up)
        
        return True
    except Exception as e:
        cprint(f"❌ Error sending cmd+return: {e}", "red")
        return False

def send_keys(text):
    """Send keyboard input using pyautogui"""
    try:
        # Type the text character by character
        for char in text:
            if char == '@':
                # On Mac, @ is Shift+2
                pyautogui.keyDown('shift')
                pyautogui.press('2')
                pyautogui.keyUp('shift')
            else:
                pyautogui.write(char)
            time.sleep(0.2)  # Small delay between characters
            
        return True
    except Exception as e:
        cprint(f"❌ Error sending keys: {e}", "red")
        return False

def send_enter():
    """Send Enter key press"""
    try:
        # Create Return key events
        return_down = CG.CGEventCreateKeyboardEvent(None, 0x24, True)  # 0x24 is Return
        return_up = CG.CGEventCreateKeyboardEvent(None, 0x24, False)
        
        # Post events
        CG.CGEventPost(CG.kCGHIDEventTap, return_down)
        time.sleep(0.1)
        CG.CGEventPost(CG.kCGHIDEventTap, return_up)
        
        return True
    except Exception as e:
        cprint(f"❌ Error sending enter: {e}", "red")
        return False

def submit_to_ai_debug(number):
    """Submit screenshot to AI debug location"""
    try:
        # First verify the screenshot exists
        screenshot_path = Path("src/data/code_runner/screenshots") / f"{number}.png"
        if not screenshot_path.exists():
            cprint(f"❌ Cannot find screenshot: {screenshot_path}", "red")
            return False
            
        cprint("\n🤖 Starting AI Debug Submission...", "cyan")
        cprint(f"📎 Will reference screenshot: {screenshot_path}", "cyan")
        
        # List all screenshots to help debug
        screenshot_dir = Path("src/data/code_runner/screenshots")
        cprint("\n📁 Available screenshots:", "cyan")
        for png in screenshot_dir.glob("*.png"):
            cprint(f"  ├─ {png.name}", "cyan")
        
        # Move to debug coordinates
        cprint(f"\n🖱️ Moving to AI debug position ({DEBUG_X}, {DEBUG_Y})", "cyan")
        if not move_mouse_cg(DEBUG_X, DEBUG_Y):
            cprint("❌ Failed to move to debug position!", "red")
            return False
            
        # Click to activate
        cprint("\n🖱️ Clicking to activate debug input...", "cyan")
        time.sleep(0.5)
        if not quick_click():
            cprint("❌ Failed to click debug input!", "red")
            return False
            
        time.sleep(0.5)
        
        # Type the @ and number, then pause for debugging
        cprint(f"\n⌨️ Typing @{number}...", "cyan")
        if not send_keys(f"@{number}"):
            cprint("❌ Failed to type screenshot reference!", "red")
            return False
            
        # Long pause for debugging
        cprint("\n⏳ Pausing for 60 seconds for debugging...", "yellow")
        cprint(f"👉 Please check if @{number} matches {screenshot_path.name}", "yellow")
        time.sleep(60)
        
        return True
        
    except Exception as e:
        cprint(f"\n❌ Error in AI debug submission: {str(e)}", "red")
        return False

def execute_and_capture():
    """Move to position, execute code, and capture screenshot"""
    try:
        cprint("\n🎯 Moon Dev's Code Executor Starting...", "cyan")
        
        # Generate screenshot name first
        screenshot_dir = setup_directories()
        while True:
            random_number = str(int.from_bytes(os.urandom(3), byteorder='big') % 90000 + 10000)
            screenshot_name = f"{random_number}.png"
            screenshot_path = screenshot_dir / screenshot_name
            if not screenshot_path.exists():
                break
        
        cprint(f"🎫 Will save screenshot as: {random_number}.png", "cyan")
        cprint(f"📸 Screenshot size: {SCREENSHOT_WIDTH}x{SCREENSHOT_HEIGHT} pixels", "cyan")
        
        # Print target info
        cprint("\n🎯 Target Information:", "cyan")
        cprint(f"  ├─ Target Position: ({TARGET_X}, {TARGET_Y})", "cyan")
        current = CG.CGEventGetLocation(CG.CGEventCreate(None))
        cprint(f"  └─ Current Mouse: ({int(current.x)}, {int(current.y)})", "cyan")
        
        # Store initial position
        initial_pos = CG.CGEventGetLocation(CG.CGEventCreate(None))
        
        # Setup countdown
        cprint("\n🚀 Moving to target position in:", "yellow")
        for i in range(3, 0, -1):
            cprint(f"{i}...", "yellow")
            time.sleep(1)
            
        # Move to target position using CoreGraphics
        cprint(f"\n🖱️ Moving to ({TARGET_X}, {TARGET_Y})", "cyan")
        if not move_mouse_cg(TARGET_X, TARGET_Y):
            cprint("❌ Failed to move to target position!", "red")
            return False
            
        # Quick pause then single click
        cprint(f"\n⏳ Quick pause before clicking...", "yellow")
        time.sleep(0.5)
        
        # One solid click
        if not quick_click():
            cprint("❌ Failed to click!", "red")
            return False
        
        # Wait for activation
        cprint(f"\n⏳ Waiting for window activation...", "yellow")
        time.sleep(1.0)
        
        # Send Command+Return using CoreGraphics
        cprint("\n⌨️ Pressing cmd+return...", "cyan")
        if not send_command_return():
            cprint("❌ Failed to send cmd+return!", "red")
            return False
        
        # Wait before screenshot
        cprint(f"\n⏳ Waiting {EXECUTE_PAUSE} seconds for execution...", "yellow")
        time.sleep(EXECUTE_PAUSE)
        
        # Take screenshot with pre-generated name
        cprint("\n📸 Taking screenshot...", "cyan")
        left = TARGET_X - SCREENSHOT_WIDTH//2
        top = TARGET_Y - SCREENSHOT_HEIGHT//2
        screenshot = pyautogui.screenshot(region=(left, top, SCREENSHOT_WIDTH, SCREENSHOT_HEIGHT))
        screenshot.save(screenshot_path)
        
        # Verify the file was saved
        if not screenshot_path.exists():
            cprint("❌ Failed to save screenshot!", "red")
            return False
            
        cprint(f"✅ Screenshot saved as: {random_number}.png", "green")
        cprint(f"📍 Screenshot location: {screenshot_path}", "cyan")
        
        # Double check file exists before submitting
        if not screenshot_path.exists():
            cprint("❌ Screenshot file not found!", "red")
            return False
            
        # Now submit to AI debug
        if not submit_to_ai_debug(random_number):
            cprint("❌ Failed to submit to AI debug!", "red")
        
        # Return to initial position using CoreGraphics
        cprint("\n🔄 Returning to initial position...", "cyan")
        move_mouse_cg(int(initial_pos.x), int(initial_pos.y))
        
        cprint("\n✨ Moon Dev's Code Executor completed successfully!", "green")
        
    except Exception as e:
        cprint(f"\n❌ Error: {str(e)}", "red")
        cprint("🔄 Attempting to return to initial position...", "yellow")
        try:
            move_mouse_cg(int(initial_pos.x), int(initial_pos.y))
        except:
            pass

if __name__ == "__main__":
    try:
        # Check if pyobjc-framework-Quartz is installed
        try:
            import Quartz
        except ImportError:
            cprint("\n❌ Quartz framework not found. Installing required package...", "yellow")
            os.system("pip install pyobjc-framework-Quartz")
            cprint("✅ Installation complete. Please run the script again.", "green")
            sys.exit(1)
            
        execute_and_capture()
    except KeyboardInterrupt:
        cprint("\n👋 Execution cancelled by user", "yellow")
    except Exception as e:
        cprint(f"\n❌ Fatal error: {str(e)}", "red")