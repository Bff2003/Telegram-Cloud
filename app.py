import os
import dotenv
from telethon.sync import TelegramClient
import json
import uuid

class TelegramBot:
    def __init__(self, api_id, api_hash):
        self.__api_id = api_id
        self.__api_hash = api_hash

    def upload_file(self, chat_target, file_path):
        with TelegramClient('session_name', self.__api_id, self.__api_hash) as client:
            sent_message = client.send_file(chat_target, file=file_path)
            return sent_message.id

    def download_file(self, chat_target, message_id, file_path):
        with TelegramClient('session_name', self.__api_id, self.__api_hash) as client:
            message = client.get_messages(chat_target, ids=message_id)
            message.download_media(file_path)
            return file_path
    
    def create_group(self, group_name):
        with TelegramClient('session_name', self.__api_id, self.__api_hash) as client:
            client.create_group(group_name)

    def create_channel(self, channel_name):
        with TelegramClient('session_name', self.__api_id, self.__api_hash) as client:
            client.create_channel(channel_name)

class FileManager:
    def __init__(self, file_path):
        """ file_path: file where manage all files (database) """
        self.__file_path = file_path
        if not os.path.exists(file_path):
            with open(file_path, 'w') as file:
                file.write('')
        
class FileSplitter:
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    TEMP_DIR = 'temp'

    def __init__(self, file_path):
        self.__file_path = file_path
        self.__file_name = os.path.basename(file_path)
        self.__file_size = os.path.getsize(file_path)

    def split(self):
        """ Split the file in parts of {MAX_SIZE} """
        parts = []
        print(f'File size: {self.__file_size}')

        print(f'The file will be split in {self.__file_size // self.MAX_SIZE + 1} parts')

        if self.__file_size <= self.MAX_SIZE:
            print('File is less than 2GB')
            return [self.__file_path]
        print('File is more than 2GB')

        os.makedirs(self.TEMP_DIR, exist_ok=True)
        with open(self.__file_path, 'rb') as file:
            part_num = 1
            while True:
                print(f'Reading part {part_num}')
                chunk = file.read(self.MAX_SIZE) # Read 2GB at a time
                if not chunk:
                    break
                print(f'Part {part_num} size: {len(chunk)}')

                print(f'Creating part {part_num}')
                part_file_path = f'{self.TEMP_DIR}/{self.__file_name}.part{part_num}'
                with open(part_file_path, 'wb') as part_file:
                    print(f'Writing part {part_num}')
                    part_file.write(chunk)
                    print(f'Part {part_num} written')
                parts.append(part_file_path)
                print(f'Part {part_num} created')
                part_num += 1
        return parts

    def join(self, file_path, parts):
        """ Join the parts in the original file """
        with open(file_path, 'wb') as original_file:
            for part in parts:
                with open(part, 'rb') as part_file:
                    original_file.write(part_file.read())
                os.remove(part)
        return file_path

class App:

    def __init__(self):
        dotenv.load_dotenv()
        self.__api_id = int(os.getenv('API_ID'))
        self.__api_hash = os.getenv('API_HASH')
        self.__bot = TelegramBot(self.__api_id, self.__api_hash)

    def upload(self, chat_target="me", file_path='README.md'):
        with open('file_uploaded.json', 'r') as file:
            files = json.load(file)
        file_uploaded = {
            'id': str(uuid.uuid4()),
            'chat_target': chat_target,
            'file_path': file_path,
            'parts': [
            ]
        }
        file_splitter = FileSplitter(file_uploaded['file_path'])

        for part in file_splitter.split():
            print(f'Uploading part {part}')
            message_id = self.__bot.upload_file(file_uploaded['chat_target'], part)
            print(f'Part {part} uploaded with message id {message_id}')
            file_uploaded['parts'].append({
                'order': len(file_uploaded['parts']) + 1,
                'message_id': message_id,
                'file_path': part
            })
        print('All parts uploaded')
        files["files"].append(file_uploaded)
        
        with open('file_uploaded.json', 'w') as file:
            json.dump(files, file, indent=4)
        
        return file_uploaded

    def download(self, id, new_file_path=None):
        with open('file_uploaded.json', 'r') as file:
            file_uploaded = json.load(file)
        
        for file in file_uploaded['files']:
            if file['id'] == id:
                parts = []
                for part in file['parts']:
                    parts.append(part['file_path'])
                    self.__bot.download_file(file['chat_target'], part['message_id'], part['file_path'])
                file_splitter = FileSplitter(file['file_path'])
                file_splitter.join(new_file_path or file['file_path'], parts)
                break

if __name__ == '__main__':
    app = App()

    print('Uploading...')
    file_uploaded = app.upload(file_path="README.md")
    print(file_uploaded)

    print('Downloading...')
    app.download(file_uploaded['id'])
