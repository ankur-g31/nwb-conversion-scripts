import os
from io import StringIO
import tempfile
import numpy as np
import pendulum
from pynwb import NWBHDF5IO
from pynwb.file import Subject
from simply_nwb import SimpleNWB
from simply_nwb.pipeline import NWBSession
from simply_nwb.pipeline.enrichments.saccades import PutativeSaccadesEnrichment
from simply_nwb.pipeline.enrichments.saccades.predict_gui import PredictedSaccadeGUIEnrichment
import matplotlib.pyplot as plt


def create_nwb():
    # Create the NWB file, TODO Put data in here about mouse and experiment
    nwbfile = SimpleNWB.create_nwb(
        # Required
        session_description="Mouse cookie eating session",
        # Subtract 1 year so we don't run into the 'NWB start time is at a greater date than current' issue
        session_start_time=pendulum.now().subtract(years=1),
        experimenter=["Schmoe, Joe"],
        lab="Felsen Lab",
        experiment_description="Gave a mouse a cookie",
        # Optional
        identifier="cookie_0",
        subject=Subject(**{
            "subject_id": "1",
            "age": "P90D",  # ISO-8601 for 90 days duration
            "strain": "TypeOfMouseGoesHere",  # If no specific used, 'Wild Strain'
            "description": "Mouse#2 idk",
            "sex": "M",  # M - Male, F - Female, U - unknown, O - other
            # NCBI Taxonomy link or Latin Binomial (e.g.'Rattus norvegicus')
            "species": "http://purl.obolibrary.org/obo/NCBITaxon_10116",
        }),
        session_id="session0",
        institution="CU Anschutz",
        keywords=["mouse"],
        # related_publications="DOI::LINK GOES HERE FOR RELATED PUBLICATIONS"
    )
    # For creating a dummy test nwb you can do SimpleNWB.test_nwb() to get an nwb object in memory
    return nwbfile


CSV_MAPPING = {
    #"x_center": "Pupil_x",
    #"y_center": "Pupil_y",
    #"likelihood": "Pupil_likelihood",
     "x_center": "Middle_x",
     "y_center": "Middle_y",
     "likelihood": "Middle_likelihood",

}

def create_putative_nwb(dlc_filepath, timestamps):
    # Create a NWB file to put our data into
    print("Creating base NWB..")
    raw_nwbfile = create_nwb()  # This is the RAW nwbfile, direct output from a 'conversion script' in this example we just make a dummy one

    # Prepare an enrichment object to be run, and insert the raw data into our nwb in memory
    enrichment = PutativeSaccadesEnrichment.from_raw(
        raw_nwbfile, dlc_filepath, timestamps, 
        units=["px", "px", "px", "p", "px", "px", "p", "px", "px", "p", "px", "px", "p", "px", "px", "p"],
        likelihood_threshold=0.7,
        #fps=150,
        **CSV_MAPPING
        )

    sess = NWBSession(raw_nwbfile)  # Create a session using our in-memory NWB
    # Enrich our nwb into 'putative' saccades (what we think *might* be a saccade)
    print("Enriching to putative NWB..")
    sess.enrich(enrichment)

    sess.save("putative.nwb")  # Save to file


def graph_saccades(sess: NWBSession):
    print(sess.available_enrichments())
    print(sess.available_keys("PredictSaccades"))
    nasal = sess.pull("PredictSaccades.saccades_predicted_nasal_waveforms")[:, :, 0]
    temporal = sess.pull("PredictSaccades.saccades_predicted_temporal_waveforms")[:, :, 0]

    [plt.plot(d, color="orange") for d in temporal]
    [plt.plot(d, color="blue") for d in nasal]

    plt.show()

    epochs_nasal = sess.pull("PredictSaccades.saccades_predicted_nasal_epochs")
    nasal_peaks = sess.pull("PredictSaccades.saccades_predicted_nasal_peak_indices")

    startstop_idxs = ((epochs_nasal - nasal_peaks[:, None]) + 40)
    for i in range(10):
        plt.plot(nasal[i])
        plt.vlines(startstop_idxs[i, 0], np.min(nasal[i]), np.max(nasal[i]))
        plt.vlines(startstop_idxs[i, 1], np.min(nasal[i]), np.max(nasal[i]))
    plt.show()

    tw = 2


