import glob
import json
import pendulum
import os
import zipfile


ROOT_FOLDER_TO_SEARCH = "/media/polegpolskylab/VIDEO-DATA-02/CompressedDataLocal"


def main():
    nwbs = glob.glob(f"{ROOT_FOLDER_TO_SEARCH}/**/*.nwb", recursive=True)

    grouped = {}
    for nwb in nwbs:
        split = nwb[len(ROOT_FOLDER_TO_SEARCH):].split("-")
        if split[0] in grouped:
            grouped[split[0]].append(nwb)
        else:
            grouped[split[0]] = [nwb]

    # print("Grouped")
    # print(json.dumps(grouped, indent=2))

    latest = []
    for prefix, matches in grouped.items():
        dates = []
        for match in matches:
            # Parse out date from the filename
            filename = os.path.basename(match)
            split = filename.split("-")[2:]
            date = "-".join(split)
            date = date[:-len(".nwb")]
            date = pendulum.from_format(date, "M-D_H-mm-s")
            dates.append([match, date.timestamp()])
        s = sorted(dates, key=lambda x: x[1])
        # print("---\n")
        # print(json.dumps(s, indent=2))
        latest.append(s[-1])

    files_to_copy = [l[0] for l in latest]
    zipf = zipfile.ZipFile("NWBs.zip", "w", zipfile.ZIP_DEFLATED)
    for file in files_to_copy:
        print(f"Writing {file} to zipfile..")
        zipf.write(file, arcname=os.path.basename(file))
    zipf.close()


if __name__ == "__main__":
    main()
