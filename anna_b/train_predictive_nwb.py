#EDIT FOLDERS IF WE WANT AND NUMBER OF SACCADES
#IN VS CODE TERMINAL:
#cd anna_b
#python train_predictive_nwb.py

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

# Get the filenames for the timestamps.txt and dlc CSV
input_folder = "putative/"
output_folder = "predicted/"
num_saccades = 100
skip_load_trainingdata = False

files = glob.glob(os.path.join(input_folder, "**.nwb"))
print("Creating enrichment..")
enrich = PredictedSaccadeGUIEnrichment(200, select_putative_training_nwbs(files, skip_load_trainingdata), num_saccades, 
{"x_center": "center_x", 
 "y_center": "center_y", 
 "likelihood": "center_likelihood"
})

for file in files:
    savefn = os.path.join(output_folder, f"predictive-{os.path.basename(file)[:-len('.nwb')]}.nwb")
    if os.path.exists(savefn):
        print(f"File exists, skipping '{savefn}'..")
    print(f"Loading '{file}'..")
    sess = NWBSession(file)
    # Take our putative saccades and do the actual prediction for the start, end time, and time location
    print("Enriching..")
    sess.enrich(enrich)
    print("Saving to NWB")
    print(f"Saving to file {savefn}..")
    sess.save(savefn)  # Save as our finalized session, ready for analysis
    tw = 2
