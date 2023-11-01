from simply_nwb import SimpleNWB
import pendulum
import uuid
import pandas as pd
import os
from simply_nwb.transforms import tif_read_subfolder_directory, tif_read_directory
import glob

NWB_FILENAME = "test.nwb"  # Name of the outputted NWB file

SESSION_NOTES = "notes about the session go here"
SESSION_FOLDER = "data/session1"

# TWO_PHOTON_ROOT_PATH = "\\\\data.ucdenver.pvt\\dept\\SOM\\PHYS\\PolegPoslkyLab\\2023\\May"  # For testing on spencer's machine
TWO_PHOTON_ROOT_PATH = "Z:\\PolegPoslkyLab\\2023\\May\\"

TWO_PHOTON_FOLDER = os.path.join(
    TWO_PHOTON_ROOT_PATH,
    "230504_opn4cre_gcamp_AAV_tm_14dpi_bilat"
)

# SPINNING_DISC_ROOT_PATH = "\\\\data.ucdenver.pvt\\dept\\SOM\\PHYS\\PolegPoslkyLab\\John microscopy backup\\230130_spinningdisc\\" # For testing on spencer's machine
SPINNING_DISC_ROOT_PATH = "Z:\\PolegPoslkyLab\\John microscopy backup\\230130_spinningdisc\\"

SPINNING_DISC_FOLDER = os.path.join(
    SPINNING_DISC_ROOT_PATH,
    "Jan9_cup_M4E2_1"
)

EMISSION_WAVELENGTH = 550.0
EXCITATION_LAMBDA = 920.0
RETINAL_LAYER = "GCL"
TWO_PHOTON_SAMPLING_RATE = 10.2


PERG_FOLDER_NAME = "*_pERG"
# Expect pERGs under 'data/sessionName/<something>_pERG


def process_perg_data(nwbfile):
    results = glob.glob(os.path.join(SESSION_FOLDER, PERG_FOLDER_NAME))
    if not results:
        raise ValueError("Unable to find pERG folder!")
    perg_folder = results[0]
    try:
        SimpleNWB.p_erg_add_folder(
            nwbfile,
            foldername=perg_folder,
            file_pattern="*_raw.txt",
            table_name="p_ergs_raw",
            description="Raw pERGs"
        )
    except ValueError as e:
        print(f"Skipping pERG raw, none found. Error {str(e)}")

    try:
        SimpleNWB.p_erg_add_folder(
            nwbfile,
            foldername=perg_folder,
            file_pattern="*_fold.txt",
            table_name="p_ergs_fold",
            description="Fold pERGs"
        )
    except ValueError as e:
        print(f"Skipping pERG fold, none found. Error {str(e)}")


def main():
    print("Creating NWB..")
    nwbfile = SimpleNWB.create_nwb(
        session_description=f"Injury Notes: {SESSION_NOTES}",
        session_start_time=pendulum.now(),
        session_id=str(uuid.uuid4()),
        experimenter="Gaynes, John",
        institution="University of Colorado Anschutz",
        lab="Poleg-Polsky Lab",
        experiment_description="TODO PUT IN LATER",
    )

    print("Reading pERG data..")
    process_perg_data(nwbfile)

    print("Reading combined data..")
    data_frame = pd.read_csv(os.path.join(SESSION_FOLDER, "combined_data.csv"))

    print("Adding combined data to NWB..")
    SimpleNWB.processing_add_dataframe(
        nwbfile,
        processed_name="combined",
        processed_description="Combined experimental data",
        data=data_frame
    )

    print("Reading spinningdisc images..")
    spinning_images = tif_read_directory(foldername=SPINNING_DISC_FOLDER,
                                         filename_glob="*.ome.tif",
                                         skip_on_error=True)

    SimpleNWB.tif_add_as_processing_imageseries(
        nwbfile,
        name="spinningdisc",
        processing_module_name="imaging",
        numpy_data=spinning_images,
        sampling_rate=1.0,
        description="Spinning disc images",
        starting_time=0.0,
        chunking=True,  # Images are large so want both chunking and compression
        compression=True
    )

    print("Reading TIFs from subfolder..")
    images = tif_read_subfolder_directory(
        parent_folder=TWO_PHOTON_FOLDER,
        subfolder_glob="file_*",
        file_glob="Image_scan*",
        skip_on_error=True
    )

    print("Adding TIFs to NWB..")
    SimpleNWB.two_photon_add_data(
        nwbfile,
        device_name="ThorLabTwoPhoton",
        device_description="Thor Lab Two Photon Microscope ex vivo",
        device_manufacturer="ThorLabs",
        optical_channel_description="GCAMP + RGCs",
        optical_channel_emission_lambda=EMISSION_WAVELENGTH,
        imaging_name="2p-rgc-gcamp",
        imaging_rate=10.0,
        excitation_lambda=EXCITATION_LAMBDA,
        indicator="GCAMP",
        location=RETINAL_LAYER,
        grid_spacing=[1.0, 1.0],
        grid_spacing_unit="um",
        origin_coords=[0.0, 0.0],
        origin_coords_unit="um",
        two_photon_rate=TWO_PHOTON_SAMPLING_RATE,
        two_photon_unit="hz",
        photon_series_name="2p",
        image_data=images
    )

    print("Writing NWB to file..")
    SimpleNWB.write(nwbfile, NWB_FILENAME)

    print("Done!")


if __name__ == "__main__":
    main()
