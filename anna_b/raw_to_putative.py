import glob
import os
import uuid

import pendulum
from pynwb import NWBHDF5IO
from pynwb.file import Subject
from simply_nwb import SimpleNWB
from simply_nwb.pipeline import NWBSession
from simply_nwb.pipeline.enrichments.saccades import PutativeSaccadesEnrichment


SESSION_FPS = 150


def create_nwb(foldername):
    # desc = open(os.path.join(foldername, "experiment_description.txt")).read()

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
    return nwbfile


def search_for_data(prefix):
    fns = []
    for filename in os.listdir(prefix):
        if filename.endswith(".nwb") and filename.startswith("raw-"):
            fns.append(os.path.join(filename))
    return fns


def process_folder(nwb_filename, outputdir, prefix):
    print(f"Processing '{nwb_filename}'")
    new_filename = os.path.basename(nwb_filename)[len("raw-"):]
    new_filename = os.path.join(prefix, new_filename)

    enrichment = PutativeSaccadesEnrichment(fps=SESSION_FPS)
    sess = NWBSession(os.path.join(prefix, nwb_filename))
    sess.enrich(enrichment)
    sess.save(os.path.join(outputdir, new_filename))  # Save to file
    del sess
    fp.close()


def main():
    prefix = "raw/"  # TODO Change me to dir of sessions
    outputdir = "putative"

    datafiles = search_for_data(prefix)
    if not os.path.exists(outputdir):
        os.mkdir(outputdir)

    for nwb_filename in datafiles:
        process_folder(nwb_filename, outputdir, prefix)

    tw = 2


if __name__ == "__main__":
    main()

