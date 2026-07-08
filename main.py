import os
import asyncio
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
from tqdm import tqdm

API_ID = int(input("Enter API ID: "))
API_HASH = input("Enter API Hash: ")
SESSION_PATH = "session/user.session"
DOWNLOAD_DIR = "/content/drive/MyDrive/Downloads"

async def parallel_download(client, message, file_path, num_parts=12):
    file_size = message.file.size
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
    # ✅ FIX: session aur download folder create karo
    os.makedirs("session", exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()
    print("✅ Logged in")
    
    while True:
        file_name = input("\n🔍 Enter file name (or 'exit'): ").strip()
        if file_name.lower() == 'exit':
            break
        found = False
        async for msg in client.iter_messages('me', search=file_name):
            if msg.media and (isinstance(msg.media, MessageMediaDocument) or isinstance(msg.media, MessageMediaPhoto)):
                if msg.file and msg.file.name and file_name.lower() in msg.file.name.lower():
                    print(f"📁 Found: {msg.file.name} | Size: {msg.file.size/(1024*1024):.2f} MB")
                    save_path = os.path.join(DOWNLOAD_DIR, msg.file.name)
                    if os.path.exists(save_path):
                        print("⚠️ Exists, skipping")
                        continue
                    await parallel_download(client, msg, save_path, num_parts=12)
                    found = True
                    break
        if not found:
            print("❌ Not found")
    await client.disconnect()
    print("👋 Done")

if __name__ == "__main__":
    asyncio.run(main())