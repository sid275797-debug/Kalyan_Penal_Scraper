#!/usr/bin/env python3
# matka_video_generator_working.py
# WORKING VERSION - Finds the correct JSON file

import os, re, json, datetime, subprocess, tempfile, shutil, time, sys
from PIL import Image, ImageDraw, ImageFont

# =============== CONFIGURATION ===============
BASE_DIR = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper"
OUT_ROOT = os.path.join(BASE_DIR, "video_output")

# Video Specifications
W, H = 1080, 1920
FPS = 30
VIDEO_DURATION = 8

# Colors
BG_COLOR = (10, 15, 30)
TEXT_WHITE = (255, 255, 255)
TEXT_GRAY = (180, 185, 200)
ACCENT_CYAN = (0, 200, 255)
ACCENT_GREEN = (0, 255, 150)
ACCENT_YELLOW = (255, 215, 0)

# =============== FIND CORRECT JSON FILE ===============
def find_predictions_json():
    """Find the correct JSON file with today's predictions"""
    output_dir = os.path.join(BASE_DIR, "output")
    
    if not os.path.exists(output_dir):
        print(f"❌ Output directory not found: {output_dir}")
        return None
    
    # List all JSON files
    json_files = []
    for file in os.listdir(output_dir):
        if file.lower().endswith('.json'):
            json_files.append(file)
    
    if not json_files:
        print("❌ No JSON files found in output directory")
        return None
    
    print(f"📁 Found {len(json_files)} JSON files:")
    for file in json_files[:10]:  # Show first 10
        print(f"   • {file}")
    
    # Priority: look for files with "prediction" or "today" in name
    priority_files = []
    other_files = []
    
    for file in json_files:
        lower_file = file.lower()
        if 'prediction' in lower_file or 'today' in lower_file:
            priority_files.append(file)
        else:
            other_files.append(file)
    
    # Sort priority files by modification time (newest first)
    if priority_files:
        priority_files.sort(key=lambda f: os.path.getmtime(os.path.join(output_dir, f)), reverse=True)
        selected = priority_files[0]
        print(f"📄 Using priority file: {selected}")
        return os.path.join(output_dir, selected)
    
    # Sort other files by modification time (newest first)
    if other_files:
        # Exclude history files
        non_history = [f for f in other_files if 'history' not in f.lower()]
        if non_history:
            non_history.sort(key=lambda f: os.path.getmtime(os.path.join(output_dir, f)), reverse=True)
            selected = non_history[0]
            print(f"📄 Using newest non-history file: {selected}")
            return os.path.join(output_dir, selected)
        else:
            # If only history files, use the newest one
            other_files.sort(key=lambda f: os.path.getmtime(os.path.join(output_dir, f)), reverse=True)
            selected = other_files[0]
            print(f"📄 Using newest file (even if history): {selected}")
            return os.path.join(output_dir, selected)
    
    return None

