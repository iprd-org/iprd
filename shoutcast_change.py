import os

def get_folder_paths():
    folders = []
    for root, dirs, files in os.walk(os.curdir):
        for dir in dirs:
            folders.append(os.path.join(root, dir))
    return folders

def replace_links(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    modified_lines = []
    for line in lines:
        if line.strip().endswith('/;') or line.strip().endswith(';') or line.strip().endswith(';'):
            modified_lines.append(line.rstrip('\n').replace(';', '') + 'listen.pls\n')
        else:
            modified_lines.append(line)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(modified_lines)

def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.m3u'):
                file_path = os.path.join(root, file)
                replace_links(file_path)

# Replace 'directory_path' with the path to the directory containing the m3u files
directories = get_folder_paths()
for directory in directories:
    process_directory(directory)