import glob
import os
import random

import pendulum
from pynwb import NWBHDF5IO
from pynwb.file import Subject
from simply_nwb import SimpleNWB
from simply_nwb.pipeline import NWBSession
from simply_nwb.pipeline.enrichments.saccades import PutativeSaccadesEnrichment
from simply_nwb.pipeline.enrichments.saccades.predict_gui import PredictedSaccadeGUIEnrichment


def select_putative_training_nwbs(list_of_nwbs, doskip):
    if doskip:
        return [list_of_nwbs[0]]
    num = len(list_of_nwbs)
    random.shuffle(list_of_nwbs)
    return list_of_nwbs[:5]

def main():
    # Get the filenames for the timestamps.txt and dlc CSV
    input_folder = "C:\\Users\\minjarec\\OneDrive - The University of Colorado Denver\\Documents\\putative_nwbs"
    output_folder = "C:\\Users\\minjarec\\OneDrive - The University of Colorado Denver\\Documents\\predict_nwbs"
    num_training_samples = 40  # TODO Change me?
    skip_load_trainingdata = True

    files = glob.glob(os.path.join(input_folder, "**.nwb"))
    print("Creating enrichment..")
    enrich = PredictedSaccadeGUIEnrichment(200, select_putative_training_nwbs(files, skip_load_trainingdata), num_training_samples, {})

    for file in files:
        savefn = os.path.join(output_folder, f"predictive-{os.path.basename(file)[:-len('.nwb')]}.nwb")
        if os.path.exists(savefn):
            print(f"File exists, skipping '{savefn}'..")
            continue
        print(f"Loading '{file}'..")
        sess = NWBSession(file)
        # Take our putative saccades and do the actual prediction for the start, end time, and time location
        print("Enriching..")
        sess.enrich(enrich)
        print("Saving to NWB")
        print(f"Saving to file {savefn}..")
        sess.save(savefn)  # Save as our finalized session, ready for analysis
        tw = 2


if __name__ == "__main__":
    main()
