import h5py
import numpy as np
from dict_plus.utils import SimpleFlattener
from hdmf.common import DynamicTable, VectorData
from simply_nwb.transforms import labjack_load_file, mp4_read_data
from simply_nwb import SimpleNWB
from simply_nwb.transforms import plaintext_metadata_read
from pynwb.file import Subject
import pendulum
import pickle
import os
import argparse

from simply_nwb.util import dict_to_dyn_tables


# Simply-NWB Package Documentation
# https://simply-nwb.readthedocs.io/en/latest/index.html

DEBUGGING = {}


def dictify_hd5(data):
    if isinstance(data, h5py.Dataset):
        try:
            return list(data[:])
        except Exception as e:
            print(f"Errorrrrrr {str(e)}")
            return "BROKEN!!!!!!!!!!!!!!!!!!!!!!"
    else:
        dd = dict(data)
        d = {}
        for k, v in dd.items():
            d[k] = dictify_hd5(v)
        return d


def decode_data(data):
    return data[0].decode("utf-8")


def _decode_dob(data):
    date = decode_data(data['general']['DOB'])
    try:
        date = f"P{pendulum.from_format(date, 'YYMMDD').diff(pendulum.now()).days}D"
    except:
        date = "Unknown"
    return date


def find_common_keyname(keylist):
    # keylist = [(key1, val1), (key2, val2), ...]
    if len(keylist) == 0:
        return []
    shared_count = 0
    done = False
    while True:
        if len(keylist[0][0]) <= shared_count:
            shared_count = shared_count - 1
            break

        to_check = keylist[0][0][:shared_count]
        for k, v in keylist:
            if not to_check == k[:shared_count]:
                shared_count = shared_count - 1
                done = True
                break
        if done:
            break
        shared_count = shared_count + 1
    if shared_count < 0:
        shared_count = 0

    grouped = {}
    for k, v in keylist:
        grouped[k[shared_count:]] = v

    return [[keylist[0][0][:shared_count], grouped]]


def group_and_filter_datasets(datadict, prefix):
    groups = {}
    for k, v in datadict.items():
        shape = v.shape
        if shape == ():
            continue
        if shape in groups:
            groups[shape].append((k, v))
        else:
            groups[shape] = [(k, v)]

    # Group any group with only one member
    groups["orphans"] = []
    for k in list(groups.keys()):
        if len(groups[k]) == 1:
            groups["orphans"].append(groups[k].pop())
    # Currently groups looks like {(a, b, ..): [(key, val)}, .., "orphans": [(key, val), ..], ..}

    result = []
    for k, v in groups.items():
        result.extend(find_common_keyname(v))  # Comes back as [name, {}]

    # [[name, {}], [name, {}], ..]
    result = [[f"{prefix}_{v[0]}", v[1]] for v in result]  # Add prefix
    return result


def traverse_hdf5(name, entry):
    # () -> leaf, {} -> tree, [] -> done

    result = []
    if isinstance(entry, h5py._hl.dataset.Dataset):
        if entry.shape != ():
            result.append((name, entry[:]))
    else:
        leafs = {}
        for entry_k, entry_v in entry.items():
            sub_result = traverse_hdf5(entry_k, entry_v)

            for sub_val in sub_result:
                if isinstance(sub_val, tuple):
                    leafs[sub_val[0]] = sub_val[1]
                elif isinstance(sub_val, list):
                    sub_val[0] = f"{name}_{sub_val[0]}"  # append prefix and pass it up
                    result.append(sub_val)
                # elif isinstance(sub_val, SubGroup):

        # [[name, {}], [name, {}], ..]
        result.extend(group_and_filter_datasets(leafs, prefix=name))

    return result


def fix(val, index=0, backup=None):
    try:
        return decode_data(val[index])
    except Exception as e:
        if backup:
            return backup
        else:
            raise e


