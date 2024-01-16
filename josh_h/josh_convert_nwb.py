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
    "Hunt, Josh"
]

LAB = "Felsen"
EXPERIMENT_DESCRIPTION = "TODO"  # TODO Change me

EXPERIMENT_KEYWORDS = ["mouse", "neuropixels"]
EXPERIMENT_RELATED_PUBLICATIONS = None  # optional


SESSIONS_TO_PROCESS = [
    "test_data/mlati9"  # TODO Change me
]


MOUSE_DETAILS = {
    "mlati9": {  # TODO Correct these values
        "birthday": pendulum.parse("5/2/22", strict=False),
        "strain": "mouse",
        "description": "this is a mouse",
        "sex": "M"
    }
}
SESSION_DESCRIPTION = "sess desc"  # TODO Change me
METADATA_FILENAME = "metadata.txt"

LABJACK_FOLDER = "labjack/"

LABJACK_NAME = "LabjackData"
LABJACK_SAMPLING_RATE = 1000.0  # in Hz
LABJACK_DESCRIPTION = "TODO"  # TODO Change me
LABJACK_COMMENTS = "labjack data"

MP4_FILES = {
    "RightEye": "videos/*_rightCam-0000.mp4",  # TODO Make sure these globs are correct
    "LeftEye": "videos/*_leftCam-0000_reflected.mp4",
    # Stim Metadata
    "FictiveSaccades": "stimuli/movies/fictiveSaccades-1.mp4",
    # "MovingBars": "stimuli/movies/movingBars-1.mp4",
    # "SparseNoise": "stimuli/movies/sparseNoise-1.mp4",
    # "DriftingGratingWithProbe": "stimuli/movies/driftingGratingWithRandomProbe-1.mp4"
}
MP4_DESCRIPTION = "TODO"  # TODO Change me
MP4_SAMPLING_RATE = 200.0

# TODO
# Do we need to include this file? I don't have a copy and there is no code for importing this yet
# HDF_FILENAME = "output.hdf"
# HDF_DATA_NAME_PREFIX = "hdfdata"
# HDF_DATA_DESCRIPTION = "TODO"

STIM_META_TXT_FILENAMES = [  # TODO possibly change these?
    # (NameOfMetadata, "file/path/to/file.txt"),
    ("DriftingGratingMetadata", "stimuli/metadata/driftingGratingMetadata.txt"),
    ("MovingBarsMetadata", "stimuli/metadata/movingBarsMetadata.txt")
]


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


def process_stimulus_metadata(nwbfile, session_path, stim_filename, stim_name):
    filename = os.path.join(session_path, stim_filename)

    fp = open(filename, "r")
    processed = {}

    ###########################
    # Parsing code, can ignore
    ###########################
    data = fp.readlines()
    # Parse Header
    file_line_idx = 0
    while True:
        line = data[file_line_idx]
        if line.startswith("------------"):
            break
        sep_idx = line.find(":")
        key = line[:sep_idx].strip()
        val = line[sep_idx + 1:].strip()
        processed[key] = "Meta" + val  # prepend meta to ensure no collisions
        file_line_idx = file_line_idx + 1
    if "Columns" not in processed:
        raise ValueError("Could not process driftingGratingMetadata.txt, couldn't find Column names")

    cols = []
    cols_str = processed["Columns"]
    starting_idx = 0
    range_len = 0
    str_idx = 0
    while True:
        char = cols_str[str_idx]
        if char == "(":
            while True:
                str_idx = str_idx + 1
                range_len = range_len + 1
                if cols_str[str_idx] == ")":
                    break
                if str_idx == 10000:
                    raise ValueError("String didn't have a terminating ')'! (or too long)")
            str_idx = str_idx + 1  # Increment past the ')'
            range_len = range_len + 1
            if str_idx >= len(cols_str):  # ) is the end of the string
                char = ""
            else:
                char = cols_str[str_idx]

        if char == "," or str_idx + 1 >= len(cols_str):
            cols.append(cols_str[starting_idx:starting_idx + range_len])
            starting_idx = str_idx + 1
            range_len = 0
            if str_idx + 1 >= len(cols_str):
                break
        range_len = range_len + 1
        str_idx = str_idx + 1

    # Clean up the header strings by removing whitespace and removing trailing ','
    cols = [c.strip() for c in cols]
    cols = [c[:-1] if c.endswith(",") else c for c in cols]

    file_line_idx = file_line_idx + 1
    drift_data = data[file_line_idx:]

    processed.update({c: [] for c in cols})

    for drift_line in drift_data:
        split = drift_line.split(",")
        if len(split) != len(cols):
            raise ValueError(f"Invalid number of columns for line '{split}' Doesnt match up with expected columns")
        for col_idx, col in enumerate(cols):
            processed[col].append(float(split[col_idx].strip()))
    ##################
    # End parsing code
    ##################
    desc = "Metadata for the stimulus '{}'".format(stim_name)
    SimpleNWB.add_to_processing_module(nwbfile, dict_to_dyn_tables(processed, stim_name, desc), "stim_metadata", desc)


