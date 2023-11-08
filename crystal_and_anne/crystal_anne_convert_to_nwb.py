import datetime
import glob

from pendulum.parsing import ParserError
from dict_plus.utils.simpleflatten import SimpleFlattener
from pynwb import TimeSeries
from pynwb.image import ImageSeries

from simply_nwb.transforms import csv_load_dataframe_str, yaml_read_file
from simply_nwb import SimpleNWB
from pynwb.file import Subject
import pendulum
import os

from simply_nwb.util import panda_df_to_list_of_timeseries

# Simply-NWB Package Documentation
# https://simply-nwb.readthedocs.io/en/latest/index.html


# Constants at the top of the file for things you might want to change for
# different NWBs for flexibility
INSTITUTION: str = "CU Anschutz"

EXPERIMENTERS: [str] = [
    "Williams, Anne",
    "Minjarez, Crystal"
]
LAB: str = "Felsen Lab"

EXPERIMENT_DESCRIPTION: str = "Measuring Saccades in Pitx2 Mice Using CNO"
EXPERIMENT_KEYWORDS: [str] = ["mouse", "saccade", "CNO", "dreadds", "pitx2", "drifting"]
EXPERIMENT_RELATED_PUBLICATIONS = None  # optional

MP4_SAMPLING_RATE: float = 200.0

MOUSE_DATA = {  # TODO ADD MORE MICE AND UPDATE BIRTHDAYS AND SEXES?
    "dcm10": {
        "subject_id": "dcm10",
        "birthday": "7/30/23",
        "description": "Mouse dcm10",
        "strain": "Gad2Cre",
        "sex": "M"
    },
    "NameOfMouse2": {  # Copy me
        "subject_id": "dcm10",
        "birthday": "7/30/23",
        "description": "Mouse dcm10",
        "strain": "Gad2Cre",
        "sex": "M"
    }
}

STIM_CSVS = {
    "RightCamStim": {  # Remove me and uncomment below
        "csv_glob": "*_rightCam*.csv",
        "units": ["idx", "px", "px", "likelihood"]
    },
    # TODO Change me to what the real data will look like, currently for testing
    # "LeftCamStim": {
    #     "csv_glob": "*_leftCam*.csv",
    #     # Units line up with
    #     #         bodyparts,tongue,tongue,tongue,spout,spout,spout
    #     "units": ["idx", "px", "px", "likelihood", "px", "px", "likelihood"]
    # },
    # "RightCamStim": {
    #     "csv_glob": "*_rightCam*.csv",
    #     # Units line up with
    #     #         bodyparts,center,center,center,nasal,nasal,nasal,temporal,temporal,temporal,dorsal,dorsal,dorsal,ventral,ventral,ventral
    #     "units": ["idx", "px", "px", "likelihood", "px", "px", "likelihood", "px", "px", "likelihood", "px", "px", "likelihood", "px", "px", "likelihood"]
    # }
}

# TODO Fill these out!
RESPONSE_SAMPLING_RATE = MP4_SAMPLING_RATE
RESPONSE_DESCRIPTION = "description about the processed response"
RESPONSE_COMMENTS = "comments about the response"


def process_labjack(nwbfile, foldername):
    if not os.path.exists(foldername):
        raise ValueError(f"Folder {foldername} doesn't exist/can't be found!")

    files = os.listdir(foldername)
    for fn in files:
        file = f"{foldername}{os.sep}{fn}"
        print(f"Adding file {fn}..")
        SimpleNWB.labjack_file_as_behavioral_data(
            nwbfile,
            labjack_filename=file,
            name=fn,
            measured_unit_list=["s", "s", "s", "s", "s", "barcode", "s", "s", "s"],  # 9 columns for data collected
            start_time=0.0,
            sampling_rate=1000.0,
            description="TTL signal for when the probe is present",
            behavior_module_name="labjack",
            comments="labjack data"
        )
    print("Adding labjack data complete")
    tw = 2


def process_video(nwbfile, filename, cam_name, video_description):
    print(f"Processing '{cam_name}' video")

    video_series = ImageSeries(
        name=cam_name,
        external_file=[filename],
        description=video_description,
        unit="n.a.",
        rate=MP4_SAMPLING_RATE,
        format="external",
        starting_time=0.0
    )
    nwbfile.add_acquisition(video_series)
    print("Video processing complete")


