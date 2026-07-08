import os
import asyncio
import aiohttp
from telethon import TelegramClient, events, utils
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
from tqdm import tqdm
import time

# ---------- CONFIG ----------
API_ID = int(input("Enter your API ID: "))          # my.telegram.org se lo
API_HASH = input("Enter your API hash: ")
SESSION_PATH = "session/user.session"               # Session save karega
DOWNLOAD_DIR = "/content/drive/MyDrive/Downloads"   # Mounted Drive path (Colab)
# Agar Colab mein ho toh drive mount karo: from google.colab import drive; drive.mount('/content/drive')
# ----------------------------

async def parallel_download(client, message, file_path, num_parts=8):
    """
    Telethon ke download_file ko parallel chunks mein download karta hai.
    num_parts = jitne concurrent connections (Google bandwidth ko full utilise karne ke liye)
    """
    file_size = message.file.size
    part_size = 1024 * 1024 * 2  # 2 MB per chunk
    total_parts = (file_size + part_size - 1) // part_size

    # Agar file chhoti hai toh single thread hi kaafi
    if total_parts < num_parts:
        num_parts = total_parts

    # Har chunk ka start aur end nikaalo
    chunks = []
    for i in range(num_parts):
        start = i * (file_size // num_parts)
        end = (i + 1) * (file_size // num_parts) if i != num_parts - 1 else file_size
        chunks.append((start, end))

    # Progress bar
    pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc="Downloading")

    # Async function jo ek part download kare
    async def download_part(start, end, part_num):
        part_data = await client.download_file(
            message,
            offset=start,
            limit=end - start,
            request_size=1024*1024  # 1 MB request size
        )
        pbar.update(len(part_data))
        return part_num, part_data

    # Sab parts ko parallel mein bhejo
    tasks = [download_part(start, end, i) for i, (start, end) in enumerate(chunks)]
    results = await asyncio.gather(*tasks)

    # Parts ko order mein assemble karo
    results.sort(key=lambda x: x[0])
    with open(file_path, 'wb') as f:
        for _, data in results:
            f.write(data)

    pbar.close()
    print(f"\n✅ File saved at: {file_path}")

async def main():
    # Create client
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)

    # Login / Session restore
    await client.start()
    print("✅ Logged in successfully!")

    # Ensure downloads directory exists
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Search karte rahenge jab tak user exit na kare
    while True:
        file_name = input("\n🔍 Enter the file name to search (or type 'exit' to quit): ").strip()
        if file_name.lower() == 'exit':
            break

        # Saved Messages mein search karo
        found = False
        async for msg in client.iter_messages('me', search=file_name):
            # Sirf documents (files) hi consider karo
            if msg.media and (isinstance(msg.media, MessageMediaDocument) or isinstance(msg.media, MessageMediaPhoto)):
                # File name check
                if msg.file and msg.file.name and file_name.lower() in msg.file.name.lower():
                    print(f"📁 Found: {msg.file.name} | Size: {msg.file.size / (1024*1024):.2f} MB")
                    save_path = os.path.join(DOWNLOAD_DIR, msg.file.name)
                    # Agar same naam ho toh overwrite mat karo (optional)
                    if os.path.exists(save_path):
                        print("⚠️ File already exists. Skipping...")
                        continue
                    # Parallel download
                    await parallel_download(client, msg, save_path, num_parts=12)   # 12 threads = full bandwidth
                    found = True
                    break   # Pehli file hi download karo (agar exact match chaahiye toh loop tod do)
        if not found:
            print("❌ No file found with that name in Saved Messages.")

    await client.disconnect()
    print("👋 Session saved, bye!")

if __name__ == "__main__":
    asyncio.run(main())