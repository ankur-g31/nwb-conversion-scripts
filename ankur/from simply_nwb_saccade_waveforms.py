from simply_nwb.pipeline import NWBSession
import numpy as np

def extract_all_saccade_frames(nwb_file="predicted.nwb"):
    """
    Extract frames for all saccade waveforms from the NWB file.
    
    Parameters:
        nwb_file (str): Path to the NWB file containing predicted saccades
        
    Returns:
        dict: Dictionary containing all saccade waveforms and their frame information
    """
    # Load the NWB session
    sess = NWBSession(nwb_file)
    
    # Extract all waveforms
    nasal_waveforms = sess.pull("PredictSaccades.saccades_predicted_nasal_waveforms")
    temporal_waveforms = sess.pull("PredictSaccades.saccades_predicted_temporal_waveforms")
    
    # Get epochs and peaks
    epochs_nasal = sess.pull("PredictSaccades.saccades_predicted_nasal_epochs")
    epochs_temporal = sess.pull("PredictSaccades.saccades_predicted_temporal_epochs")
    nasal_peaks = sess.pull("PredictSaccades.saccades_predicted_nasal_peak_indices")
    temporal_peaks = sess.pull("PredictSaccades.saccades_predicted_temporal_peak_indices")
    
    # Calculate frames for all waveforms
    all_saccades = []
    
    # Process nasal waveforms
    if nasal_waveforms is not None:
        for i in range(nasal_waveforms.shape[0]):
            waveform = nasal_waveforms[i, :, 0]  # Get first dimension of waveform
            if i < len(epochs_nasal):
                start_frame = int(epochs_nasal[i][0])
                end_frame = int(epochs_nasal[i][1])
                peak_frame = int(nasal_peaks[i]) if i < len(nasal_peaks) else None
            else:
                # For waveforms without epoch data, estimate frames based on waveform length
                start_frame = i * len(waveform)
                end_frame = start_frame + len(waveform)
                peak_frame = None
                
            all_saccades.append({
                'type': 'nasal',
                'start': start_frame,
                'end': end_frame,
                'peak': peak_frame,
                'waveform': waveform
            })
    
    # Process temporal waveforms
    if temporal_waveforms is not None:
        for i in range(temporal_waveforms.shape[0]):
            waveform = temporal_waveforms[i, :, 0]  # Get first dimension of waveform
            if i < len(epochs_temporal):
                start_frame = int(epochs_temporal[i][0])
                end_frame = int(epochs_temporal[i][1])
                peak_frame = int(temporal_peaks[i]) if i < len(temporal_peaks) else None
            else:
                # For waveforms without epoch data, estimate frames based on waveform length
                start_frame = i * len(waveform)
                end_frame = start_frame + len(waveform)
                peak_frame = None
                
            all_saccades.append({
                'type': 'temporal',
                'start': start_frame,
                'end': end_frame,
                'peak': peak_frame,
                'waveform': waveform
            })
    
    return {
        'all_saccades': all_saccades,
        'total_saccades': len(all_saccades),
        'waveform_shapes': {
            'nasal': nasal_waveforms.shape if nasal_waveforms is not None else None,
            'temporal': temporal_waveforms.shape if temporal_waveforms is not None else None
        }
    }

# Example usage
if __name__ == "__main__":
    saccade_data = extract_all_saccade_frames()
    
    print(f"Total saccades found: {saccade_data['total_saccades']}")
    print(f"Waveform shapes:")
    print(f"  Nasal: {saccade_data['waveform_shapes']['nasal']}")
    print(f"  Temporal: {saccade_data['waveform_shapes']['temporal']}")
    
    # Print first few saccades
    print("\nFirst 5 saccades:")
    for i, saccade in enumerate(saccade_data['all_saccades'][:5]):
        print(f"Saccade {i+1}: Type: {saccade['type']}")
        print(f"  Start frame: {saccade['start']}")
        print(f"  End frame: {saccade['end']}")
        print(f"  Peak frame: {saccade['peak']}")
        print(f"  Waveform shape: {saccade['waveform'].shape}")