def process_drifting_meta(nwbfile, filename):
    fp = open(filename, "r")
    processed = {}

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

    SimpleNWB.processing_add_dict(
        nwbfile,
        "DriftingGratingMetadata",
        processed,
        "Metadata for the drifting grating",
        uneven_columns=True,
        processing_module_name="metadata"
    )


def process_eyetracking(nwbfile, session_folder):
    # STIM_CSVS
    for name, stim_data in STIM_CSVS.items():
        csv_glob = stim_data["csv_glob"]
        fullpath = os.path.join(session_folder, csv_glob)
        results = glob.glob(fullpath)
        if not results:
            raise ValueError(f"Unable to find any files matching '{fullpath}'")
        results = results[0]
        io = open(results, "r")
        lines = io.readlines()

        lines.pop(0)  # First line is not important, just 'scorer,<resnet name>*6'
        col_prefixes = lines.pop(0).split(",")  # Next line is the prefixes of the columns
        col_suffixes = lines.pop(0).split(",")

        # Combine the column names, insert back into data list
        headers = [f"{col_prefixes[i].strip()}_{col_suffixes[i].strip()}" for i in range(0, len(col_prefixes))]
        lines.insert(0, ",".join(headers))

        # Create the module to add the data to
        response_processing_module = nwbfile.create_processing_module(
            name=name,
            description="Processed eyetracking data for {}".format(name)
        )

        # Load CSV into a dataframe, convert to TimeSeries
        response_df = csv_load_dataframe_str("\n".join(lines))
        response_ts = panda_df_to_list_of_timeseries(
            response_df,
            measured_unit_list=stim_data["units"],
            start_time=0.0,
            sampling_rate=RESPONSE_SAMPLING_RATE,
            description=RESPONSE_DESCRIPTION,
            comments=RESPONSE_COMMENTS
        )
        # Add the timeseries into the processing module
        [response_processing_module.add(ts) for ts in response_ts]

    tw = 2
    pass


def flatten_and_format(data):
    flattener = SimpleFlattener(simple_types=[datetime.date, list])
    data = flattener.flatten(data)
    for k in list(data.keys()):
        if isinstance(data[k], datetime.date):
            data[k] = str(data[k])
    return data