def _load_pickle(session_path, filename):
    fp = open(os.path.join(session_path, filename), "rb")
    return pickle.load(fp)


def process_fictive_pkl(nwbfile, session_path, filename, name):
    # Needed specific functions for different pickle files since NWB doesn't support freeform data input
    data = _load_pickle(session_path, filename)
    trial_vals = []
    trial_types = []
    [(trial_vals.append(f"{v[0]},{v[1]}"), trial_types.append(v[2])) for v in data["trials"]]

    trial_detail = [v[0] for v in data["events"]]
    all_data = {
        "trial_vals": trial_vals,
        "trial_types": trial_types,
        "trial_detail": trial_detail
    }
    # Adding to processing module since NWB doesn't seem to want to write it to the stimulus module so that it persists
    # across file save
    SimpleNWB.processing_add_dict(nwbfile, "FictiveSaccadePkl", all_data, "FictiveSaccade Pickle data", uneven_columns=True)


def process_sparse_noise_pkl(nwbfile, session_path, filename, name):
    data = _load_pickle(session_path, filename)
    # Needed specific functions for different pickle files since NWB doesn't support freeform data input
    data["events"] = list(np.squeeze(data.pop("events")))

    SimpleNWB.processing_add_dict(nwbfile, "SparseNoisePkl", data, "Sparse Noise Pickle data", uneven_columns=True)


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


# Defined down here to include defined processing funcs above
STIM_META_PKL_FILENAMES = [  # TODO possibly change these?
    ("FictiveSaccadeMetadata", "stimuli/metadata/fictiveSaccadeMetadata.pkl", process_fictive_pkl),
    ("SparseNoise", "stimuli/metadata/sparseNoiseMetadata-1.pkl", process_sparse_noise_pkl)
]


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
        related_publications=EXPERIMENT_RELATED_PUBLICATIONS
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

    print("Adding stimuli metadata")
    for stim_name, stim_filename in STIM_META_TXT_FILENAMES:
        process_stimulus_metadata(nwbfile, session_path, stim_filename, stim_name)

    print("Loading pickle stimuli metadata")
    for pickle_name, pickle_filename, pkl_func in STIM_META_PKL_FILENAMES:
        pkl_func(nwbfile, session_path, pickle_filename, pickle_name)

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
    # How to access Stimuli metadata
    # nwbfile.processing["stim_metadata"]["DriftingGratingMetadata_Velocity"]["Velocity"][0]
    #
    # How to access Stimulus Pkl metadata
    # nwbfile.processing["misc"]["SparseNoisePkl_cycle"]["cycle"][:]
    #

    filename_to_save = "nwb-{}-{}-{}_{}.nwb".format(session_id, start_date.month, start_date.day, start_date.hour)
    print("Writing to file '{}' (could take a while!!)..".format(filename_to_save))
    SimpleNWB.write(nwbfile, filename_to_save)
    print("Done!")
    from pynwb import NWBHDF5IO as nwbio  # Want to load file to check that it didn't corrupt
    try:
        test_nwb = nwbio(filename_to_save).read()
        # Also note that your data can just 'be missing' because NWB decided not to write it 'for some reason'
    except Exception as e:
        print(f"File is corrupted! NWB lets you write data that it won't read correctly, check your input data!")
        raise e
    tw = 2


def main():
    pass


if __name__ == "__main__":
    # main()
    # [process_session(s) for s in SESSIONS_TO_PROCESS]

    process_session(SESSIONS_TO_PROCESS[-1], "test_session_name")
    tw = 2
