from datetime import datetime
import os

def test_fs_logic():
    print("Testing FS datetime logic...")
    # Simulate list_directory logic
    mtime_raw = os.path.getmtime(__file__)
    mtime = datetime.fromtimestamp(mtime_raw).strftime("%Y-%m-%d %H:%M")
    print(f"Mtime: {mtime}")
    
def test_web_logic():
    print("Testing Web datetime logic...")
    # Simulate web_search logic
    now = datetime.now().strftime("%d %B %Y, %H:%M")
    print(f"Now: {now}")

if __name__ == "__main__":
    try:
        test_fs_logic()
        test_web_logic()
        print("✅ Datetime logic OK")
    except Exception as e:
        print(f"❌ Datetime logic FAILED: {e}")