def load_market_data():
    """Load market predictions from the correct JSON file"""
    json_path = find_predictions_json()
    
    if not json_path:
        print("❌ Could not find a suitable JSON file")
        return []
    
    try:
        print(f"📖 Loading data from: {os.path.basename(json_path)}")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Show JSON structure for debugging
        print(f"📊 JSON structure type: {type(data)}")
        if isinstance(data, dict):
            print(f"📊 JSON keys: {list(data.keys())[:10]}...")
        
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return []
    
    markets = []
    
    # Try different JSON structures
    if isinstance(data, dict):
        # Try to find markets list
        if 'markets' in data and isinstance(data['markets'], list):
            print(f"✅ Found 'markets' list with {len(data['markets'])} items")
            items = data['markets']
        elif 'data' in data and isinstance(data['data'], list):
            print(f"✅ Found 'data' list with {len(data['data'])} items")
            items = data['data']
        elif 'predictions' in data and isinstance(data['predictions'], list):
            print(f"✅ Found 'predictions' list with {len(data['predictions'])} items")
            items = data['predictions']
        else:
            # Try to find any list in the dictionary
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    print(f"✅ Found list in key '{key}' with {len(value)} items")
                    items = value
                    break
            else:
                print("❌ No list found in JSON dictionary")
                return []
    elif isinstance(data, list):
        print(f"✅ JSON is a list with {len(data)} items")
        items = data
    else:
        print("❌ JSON is neither dict nor list")
        return []
    
    # Process each market
    processed_count = 0
    for i, item in enumerate(items[:100]):  # Limit to 100 for testing
        if not isinstance(item, dict):
            continue
        
        # Try to get market name
        market_name = item.get('market') or item.get('market_name') or item.get('name') or f"Market_{i+1}"
        
        # Try to get predictions
        predictions = item
        if 'predictions' in item and isinstance(item['predictions'], dict):
            predictions = item['predictions']
        
        # Extract data with fallbacks
        market_data = {
            'name': str(market_name),
            'open_digits': extract_field(predictions, ['open_digits', 'open_digit', 'openDigits', 'open']),
            'close_digits': extract_field(predictions, ['close_digits', 'close_digit', 'closeDigits', 'close']),
            'jodis': extract_jodis(predictions),
            'open_pannas': extract_pannas(predictions, 'open'),
            'close_pannas': extract_pannas(predictions, 'close')
        }
        
        markets.append(market_data)
        processed_count += 1
        
        # Show first few for debugging
        if processed_count <= 3:
            print(f"   Sample market {processed_count}: {market_data['name']}")
    
    print(f"✅ Processed {processed_count} markets from JSON")
    
    # If we got 0 markets, try a different approach
    if processed_count == 0 and isinstance(data, dict):
        print("⚠️ No markets found with standard parsing, trying alternative...")
        # Try to parse the entire JSON as a single market
        market_data = {
            'name': data.get('market', 'Daily Predictions'),
            'open_digits': extract_field(data, ['open_digits', 'open_digit', 'openDigits', 'open']),
            'close_digits': extract_field(data, ['close_digits', 'close_digit', 'closeDigits', 'close']),
            'jodis': extract_jodis(data),
            'open_pannas': extract_pannas(data, 'open'),
            'close_pannas': extract_pannas(data, 'close')
        }
        markets.append(market_data)
        print(f"✅ Created single market from root JSON")
    
    return markets

def extract_field(data, field_names):
    """Extract field from data with multiple possible names"""
    for field in field_names:
        if field in data:
            value = data[field]
            if isinstance(value, list):
                return [str(x) for x in value[:4]]
            elif isinstance(value, str):
                # Extract digits from string
                digits = re.findall(r'\d', value)
                return digits[:4]
            elif value is not None:
                return list(str(value))[:4]
    return ['0', '1', '2', '3']  # Default

def extract_jodis(data):
    """Extract jodis from data"""
    for field in ['jodis', 'jodi', 'Jodis', 'Jodi']:
        if field in data:
            value = data[field]
            if isinstance(value, list):
                return [str(x).zfill(2) for x in value[:6]]
            elif isinstance(value, str):
                # Extract 2-digit numbers
                jodis = re.findall(r'\d{2}', value)
                return jodis[:6]
    return ['00', '11', '22', '33', '44', '55']  # Default

def extract_pannas(data, prefix):
    """Extract pannas from data"""
    for field in [f'{prefix}_pannas', f'{prefix}_panna', f'{prefix}Pannas', f'{prefix}Panna']:
        if field in data:
            value = data[field]
            if isinstance(value, list):
                return [str(x).zfill(3) for x in value[:3]]
            elif isinstance(value, str):
                # Extract 3-digit numbers
                pannas = re.findall(r'\d{3}', value)
                return pannas[:3]
    return ['000', '111', '222']  # Default

# =============== HELPER FUNCTIONS ===============
def ensure_dir(path):
    """Ensure directory exists"""
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def get_font(size, bold=False):
    """Get font - simple"""
    try:
        if bold:
            return ImageFont.truetype("arialbd.ttf", size)
        else:
            return ImageFont.truetype("arial.ttf", size)
    except:
        # Ultimate fallback
        return ImageFont.load_default()