def process_analysis(nwbfile, d):
    data = d["analysis"]
    all_keys = list(data)

    fl = SimpleFlattener(simple_types=[np.ndarray, type(None), h5py._hl.dataset.Dataset],
                         dict_types=[h5py._hl.group.Group])

    # Process Events
    for event_name in list(data["events"]):
        event = data["events"][event_name]
        result = traverse_hdf5(event_name, event)
        for prefix, event_data in result:
            uneven = False
            event_items = list(event_data.items())
            if len(event_items) > 1:
                if len(event_items[0][1]) != len(event_items[1][1]):
                    # Columns are uneven
                    uneven = True
            if prefix.endswith("_"):
                prefix = prefix[:-1]

            # Workaround to collisions, increment until there isn't one
            val = 0
            while True:
                try:
                    dyn = dict_to_dyn_tables(
                        event_data,
                        f"analysis_events_{prefix}_{val}",
                        f"Analysis events for event '{event_name}' with data value {prefix}",
                        multiple_objs=uneven
                    )
                    SimpleNWB.add_to_processing_module(nwbfile, dyn, "analysis_events", "Analysis Events")
                    break
                except ValueError as e:
                    val = val + 1
                    if val > 1000:
                        print("Tried 1,000 times to find a different keyname, not continuing")
                        raise e

    # Process Traces
    for subkey in all_keys:
        if subkey == "events":
            continue
        flattened = {k: v[:] for k, v in fl.flatten(data[subkey]).items()}  # Convert to numpy array

        dyn = dict_to_dyn_tables(
            flattened,
            f"analysis_{subkey}",
            f"Analysis for {subkey}",
            multiple_objs=True
        )
        SimpleNWB.add_to_processing_module(nwbfile, dyn, f"analysis_{subkey}", "Analysis Traces")

    tw = 2


def fill_data(listdata):
    largest_dim_lens = []
    for v in listdata:
        if v is not None:
            # Find the largest dimension among all the list entries
            if len(largest_dim_lens) < len(v.shape):
                [largest_dim_lens.append(0) for _ in range(len(v.shape) - len(largest_dim_lens))]  # Add new dimension maxes
            for idx, dim in enumerate(v.shape):
                if largest_dim_lens[idx] < dim:
                    largest_dim_lens[idx] = dim

    fill = np.ma.masked
    if isinstance(listdata[0][0], (bytes, str)):
        fill = None

    dtype = listdata[0][:].dtype
    if listdata[0][:].dtype == object:
        dtype = object

    new_listdata = np.empty([len(listdata), *largest_dim_lens], dtype=dtype)
    new_listdata[:] = fill

    for idx, l in enumerate(listdata):
        if l is None:
            continue
        l = l[:]
        l_shape = []

        if len(l.shape) < len(largest_dim_lens):
            for _ in range(len(largest_dim_lens) - len(l.shape)):
                l = l[..., None]

        for lsh_idx, lsh in enumerate(largest_dim_lens):
            if len(l.shape) <= lsh_idx:
                l_shape.append(0)
            else:
                l_shape.append(l.shape[lsh_idx])



        new_listdata[idx, :] = np.pad(
            l,
            [(0, largest_dim_lens[i] - l_shape[i]) for i in range(len(largest_dim_lens))],
            constant_values=fill
        )
    return new_listdata


