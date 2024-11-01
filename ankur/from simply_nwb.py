from simply_nwb.pipeline import NWBSession
import numpy as np

def extract_saccade_frames(nwb_file="predicted.nwb"):
    """
    Extract frames where saccades occur from the NWB file.
    
    Parameters:
        nwb_file (str): Path to the NWB file containing predicted saccades
        
    Returns:
        dict: Dictionary containing nasal and temporal saccade frames and their peak indices
    """
    # Load the NWB session
    sess = NWBSession(nwb_file)
    
    # Extract nasal and temporal saccade information
    epochs_nasal = sess.pull("PredictSaccades.saccades_predicted_nasal_epochs")
    epochs_temporal = sess.pull("PredictSaccades.saccades_predicted_temporal_epochs")
    
    nasal_peaks = sess.pull("PredictSaccades.saccades_predicted_nasal_peak_indices")
    temporal_peaks = sess.pull("PredictSaccades.saccades_predicted_temporal_peak_indices")
    
    # Calculate start and end frames for nasal saccades
    nasal_frames = []
    for epoch, peak in zip(epochs_nasal, nasal_peaks):
        start_frame = epoch[0]
        end_frame = epoch[1]
        peak_frame = peak
        nasal_frames.append({
            'start': int(start_frame),
            'peak': int(peak_frame),
            'end': int(end_frame)
        })
    
    # Calculate start and end frames for temporal saccades
    temporal_frames = []
    for epoch, peak in zip(epochs_temporal, temporal_peaks):
        start_frame = epoch[0]
        end_frame = epoch[1]
        peak_frame = peak
        temporal_frames.append({
            'start': int(start_frame),
            'peak': int(peak_frame),
            'end': int(end_frame)
        })
    
    # Get total counts
    total_nasal = len(nasal_frames)
    total_temporal = len(temporal_frames)
    
    return {
        'nasal_saccades': nasal_frames,
        'temporal_saccades': temporal_frames,
        'total_nasal': total_nasal,
        'total_temporal': total_temporal,
        'total_saccades': total_nasal + total_temporal
    }

# Example usage
if __name__ == "__main__":
    saccade_data = extract_saccade_frames()
    
    print(f"Total saccades found: {saccade_data['total_saccades']}")
    print(f"Nasal saccades: {saccade_data['total_nasal']}")
    print(f"Temporal saccades: {saccade_data['total_temporal']}")
    
    # Print first few saccades of each type
    print("\nFirst 5 nasal saccades:")
    for i, saccade in enumerate(saccade_data['nasal_saccades'][:5]):
        print(f"Saccade {i+1}: Start frame: {saccade['start']}, Peak frame: {saccade['peak']}, End frame: {saccade['end']}")
    
    print("\nFirst 5 temporal saccades:")
    for i, saccade in enumerate(saccade_data['temporal_saccades'][:5]):
        print(f"Saccade {i+1}: Start frame: {saccade['start']}, Peak frame: {saccade['peak']}, End frame: {saccade['end']}")


        from simply_nwb.pipeline import NWBSession
import numpy as np

def diagnose_saccade_data(nwb_file="predicted.nwb"):
    """
    Diagnostic function to inspect all saccade-related data in the NWB file.
    """
    # Load the NWB session
    sess = NWBSession(nwb_file)
    
    # Print all available enrichments and keys
    print("Available enrichments:")
    print(sess.available_enrichments())
    print("\nAvailable keys in PredictSaccades:")
    print(sess.available_keys("PredictSaccades"))
    
    # Extract and print shapes of all relevant data
    print("\nData shapes:")
    
    # Waveforms
    nasal_waveforms = sess.pull("PredictSaccades.saccades_predicted_nasal_waveforms")
    temporal_waveforms = sess.pull("PredictSaccades.saccades_predicted_temporal_waveforms")
    print(f"Nasal waveforms shape: {nasal_waveforms.shape if nasal_waveforms is not None else 'None'}")
    print(f"Temporal waveforms shape: {temporal_waveforms.shape if temporal_waveforms is not None else 'None'}")
    
    # Epochs
    epochs_nasal = sess.pull("PredictSaccades.saccades_predicted_nasal_epochs")
    epochs_temporal = sess.pull("PredictSaccades.saccades_predicted_temporal_epochs")
    print(f"Nasal epochs shape: {epochs_nasal.shape if epochs_nasal is not None else 'None'}")
    print(f"Temporal epochs shape: {epochs_temporal.shape if epochs_temporal is not None else 'None'}")
    
    # Peaks
    nasal_peaks = sess.pull("PredictSaccades.saccades_predicted_nasal_peak_indices")
    temporal_peaks = sess.pull("PredictSaccades.saccades_predicted_temporal_peak_indices")
    print(f"Nasal peaks shape: {nasal_peaks.shape if nasal_peaks is not None else 'None'}")
    print(f"Temporal peaks shape: {temporal_peaks.shape if temporal_peaks is not None else 'None'}")
    
    # Try to get putative saccades data
    try:
        putative_data = sess.pull("PutativeSaccades.putative_saccade_times")
        print(f"\nPutative saccades shape: {putative_data.shape if putative_data is not None else 'None'}")
    except:
        print("\nNo putative saccades data found")
    
    # Print first few values from each array
    print("\nFirst few values:")
    print("Nasal waveforms first shape:", nasal_waveforms[0].shape if nasal_waveforms is not None else 'None')
    print("Temporal waveforms first shape:", temporal_waveforms[0].shape if temporal_waveforms is not None else 'None')
    
    if epochs_nasal is not None and len(epochs_nasal) > 0:
        print("First nasal epoch:", epochs_nasal[0])
    if epochs_temporal is not None and len(epochs_temporal) > 0:
        print("First temporal epoch:", epochs_temporal[0])
        
    # Calculate totals
    total_nasal = nasal_waveforms.shape[0] if nasal_waveforms is not None else 0
    total_temporal = temporal_waveforms.shape[0] if temporal_waveforms is not None else 0
    print(f"\nTotal saccades in waveforms: {total_nasal + total_temporal}")
    
    # Try to get any other relevant keys that might contain saccade data
    all_keys = sess.available_keys("PredictSaccades")
    print("\nAll available keys that might contain saccade information:")
    for key in all_keys:
        if "saccade" in key.lower():
            try:
                data = sess.pull(f"PredictSaccades.{key}")
                print(f"{key}: shape {data.shape if hasattr(data, 'shape') else 'no shape'}")
            except:
                print(f"Could not pull data for {key}")

if __name__ == "__main__":
    diagnose_saccade_data()