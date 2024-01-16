import h5py
from simply_nwb.transforms import labjack_load_file, mp4_read_data
from simply_nwb import SimpleNWB
from simply_nwb.transforms import plaintext_metadata_read
from pynwb.file import Subject
import pendulum
import pickle
import os
import argparse


# Simply-NWB Package Documentation
# https://simply-nwb.readthedocs.io/en/latest/index.html


def dictify_hd5(data):
    if isinstance(data, h5py.Dataset):
        return data[:]
    else:
        dd = dict(data)
        d = {}
        for k, v in dd.items():
            d[k] = dictify_hd5(v)
        return d


def decode_data(data):
    return data[0].decode("utf-8")


def main(h5_source_file, nwb_output_filename):
    # TODO Read hdf5 file here, populate data and insert into NWB
    data = h5py.File(h5_source_file)
    # Dictify'd data for debugging ONLY
    dd = dictify_hd5(data)
    tw = 2

    # Create the NWB object
    description = "Ex-vivo electrophysiology and two photon imaging"
    nwbfile = SimpleNWB.create_nwb(
        session_description=description,
        session_start_time=pendulum.parse(decode_data(data["general"]["Date"])),
        experimenter=decode_data(data["general"]["Experimentalist"]),
        lab="Poleg-Polsky Lab",
        subject=Subject(
            subject_id="mouse1",
            age=f"P{pendulum.from_format(decode_data(data['general']['DOB']), 'YYMMDD').diff(pendulum.now()).days}D",
            strain=decode_data(data["general"]["Strain"]),
            sex=decode_data(data["general"]["Sex"]),
            description="Mouse"
        ),
        experiment_description=description,
        session_id=f"session_{decode_data(data['general']['Date'])}",
        institution="University of Colorado Anschutz",
        keywords=["mouse", "two photon", "electrophysiology", "retina"]
    )


    tw = 2

    # TODO add data, use notebook as basic guide, also probably wait for real data example

    # now = pendulum.now()
    # SimpleNWB.write(nwbfile, "nwb-{}-{}_{}".format(now.month, now.day, now.hour))


if __name__ == "__main__":
    # TODO remove me
    import sys

    sys.argv = [sys.argv[0], "test_data/iPhys_2023_08_19 APP.h5", "test_data/converted.nwb"]
    # TODO end remove me

    arg_parser = argparse.ArgumentParser(
        prog="polegpolsky_convert_nwb.py",  # TODO rename program?
        description="Converts incoming formatted hdf5 file into NWB"
    )
    arg_parser.add_argument("h5_filename")
    arg_parser.add_argument("nwb_filename")
    arg_parser.add_argument("-f", "--force", action="store_true")

    args = arg_parser.parse_args()

    h5_source_filename = args.h5_filename
    nwb_output_filename = args.nwb_filename

    if not os.path.exists(h5_source_filename):
        raise FileNotFoundError(f"Could not find H5 source file '{h5_source_filename}'")

    if os.path.exists(nwb_output_filename) and not args.force:
        raise ValueError("NWB output filename exists already! Use the -f option to force overwrite!")

    main(h5_source_filename, nwb_output_filename)