def process_data(nwbfile, d):
    data = d["data"]
    # dd = dictify_hd5(data["data"])

    trace_sweep_join = [  # If something doesn't exist just ignore
        ("M_EPChannelsParams",),
        ("W_EPparams",),
        ("ephys", "ChRead_0"),
        ("ephys", "ChRead_2"),
        ("two_photon", "W_RecordedChannels"),
        ("two_photon", "file_name"),
        ('visual_stim', 'M_Movie'),
        # ('visual_stim', 'M_SpeedModulation'),  # Disable since all values are NaN
        ('visual_stim', 'M_TimeModulation'),
        ('visual_stim', 'T_VSprotocol'),
        ('visual_stim', 'W_Params'),
        ('visual_stim', 'W_VSparams')
    ]
    sweep_data = {j: [] for j in trace_sweep_join}
    id_fields = ["trace_ids", "sweep_ids"]
    extra_fields = [*id_fields, "filedata"]
    for f in extra_fields:
        sweep_data[f] = []

    get_name = lambda x: "_".join(x)
    
    def delve_dict(keylist, data_to_delve):
        for k in keylist:
            if k in data_to_delve:
                data_to_delve = data_to_delve[k]
            else:
                return False, None
        return True, data_to_delve

    def find_filedata(sweep_data_root):
        if "two_photon" in sweep_data_root:
            sweep_data_root = sweep_data_root["two_photon"]
            for sweep_data_root_key, sweep_data_root_value in sweep_data_root.items():
                # Search for something like    # Need to find file_*_ChanA
                if sweep_data_root_key.startswith("file_") and sweep_data_root_key.endswith("_ChanA"):
                    return sweep_data_root_value
        return None

    trace_list = list(data)
    # Either the number of sweeps is the largest, or the value attached to it is
    largest_trace_num = max(len(trace_list), max([int(v.split("_")[1]) for v in list(data)]))
    for trace_num in range(largest_trace_num):
        trace_id = f"trace_{trace_num}"
        if trace_id in data:   # For each trace
            trace = data[trace_id]
            # Process sweeps
            for sweep_id, sweep_val in trace.items():  # Check each sweep in each trace
                if not sweep_id.startswith("sweep_"):
                    continue  # Skip over non-sweep data

                sweep_data["trace_ids"].append([trace_id])
                sweep_data["sweep_ids"].append([sweep_id])
                for join_on in trace_sweep_join:  # Pull out the data we're interested in
                    delve_found, delved_data = delve_dict(join_on, sweep_val)  # Pull out nested data
                    if not delve_found:
                        sweep_data[join_on].append(None)
                        continue
                    else:
                        sweep_data[join_on].append(delved_data)
                sweep_data["filedata"].append(find_filedata(sweep_val))

    tmp = {}
    for f in id_fields:
        tmp[f] = sweep_data.pop(f)

    sweep_data = {get_name(k): fill_data(v) for k, v in sweep_data.items()}

    for f in id_fields:
        sweep_data[f] = tmp.pop(f)

    dyn = dict_to_dyn_tables(
        sweep_data,
        f"data",
        f"Data table by sweep",
        multiple_objs=True
    )

    for k, v in sweep_data.items():
        DynamicTable(
            name=table_name,
            description=description,
            columns=VectorData(
                name=col_name,
                data=col_data,
                description=col_name
            )
        )
        SimpleNWB.add_to_processing_module(nwbfile, dyn, "data", "Sweep data")

    tw = 2

    pass


def process_events(nwbfile, data):
    pass


def process_general(nwbfile, data):
    pass


def main(h5_source_file, nwb_output_filename):
    # TODO Read hdf5 file here, populate data and insert into NWB
    data = h5py.File(h5_source_file)
    # Dictify'd data for debugging ONLY
    import os
    import json
    #
    # if not os.path.exists("test.json"):
    #     dd = dictify_hd5(data)
    #     fp = open("test.json", "w")
    #     json.dump(dd, fp)
    #     fp.close()
    # else:
    #     fp2 = open("test.json", "r")
    #     dd = json.load(fp2)
    #     fp2.close()
    #
    # DEBUGGING["d"] = dd
    # tw = 2

    # Create the NWB object
    description = "Ex-vivo electrophysiology and two photon imaging"
    nwbfile = SimpleNWB.create_nwb(
        session_description=description,
        session_start_time=pendulum.parse(decode_data(data["general"]["Date0"])),
        experimenter=decode_data(data["general"]["Experimentalist"]),
        lab="Poleg-Polsky Lab",
        subject=Subject(
            subject_id="mouse1",
            age=f"P{_decode_dob(data)}",
            strain=decode_data(data["general"]["Strain"]),
            sex=decode_data(data["general"]["Sex"]),
            description="Mouse"
        ),
        experiment_description=description,
        session_id=f"session_{decode_data(data['general']['Date0'])}",
        institution="University of Colorado Anschutz",
        keywords=["mouse", "two photon", "electrophysiology", "retina"]
    )

    # process_analysis(nwbfile, data)
    process_data(nwbfile, data)
    # r = fill_data([
    #     np.zeros((1, 2)),
    #     np.zeros((2, 1, 3)),
    #     np.zeros((2,)),
    #     np.zeros((4, 4)),
    #     np.zeros((1,))
    # ])
    process_events(nwbfile, data)
    process_general(nwbfile, data)

    tw = 2

    now = pendulum.now()
    filename_to_save = "nwb-{}-{}_{}.nwb".format(now.month, now.day, now.hour)

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
