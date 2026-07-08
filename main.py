import os
import asyncio
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto, MessageMediaWebPage
from tqdm import tqdm

API_ID = int(input("Enter API ID: "))
API_HASH = input("Enter API Hash: ")
SESSION_PATH = "session/user.session"
DOWNLOAD_DIR = "/content/drive/MyDrive/Downloads"

async def parallel_download(client, message, file_path, num_parts=12):
    # File size detect karo (video/photo/document sab ke liye)
    if message.file:
        file_size = message.file.size
    elif message.photo:
        # Photo ka size alag se nikaalna padega
        file_size = 0
        for size in message.photo.sizes:
            if hasattr(size, 'size'):
                file_size = max(file_size, size.size)
    else:
        file_size = 0
    
    if file_size == 0:
        print("⚠️ File size unknown, downloading normally...")
        await client.download_file(message, file_path)
        return
    
    part_size = 1024 * 1024 * 2
    total_parts = (file_size + part_size - 1) // part_size
    if total_parts < num_parts:
        num_parts = total_parts
    
    chunks = []
    for i in range(num_parts):
        start = i * (file_size // num_parts)
        end = (i + 1) * (file_size // num_parts) if i != num_parts - 1 else file_size
        chunks.append((start, end))
    
    pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc="Downloading")
    
    async def download_part(start, end, part_num):
        part_data = await client.download_file(
            message,
            offset=start,
            limit=end - start,
            request_size=1024*1024
        )
        pbar.update(len(part_data))
        return part_num, part_data
    
    tasks = [download_part(start, end, i) for i, (start, end) in enumerate(chunks)]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda x: x[0])
    
    with open(file_path, 'wb') as f:
        for _, data in results:
            f.write(data)
    pbar.close()
    print(f"\n✅ Saved: {file_path}")

async def main():
    # Folders create karo
    os.makedirs("session", exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()
    print("✅ Logged in successfully!")
    
    # Sab messages fetch karo Saved Messages se
    print("📥 Fetching all messages from Saved Messages...")
    all_messages = []
    async for msg in client.iter_messages('me', limit=2000):  # Limit 2000 tak
        all_messages.append(msg)
    print(f"✅ Found {len(all_messages)} total messages in Saved Messages")
    
    while True:
        file_name = input("\n🔍 Enter file name to search (or 'exit'): ").strip()
        if file_name.lower() == 'exit':
            break
        
        found = False
        matching_messages = []
        
        # Saare messages mein search karo
        for msg in all_messages:
            if not msg.media:
                continue
                
            # File name nikaalo
            msg_file_name = None
            if msg.file and msg.file.name:
                msg_file_name = msg.file.name
            elif msg.photo:
                # Photo ka naam nahi hota, toh "photo.jpg" type ka kuch bana do
                msg_file_name = f"photo_{msg.id}.jpg"
            elif msg.video:
                # Video ka naam bhi nikaalo
                if msg.file and msg.file.name:
                    msg_file_name = msg.file.name
                else:
                    msg_file_name = f"video_{msg.id}.mp4"
            
            if msg_file_name and file_name.lower() in msg_file_name.lower():
                matching_messages.append((msg, msg_file_name))
        
        if not matching_messages:
            print("❌ No file found with that name in Saved Messages")
            continue
        
        # Sab matching files dikhao
        print(f"\n📁 Found {len(matching_messages)} matching file(s):")
        for i, (msg, name) in enumerate(matching_messages):
            size = "Unknown"
            if msg.file and msg.file.size:
                size = f"{msg.file.size/(1024*1024):.2f} MB"
            elif msg.photo:
                size = "Photo"
            print(f"{i+1}. {name} | Size: {size}")
        
        # User ko choose karne do
        choice = input(f"\nEnter number (1-{len(matching_messages)}) to download or 'all' for all: ").strip()
        
        if choice.lower() == 'all':
            for msg, name in matching_messages:
                save_path = os.path.join(DOWNLOAD_DIR, name)
                if os.path.exists(save_path):
                    print(f"⚠️ {name} already exists, skipping")
                    continue
                print(f"\n📥 Downloading: {name}")
                await parallel_download(client, msg, save_path, num_parts=12)
            found = True
        elif choice.isdigit() and 1 <= int(choice) <= len(matching_messages):
            idx = int(choice) - 1
            msg, name = matching_messages[idx]
            save_path = os.path.join(DOWNLOAD_DIR, name)
            if os.path.exists(save_path):
                print(f"⚠️ {name} already exists, skipping")
            else:
                print(f"\n📥 Downloading: {name}")
                await parallel_download(client, msg, save_path, num_parts=12)
            found = True
        else:
            print("❌ Invalid choice")
            continue
        
        if not found:
            print("❌ No file downloaded")
    
    await client.disconnect()
    print("👋 Session saved, bye!")

if __name__ == "__main__":
    asyncio.run(main())