def clean_text(text):
    """Clean text for display"""
    if not text:
        return "MARKET"
    text = str(text)
    # Remove panel/penal/chart and clean up
    text = re.sub(r'(?i)\b(panel|penal|chart)\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return "MARKET"
    return text.upper()

# =============== IMAGE CREATION ===============
def create_slide(market, date_str):
    """Create slide for a market"""
    img = Image.new('RGB', (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    y = 150
    
    # Market name
    font = get_font(70, True)
    name = clean_text(market['name'])
    text_width = draw.textbbox((0, 0), name, font=font)[2]
    draw.text(((W - text_width) // 2, y), name, font=font, fill=ACCENT_CYAN)
    y += 120
    
    # Date
    date_font = get_font(40, False)
    date_text = f"DATE: {date_str}"
    date_width = draw.textbbox((0, 0), date_text, font=date_font)[2]
    draw.text(((W - date_width) // 2, y), date_text, font=date_font, fill=TEXT_GRAY)
    y += 100
    
    # OPEN
    y = add_digits(draw, y, "OPEN", market['open_digits'], ACCENT_GREEN)
    y += 40
    
    # CLOSE
    y = add_digits(draw, y, "CLOSE", market['close_digits'], ACCENT_YELLOW)
    y += 60
    
    # JODI
    y = add_jodi(draw, y, market['jodis'])
    y += 50
    
    # PANNA
    add_panna(draw, y, market['open_pannas'], market['close_pannas'])
    
    return img

def add_digits(draw, y, label, digits, color):
    """Add digits section"""
    font = get_font(45, True)
    text_width = draw.textbbox((0, 0), label, font=font)[2]
    draw.text(((W - text_width) // 2, y), label, font=font, fill=color)
    y += 70
    
    digit_font = get_font(140, True)
    digit_text = "  ".join(digits[:4])
    digit_width = draw.textbbox((0, 0), digit_text, font=digit_font)[2]
    draw.text(((W - digit_width) // 2, y), digit_text, font=digit_font, fill=TEXT_WHITE)
    
    return y + 150

def add_jodi(draw, y, jodis):
    """Add jodi section"""
    font = get_font(45, True)
    label = "JODI PREDICTIONS"
    text_width = draw.textbbox((0, 0), label, font=font)[2]
    draw.text(((W - text_width) // 2, y), label, font=font, fill=ACCENT_CYAN)
    y += 70
    
    jodi_font = get_font(50, True)
    chip_w = 100
    chip_h = 70
    spacing = 15
    
    total_w = len(jodis) * chip_w + (len(jodis) - 1) * spacing
    start_x = (W - total_w) // 2
    
    for i, jodi in enumerate(jodis[:6]):
        x = start_x + i * (chip_w + spacing)
        
        # Simple rectangle
        draw.rectangle([x, y, x + chip_w, y + chip_h], fill=(30, 35, 55), outline=ACCENT_CYAN, width=2)
        
        # Jodi text
        text_width = draw.textbbox((0, 0), jodi, font=jodi_font)[2]
        text_x = x + (chip_w - text_width) // 2
        text_y = y + (chip_h - 50) // 2
        draw.text((text_x, text_y), jodi, font=jodi_font, fill=TEXT_WHITE)
    
    return y + chip_h + 30

def add_panna(draw, y, open_pannas, close_pannas):
    """Add panna section"""
    # Simple card
    card_w = 900
    card_h = 280
    card_x = (W - card_w) // 2
    
    draw.rectangle([card_x, y, card_x + card_w, y + card_h], fill=(25, 30, 50), outline=ACCENT_CYAN, width=2)
    
    # Titles
    title_font = get_font(38, True)
    title_y = y + 20
    
    open_title = "OPEN PANNA"
    open_width = draw.textbbox((0, 0), open_title, font=title_font)[2]
    draw.text((card_x + (card_w // 4) - open_width // 2, title_y), open_title, font=title_font, fill=ACCENT_GREEN)
    
    close_title = "CLOSE PANNA"
    close_width = draw.textbbox((0, 0), close_title, font=title_font)[2]
    draw.text((card_x + 3 * (card_w // 4) - close_width // 2, title_y), close_title, font=title_font, fill=ACCENT_YELLOW)
    
    # Items
    item_font = get_font(42, False)
    item_y = title_y + 60
    
    for i in range(3):
        # Open panna
        if i < len(open_pannas):
            panna = open_pannas[i]
            text_width = draw.textbbox((0, 0), panna, font=item_font)[2]
            draw.text((card_x + (card_w // 4) - text_width // 2, item_y + i * 60), panna, font=item_font, fill=TEXT_WHITE)
        
        # Close panna
        if i < len(close_pannas):
            panna = close_pannas[i]
            text_width = draw.textbbox((0, 0), panna, font=item_font)[2]
            draw.text((card_x + 3 * (card_w // 4) - text_width // 2, item_y + i * 60), panna, font=item_font, fill=TEXT_WHITE)

# =============== VIDEO CREATION ===============
def create_video_simple(image_path, output_path, duration):
    """Create video using simplest possible FFmpeg command"""
    print(f"  Creating video...")
    
    # Build ULTRA SIMPLE command
    cmd = [
        'ffmpeg',
        '-y',
        '-loop', '1',
        '-i', image_path,
        '-c:v', 'libx264',
        '-t', str(duration),
        '-pix_fmt', 'yuv420p',
        '-r', str(FPS),
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ Video created")
            return True
        else:
            print(f"  ❌ FFmpeg failed")
            if result.stderr:
                # Show first few lines of error
                lines = result.stderr.split('\n')
                for line in lines[:5]:
                    if line.strip():
                        print(f"     {line[:100]}")
            return False
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

def create_video_from_image(image, output_path, duration):
    """Main function to create video from image"""
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save image
        img_path = os.path.join(temp_dir, "image.jpg")
        image.save(img_path, "JPEG", quality=90)
        
        # Create video
        success = create_video_simple(img_path, output_path, duration)
        
        return success
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
        
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def add_audio_to_video(video_path, audio_path):
    """Add audio to existing video"""
    if not audio_path or not os.path.exists(audio_path):
        return False
    
    temp_path = video_path + ".temp.mp4"
    
    cmd = [
        'ffmpeg',
        '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest',
        temp_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Replace original with audio version
            try:
                os.remove(video_path)
                os.rename(temp_path, video_path)
                print(f"  🔊 Audio added")
                return True
            except:
                print(f"  ⚠️ Could not replace file, keeping both")
                return True
        else:
            print(f"  ⚠️ Could not add audio (keeping silent)")
            return False
            
    except Exception as e:
        print(f"  ⚠️ Audio error: {e}")
        return False

def find_audio_file():
    """Find background music"""
    check_locations = [
        os.path.join(BASE_DIR, "music"),
        os.path.join(BASE_DIR, "assets"),
        BASE_DIR
    ]
    
    for folder in check_locations:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.lower().endswith(('.mp3', '.m4a', '.wav')):
                    full_path = os.path.join(folder, file)
                    print(f"🎵 Found audio: {file}")
                    return full_path
    
    print("⚠️ No audio found - will create silent videos")
    return None

# =============== TEST FUNCTIONS ===============
def test_ffmpeg():
    """Test if FFmpeg works"""
    print("🧪 Testing FFmpeg...")
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg is working")
            return True
        else:
            print("❌ FFmpeg returned error")
            return False
    except Exception as e:
        print(f"❌ Cannot run FFmpeg: {e}")
        return False

def create_test_video():
    """Create a simple test video to verify FFmpeg works"""
    print("🧪 Creating test video...")
    test_output = os.path.join(BASE_DIR, "test_video.mp4")
    
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'lavfi',
        '-i', 'color=c=blue:s=1080x1920:d=2',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        test_output
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(test_output):
            print(f"✅ Test video created: {test_output}")
            # Clean up
            try:
                os.remove(test_output)
            except:
                pass
            return True
        else:
            print(f"❌ Test video creation failed")
            return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

# =============== MAIN ===============
def main():
    print("""
    ╔══════════════════════════════════════╗
    ║     MATKA VIDEO GENERATOR v2.0       ║
    ║     Fixed & Working                  ║
    ╚══════════════════════════════════════╝
    """)
    
    # Test FFmpeg
    if not test_ffmpeg():
        print("\n❌ FFmpeg is not working properly.")
        print("   Please make sure FFmpeg is installed and in your PATH.")
        print("   Download from: https://ffmpeg.org/download.html")
        return
    
    # Create a test video to verify
    print("\n🧪 Verifying video creation...")
    if not create_test_video():
        print("⚠️ Video creation test failed, but will continue anyway...")
    
    # Setup
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    date_display = datetime.datetime.now().strftime("%d-%m-%Y")
    output_dir = ensure_dir(os.path.join(OUT_ROOT, today, "videos"))
    
    print(f"\n📅 Date: {date_display}")
    print(f"📁 Output: {output_dir}")
    
    # Find audio
    bgm = find_audio_file()
    
    # Load market data
    print("\n📊 Loading market data...")
    markets = load_market_data()
    
    if not markets:
        print("❌ No market data found. Please check your JSON files.")
        print("\n💡 Expected JSON structure:")
        print("   Option 1: List of markets: [{'market': 'name', 'predictions': {...}}, ...]")
        print("   Option 2: Dict with 'markets' key: {'markets': [...]}")
        print("   Option 3: Dict with 'data' key: {'data': [...]}")
        return
    
    print(f"\n🎬 Processing {len(markets)} markets...")
    print("=" * 60)
    
    successful = []
    failed = []
    
    # Process each market
    for i, market in enumerate(markets, 1):
        market_name = market['name']
        
        # Create safe filename
        safe_name = re.sub(r'[^\w]', '_', market_name)
        safe_name = safe_name[:30]  # Limit length
        output_file = f"{i:03d}_{safe_name}.mp4"
        output_path = os.path.join(output_dir, output_file)
        
        print(f"\n[{i}/{len(markets)}] {market_name}")
        print(f"   Output: {output_file}")
        
        try:
            # Create slide
            slide = create_slide(market, date_display)
            
            # Create video (silent first)
            if create_video_from_image(slide, output_path, VIDEO_DURATION):
                # Add audio if available
                if bgm:
                    add_audio_to_video(output_path, bgm)
                
                successful.append(output_path)
                print(f"   ✅ Success!")
            else:
                failed.append(market_name)
                print(f"   ❌ Failed to create video")
                
        except Exception as e:
            failed.append(market_name)
            print(f"   ❌ Error: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("🎬 PROCESSING COMPLETE")
    print(f"{'='*60}")
    
    if successful:
        print(f"✅ SUCCESS: {len(successful)} videos created")
        print(f"❌ FAILED: {len(failed)} markets")
        
        if failed:
            print("\nFailed markets:")
            for name in failed[:10]:  # Show first 10
                print(f"   • {name}")
            if len(failed) > 10:
                print(f"   ... and {len(failed)-10} more")
        
        print(f"\n📁 Videos saved to: {output_dir}")
        
        # Show first few successful videos
        print("\n📹 Created videos:")
        for vid in successful[:5]:
            print(f"   • {os.path.basename(vid)}")
        if len(successful) > 5:
            print(f"   ... and {len(successful)-5} more")
        
        # Open folder
        try:
            os.startfile(output_dir)
            print(f"\n📂 Opened output folder")
        except:
            pass
    else:
        print("❌ No videos were created successfully")
        print("\n💡 Troubleshooting:")
        print("   1. Check if JSON files exist in output/ folder")
        print("   2. Verify JSON structure matches expected format")
        print("   3. Make sure FFmpeg is properly installed")
        print("   4. Try running: ffmpeg -version")
    
    print(f"\n📊 Summary: {len(successful)} successful, {len(failed)} failed")
    print(f"🎵 Audio: {'Enabled' if bgm else 'Disabled'}")
    print(f"⏱️  Duration: {VIDEO_DURATION} seconds per video")
    print(f"📐 Resolution: {W}x{H} (Instagram Reels)")

if __name__ == "__main__":
    main()