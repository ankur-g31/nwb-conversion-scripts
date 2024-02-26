import h5py
import numpy as np
from dict_plus.utils import SimpleFlattener
from hdmf.backends.hdf5 import H5DataIO
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


def fill_data(listdata):
    # Takes a list of numpy arrays and fills them so that all arrays are the same dimensions, but fills with NaN values
    # listdata = [arr1, ..]
    largest_dim_lens = []
    for v in listdata:
        if v is not None:
            # Find the largest dimension among all the list entries
            if len(largest_dim_lens) < len(v.shape):
                [largest_dim_lens.append(0) for _ in
                 range(len(v.shape) - len(largest_dim_lens))]  # Add new dimension maxes
            for idx, dim in enumerate(v.shape):
                if largest_dim_lens[idx] < dim:
                    largest_dim_lens[idx] = dim

    fill = np.ma.masked
    if listdata[0] is None:  # Can't fill empty values, return nothing
        return np.array([[]])

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


def process_analysis_events(nwbfile, data):
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


def process_analysis_traces(nwbfile, data):
    all_keys = list(data)

    fl = SimpleFlattener(simple_types=[np.ndarray, type(None), h5py._hl.dataset.Dataset],
                         dict_types=[h5py._hl.group.Group])
    for subkey in all_keys:
        if subkey == "events":
            continue
        flattened = {k: v[:] for k, v in fl.flatten(data[subkey]).items()}  # Convert to numpy array

        for k, v in flattened.items():
            SimpleNWB.add_to_processing_module(
                nwbfile,
                DynamicTable(
                    name=k,
                    description="Analysis Traces",
                    columns=[VectorData(
                        name=k,
                        data=H5DataIO(
                            data=v,
                            compression=True,
                            chunks=True
                        ),
                        description="Analysis Traces"
                    )]
                ), f"analysis_{subkey}", f"Analysis for {subkey}")

    tw = 2


def process_analysis(nwbfile, d):
    data = d["analysis"]

    # Process Events
    print("Processing Analysis Events..")
    process_analysis_events(nwbfile, data)

    # Process Traces
    print("Processing Analysis Traces..")
    process_analysis_traces(nwbfile, data)


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
        if trace_id in data:  # For each trace
            trace = data[trace_id]
            print(f"Processing Trace '{trace_id}'..")
            # Process sweeps
            for sweep_id, sweep_val in trace.items():  # Check each sweep in each trace
                if not sweep_id.startswith("sweep_"):
                    continue  # Skip over non-sweep data

                sweep_data["trace_ids"].append(trace_id)
                sweep_data["sweep_ids"].append(sweep_id)
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
    two_photon = ("two_photon", "file_name")
    # NWB doesn't like bytes as strings
    two_photon_data = [(v or [b''])[:][0].decode("utf-8") for v in sweep_data.pop(two_photon)]

    print("Resizing arrays, might take a minute..")
    sweep_data = {get_name(k): fill_data(v) for k, v in sweep_data.items()}
    sweep_data["filedata"] = sweep_data.pop(get_name("filedata"))

    sweep_data[get_name(two_photon)] = two_photon_data
    for f in id_fields:
        sweep_data[f] = tmp.pop(f)
    print("Writing data to NWB file and compressing..")
    for k, v in sweep_data.items():
        SimpleNWB.add_to_processing_module(
            nwbfile,
            DynamicTable(
                name=f"data_{k}",
                description="Sweep data",
                columns=[VectorData(
                    name=k,
                    data=H5DataIO(
                        data=v,
                        compression=True,
                        chunks=True
                    ),
                    description="Sweep data"
                )]
            ), "data", "Sweep data")


