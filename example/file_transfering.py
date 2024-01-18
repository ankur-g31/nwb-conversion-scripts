from simply_nwb import NWBTransfer
from simply_nwb.transferring import OneWayFileSync


def oneway_simple():
    OneWayFileSync(
        # Note that the path can be something like a NAS ie \\10.1.2.3\\MyFiles\MyProject
        # Will watch the folder 'from_src' for files and changes
        "test_data/sync_src",
        # Will copy all new files / changes to this directory
        "test_data/sync_dst",
        # Include all files, could also do '*.txt' for all txt files, etc
        "*",
        delete_on_copy=True  # Will delete the file/folder from the src directory upon successful copy
    ).start()
    # Program will run continuously until killed


def remove_extension(filename):
    return filename.split(".")[0]


def oneway_complex():
    OneWayFileSync(
        # Will watch the folder 'from_src' for files and changes
        source_directory="test_data/sync_src",
        # Will copy all new files / changes to this directory
        destination_directory="test_data/sync_dst",
        watch_file_glob={
            # Copy all bmp files
            "*.bmp": {},
            # Will copy all <name>.txt files to 'TextFiles/myfile_name_me_<name>.py'
            # Will create directories under the destination folder
            "*.txt": {
                "filename": "TextFiles/myfile_{name}.py",
                "name_func": remove_extension
            }
        },
        delete_on_copy=True  # Will delete the file/folder from the src directory upon successful copy
    ).start()
    # Program will run continuously until killed


def nwb_transfer():
    transfer0 = NWBTransfer(
        nwb_file_location="test_data/mydata/fake.nwb",  # Where the NWB is
        raw_data_folder_location="test_data/mydata/raw_data",  # Raw data location
        # Note that the path can be something like a NAS ie \\10.1.2.3\\MyFiles\MyProject
        transfer_location_root="test_data/server_folder",  # Where the destination root is
        lab_name="FelsenLab",
        project_name="test_project",
        session_name="session0"
    )
    transfer0.upload()


if __name__ == "__main__":
    # oneway_simple()
    # oneway_complex()
    nwb_transfer()
