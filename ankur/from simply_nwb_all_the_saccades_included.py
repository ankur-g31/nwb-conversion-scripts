from simply_nwb.pipeline import NWBSession
import numpy as np

def extract_all_frames(nwb_file="predicted.nwb"):
    """
    Extract frames for all waveforms (nasal, temporal, and noise) from the NWB file.
    
    Parameters:
        nwb_file (str): Path to the NWB file containing predicted saccades
        
    Returns:
        dict: Dictionary containing all waveform information and their frame information
    """
    # Load the NWB session
    sess = NWBSession(nwb_file)
    
    # Extract all waveforms
    nasal_waveforms = sess.pull("PredictSaccades.saccades_predicted_nasal_waveforms")
    temporal_waveforms = sess.pull("PredictSaccades.saccades_predicted_temporal_waveforms")
    noise_waveforms = sess.pull("PredictSaccades.saccades_predicted_noise_waveforms")
    
    # Get epochs and peaks
    epochs_nasal = sess.pull("PredictSaccades.saccades_predicted_nasal_epochs")
    epochs_temporal = sess.pull("PredictSaccades.saccades_predicted_temporal_epochs")
    nasal_peaks = sess.pull("PredictSaccades.saccades_predicted_nasal_peak_indices")
    temporal_peaks = sess.pull("PredictSaccades.saccades_predicted_temporal_peak_indices")
    
    # Get FPS if available
    try:
        fps = sess.pull("PredictSaccades.saccades_fps")[0]
    except:
        fps = None
    
    all_events = []
    
    # Process nasal waveforms
    for i in range(nasal_waveforms.shape[0]):
        waveform = nasal_waveforms[i, :, :]  # Keep both dimensions of waveform
        start_frame = int(epochs_nasal[i][0])
        end_frame = int(epochs_nasal[i][1])
        peak_frame = int(nasal_peaks[i])
        
        all_events.append({
            'type': 'nasal',
            'start_frame': start_frame,
            'end_frame': end_frame,
            'peak_frame': peak_frame,
            'start_time': start_frame/fps if fps else None,
            'end_time': end_frame/fps if fps else None,
            'peak_time': peak_frame/fps if fps else None,
            'waveform': waveform
        })
    
    # Process temporal waveforms
    for i in range(temporal_waveforms.shape[0]):
        waveform = temporal_waveforms[i, :, :]
        start_frame = int(epochs_temporal[i][0])
        end_frame = int(epochs_temporal[i][1])
        peak_frame = int(temporal_peaks[i])
        
        all_events.append({
            'type': 'temporal',
            'start_frame': start_frame,
            'end_frame': end_frame,
            'peak_frame': peak_frame,
            'start_time': start_frame/fps if fps else None,
            'end_time': end_frame/fps if fps else None,
            'peak_time': peak_frame/fps if fps else None,
            'waveform': waveform
        })
    
    # Process noise waveforms
    for i in range(noise_waveforms.shape[0]):
        waveform = noise_waveforms[i, :]
        
        all_events.append({
            'type': 'noise',
            'waveform': waveform,
            # Noise waveforms don't have associated epochs or peaks
            'start_frame': None,
            'end_frame': None,
            'peak_frame': None,
            'start_time': None,
            'end_time': None,
            'peak_time': None
        })
    
    return {
        'all_events': all_events,
        'total_events': len(all_events),
        'counts': {
            'nasal': nasal_waveforms.shape[0],
            'temporal': temporal_waveforms.shape[0],
            'noise': noise_waveforms.shape[0]
        },
        'fps': fps
    }

# Example usage
if __name__ == "__main__":
    data = extract_all_frames()
    
    print(f"\nTotal events found: {data['total_events']}")
    print("\nBreakdown:")
    print(f"Nasal saccades: {data['counts']['nasal']}")
    print(f"Temporal saccades: {data['counts']['temporal']}")
    print(f"Noise events: {data['counts']['noise']}")
    print(f"FPS: {data['fps']}")
    
    # Print example of each type
    print("\nExample events:")
    for event_type in ['nasal', 'temporal', 'noise']:
        event = next(e for e in data['all_events'] if e['type'] == event_type)
        print(f"\n{event_type.capitalize()} event:")
        print(f"  Start frame: {event['start_frame']}")
        print(f"  End frame: {event['end_frame']}")
        print(f"  Peak frame: {event['peak_frame']}")
        print(f"  Waveform shape: {event['waveform'].shape}")