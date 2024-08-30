import glob
import os
import uuid

import pendulum
from pynwb import NWBHDF5IO
from pynwb.file import Subject
from simply_nwb import SimpleNWB
from simply_nwb.pipeline import NWBSession
from simply_nwb.pipeline.enrichments.saccades import PutativeSaccadesEnrichment


def search_for_data(prefix):
    print(f"Found {len(os.listdir(prefix))} files in {prefix}")
    datafiles = []

    for file in os.listdir(prefix):
        if file.endswith(".nwb"):
            datafiles.append(os.path.join(prefix, file))
            tw = 2
    return datafiles


def process_folder(nwbfilename, outputdir):
    print(f"Processing '{nwbfilename}'")
    save_fn = os.path.basename(nwbfilename)[:-len(".nwb")]  # Remove .nwb and truncate path
    savename = os.path.join(outputdir, f"{save_fn}_putative.nwb")
    if os.path.exists(savename):
        print(f"File {savename} exists, skipping. Delete to re-generate..")
        return
    tmp_dir = os.path.join("tmpdir", str(uuid.uuid4()))

    if not os.path.exists("tmpdir"):
        os.mkdir("tmpdir")

    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    sess = NWBSession(os.path.join(nwbfilename))
    enrichment = PutativeSaccadesEnrichment()
    sess.enrich(enrichment)

    sess.save(savename)  # Save to file
    del sess


def main():
    prefix = "/run/user/1000/gvfs/smb-share:server=felsenlabnas.local,share=felsennasfolder/AnneData/raw_nwbs_unzipped"  # TODO Change me to dir of sessions
    outputdir = "putative_output"

    datafiles = search_for_data(prefix)
    if not os.path.exists(outputdir):
        os.mkdir(outputdir)

    for filename in datafiles:
        try:
            process_folder(filename, outputdir)
        except Exception as e:
            print(f"Error '{e}'")
            with open(os.path.basename(filename) + "-error.txt", "w") as f:
                f.write(str(e))

    tw = 2


if __name__ == "__main__":
    main()

