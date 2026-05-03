# SpineSlicerUS Usage Guide

## Overview
`SpineSlicerUS` is a 3D Slicer module for live ultrasound-based spine reconstruction.
It is designed to:

- Receive live ultrasound and transforms from OpenIGTLink
- Reconstruct a 3D volume from streamed prediction frames
- Display the reconstructed volume in 3D
- Record synchronized streams for later review

This guide is written for intermediate Slicer users who already know basic scene and node operations.

## Before You Start

### Prerequisites
1. Install 3D Slicer (5.x recommended).
2. Make sure the `SpineSlicerUS` module path is added in Slicer settings.
3. Prepare a scene (or live stream) that provides the expected node names:
   - `Image_Image` (input ultrasound image)
   - `Prediction` (segmentation/prediction stream)
   - `ProbeToReference` or `ImageToProbe` (probe transform)
   - `PredToReference` (prediction transform)
   - `VolumeReconstruction` (reconstruction node)
4. If using live acquisition, prepare OpenIGTLink connectors in the scene:
   - `PlusConnector` (commonly using port `18944`)
   - `PredictionConnector` (commonly using port `18945`)

### Open the Module
1. Start 3D Slicer.
2. Open `Modules -> Ultrasound -> SpineSlicerUS`.
3. Confirm the module loads with these sections:
   - `Record a Sequence`
   - `Scene Nodes and Transforms`
   - `Outputs`
   - `Advanced`

## Step-by-Step: Live Reconstruction

### Step 1 - Load or prepare your scene
1. Load your prepared scene (`.mrb`) or connect your data source.
2. Open `Scene Nodes and Transforms`.
3. Verify these selectors are set correctly:
   - `Input image` -> `Image_Image`
   - `Prediction volume` -> `Prediction`
   - `Probe / ImageToProbe` -> your probe transform
   - `Volume reconstructor` -> `VolumeReconstruction`
4. Expected result: all required selectors are populated and not empty.

### Step 2 - Verify incoming image stream
1. Go to the Red slice view.
2. Confirm `Image_Image` updates frame-by-frame.
3. Expected result: live ultrasound is visible in Red view.

### Step 3 - Start OpenIGTLink connections
1. In `Outputs`, click `Start OpenIGTLink connection`.
2. Expected result: button remains checked (active).
3. If the button turns off immediately, your connector nodes are missing or not configured.

### Step 4 - Set reconstruction ROI and orientation
1. Click `Set ROI and orientation`.
2. Expected result: reconstruction ROI is recentered to the current image position.

### Step 5 - Start reconstruction
1. Click `Start reconstruction`.
2. Expected result:
   - Button text changes to `Stop volume reconstruction`
   - Reconstructed output updates in 3D as new frames arrive

### Step 6 - Tune visualization
1. Adjust `Volume opacity` to improve visibility in 3D.
2. (Optional) Toggle `Spine (Class 1)` on/off to show or hide segmentation-style rendering.
3. (Optional) In `Advanced`, adjust `Blur sigma (mm)` and click `Blur current volume`.
4. Expected result: 3D rendering becomes easier to interpret for your data quality.

### Step 7 - Stop reconstruction safely
1. Click `Stop volume reconstruction` when done.
2. If needed, uncheck `Start OpenIGTLink connection` to stop streaming connectors.
3. Expected result: reconstruction and connector activity stop cleanly.

## Step-by-Step: Recording a Sequence

Use this workflow when you want to save synchronized transforms and volumes.

### Step 1 - Set participant and output location
1. In `Record a Sequence`, set `Participant ID`.
2. Set `Output folder`.
3. If no output folder is set, default is:
   - `~/Documents/SpineUSRecordings`

### Step 2 - Choose whether to record labelmap predictions (optional)
1. In `Outputs`, enable `Record Predictions as LabelMap` if required.
2. Expected result: prediction labelmap snapshots are added to recorded synchronized nodes.

### Step 3 - Initialize recording
1. Click `Initialize recording`.
2. Expected result:
   - A sequence browser is created for the current participant ID (3-digit format, e.g. `001`)
   - Sequence browser widgets become linked to that browser
   - Recording proxies are configured for available synchronized nodes

### Step 4 - Acquire data
1. Keep your stream running and perform your scan.
2. Use the sequence browser controls to monitor timeline growth.
3. Expected result: frames are accumulated while the stream updates.

### Step 5 - Save to disk
1. Click `Save recording to file`.
2. Expected result: files are written under:
   - `<OutputFolder>/<ParticipantID>/`
3. Typical saved outputs include:
   - `<ParticipantID>.mrml` (sequence browser)
   - `<ParticipantID>_<NodeName>.seq.nrrd` (synchronized sequence nodes)
   - `<ParticipantID>_metadata.json`

## Controls Reference

- `Initialize recording`: Create and prepare the sequence browser for the selected participant.
- `Save recording to file`: Stop recording state and save the sequence bundle to disk.
- `Input image`: Select live/scalar input volume (usually `Image_Image`).
- `Prediction volume`: Select prediction volume used for reconstruction input.
- `Probe / ImageToProbe`: Select probe transform driving spatial placement.
- `Volume reconstructor`: Select reconstruction node used by live volume reconstruction.
- `Volume opacity`: Adjust rendered volume transfer function response.
- `Spine (Class 1)`: Toggle segmentation-style rendering visibility.
- `Start OpenIGTLink connection`: Start/stop both configured connectors.
- `Set ROI and orientation`: Recenter reconstruction ROI on current image location.
- `Record Predictions as LabelMap`: Include prediction labelmap stream in sequence recording.
- `Start reconstruction` / `Stop volume reconstruction`: Toggle live volume reconstruction.
- `Blur current volume`: Create a blurred copy of current reconstructed output.
- `Blur sigma (mm)`: Control blur strength used by `Blur current volume`.

## Troubleshooting

### Symptom: `Start OpenIGTLink connection` will not stay enabled
- Confirm connector nodes named `PlusConnector` and `PredictionConnector` exist in the scene.
- Confirm connector endpoints are configured correctly in OpenIGTLink settings.
- Confirm external sender(s) are running.

### Symptom: No ultrasound in Red view
- Confirm `Input image` is set to `Image_Image` (or valid live scalar volume).
- Confirm live stream is active and node is updating.
- Confirm transform and stream device names match your acquisition setup.

### Symptom: Reconstruction does not start or update
- Confirm `Volume reconstructor` is selected.
- Confirm prediction stream (`Prediction`) is receiving data.
- Click `Set ROI and orientation` and retry.
- Check Slicer Python console logs for missing node warnings.

### Symptom: Save says no active recording
- Click `Initialize recording` first.
- Confirm `Input image` exists before initialization.
- Ensure stream has run long enough to accumulate frames.

### Symptom: Save says no frames recorded
- Verify incoming stream changed over time after initialization.
- Confirm synchronized nodes are present in the sequence browser.
- Reinitialize recording and scan again.

## Quick Verification Checklist

- OpenIGTLink button stays checked after enabling.
- Red view shows live `Image_Image`.
- Reconstruction button toggles to `Stop volume reconstruction`.
- 3D view updates during streaming.
- `Initialize recording` creates a sequence browser for your participant.
- `Save recording to file` writes `.mrml`, `.seq.nrrd`, and metadata outputs.

## Notes
- This module expects scene consistency. If selectors are empty, set them manually in `Scene Nodes and Transforms`.
- For technical details and latest behavior, refer to `SpineSlicerUS.py`.
