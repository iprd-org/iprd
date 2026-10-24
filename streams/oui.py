from pathlib import Path
import shutil

ROOT = Path(r"D:\GH Repos\IPRD\IPRD\streams")

DRY_RUN = False


directories = [
    p for p in ROOT.iterdir()
    if p.is_dir()
]

for file in ROOT.iterdir():
    if not file.is_file():
        continue

    stem = file.stem

    matches = []

    for directory in directories:
        name = directory.name

        if stem == name or stem.startswith(name + "_"):
            matches.append(directory)

    if not matches:
        print(f"[IGNORÉ] Aucun dossier correspondant : {file.name}")
        continue

    if len(matches) > 1:
        print(f"[AMBIGU] Plusieurs dossiers pour : {file.name}")
        for match in matches:
            print(f"          -> {match.name}")
        continue

    destination = matches[0] / file.name

    if destination.exists():
        print(f"[OVERWRITE] {file.name} -> {matches[0].name}/")

        if not DRY_RUN:
            destination.unlink()
            shutil.move(str(file), str(destination))
    else:
        print(f"[MOVE]      {file.name} -> {matches[0].name}/")

        if not DRY_RUN:
            shutil.move(str(file), str(destination))