def main():
    # Get the filenames for the timestamps.txt and dlc CSV
    # prefix = "example_data"
    # dlc_filepath = os.path.abspath(os.path.join(prefix, "20240410_unitME_session001_rightCam-0000DLC_resnet50_GazerMay24shuffle1_1030000.csv"))
    
    dlc_filepath = "C:\\Users\\Ankur\\Documents\\GitHub\\nwb-conversion-scripts\\nwb-conversion-scripts\\ankur\\20241030_unitB01_session002_flirCam-0000DLC_Resnet50_Fixed_Eye_PositionOct28shuffle1_snapshot_200_filtered.csv"
   
    timestamps = "C:\\Users\\Ankur\\Documents\\GitHub\\nwb-conversion-scripts\\nwb-conversion-scripts\\ankur\\20241030_unitB01_session002_flirCam_timestamps.txt"

    
    create_putative_nwb(dlc_filepath, timestamps)

    sess = NWBSession("putative.nwb")  # Load in the session we would like to enrich to predictive saccades


    # nasal = sess.pull("PredictSaccades.saccades_predicted_nasal_waveforms")[:, :, 0]
    # temporal = sess.pull("PredictSaccades.saccades_predicted_temporal_waveforms")[:, :, 0]

    # print(f'nasla is {nasal.shape}')

    # Take our putative saccades and do the actual prediction for the start, end time, and time location
    print("Adding predictive data..")

    # For 'putative_kwargs' put the arguments in dict kwarg style for the PutativeSaccadesEnrichment() if it is non-default. Format like {"x_center": .., }
    # this example there are no extra kwargs, but if you name your DLC columns different, you will need to tell it which column names relate to your data
    # columns will be concatenated with the above column, so something like
    # a,b,c
    # x,y,z
    # will be turned into the keys a_x, b_y, and z_c
    # so you would use {"x_center": "a_x", ..}
    # Normally for list_of_putative_nwbs_filenames you would want more than one session, this is where the training data
    # will be sampled from

    # fn = "D:\\spencer_data\\putative_nwbs"
    # l = os.listdir(fn)
    # putats = [os.path.join(fn, v) for v in l[:5]]
    # enrich = PredictedSaccadeGUIEnrichment(200, putats, 20, putative_kwargs={})

    enrich = PredictedSaccadeGUIEnrichment(150, ["putative.nwb", "putative.nwb"], 120, putative_kwargs=CSV_MAPPING)
    """sess_dict = sess.to_dict()
    print(sess_dict['PredictSaccades']['saccades_fps'])"""

   

    # This will open two guis, where you will identify which direction the saccade is, and what the start and stop is
    # when the gui data entry is done, it will begin training the classifier models. The models are saved so if
    # something breaks it can be re-started easily
    # Next time you enrich an NWB, if the model files are in the directory where this script is being run, it will use
    # those instead of training a new model
    # You will need to label at least 10 directional saccade, at least 2 of each direction (BARE MINIMUM, NOT GOOD FOR ACTUAL DATA)
    # and at least 10 epochs
    # To label direction, click the radio button (circle button) on the left and then click next
    # To label epoch timing, select start/stop and move the line with the arrow keys to the approximate start/stop of the saccade

    sess.enrich(enrich)
    print("Saving to NWB")
    sess.save("predicted.nwb")  # Save as our finalized session, ready for analysis
    fps = sess.pull("PredictSaccades.saccades_fps")[0]
    #print(f"Recording FPS: {fps}")
    temporal_epochs=sess.pull("PredictSaccades.saccades_predicted_temporal_epochs")
    fps = sess.pull("PredictSaccades.saccades_fps")[0]  # Get the FPS
    sess.description("PredictSaccades")
    #starttime = arr[saccnum][0]
    #print(sess.description("PredictSaccades"))
    temporal_epochs = sess.pull("PredictSaccades.saccades_predicted_temporal_epochs")
    nasal_epochs = sess.pull("PredictSaccades.saccades_predicted_nasal_epochs")

    # --- Combine nasal and temporal epochs ---
    all_epochs = np.concatenate((temporal_epochs, nasal_epochs), axis=0)

    # Sort all epochs by start time
    all_epochs = all_epochs[all_epochs[:, 0].argsort()]

    # Extract start and end times (assuming epochs are in frames)
    start_times = all_epochs[:, 0]
    end_times = all_epochs[:, 1]

    # --- Account for the incorrect FPS ---
    actual_fps = 150.0  # The actual recording FPS
    nwb_fps = sess.pull("PredictSaccades.saccades_fps")[0]  # The (incorrect) FPS in the NWB file

    # Convert frame numbers to seconds using the ACTUAL FPS
    start_times_seconds = start_times / actual_fps
    end_times_seconds = end_times / actual_fps

    
    """# Extract start and end times in SECONDS
    start_times_seconds = all_epochs[:, 0] / fps
    end_times_seconds = all_epochs[:, 1] / fps"""

    # --- Save to a text file (in frames) ---
    output_filename_frames = "saccade_timings_frames.txt"
    with open(output_filename_frames, "w") as f:
        f.write("Saccade\tStart Frame\tEnd Frame\n")  # Header row
        for i, (start, end) in enumerate(zip(start_times, end_times)):
            f.write(f"{i+1}\t{start:.2f}\t{end:.2f}\n")

    print(f"Saccade timings (frames) saved to: {output_filename_frames}")

    # --- Save to a text file (in seconds) ---
    output_filename_seconds = "saccade_timings_seconds.txt"
    with open(output_filename_seconds, "w") as f:
        f.write("Saccade\tStart Time (s)\tEnd Time (s)\n")  # Header row
        for i, (start, end) in enumerate(zip(start_times_seconds, end_times_seconds)):
            f.write(f"{i+1}\t{start:.2f}\t{end:.2f}\n")

    print(f"Saccade timings (seconds) saved to: {output_filename_seconds}")


    """# Extract start and end times (assuming epochs are in frames)
    start_times = temporal_epochs[:, 0] 
    end_times = temporal_epochs[:, 1]

    # Extract start and end times in SECONDS
    start_times_seconds = temporal_epochs[:, 0] / fps
    end_times_seconds = temporal_epochs[:, 1] / fps

    # --- Save to a text file ---
    output_filename = "saccade_timings.txt"
    with open(output_filename, "w") as f:
        f.write("Saccade\tStart Frame\tEnd Frame\n")  # Header row
        for i, (start, end) in enumerate(zip(start_times, end_times)):
            f.write(f"{i+1}\t{start:.2f}\t{end:.2f}\n")

    print(f"Saccade timings saved to: {output_filename}")

    # --- Save to a text file (in seconds) ---
    output_filename_seconds = "saccade_timings_seconds.txt"
    with open(output_filename_seconds, "w") as f:
        f.write("Saccade\tStart Time (s)\tEnd Time (s)\n")  # Header row
        for i, (start, end) in enumerate(zip(start_times_seconds, end_times_seconds)):
            f.write(f"{i+1}\t{start:.2f}\t{end:.2f}\n")

    print(f"Saccade timings (seconds) saved to: {output_filename_seconds}")"""

    nasal_saccades = sess.pull("PredictSaccades.saccades_predicted_nasal_waveforms")
    num_nasal_saccades = nasal_saccades.shape[0]

    temporal_saccades = sess.pull("PredictSaccades.saccades_predicted_temporal_waveforms")
    num_temporal_saccades = temporal_saccades.shape[0]

    total_saccades = num_nasal_saccades + num_temporal_saccades
    
    
    print(f"Number of nasal saccades: {num_nasal_saccades}")
    print(f"Number of temporal saccades: {num_temporal_saccades}")
    print(f"Total saccades: {total_saccades}")
    

    graph_saccades(sess)
    tw = 2


if __name__ == "__main__":
    main()