def process_events(nwbfile, data):
    event_datas = {}

    all_subkeys = [list(data["events"][v]) for v in list(data["events"])]  # Create a set of all possible subkeys
    possible_subkeys = set()
    for subk in all_subkeys:
        [possible_subkeys.add(subk_val) for subk_val in subk]

    def add(k, v, arr):
        if k in arr:
            arr[k].append(v)
        else:
            arr[k] = [v]

    eventdata = data["events"]
    basickeys = ["T_2pZstack", "T_comment", "eventTime"]

    for event in list(data["events"]):
        # T_Event - looks like string info in a 10,2 arr
        add("event_num", event, event_datas)
        t_eventdata = eventdata[event].get("T_Event", np.full((10, 2), b''))[:]
        add("T_Event", np.array([[vv.decode("utf-8") for vv in v] for v in t_eventdata]), event_datas)

        # Basic single value keys
        for k in basickeys:
            add(k, eventdata[event].get(k, [b''])[0].decode("utf-8"), event_datas)

        two_photon = eventdata[event].get("two_photon", {})
        for k, v in two_photon.items():
            if k.startswith("file_") and (k.endswith("_ChanB") or k.endswith("_ChanA")):
                add("two_photon_datas", v[:], event_datas)
                add("two_photon_datas_ids", [event, k], event_datas)

    for k, v in event_datas.items():
        if k == "two_photon_datas":  # Fill empty values for two_photon data
            v = fill_data(v)
        v = np.array(v)
        SimpleNWB.add_to_processing_module(
            nwbfile,
            DynamicTable(
                name=k,
                description="Events data",
                columns=[VectorData(
                    name=k,
                    data=v,
                    description="Events data"
                )]
            ), "events", "Events data")


def process_general(nwbfile, d):
    data = dictify_hd5(d["general"])
    data = {k: np.array(v) for k, v in data.items()}

    for k, v in data.items():
        SimpleNWB.add_to_processing_module(
            nwbfile,
            DynamicTable(
                name=k,
                description="General Information",
                columns=[VectorData(
                    name=k,
                    data=v,
                    description="General Information"
                )]
            ), "general", "General Information")


def main(h5_source_file, nwb_output_filename):
    # TODO Read hdf5 file here, populate data and insert into NWB
    data = h5py.File(h5_source_file)

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

    print("Processing Analysis Section..")
    process_analysis(nwbfile, data)
    print("Processing Data Section..")
    process_data(nwbfile, data)
    print("Processing Events Section..")
    process_events(nwbfile, data)
    print("Processing General Section..")
    process_general(nwbfile, data)

    now = pendulum.now()
    filename_to_save = "{}-{}-{}_{}{}{}.nwb".format(nwb_output_filename, now.month, now.day, now.hour, now.minute,
                                                    now.second)

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


def test_all():
    drive_letter = "F:"
    path = f"{drive_letter}\\PolegPolskyConversionData"
    files = []
    for f in os.listdir(path):
        if f.endswith(".h5"):
            files.append(f"{path}\\{f}")

    for f in files:
        print(f"Trying {f}")
        main(f, "test.nwb")


if __name__ == "__main__":
    # TODO remove me
    # import sys
    # sys.argv = [sys.argv[0], "example_dataset.h5", "converted.nwb"]
    # TODO end remove me

    test_all()
    # TODO Uncomment me
    # arg_parser = argparse.ArgumentParser(
    #     prog="polegpolsky_convert_nwb.py",  # TODO rename program?
    #     description="Converts incoming formatted hdf5 file into NWB"
    # )
    # arg_parser.add_argument("h5_filename")
    # arg_parser.add_argument("nwb_filename")
    # arg_parser.add_argument("-f", "--force", action="store_true")
    #
    # args = arg_parser.parse_args()
    #
    # h5_source_filename = args.h5_filename
    # nwb_output_filename = args.nwb_filename
    #
    # if not os.path.exists(h5_source_filename):
    #     raise FileNotFoundError(f"Could not find H5 source file '{h5_source_filename}'")
    #
    # if os.path.exists(nwb_output_filename) and not args.force:
    #     raise ValueError("NWB output filename exists already! Use the -f option to force overwrite!")
    #
    # main(h5_source_filename, nwb_output_filename)


