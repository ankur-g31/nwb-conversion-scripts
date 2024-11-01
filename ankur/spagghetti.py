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


CSV_MAPPING = {
    "x_center": "Pupil_x",
    "y_center": "Pupil_y",
    "likelihood": "Pupil_likelihood",
    # "x_center": "Middle_x",
    # "y_center": "Middle_y",
    # "likelihood": "Middle_likelihood",

}

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

sess = NWBSession("putative.nwb")  # Load in the session we would like to enrich to predictive saccades
enrich = PredictedSaccadeGUIEnrichment(200, ["putative.nwb", "putative.nwb"], 120, putative_kwargs=CSV_MAPPING)
sess.enrich(enrich)

#print(sess.available_enrichments())
#print(sess.available_keys("PredictSaccades"))
print(sess.available_keys("PutativeSaccades"))
nasal = sess.pull("PredictSaccades.saccades_predicted_nasal_waveforms")[:, :, 0]
temporal = sess.pull("PredictSaccades.saccades_predicted_temporal_waveforms")[:, :, 0]

print(f'nasla is {nasal.shape}')
#print(sess.available_keys("predictSaccades"))
sess_dict = sess.to_dict()
#print(sess_dict['PredictSaccades']['saccades_predicted_nasal_peak_indices'])
print(sess_dict['PutativeSaccades']['saccades_fps'])
#putativeSaccades


# numpy array of epochs with apparent 6 unit delta between them
#sess_dict['PredictSaccades']['saccades_predicted_temporal_epochs']