def process_session(prefix, session_id, session_desc, mouse_name, mouse_weight):
    session_date = session_id.split("/")[0]
    session_number = session_id.split("/")[-1]
    labjack_folder = f"{session_date}_{session_number}"  # Ex: 20230121_session001

    session_path_prefix = prefix + session_id
    file_prefix = "_".join(session_id.split("/"))  # 20230921/unitME/session001 -> 20230921_unitME_session001
    cams = [
        "leftCam",
        "rightCam"
    ]
    video_suffix = "-0000.mp4"
    timestamp_suffix = "_timestamps.txt"
    drift_meta = "driftingGratingMetadata.txt"
    session_meta = "_metadata.yaml"

    probe_video_name = "driftingGratingWithRandomProbe-1.mp4"
    stim_config = "visualStimulusConfig.yaml"

    mouse_data = MOUSE_DATA[mouse_name]
    mouse_age = "P" + str(pendulum.parse(mouse_data["birthday"], strict=False).diff(
        pendulum.now()).in_days()) + "D"  # How many days since birthday

    try:
        session_start_time = pendulum.parse(session_id.split("/")[0])
        # parse first part of this "20230921/unitME/session001"
    except ParserError as e:
        raise ValueError(f"Invalid session id string, must be formatted like 'date/folders'"
                         f" first entry must be datetime parsable. Error {str(e)}")

    nwbfile = SimpleNWB.create_nwb(
        session_description=session_desc,
        session_start_time=session_start_time,
        experimenter=EXPERIMENTERS,
        lab=LAB,
        experiment_description=EXPERIMENT_DESCRIPTION,
        session_id=session_id,
        institution=INSTITUTION,
        keywords=EXPERIMENT_KEYWORDS,
        related_publications=EXPERIMENT_RELATED_PUBLICATIONS,
        subject=Subject(
            subject_id=mouse_name,
            age=mouse_age,  # ISO-8601 days format
            strain=mouse_data["strain"],  # if unknown, put Wild Strain
            description=mouse_data["description"],
            sex=mouse_data["sex"],
            weight=mouse_weight
        )
    )

    # Processing Eyetracking Data
    print("Processing Eyetracking CSV Data")
    process_eyetracking(nwbfile, session_path_prefix)

    # Process LabJack folder
    print("Processing Labjack folder")
    process_labjack(nwbfile, f"{session_path_prefix}{os.sep}{labjack_folder}")

    # Process Cam Videos and timestamps
    print("Processing Cam Videos")
    for eyecam in cams:
        process_video(
            nwbfile,
            f"{file_prefix}_{eyecam}{video_suffix}",
            f"{eyecam}",
            f"{eyecam} video of eye"
        )

        # Timestamps
        # example: '20230921/unitME/session001/20230921_unitME_session001_leftCam_timestamps.txt'
        csv_filepath = f"{session_path_prefix}{os.sep}{file_prefix}_{eyecam}{timestamp_suffix}"
        csv_fp = open(csv_filepath, "r")
        csv_data = csv_load_dataframe_str("Timestamps\n" + csv_fp.read())
        csv_fp.close()

        nwbfile.add_stimulus(TimeSeries(
            name=f"{eyecam}Timestamps",
            data=list(csv_data["Timestamps"]),
            rate=1.0,
            unit="s"
        ))

    # Process probe video
    print("Processing Probe Video(s), might take a while..")
    process_video(
        nwbfile,
        f"{probe_video_name}",
        "ProbeVideo",
        "Drifting grating of the probe stimulus"
    )

    # Process driftingGratingMetdata
    print("Processing Drifting Grating Metadata")
    process_drifting_meta(nwbfile, f"{session_path_prefix}{os.sep}{drift_meta}")

    # Process visualStimConfig YAML
    print("Processing Visual Stimulus Config")
    yaml_data = yaml_read_file(f"{session_path_prefix}{os.sep}{stim_config}")
    yaml_data = flatten_and_format(yaml_data)
    SimpleNWB.processing_add_dict(
        nwbfile,
        "GratingStimConfig",
        yaml_data,
        "Configuration information on grating drift and different stimuli",
        uneven_columns=True,
        processing_module_name="metadata"
    )

    # General metadata
    print("Processing general experiment metadata")
    general_metadata = yaml_read_file(f"{session_path_prefix}{os.sep}{file_prefix}{session_meta}")
    general_metadata = flatten_and_format(general_metadata)
    SimpleNWB.processing_add_dict(
        nwbfile,
        "ROICropCamData",
        general_metadata,
        "Data of eye video cropping, misc general experiment metadata",
        uneven_columns=True,
        processing_module_name="metadata"
    )

    # Processed all the data, write to file
    now = pendulum.now()
    nwb_filename = "{}-nwb-{}-{}_{}-{}-{}.nwb".format(file_prefix, now.month, now.day, now.hour, now.minute, now.second)

    print(f"Finished, writing NWB {nwb_filename}")
    SimpleNWB.write(nwbfile, f"{session_path_prefix}{os.sep}{nwb_filename}")
    # from pynwb import NWBHDF5IO
    # io = NWBHDF5IO(nwb_filename)
    # ff = io.read()
    tw = 2


def main():
    prefix = "/media/polegpolskylab/VIDEO-DATA-02/CompressedDataLocal/"

    # start remove TEST CODE PLS IGNORE
    print("TESTING REMOVE ME!\n" * 10)
    import os
    os.chdir("test_data")
    prefix = ""
    # end remove

    sessions_to_process = {
        "20230921/unitME/session001": {
            "session_description": "Pilot experiment, control mouse, no CNO",
            "mouse_name": "dcm10",
            "mouse_weight": "5g"  # TODO PUT ACTUAL WEIGHT HERE
        }
        # Add more sessions to process here, comment out sessions you don't want processed
    }

    for session_id, session_data in sessions_to_process.items():
        print(f"Processing session '{session_id}'")
        process_session(
            prefix,
            session_id,
            session_data["session_description"],
            session_data["mouse_name"],
            session_data["mouse_weight"]
        )


if __name__ == "__main__":
    main()
