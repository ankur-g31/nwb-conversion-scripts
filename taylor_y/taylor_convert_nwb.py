import pendulum
from simply_nwb import SimpleNWB
from simply_nwb.util import create_mouse_subject


# TODO Check all these params
SESSION_DESCRIPTION = "todo"
EXPERIMENT_DESCRIPTION = "todo"
EXPERIMENTER = "Taylor Y"
EXPERIMENT_KEYWORDS = ["mouse", "two photon", "electrophysiology", "retina"]
MOUSE_DETAILS = {
    "mousename1": {
        "subject_id": "mousename1",
        "birthday_str": "10/5/23",
        "strain": "mouse idk",
        "sex": "M",
        "desc": "Mouse idk desc"
    }
}

# TODO set these as well
BLACKROCK_CONSTANTS = {
    "device_description": "todo",
    "electrode_name": "Bob_idk",
    "electrode_description": "todo",
    "electrode_location_description": "todo",
    "electrode_resistance": 1.0,  # TODO
    "device_manufacturer": "todo",
    "device_name": "Steve the blackrock machine",
}


def process_session(session_start_date, mouse_name, nev_filepath):
    if mouse_name not in MOUSE_DETAILS:
        raise ValueError(f"Mouse name '{mouse_name}' not in MOUSE_DETAILS, cannot infer properties, please add or correct!")

    mouse_details = MOUSE_DETAILS[mouse_name]

    nwbfile = SimpleNWB.create_nwb(
        session_description=SESSION_DESCRIPTION,
        session_start_time=pendulum.parse(session_start_date, strict=False),
        experimenter=EXPERIMENTER,
        lab="Felsen Lab",
        subject=create_mouse_subject(**mouse_details),
        experiment_description=EXPERIMENT_DESCRIPTION,
        session_id=session_start_date,
        institution="University of Colorado Anschutz",
        keywords=EXPERIMENT_KEYWORDS
    )

    SimpleNWB.blackrock_spiketrains_as_units(
        nwbfile,
        blackrock_filename=nev_filepath,
        **BLACKROCK_CONSTANTS
    )

    now = pendulum.now()
    nwbfilename = f"nwb-{now.day}-{now.month}-{now.year}-{mouse_name}.nwb"
    print("Writing NWB '{}'..".format(nwbfilename))
    SimpleNWB.write(nwbfile, nwbfilename)
    print("Done!")


def main():
    process_session(
        "10-10-2023",
        "mousename1",
        "test_data/wheel_4p3_lSC_2001.nev"
    )


if __name__ == "__main__":
    main()
