from pynwb.behavior import BehavioralEvents
from simply_nwb.transforms import labjack_load_file, mp4_read_data
from simply_nwb import SimpleNWB
from simply_nwb.transforms import plaintext_metadata_read
from simply_nwb.util import panda_df_to_list_of_timeseries, dict_to_dyn_tables
from pynwb.file import Subject
import uuid
import pendulum
import glob
import pickle
import os
import h5py
import numpy as np
from pathlib import Path
import pandas as pd

# Simply-NWB Package Documentation
# https://simply-nwb.readthedocs.io/en/latest/index.html

# Constants at the top of the file for things you might want to change for
# different NWBs for flexibility

INSTITUTION = "CU Anschutz"
EXPERIMENTERS = [
    "Hanson, Spencer"
]

LAB = "Felsen Lab"
EXPERIMENT_DESCRIPTION = "experiment description goes here"

EXPERIMENT_KEYWORDS = ["mouse", "neuropixels"]

SESSIONS_TO_PROCESS = [
    "test_data/mlati9"
]
MOUSE_DETAILS = {
    "mlati9": {
        "birthday": pendulum.parse("5/2/22", strict=False),
        "strain": "mouse",
        "description": "this is a mouse",
        "sex": "M"
    }
}
SESSION_DESCRIPTION = "Mouse shown a drifting grating and record eye position, response data, "
METADATA_FILENAME = "metadata.txt"

LABJACK_FOLDER = "labjack/"

LABJACK_NAME = "LabjackData"
LABJACK_SAMPLING_RATE = 1000.0  # in Hz
LABJACK_DESCRIPTION = "stimulus response data"
LABJACK_COMMENTS = "labjack data"

MP4_FILES = {
    "RightEye": "videos/*_rightCam-0000.mp4",
    "LeftEye": "videos/*_leftCam-0000_reflected.mp4",
    # Stim Metadata
    "FictiveSaccades": "stimuli/movies/fictiveSaccades-1.mp4",
}

MP4_DESCRIPTION = "Video of a mouse's eye as it responds to a drifting grating"
MP4_SAMPLING_RATE = 200.0


def process_labjack_data(nwbfile, session_path):

    labjack_folder = os.path.join(session_path, LABJACK_FOLDER)

    labjack_files = glob.glob(os.path.join(labjack_folder, "*.dat"))
    labjack_datas = []
    for filename in labjack_files:
        # print(f"Processing {filename}")
        try:
            labjack_datas.append(labjack_load_file(filename)["data"])
        except Exception as e:
            print(f"Failed parsing {filename}, Error '{str(e)}'skipping..")
            continue
    if not labjack_datas:
        raise ValueError("Labjack data is empty! Cannot continue")

    labjack_combined = pd.concat(labjack_datas)

    timeseries_list = panda_df_to_list_of_timeseries(
        pd_df=labjack_combined,
        measured_unit_list=["s", "v", "v", "v", "v", "v", "v", "v", "v"],
        start_time=0.0,
        sampling_rate=LABJACK_SAMPLING_RATE,
        description=LABJACK_DESCRIPTION,
        comments=LABJACK_COMMENTS
    )

    behavior_events = BehavioralEvents(
        time_series=timeseries_list,
        name=f"labjack_events"
    )

    nwbfile.add_acquisition(behavior_events)


def process_ephys_data(nwbfile, session_path):
    try:
        spike_cluster_filename = next(Path(session_path).rglob("spike_clusters.npy"))
    except StopIteration:
        raise ValueError("Unable to find spike_clusters.npy!")

    try:
        spike_times_filename = next(Path(session_path).rglob("spike_times.npy"))
    except StopIteration:
        raise ValueError("Unable to find spike_times.npy!")

    spike_cluster_data = np.load(str(spike_cluster_filename))
    spike_time_data = np.load(str(spike_times_filename))

    for cluster_number in np.unique(spike_cluster_data):
        spike_time_indices_for_cluster = np.where(spike_cluster_data == cluster_number)[0]
        spike_times_for_cluster = spike_time_data[spike_time_indices_for_cluster].flatten()
        nwbfile.add_unit(spike_times=spike_times_for_cluster)

    nwbfile.create_device(
        name="NeuroPixels Phase3A", description="NeuroPixels electrode", manufacturer="IMEC"
    )


def process_session(session_path, session_id):
    mouse_name = os.path.basename(session_path)  # something like 'lick1' etc

    print("Reading metadata file..")
    metadata = plaintext_metadata_read(os.path.join(session_path, METADATA_FILENAME))

    start_date = pendulum.parse(metadata["Date"], tz="local")

    print("Checking mp4 files..")
    for mp4_name, mp4_glob in MP4_FILES.items():
        mp4_file_glob = os.path.join(session_path, mp4_glob)
        files = glob.glob(mp4_file_glob)
        if not files:
            raise ValueError(f"Couldn't find file with glob '{mp4_file_glob}'")

    print("Creating NWB file..")
    if mouse_name not in MOUSE_DETAILS:
        raise ValueError(f"Unknown mouse '{mouse_name}', not found in MOUSE_DETAILS dict")

    birthday_diff = pendulum.now().diff(MOUSE_DETAILS[mouse_name]["birthday"])

    nwbfile = SimpleNWB.create_nwb(
        session_description=SESSION_DESCRIPTION,
        session_start_time=start_date,
        experimenter=EXPERIMENTERS,
        subject=Subject(**{
            "subject_id": mouse_name,
            "age": f"P{birthday_diff.days}D",  # ISO-8601 for days duration
            "strain": MOUSE_DETAILS[mouse_name]["strain"],
            "description": f"Mouse id '{mouse_name}'",
            "sex": MOUSE_DETAILS[mouse_name]["sex"]
        }),
        lab=LAB,
        experiment_description=EXPERIMENT_DESCRIPTION,
        session_id=session_id,
        institution=INSTITUTION,
        keywords=EXPERIMENT_KEYWORDS,
        related_publications=None  # But would put ["doi://some_paper", ..]
    )

    print("Reading labjack datas..")
    process_labjack_data(nwbfile, session_path)

    print("Reading ephys datas..")
    process_ephys_data(nwbfile, session_path)

    print("Adding MP4 Data, might take a while..")
    # Add mp4 data to NWB
    for mp4_name, mp4_glob in MP4_FILES.items():
        print(f"Processing '{mp4_name}'..")
        mp4_file_glob = os.path.join(session_path, mp4_glob)
        files = glob.glob(mp4_file_glob)
        if not files:
            raise ValueError(f"Couldn't find file with glob '{mp4_file_glob}'")

        data, frames = mp4_read_data(files[0])
        SimpleNWB.mp4_add_as_acquisition(
            nwbfile,
            name=mp4_name,
            numpy_data=data,
            frame_count=frames,
            sampling_rate=MP4_SAMPLING_RATE,
            description=MP4_DESCRIPTION
        )

    # HOW TO USE
    # How to access LabJack data
    # nwbfile.acquisition["labjack_data"]["Time"].data[:]
    #
    # How to access EPhys data
    # nwbfile.units["spike_times"].data[:]
    #
    # How to access Video data
    # nwbfile.acquisition["RightEye"].data[:]
    #

    filename_to_save = "nwb-{}-{}-{}_{}.nwb".format(session_id, start_date.month, start_date.day, start_date.hour)
    print("Writing to file '{}' (could take a while!!)..".format(filename_to_save))
    SimpleNWB.write(nwbfile, filename_to_save)
    print("Done!")
    tw = 2


if __name__ == "__main__":
    process_session(SESSIONS_TO_PROCESS[-1], "test_session_name")
    tw = 2
